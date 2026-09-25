"""
Sitemap generator — builds a real, complete sitemap for a site.

The tools this replaces (free online generators) stop at ~500 URLs. This one
has no such ceiling: URLs are gathered from every source we have, merged and
de-duplicated, then written as a sitemap INDEX (sitemap.xml) pointing at
per-type child files, each split before Google's 50,000-URL / 50 MB limits:

  sitemap-pages.xml       ordinary pages
  sitemap-posts.xml       blog posts / articles
  sitemap-categories.xml  category archives
  sitemap-tags.xml        tag archives

Image and video URLs are attached to the page that shows them, using Google's
image/video sitemap extensions, so they count towards "Image URL"/"Video URL"
coverage without needing their own listing.

Discovery sources, all merged:
  1. WordPress REST API (pages, posts, categories, tags — paginated, so it
     scales to thousands of URLs and knows real modified dates)
  2. Blog posts published through this app (seo_blog_posts)
  3. Sitemap(s) the site already serves (index files are followed)
  4. A multi-threaded same-origin crawl, which VERIFIES each URL (200, not
     noindex, not a redirect) and finds pages nothing else lists

Everything here is pure (network in, XML out); storing, publishing and
scheduling live in sitemap_service.py.
"""
import hashlib
import logging
import re
import threading
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Callable, Dict, Iterable, List, Optional, Tuple
from xml.sax.saxutils import escape

import requests
from bs4 import BeautifulSoup

from automation.seo.url_safety import UnsafeUrlError, assert_public_url

logger = logging.getLogger(__name__)

TIMEOUT_SECONDS = 15
USER_AGENT = "WorkPulseAI-SEO-Agent/1.0 (+https://workpulse.ai)"
DEFAULT_MAX_CRAWL_PAGES = 5000
CRAWL_WORKERS = 8
MAX_URLS_PER_FILE = 50_000
MAX_BYTES_PER_FILE = 40 * 1024 * 1024  # under Google's 50 MB, with headroom
MAX_IMAGES_PER_URL = 25
MAX_VIDEOS_PER_URL = 5
WP_PER_PAGE = 100
WP_MAX_PAGES = 200  # 20,000 items per content type

KINDS = ("page", "post", "category", "tag")
GROUP_FILENAMES = {"page": "sitemap-pages", "post": "sitemap-posts", "category": "sitemap-categories", "tag": "sitemap-tags"}

_SKIP_PATH = re.compile(
    r"(/wp-admin|/wp-login|/wp-json|/wp-content/|/wp-includes/|/feed/?$|/xmlrpc|/cart/?$|/checkout|/my-account|"
    r"/login/?$|/logout|/register/?$|/cgi-bin|/trackback|/amp/?$|/print/?$)",
    re.IGNORECASE,
)
_SKIP_EXT = re.compile(
    r"\.(jpe?g|png|gif|webp|svg|ico|bmp|avif|pdf|zip|rar|gz|mp3|mp4|webm|mov|avi|css|js|json|xml|txt|docx?|xlsx?|pptx?|woff2?|ttf|eot)$",
    re.IGNORECASE,
)
_IMG_EXT = re.compile(r"\.(jpe?g|png|gif|webp|svg|avif|bmp)(\?.*)?$", re.IGNORECASE)
_YOUTUBE = re.compile(r"(?:youtube\.com/embed/|youtube-nocookie\.com/embed/|youtu\.be/)([A-Za-z0-9_-]{11})")
_VIMEO = re.compile(r"player\.vimeo\.com/video/(\d+)")


@dataclass
class VideoRef:
    thumbnail: str
    title: str
    description: str
    content_loc: Optional[str] = None
    player_loc: Optional[str] = None


@dataclass
class SitemapEntry:
    url: str
    kind: str = "page"  # one of KINDS
    lastmod: Optional[str] = None  # W3C datetime, e.g. 2026-09-25 or 2026-09-25T10:00:00+00:00
    images: List[str] = field(default_factory=list)
    videos: List[VideoRef] = field(default_factory=list)
    content_hash: Optional[str] = None
    source: str = "crawl"  # crawl | wordpress | blog | sitemap

    def to_json(self) -> dict:
        return {
            "url": self.url, "kind": self.kind, "lastmod": self.lastmod, "images": self.images,
            "videos": [v.__dict__ for v in self.videos], "content_hash": self.content_hash, "source": self.source,
        }

    @staticmethod
    def from_json(d: dict) -> "SitemapEntry":
        return SitemapEntry(
            url=d["url"], kind=d.get("kind", "page"), lastmod=d.get("lastmod"), images=list(d.get("images") or []),
            videos=[VideoRef(**v) for v in d.get("videos") or []], content_hash=d.get("content_hash"),
            source=d.get("source", "crawl"),
        )


ProgressFn = Callable[[str], None]


# ── helpers ──


def _now_w3c() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")


def _to_w3c(value: Optional[str]) -> Optional[str]:
    """Best-effort conversion of an ISO date or an HTTP date to W3C form."""
    if not value:
        return None
    value = value.strip()
    try:
        if re.match(r"^\d{4}-\d{2}-\d{2}", value):
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        else:
            dt = parsedate_to_datetime(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
    except Exception:
        return None


def _key(url: str) -> str:
    """Dedup key — scheme/host case and a trailing slash don't make a
    different page."""
    parts = urllib.parse.urlsplit(url)
    return f"{parts.netloc.lower()}{parts.path.rstrip('/')}"


def classify_url(url: str) -> str:
    path = urllib.parse.urlsplit(url).path.lower()
    if re.search(r"/(category|categories|cat|product-category|topics?)/", path):
        return "category"
    if re.search(r"/(tag|tags|product-tag)/", path):
        return "tag"
    if re.search(r"/(blog|news|articles?|posts?|insights|resources)/[^/]+", path) or re.search(r"/\d{4}/\d{1,2}/", path):
        return "post"
    return "page"


def _indexable_url(url: str, base_netloc: str) -> bool:
    parts = urllib.parse.urlsplit(url)
    if parts.scheme not in ("http", "https") or parts.netloc.lower() != base_netloc.lower():
        return False
    if parts.query or _SKIP_PATH.search(parts.path) or _SKIP_EXT.search(parts.path):
        return False
    return True


def _clean(url: str, base_scheme: str) -> str:
    parts = urllib.parse.urlsplit(url)
    return urllib.parse.urlunsplit((base_scheme, parts.netloc, parts.path or "/", "", ""))


def _http_get(session: requests.Session, url: str, **kw) -> requests.Response:
    return session.get(url, timeout=TIMEOUT_SECONDS, headers={"User-Agent": USER_AGENT}, **kw)


# ── media extraction ──


def _absolute(base: str, ref: Optional[str]) -> Optional[str]:
    if not ref:
        return None
    ref = ref.strip()
    if not ref or ref.startswith(("data:", "javascript:", "#")):
        return None
    return urllib.parse.urljoin(base, ref)


def extract_media(soup: BeautifulSoup, page_url: str) -> Tuple[List[str], List[VideoRef]]:
    images: List[str] = []
    seen = set()

    def add_image(ref: Optional[str]) -> None:
        url = _absolute(page_url, ref)
        if url and url.startswith(("http://", "https://")) and url not in seen and len(images) < MAX_IMAGES_PER_URL:
            seen.add(url)
            images.append(url)

    og = soup.find("meta", attrs={"property": "og:image"})
    if og and og.get("content"):
        add_image(og["content"])
    for img in soup.find_all("img"):
        src = img.get("src") or img.get("data-src") or img.get("data-lazy-src")
        if not src and img.get("srcset"):
            src = img["srcset"].split(",")[0].strip().split(" ")[0]
        # tracking pixels / icons aren't worth listing
        w, h = img.get("width", ""), img.get("height", "")
        if w.isdigit() and h.isdigit() and int(w) <= 2 and int(h) <= 2:
            continue
        add_image(src)

    title_tag = soup.find("title")
    page_title = (title_tag.get_text(strip=True) if title_tag else "") or "Video"
    desc_tag = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"})
    page_desc = (desc_tag.get("content", "").strip() if desc_tag else "") or page_title

    videos: List[VideoRef] = []
    seen_v = set()

    def add_video(v: VideoRef, ident: str) -> None:
        if ident not in seen_v and len(videos) < MAX_VIDEOS_PER_URL:
            seen_v.add(ident)
            videos.append(v)

    for tag in soup.find_all(["iframe", "embed"]):
        src = _absolute(page_url, tag.get("src") or tag.get("data-src"))
        if not src:
            continue
        m = _YOUTUBE.search(src)
        if m:
            vid = m.group(1)
            add_video(
                VideoRef(
                    thumbnail=f"https://img.youtube.com/vi/{vid}/hqdefault.jpg",
                    title=(tag.get("title") or page_title)[:100], description=page_desc[:2000],
                    player_loc=f"https://www.youtube.com/embed/{vid}",
                ),
                f"yt:{vid}",
            )
            continue
        m = _VIMEO.search(src)
        if m:
            # Vimeo has no guessable thumbnail URL — use the page's og:image if it has one.
            thumb = images[0] if images else None
            if thumb:
                add_video(
                    VideoRef(thumbnail=thumb, title=(tag.get("title") or page_title)[:100], description=page_desc[:2000],
                             player_loc=f"https://player.vimeo.com/video/{m.group(1)}"),
                    f"vm:{m.group(1)}",
                )
    for vtag in soup.find_all("video"):
        src = _absolute(page_url, vtag.get("src"))
        if not src:
            source = vtag.find("source", src=True)
            src = _absolute(page_url, source["src"]) if source else None
        thumb = _absolute(page_url, vtag.get("poster")) or (images[0] if images else None)
        if src and thumb:
            add_video(VideoRef(thumbnail=thumb, title=page_title[:100], description=page_desc[:2000], content_loc=src), f"v:{src}")
    return images, videos


# ── source 1: WordPress REST API ──


def collect_wordpress(base_url: str, session: requests.Session, progress: ProgressFn) -> List[SitemapEntry]:
    """Every published page/post/category/tag via the public REST API. Never
    raises — a site that isn't WordPress (or has the API locked down) just
    yields nothing and the other sources cover it."""
    origin = f"{urllib.parse.urlsplit(base_url).scheme}://{urllib.parse.urlsplit(base_url).netloc}"
    root = base_url.rstrip("/")
    entries: List[SitemapEntry] = []
    plan = [
        ("pages", "page", "link,modified_gmt,content"),
        ("posts", "post", "link,modified_gmt,content"),
        ("categories", "category", "link"),
        ("tags", "tag", "link"),
    ]
    for endpoint, kind, fields in plan:
        got = 0
        for page in range(1, WP_MAX_PAGES + 1):
            url = f"{root}/wp-json/wp/v2/{endpoint}?per_page={WP_PER_PAGE}&page={page}&_fields={fields}"
            try:
                resp = _http_get(session, url)
            except requests.RequestException:
                break
            if resp.status_code != 200:
                break
            try:
                items = resp.json()
            except ValueError:
                break
            if not isinstance(items, list) or not items:
                break
            for item in items:
                link = item.get("link")
                if not link or not link.startswith(origin):
                    continue
                entry = SitemapEntry(url=link, kind=kind, lastmod=_to_w3c(item.get("modified_gmt") and item["modified_gmt"] + "Z"), source="wordpress")
                rendered = (item.get("content") or {}).get("rendered")
                if rendered:
                    entry.images, entry.videos = extract_media(BeautifulSoup(rendered, "html.parser"), link)
                entries.append(entry)
            got += len(items)
            if len(items) < WP_PER_PAGE:
                break
        if got:
            progress(f"WordPress: found {got} {endpoint}")
    return entries


# ── source 3: sitemaps the site already serves ──


def read_existing_sitemaps(base_url: str, session: requests.Session, progress: ProgressFn) -> Dict[str, Optional[str]]:
    """URLs listed by sitemap(s) the site already serves (index files are
    followed, gzip is handled by requests). Only used as crawl SEEDS — a URL
    a stale sitemap still lists but the site no longer serves is dropped
    when the crawl fails to fetch it."""
    root = base_url.rstrip("/")
    candidates = [f"{root}/sitemap.xml", f"{root}/sitemap_index.xml", f"{root}/wp-sitemap.xml"]
    try:
        robots = _http_get(session, f"{urllib.parse.urlsplit(base_url).scheme}://{urllib.parse.urlsplit(base_url).netloc}/robots.txt")
        if robots.status_code == 200:
            candidates += re.findall(r"(?im)^\s*sitemap:\s*(\S+)", robots.text)
    except requests.RequestException:
        pass

    urls: Dict[str, Optional[str]] = {}
    seen_files = set()
    stack = [(c, 0) for c in candidates]
    files_read = 0
    while stack and files_read < 300:
        loc, depth = stack.pop()
        if loc in seen_files or depth > 3:
            continue
        seen_files.add(loc)
        try:
            resp = _http_get(session, loc)
            if resp.status_code != 200:
                continue
            text = resp.text
        except requests.RequestException:
            continue
        files_read += 1
        locs = [html_unescape(x) for x in re.findall(r"<loc>\s*(.*?)\s*</loc>", text, re.IGNORECASE | re.DOTALL)]
        if re.search(r"<sitemapindex", text, re.IGNORECASE):
            stack.extend((child, depth + 1) for child in locs)
        else:
            # <image:loc>/<video:*> are separate tags, not <loc>, so this reads pages only
            for block in re.findall(r"<url>(.*?)</url>", text, re.IGNORECASE | re.DOTALL):
                m_loc = re.search(r"<loc>\s*(.*?)\s*</loc>", block, re.IGNORECASE | re.DOTALL)
                m_mod = re.search(r"<lastmod>\s*(.*?)\s*</lastmod>", block, re.IGNORECASE | re.DOTALL)
                if m_loc:
                    urls[html_unescape(m_loc.group(1))] = _to_w3c(m_mod.group(1)) if m_mod else None
    if urls:
        progress(f"Existing sitemap: found {len(urls)} listed URL(s)")
    return urls


def html_unescape(s: str) -> str:
    import html

    return html.unescape(s)


# ── source 4: crawl ──


@dataclass
class _Fetched:
    entry: Optional[SitemapEntry]
    links: List[str]
    redirect_to: Optional[str] = None


def _fetch_for_sitemap(session: requests.Session, url: str, base_netloc: str, base_scheme: str) -> _Fetched:
    try:
        resp = _http_get(session, url, allow_redirects=True, stream=True)
        ctype = resp.headers.get("Content-Type", "")
        if resp.history:
            final = resp.url
            resp.close()
            if _indexable_url(final, base_netloc):
                return _Fetched(None, [], redirect_to=_clean(final, base_scheme))
            return _Fetched(None, [])
        if resp.status_code != 200 or "text/html" not in ctype:
            resp.close()
            return _Fetched(None, [])
        body = resp.content[:5 * 1024 * 1024]
        header_modified = _to_w3c(resp.headers.get("Last-Modified"))
        resp.close()
        html = body.decode(resp.encoding or "utf-8", errors="replace")
    except requests.RequestException as exc:
        logger.info("sitemap crawl: %s failed (%s)", url, exc)
        return _Fetched(None, [])

    soup = BeautifulSoup(html, "html.parser")
    robots = soup.find("meta", attrs={"name": re.compile("^robots$", re.I)})
    if robots and "noindex" in (robots.get("content") or "").lower():
        return _Fetched(None, [])
    canonical = soup.find("link", rel="canonical")
    if canonical and canonical.get("href"):
        target = _absolute(url, canonical["href"])
        if target and _key(target) != _key(url):
            # This page says another URL is the real one — list that instead (it is linked/queued on its own).
            links = [target] if _indexable_url(target, base_netloc) else []
            return _Fetched(None, links)

    links: List[str] = []
    for a in soup.find_all("a", href=True):
        href = _absolute(url, a["href"])
        if href:
            href = href.split("#")[0]
            if _indexable_url(href, base_netloc):
                links.append(_clean(href, base_scheme))

    images, videos = extract_media(soup, url)
    modified = None
    for attrs in ({"property": "article:modified_time"}, {"property": "og:updated_time"}):
        m = soup.find("meta", attrs=attrs)
        if m and m.get("content"):
            modified = _to_w3c(m["content"])
            break
    modified = modified or header_modified
    kind = classify_url(url)
    og_type = soup.find("meta", attrs={"property": "og:type"})
    is_article = bool(soup.find("meta", attrs={"property": "article:published_time"})) or (
        og_type is not None and (og_type.get("content") or "").lower() == "article"
    )
    if kind == "page" and is_article and urllib.parse.urlsplit(url).path.strip("/"):
        kind = "post"
    text = soup.get_text(" ", strip=True)
    entry = SitemapEntry(
        url=url, kind=kind, lastmod=modified, images=images, videos=videos,
        content_hash=hashlib.sha1(text.encode("utf-8", "ignore")).hexdigest(), source="crawl",
    )
    return _Fetched(entry, links)


def crawl_for_sitemap(
    base_url: str, seeds: Iterable[str], max_pages: int, session: requests.Session, progress: ProgressFn,
    should_stop: Callable[[], bool] = lambda: False,
) -> Tuple[Dict[str, SitemapEntry], set, set]:
    """Threaded breadth-first crawl. Returns (verified entries by key, keys
    that were fetched and turned out NOT to be indexable pages, keys still
    queued when the page cap was reached and so never checked)."""
    parts = urllib.parse.urlsplit(base_url)
    base_netloc, base_scheme = parts.netloc, parts.scheme
    start = _clean(base_url, base_scheme)
    queued = {_key(start)}
    frontier = [start]
    for s in seeds:
        if _indexable_url(s, base_netloc) and _key(s) not in queued:
            queued.add(_key(s))
            frontier.append(_clean(s, base_scheme))

    entries: Dict[str, SitemapEntry] = {}
    rejected: set = set()
    fetched = 0
    lock = threading.Lock()

    with ThreadPoolExecutor(max_workers=CRAWL_WORKERS) as pool:
        while frontier and fetched < max_pages and not should_stop():
            take = min(200, max_pages - fetched)
            batch, frontier = frontier[:take], frontier[take:]
            results = list(pool.map(lambda u: (u, _fetch_for_sitemap(session, u, base_netloc, base_scheme)), batch))
            fetched += len(batch)
            for url, res in results:
                if res.entry is not None:
                    with lock:
                        entries.setdefault(_key(url), res.entry)
                else:
                    rejected.add(_key(url))
                targets = list(res.links)
                if res.redirect_to:
                    targets.append(res.redirect_to)
                for link in targets:
                    k = _key(link)
                    if k not in queued:
                        queued.add(k)
                        frontier.append(link)
            progress(f"Crawled {fetched} page(s) — {len(entries)} listable, {len(frontier)} still queued")
    # Anything still queued when the page cap hit was never checked.
    unchecked = {_key(u) for u in frontier}
    return entries, rejected - set(entries), unchecked


# ── merge ──


def merge_entries(
    base_url: str, sources: List[List[SitemapEntry]], previous: Dict[str, SitemapEntry]
) -> List[SitemapEntry]:
    """Later sources fill gaps in earlier ones. `lastmod` handling for
    crawled pages: an unchanged page keeps its previous lastmod, a changed
    one (content hash differs) gets 'now' — this is what makes "an existing
    page was modified" show up without the site reporting dates itself."""
    merged: Dict[str, SitemapEntry] = {}
    for entries in sources:
        for e in entries:
            k = _key(e.url)
            cur = merged.get(k)
            if cur is None:
                merged[k] = e
                continue
            if not cur.lastmod and e.lastmod:
                cur.lastmod = e.lastmod
            if e.source in ("wordpress", "blog") and cur.source == "crawl":
                cur.kind = e.kind
            if e.content_hash and not cur.content_hash:
                cur.content_hash = e.content_hash
            for img in e.images:
                if img not in cur.images and len(cur.images) < MAX_IMAGES_PER_URL:
                    cur.images.append(img)
            known = {(v.player_loc, v.content_loc) for v in cur.videos}
            for v in e.videos:
                if (v.player_loc, v.content_loc) not in known and len(cur.videos) < MAX_VIDEOS_PER_URL:
                    cur.videos.append(v)

    now = _now_w3c()
    for k, e in merged.items():
        old = previous.get(k)
        # A first sighting keeps only a date the site really reported (or
        # none) — stamping every page "today" is what makes Google stop
        # trusting <lastmod>. 'now' is used only when a change is detected.
        if e.source == "crawl" or e.content_hash:
            if old is None:
                pass
            elif old.content_hash and e.content_hash and old.content_hash != e.content_hash:
                # changed since last run: 'now', unless the page states a newer date itself
                e.lastmod = e.lastmod if (e.lastmod and old.lastmod and e.lastmod > old.lastmod) else now
            else:
                e.lastmod = old.lastmod or e.lastmod
        else:
            e.lastmod = e.lastmod or (old.lastmod if old else None)
        if not e.content_hash and old:
            e.content_hash = old.content_hash
    out = list(merged.values())
    out.sort(key=lambda e: (e.url.count("/"), e.url))
    return out


# ── XML output ──


def _url_xml(e: SitemapEntry) -> str:
    parts = [f"  <url>\n    <loc>{escape(e.url)}</loc>"]
    if e.lastmod:
        parts.append(f"    <lastmod>{escape(e.lastmod)}</lastmod>")
    for img in e.images:
        parts.append(f"    <image:image><image:loc>{escape(img)}</image:loc></image:image>")
    for v in e.videos:
        vx = [f"    <video:video>", f"      <video:thumbnail_loc>{escape(v.thumbnail)}</video:thumbnail_loc>",
              f"      <video:title>{escape(v.title or 'Video')}</video:title>",
              f"      <video:description>{escape(v.description or v.title or 'Video')}</video:description>"]
        if v.content_loc:
            vx.append(f"      <video:content_loc>{escape(v.content_loc)}</video:content_loc>")
        if v.player_loc:
            vx.append(f"      <video:player_loc>{escape(v.player_loc)}</video:player_loc>")
        vx.append("    </video:video>")
        parts.append("\n".join(vx))
    parts.append("  </url>")
    return "\n".join(parts)


_URLSET_OPEN = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
    'xmlns:image="http://www.google.com/schemas/sitemap-image/1.1" '
    'xmlns:video="http://www.google.com/schemas/sitemap-video/1.1">\n'
)


_BLOG_INDEX = re.compile(r"^(blog|news|articles?|insights|resources)(\.html?|\.php)?$", re.IGNORECASE)


def _rank(e: SitemapEntry) -> int:
    """Priority order in the file: home page, service/other pages, the blog
    listing page, blog posts, then category and tag archives. Images and
    videos are listed inside the page that shows them, so they sit right
    under their own page in this order."""
    path = urllib.parse.urlsplit(e.url).path.strip("/")
    if e.kind == "page":
        if not path:
            return 0
        return 2 if _BLOG_INDEX.match(path) else 1
    return {"post": 3, "category": 4, "tag": 5}.get(e.kind, 1)


def order_entries(entries: List[SitemapEntry]) -> List[SitemapEntry]:
    def key(e: SitemapEntry):
        rank = _rank(e)
        # newest posts first; everything else: shallow URLs first, then alphabetical
        if rank == 3:
            return (rank, "", "".join(chr(0x10FFFF - ord(c)) for c in (e.lastmod or "")), e.url)
        return (rank, e.url.count("/"), "", e.url)

    return sorted(entries, key=key)


def build_files(base_url: str, entries: List[SitemapEntry]) -> Dict[str, str]:
    """{filename: xml}. Always includes sitemap.xml.

    Everything goes into that ONE file (pages, posts, categories, tags, with
    their images and videos) whenever it fits Google's limits — 50,000 URLs
    and 50 MB. Only a site too big for that gets the split layout: a
    sitemap.xml index pointing at per-type files."""
    ordered = order_entries(entries)
    blocks = [_url_xml(e) for e in ordered]
    if len(ordered) <= MAX_URLS_PER_FILE and sum(len(b.encode("utf-8")) + 1 for b in blocks) <= MAX_BYTES_PER_FILE:
        return {"sitemap.xml": _URLSET_OPEN + "\n".join(blocks) + ("\n" if blocks else "") + "</urlset>\n"}
    return _build_split_files(base_url, entries)


def _build_split_files(base_url: str, entries: List[SitemapEntry]) -> Dict[str, str]:
    root = base_url.rstrip("/")
    files: Dict[str, str] = {}
    child_meta: List[Tuple[str, Optional[str]]] = []

    for kind in KINDS:
        group = [e for e in entries if e.kind == kind]
        if not group:
            continue
        chunk: List[str] = []
        chunk_bytes = 0
        chunk_last = ""
        chunks: List[Tuple[List[str], str]] = []
        for e in group:
            xml = _url_xml(e)
            size = len(xml.encode("utf-8")) + 1
            if chunk and (len(chunk) >= MAX_URLS_PER_FILE or chunk_bytes + size > MAX_BYTES_PER_FILE):
                chunks.append((chunk, chunk_last))
                chunk, chunk_bytes, chunk_last = [], 0, ""
            chunk.append(xml)
            chunk_bytes += size
            chunk_last = max(chunk_last, e.lastmod or "")
        if chunk:
            chunks.append((chunk, chunk_last))
        for i, (items, last) in enumerate(chunks, start=1):
            name = GROUP_FILENAMES[kind] + (f"-{i}" if len(chunks) > 1 else "") + ".xml"
            files[name] = _URLSET_OPEN + "\n".join(items) + "\n</urlset>\n"
            child_meta.append((name, last or None))

    idx = ['<?xml version="1.0" encoding="UTF-8"?>\n<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for name, last in child_meta:
        idx.append(f"  <sitemap>\n    <loc>{escape(root + '/' + name)}</loc>" + (f"\n    <lastmod>{escape(last)}</lastmod>" if last else "") + "\n  </sitemap>")
    idx.append("</sitemapindex>\n")
    files["sitemap.xml"] = "\n".join(idx)
    return files


def summarize(entries: List[SitemapEntry], files: Dict[str, str]) -> dict:
    return {
        "total": len(entries),
        "counts": {
            "pages": sum(e.kind == "page" for e in entries),
            "posts": sum(e.kind == "post" for e in entries),
            "categories": sum(e.kind == "category" for e in entries),
            "tags": sum(e.kind == "tag" for e in entries),
            "images": sum(len(e.images) for e in entries),
            "videos": sum(len(e.videos) for e in entries),
        },
        "files": [
            {
                "name": n,
                "is_index": "<sitemapindex" in x[:400],
                "urls": x.count("<sitemap>") if "<sitemapindex" in x[:400] else x.count("<url>"),
                "bytes": len(x.encode("utf-8")),
            }
            for n, x in files.items()
        ],
    }


def discover(
    base_url: str,
    blog_entries: List[SitemapEntry],
    previous: Dict[str, SitemapEntry],
    *,
    max_crawl_pages: int = DEFAULT_MAX_CRAWL_PAGES,
    progress: ProgressFn = lambda _m: None,
    should_stop: Callable[[], bool] = lambda: False,
) -> List[SitemapEntry]:
    """Runs every discovery source and returns the merged entry list. Raises
    UnsafeUrlError only for a base_url that isn't a public address."""
    assert_public_url(base_url)
    session = requests.Session()
    try:
        progress("Reading the site's WordPress content lists…")
        wp = collect_wordpress(base_url, session, progress)
        progress("Reading any sitemap the site already has…")
        listed = read_existing_sitemaps(base_url, session, progress)

        # Everything not already known-good from the CMS is verified by the crawl.
        trusted = {_key(e.url) for e in wp} | {_key(e.url) for e in blog_entries}
        seeds = [u for u in listed if _key(u) not in trusted]
        progress("Crawling the site to verify URLs and find the rest…")
        crawled, rejected, unchecked = crawl_for_sitemap(base_url, seeds, max_crawl_pages, session, progress, should_stop)
    finally:
        session.close()

    listed_unchecked = [
        SitemapEntry(url=u, kind=classify_url(u), lastmod=listed[u], source="sitemap")
        for u in listed
        if _key(u) in unchecked and _key(u) not in rejected
    ]
    # A URL the crawl fetched and rejected (404, noindex, redirect) is dropped even if a CMS list has it
    # only when the CMS didn't vouch for it; CMS-listed URLs are published content, so they stay.
    # The site's own sitemap knows real dates for pages the pages themselves don't state.
    by_key = {_key(u): m for u, m in listed.items() if m}
    for e in crawled.values():
        if not e.lastmod and _key(e.url) in by_key and not previous.get(_key(e.url)):
            e.lastmod = by_key[_key(e.url)]
    return merge_entries(
        base_url,
        [wp, blog_entries, list(crawled.values()), listed_unchecked],
        previous,
    )
