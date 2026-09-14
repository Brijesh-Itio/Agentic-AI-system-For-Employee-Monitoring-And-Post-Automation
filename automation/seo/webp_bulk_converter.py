"""
MODULE 39 — Bulk CMS image-to-WebP conversion.

Scans every post/page already published through this site's CMS, finds
JPG/PNG images referenced in <img src> and <img srcset>, downloads each
one, converts it to WebP (automation/seo/webp_converter.py — the same
converter ai/seo/image_pipeline.py uses for newly-generated images, just
applied here to images that already exist in published content), uploads
the WebP alongside the original (never deletes/overwrites the source
file — this is additive, not destructive), and rewrites the post's HTML
to point at the new WebP URLs.

Design choices, each because of something that would otherwise bite:
- Reads/writes through CmsClient.get_post_raw_content, not get_post's
  rendered HTML — see base.py's docstring on why: writing rendered HTML
  back would silently convert a Gutenberg block-editor post into a
  classic-HTML one.
- Every source URL's conversion result is cached in seo_webp_conversions
  (site_id + original_url) — a second run, or the same image appearing
  in many posts/srcset variants, is a cache hit, not duplicate network/
  upload work. This is what makes the job safe to re-run at all.
- A post's original raw content is snapshotted into seo_content_backups
  immediately before it's overwritten, every time — cheap, always on,
  not an opt-in flag, since there's no real cost to keeping it and a
  real cost to a bad rewrite with no way back.
- dry_run (the default) reports exactly what a real run would do —
  images found, which are cached vs new, which posts would change —
  without downloading, uploading, or writing anything.
- Only same-site images are touched (hotlinked third-party images are
  left alone — this app has no business rewriting someone else's URLs,
  and no way to upload to a server it doesn't have access to).
"""
import logging
import re
import time
import urllib.parse
from dataclasses import dataclass, field
from typing import List, Optional

import requests
from bs4 import BeautifulSoup

from agent import database
from ai.seo.image_pipeline import resolve_web_root_prefix
from automation.seo.cms.base import CmsClient
from automation.seo.server_access import client_for_site
from automation.seo.webp_converter import convert_to_webp

logger = logging.getLogger(__name__)

IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png")
TIMEOUT_SECONDS = 30
FETCH_PAGE_SIZE = 100  # posts/pages per CMS list call — see scan_site_images's own note on pagination


@dataclass
class PostConversionDetail:
    post_id: str
    kind: str
    title: str
    image_urls_found: List[str] = field(default_factory=list)
    images_converted: int = 0
    images_cached: int = 0
    images_failed: int = 0
    content_changed: bool = False
    updated: bool = False
    backup_id: Optional[int] = None
    error: Optional[str] = None


@dataclass
class BulkConvertReport:
    dry_run: bool
    posts_scanned: int = 0
    posts_with_images: int = 0
    posts_updated: int = 0
    images_found: int = 0
    images_converted: int = 0
    images_cached: int = 0
    images_failed: int = 0
    error: Optional[str] = None
    details: List[PostConversionDetail] = field(default_factory=list)


def _is_convertible(url: str) -> bool:
    path = urllib.parse.urlsplit(url).path.lower()
    return path.endswith(IMAGE_EXTENSIONS)


def _is_same_site(url: str, site_netloc: str) -> bool:
    return urllib.parse.urlsplit(url).netloc == site_netloc


def _extract_image_urls(html: str) -> List[str]:
    """Every distinct convertible URL referenced by <img src> or <img
    srcset> in this content, in document order, de-duplicated. srcset
    is "url1 300w, url2 600w" or "url1 1x, url2 2x" — each comma-
    separated entry is "URL descriptor"; only the URL is extracted."""
    soup = BeautifulSoup(html, "html.parser")
    urls: List[str] = []
    seen = set()

    def _add(url: Optional[str]):
        if url and url not in seen:
            seen.add(url)
            urls.append(url)

    for img in soup.find_all("img"):
        _add(img.get("src"))
        srcset = img.get("srcset")
        if srcset:
            for entry in srcset.split(","):
                parts = entry.strip().split()
                if parts:
                    _add(parts[0])

    return [u for u in urls if _is_convertible(u)]


def _rewrite_content(html: str, url_map: dict) -> str:
    """Replaces every occurrence of a converted URL in <img src>/
    <img srcset> with its new WebP URL, preserving srcset's width/
    density descriptors exactly as they were. Only touches <img> tag
    attributes — never a blind string replace across the whole
    document, so a URL that happens to also appear in visible text
    (a caption mentioning a filename, say) is left alone."""
    soup = BeautifulSoup(html, "html.parser")
    changed = False

    for img in soup.find_all("img"):
        src = img.get("src")
        if src in url_map:
            img["src"] = url_map[src]
            changed = True

        srcset = img.get("srcset")
        if srcset:
            new_entries = []
            entry_changed = False
            for entry in srcset.split(","):
                stripped = entry.strip()
                if not stripped:
                    continue
                parts = stripped.split()
                url = parts[0]
                descriptor = f" {parts[1]}" if len(parts) > 1 else ""
                if url in url_map:
                    new_entries.append(f"{url_map[url]}{descriptor}")
                    entry_changed = True
                else:
                    new_entries.append(stripped)
            if entry_changed:
                img["srcset"] = ", ".join(new_entries)
                changed = True

    return str(soup) if changed else html


def _convert_one_image(site, server_client, web_root_prefix: str, url: str) -> tuple[Optional[str], bool, Optional[str]]:
    """Returns (webp_url, was_cached, error). Checks the cache first;
    on a miss, downloads, converts, and uploads into the SAME directory
    the original lives in (just swapping the file extension) so the
    new file sits alongside the original rather than in some unrelated
    uploads folder — a caption/lightbox/CDN rule scoped to that
    directory keeps working."""
    cached = database.get_cached_webp_conversion(site.id, url)
    if cached:
        return cached, True, None

    try:
        response = requests.get(url, timeout=TIMEOUT_SECONDS)
        response.raise_for_status()
        original_bytes = response.content
    except Exception as exc:
        return None, False, f"Download failed: {exc}"

    webp = convert_to_webp(original_bytes)
    if webp is None:
        return None, False, "WebP conversion failed — corrupt or unsupported image"

    parsed = urllib.parse.urlsplit(url)
    original_path = parsed.path
    webp_path = re.sub(r"\.(jpe?g|png)$", ".webp", original_path, flags=re.IGNORECASE)
    remote_path = f"{web_root_prefix}{webp_path}".replace("//", "/")
    remote_dir = remote_path.rsplit("/", 1)[0]

    try:
        server_client.mkdir_p(remote_dir)
        server_client.write_binary_file(remote_path, webp.webp_bytes)
    except Exception as exc:
        logger.exception("Bulk WebP upload to %s failed for site %s", remote_path, site.id)
        return None, False, f"Upload failed: {exc}"

    webp_url = urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, webp_path, "", ""))
    database.save_webp_conversion(site.id, url, webp_url, len(original_bytes), len(webp.webp_bytes))
    return webp_url, False, None


def _resolve_web_root_for_site(site, server_client) -> Optional[str]:
    url_for_path = getattr(site, "cms_base_url", None) or site.base_url
    cms_url_path = urllib.parse.urlsplit(url_for_path).path.rstrip("/")
    return resolve_web_root_prefix(server_client, cms_url_path)


def _process_post(
    site, cms_client: CmsClient, server_client, web_root_prefix: Optional[str], item, site_netloc: str, *, dry_run: bool
) -> Optional[PostConversionDetail]:
    """The actual per-post work, shared by both scan_site_images (looped
    over every post) and convert_url_images (one specific post resolved
    from a URL) — everything about how a single post gets scanned/
    converted/rewritten lives here exactly once. Returns None if the
    post has no convertible same-site images at all (nothing to report)."""
    raw_content = cms_client.get_post_raw_content(item.id, kind=item.kind)
    if raw_content is None:
        return None

    found = [u for u in _extract_image_urls(raw_content) if _is_same_site(u, site_netloc)]
    if not found:
        return None

    detail = PostConversionDetail(post_id=item.id, kind=item.kind, title=item.title, image_urls_found=found)

    if dry_run:
        for url in found:
            if database.get_cached_webp_conversion(site.id, url):
                detail.images_cached += 1
        return detail

    url_map = {}
    for url in found:
        webp_url, was_cached, error = _convert_one_image(site, server_client, web_root_prefix, url)
        if webp_url:
            url_map[url] = webp_url
            if was_cached:
                detail.images_cached += 1
            else:
                detail.images_converted += 1
        else:
            detail.images_failed += 1
            logger.warning("Skipping unconvertible image %s in %s %s: %s", url, item.kind, item.id, error)

    if url_map:
        new_content = _rewrite_content(raw_content, url_map)
        if new_content != raw_content:
            detail.content_changed = True
            detail.backup_id = database.save_content_backup(site.id, item.id, item.kind, "webp_convert", raw_content)
            result = cms_client.update_post(item.id, content=new_content, kind=item.kind)
            if result.ok:
                detail.updated = True
            else:
                detail.error = result.detail

    return detail


def _accumulate(report: BulkConvertReport, detail: PostConversionDetail) -> None:
    report.posts_with_images += 1
    report.images_found += len(detail.image_urls_found)
    report.images_cached += detail.images_cached
    report.images_converted += detail.images_converted
    report.images_failed += detail.images_failed
    if detail.updated:
        report.posts_updated += 1
    report.details.append(detail)


def convert_url_images(site, cms_client: CmsClient, url: str, *, dry_run: bool = True) -> BulkConvertReport:
    """Module 39 follow-up — the per-URL alternative to scanning the
    whole site: resolves one specific page URL to its actual CMS post
    (CmsClient.find_post_by_url) and runs the exact same conversion
    logic scan_site_images uses, just for that one post. Same caching,
    same backup-before-rewrite, same dry-run default. Reports
    posts_scanned=1 with error set if the URL couldn't be resolved to
    any post/page on this site, so the caller sees a clear reason
    rather than a silently-empty report."""
    report = BulkConvertReport(dry_run=dry_run)

    item = cms_client.find_post_by_url(url)
    if item is None:
        report.error = f"Could not find a post/page on this site matching {url!r} — check the URL is correct and on this site's domain."
        return report
    report.posts_scanned = 1

    server_client = client_for_site(site) if not dry_run else None
    if not dry_run and server_client is None:
        report.error = "No server access configured for this site — add SFTP/FTP credentials in the Server Access tab."
        return report

    web_root_prefix = None
    if not dry_run:
        web_root_prefix = _resolve_web_root_for_site(site, server_client)
        if web_root_prefix is None:
            report.error = "Could not find this site's actual web root on the server — check Server Access credentials."
            return report

    site_netloc = urllib.parse.urlsplit(site.base_url).netloc
    detail = _process_post(site, cms_client, server_client, web_root_prefix, item, site_netloc, dry_run=dry_run)
    if detail is None:
        report.error = "No JPG/PNG images found on this page."
        return report

    _accumulate(report, detail)
    return report


def scan_site_images(site, cms_client: CmsClient, *, dry_run: bool = True) -> BulkConvertReport:
    """The whole-site bulk job. Never raises — a per-post or per-image
    failure is recorded in the report and the job moves on; only a
    site-level problem (no server access at all) short-circuits the
    whole run, reported via BulkConvertReport.error.

    Pagination note: fetches the first FETCH_PAGE_SIZE posts/pages —
    sites with more than that need this run again to reach the rest
    (each run only ever processes what it's shown, and thanks to the
    conversion cache a repeat run just picks up where the last one's
    coverage stopped, so this is a real limitation but not a
    correctness problem)."""
    report = BulkConvertReport(dry_run=dry_run)

    server_client = client_for_site(site) if not dry_run else None
    if not dry_run and server_client is None:
        report.error = "No server access configured for this site — add SFTP/FTP credentials in the Server Access tab."
        return report

    site_netloc = urllib.parse.urlsplit(site.base_url).netloc

    web_root_prefix = None
    if not dry_run:
        web_root_prefix = _resolve_web_root_for_site(site, server_client)
        if web_root_prefix is None:
            report.error = "Could not find this site's actual web root on the server — check Server Access credentials."
            return report

    items = cms_client.list_posts(status="publish", per_page=FETCH_PAGE_SIZE) + cms_client.list_pages(
        status="publish", per_page=FETCH_PAGE_SIZE
    )

    for item in items:
        report.posts_scanned += 1
        detail = _process_post(site, cms_client, server_client, web_root_prefix, item, site_netloc, dry_run=dry_run)
        if detail is not None:
            _accumulate(report, detail)

    return report
