"""
MODULE 35 — Applies a generated technical-issue fix to the real CMS.

Companion to ai/seo/issue_remediation.py: that module only ever reads
the live page and calls the LLM factory; this module is where an actual
write to the real site happens, and only for the three rules module 28
and 35 both scoped as safe (see issue_remediation.py's docstring for
why the rest — broken links, redirect chains, crawl depth, robots.txt,
hreflang — stay manual-fix-only).

Two things this module refuses to do quietly:

1. Guess which CMS post a crawled URL belongs to. A technical issue only
   carries a URL, not a CMS post ID, so find_post_by_url() searches both
   list_posts() and list_pages() for an exact link match and gives up
   (rather than guessing the "closest" one) if it can't find one at all
   — verified live that this distinction is real, not theoretical: a
   real WordPress business site's missing-meta-description issues were
   all on ordinary Pages (About, Contact, Packages), which a posts-only
   search never found.

2. Assume a write succeeded. meta-based fixes (missing_meta_description,
   missing_canonical) go through an SEO plugin's own postmeta field
   (Yoast's, RankMath's — tried together since there's no reliable way
   to detect which one, if either, a site runs from the REST API
   alone), and WordPress silently drops a meta key nothing has
   registered for REST access rather than erroring. apply_fix always
   re-reads the post after writing and only reports success if the new
   value is actually confirmed present.
"""
import logging
import re
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse

from automation.seo.cms.base import CmsClient, CmsPost

logger = logging.getLogger(__name__)

MAX_POST_SEARCH_PAGES = 5  # 5 pages * 100/page = 500 posts before giving up

# Tried together on every meta-based fix since the REST API gives no
# reliable signal of which SEO plugin (if any) a WordPress site runs.
# WordPress ignores a meta key nothing has registered for REST access,
# so trying an inapplicable plugin's key is a no-op, not a risk.
_META_DESCRIPTION_KEYS = ("_yoast_wpseo_metadesc", "rank_math_description")
_CANONICAL_KEYS = ("_yoast_wpseo_canonical", "rank_math_canonical_url")


@dataclass
class ApplyFixResult:
    ok: bool
    detail: str
    # True specifically when apply_fix failed because no CMS post/page
    # matches the URL at all (not any other kind of failure) — lets a
    # caller with Server Access credentials for the site retry via
    # apply_fix_to_static_file below instead of just giving up.
    not_found: bool = False


def find_post_by_url(client: CmsClient, url: str) -> Optional[CmsPost]:
    """Never raises — returns None if nothing matches or the search
    itself fails, same graceful-degrade convention as the rest of this
    package. Searches every status, not just 'publish', so a page
    that's still a draft is still findable. Tries Posts before Pages —
    an arbitrary but stable order, since a URL can't be both."""
    for lister in (client.list_posts, client.list_pages):
        for status in ("publish", "draft", "pending", "future"):
            for page_num in range(1, MAX_POST_SEARCH_PAGES + 1):
                items = lister(status=status, per_page=100, page=page_num)
                if not items:
                    break
                for item in items:
                    if item.link and item.link.rstrip("/") == url.rstrip("/"):
                        return item
    return None


def apply_fix(client: CmsClient, rule: str, url: str, fix_value: str) -> ApplyFixResult:
    """Never raises — always returns an ApplyFixResult, matching this
    codebase's graceful-degrade convention. Callers (api/routes/seo.py)
    are responsible for only calling this once a human has approved the
    underlying issue — this function itself has no approval gate."""
    post = find_post_by_url(client, url)
    if post is None:
        return ApplyFixResult(
            ok=False,
            not_found=True,
            detail=f"Couldn't find a CMS post or page matching {url} — it may already be unpublished.",
        )

    if rule == "duplicate_title":
        result = client.update_post(post.id, title=fix_value, kind=post.kind)
        if not result.ok:
            return ApplyFixResult(ok=False, detail=result.detail)
        refetched = client.get_post(post.id, kind=post.kind)
        if refetched is not None and refetched.title.strip() == fix_value.strip():
            return ApplyFixResult(ok=True, detail=f"Title updated on {post.kind} {post.id}")
        return ApplyFixResult(ok=False, detail="Update call succeeded but the new title wasn't confirmed on re-read")

    if rule == "missing_meta_description":
        result = client.update_post(post.id, meta={k: fix_value for k in _META_DESCRIPTION_KEYS}, kind=post.kind)
        return _verify_meta_write(client, post, result, _META_DESCRIPTION_KEYS, fix_value, "meta description")

    if rule == "missing_canonical":
        result = client.update_post(post.id, meta={k: fix_value for k in _CANONICAL_KEYS}, kind=post.kind)
        return _verify_meta_write(client, post, result, _CANONICAL_KEYS, fix_value, "canonical URL")

    return ApplyFixResult(ok=False, detail=f"{rule!r} has no apply implementation")


def _verify_meta_write(
    client: CmsClient, post: CmsPost, write_result, keys: tuple, expected_value: str, label: str
) -> ApplyFixResult:
    if not write_result.ok:
        return ApplyFixResult(ok=False, detail=write_result.detail)

    echoed = write_result.meta or {}
    if any((echoed.get(k) or "").strip() == expected_value.strip() for k in keys):
        return ApplyFixResult(ok=True, detail=f"{label} set via {client.name}'s SEO plugin meta fields")

    # The PATCH response didn't confirm it — treat as not applied rather
    # than assume a round-trip quirk, since the far more likely
    # explanation is simply that no SEO plugin exposing these keys for
    # REST access is active on this site.
    logger.warning(
        "issue_applier: %s meta not confirmed in update response for %s %s — treating as not applied",
        label, post.kind, post.id,
    )
    return ApplyFixResult(
        ok=False,
        detail=(
            f"Wrote {label} but this site didn't confirm it — most likely no SEO plugin exposing "
            f"{', '.join(keys)} for REST access is active here. Nothing else was changed."
        ),
    )


def remote_path_for_url(url: str) -> str:
    """The URL's own path is the file's path relative to wherever the
    site's Server Access connection is rooted — verified true for a real
    site this session (webpays.com's FTP root IS its web document root:
    the URL path /casino-merchant-account-netherlands.html is literally
    /casino-merchant-account-netherlands.html over FTP, no public_html/
    prefix needed). A site whose connection is rooted somewhere else will
    get a clear file-not-found error from the read below rather than a
    silent wrong write — this never guesses a prefix to prepend."""
    path = urlparse(url).path
    if not path or path == "/":
        return "/index.html"
    return path


def _replace_title_tag(html: str, new_title: str) -> tuple:
    pattern = re.compile(r"<title[^>]*>.*?</title>", re.IGNORECASE | re.DOTALL)
    if not pattern.search(html):
        return html, False
    # A function replacement (not a plain string) so nothing in fix_value
    # (e.g. a literal backslash) is misread as a regex backreference.
    return pattern.sub(lambda m: f"<title>{new_title}</title>", html, count=1), True


def _upsert_meta_tag(html: str, name: str, content_value: str) -> tuple:
    escaped_value = content_value.replace('"', "&quot;")
    pattern = re.compile(rf'<meta\s+name=["\']{re.escape(name)}["\']\s+content=["\'][^"\']*["\']\s*/?>', re.IGNORECASE)
    if pattern.search(html):
        return pattern.sub(lambda m: f'<meta name="{name}" content="{escaped_value}">', html, count=1), True
    head_close = re.search(r"</head>", html, re.IGNORECASE)
    if not head_close:
        return html, False
    insertion = f'  <meta name="{name}" content="{escaped_value}">\n'
    idx = head_close.start()
    return html[:idx] + insertion + html[idx:], True


def _upsert_canonical_tag(html: str, canonical_url: str) -> tuple:
    pattern = re.compile(r'<link\s+rel=["\']canonical["\']\s+href=["\'][^"\']*["\']\s*/?>', re.IGNORECASE)
    if pattern.search(html):
        return pattern.sub(lambda m: f'<link rel="canonical" href="{canonical_url}">', html, count=1), True
    head_close = re.search(r"</head>", html, re.IGNORECASE)
    if not head_close:
        return html, False
    insertion = f'  <link rel="canonical" href="{canonical_url}">\n'
    idx = head_close.start()
    return html[:idx] + insertion + html[idx:], True


def apply_fix_to_static_file(server_client, url: str, rule: str, fix_value: str) -> ApplyFixResult:
    """Direct file-level fix for pages that aren't real CMS posts/pages at
    all — a genuine case, not a hypothetical: webpays.com's landing pages
    (index.php, casino-merchant-account-netherlands.html, and more) are
    static files sitting directly in the web root with no wp-content/
    wp-admin alongside them, so find_post_by_url correctly finds nothing
    for them — there's truly no WordPress post backing these URLs, not a
    matching bug. This edits the file's raw HTML over the site's Server
    Access (SFTP/FTP/FTPS) connection instead, with the same
    write-then-re-read-to-confirm discipline as apply_fix above."""
    remote_path = remote_path_for_url(url)
    try:
        content = server_client.read_file(remote_path)
    except Exception as exc:
        return ApplyFixResult(ok=False, detail=f"Couldn't read {remote_path} over the server connection: {exc}")

    if rule == "duplicate_title":
        new_content, changed = _replace_title_tag(content, fix_value)
    elif rule == "missing_meta_description":
        new_content, changed = _upsert_meta_tag(content, "description", fix_value)
    elif rule == "missing_canonical":
        new_content, changed = _upsert_canonical_tag(content, fix_value)
    else:
        return ApplyFixResult(ok=False, detail=f"{rule!r} has no static-file apply implementation")

    if not changed:
        return ApplyFixResult(ok=False, detail=f"Couldn't find the right tag to edit in {remote_path} (no <head> found)")

    try:
        server_client.write_file(remote_path, new_content)
    except Exception as exc:
        return ApplyFixResult(ok=False, detail=f"Write failed for {remote_path}: {exc}")

    try:
        reread = server_client.read_file(remote_path)
    except Exception as exc:
        return ApplyFixResult(ok=False, detail=f"Write succeeded but re-read failed to confirm: {exc}")

    if fix_value.strip() in reread:
        return ApplyFixResult(ok=True, detail=f"Updated directly in {remote_path} over the server connection")
    return ApplyFixResult(ok=False, detail="Write call succeeded but the new value wasn't confirmed on re-read")
