"""
MODULE 28.1 — Site crawler.

A same-origin-only crawler over `requests` + BeautifulSoup: starts at a
site's base URL, follows internal <a href> links breadth-first up to
max_pages, and returns each page's status code, HTML, and outbound
internal links for automation/seo/technical_audit.py's detectors to
analyse. Not Scrapy — a full crawling framework is overkill for "check a
few hundred pages a few times a week"; a small BFS loop over the same
requests/bs4 stack already used elsewhere in this package keeps things
simple, matching this codebase's lean-dependency style.
"""
import logging
import time
import urllib.parse
from collections import deque
from dataclasses import dataclass, field
from typing import List, Optional, Set

import requests
from bs4 import BeautifulSoup

from automation.seo.url_safety import UnsafeUrlError, assert_public_url

logger = logging.getLogger(__name__)

TIMEOUT_SECONDS = 15
USER_AGENT = "WorkPulseAI-SEO-Agent/1.0 (+https://workpulse.ai)"
DEFAULT_MAX_PAGES = 100
CRAWL_DELAY_SECONDS = 0.5  # be a polite crawler, not a hammer


@dataclass
class RedirectHop:
    url: str
    status_code: int


@dataclass
class CrawledPage:
    url: str
    status_code: Optional[int]
    html: Optional[str]
    internal_links: List[str] = field(default_factory=list)
    error: Optional[str] = None
    # Clicks from the crawl's start_url, via the shortest BFS path found —
    # feeds technical_audit.py's crawl-depth check.
    depth: int = 0
    # Hops (each with the redirecting response's own status code) taken
    # before landing on `url`/`status_code` above; empty means no redirect
    # happened. `requests` follows redirects transparently (allow_redirects=
    # True), so without this the crawler would have no way to tell a
    # direct 200 apart from one reached only after a multi-hop chain —
    # feeds technical_audit.py's redirect-chain check.
    redirect_chain: List[RedirectHop] = field(default_factory=list)


def _normalize_url(url: str, base_netloc: str) -> Optional[str]:
    """Strips fragments/query noise for dedup purposes, keeps only
    same-origin http(s) URLs — returns None for anything external,
    mailto:, javascript:, etc."""
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme not in ("http", "https", ""):
        return None
    if parsed.netloc and parsed.netloc != base_netloc:
        return None
    path = parsed.path or "/"
    normalized = urllib.parse.urlunsplit(
        (parsed.scheme or "https", parsed.netloc or base_netloc, path, parsed.query, "")
    )
    return normalized.rstrip("/") or normalized


def crawl_site(base_url: str, max_pages: int = DEFAULT_MAX_PAGES) -> List[CrawledPage]:
    """Breadth-first same-origin crawl. Never raises — a page that fails
    to fetch is recorded with its error rather than aborting the whole
    crawl, so one broken URL doesn't hide every other finding."""
    # Defense in depth against DNS rebinding: the site's base_url was
    # already validated at registration time (api/routes/seo.py's
    # create_site), but re-checking here catches a hostname that's since
    # been repointed at an internal address — see url_safety.py's module
    # docstring for why this isn't also done per-page during the crawl.
    try:
        assert_public_url(base_url)
    except UnsafeUrlError as exc:
        logger.error("crawl_site: refusing unsafe base_url %r: %s", base_url, exc)
        return []

    base_netloc = urllib.parse.urlsplit(base_url).netloc
    start_url = _normalize_url(base_url, base_netloc)
    if start_url is None:
        logger.error("crawl_site: invalid base_url %r", base_url)
        return []

    visited: Set[str] = set()
    queued: Set[str] = {start_url}
    queue: deque = deque([(start_url, 0)])
    pages: List[CrawledPage] = []
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    while queue and len(pages) < max_pages:
        url, depth = queue.popleft()
        if url in visited:
            continue
        visited.add(url)

        try:
            response = session.get(url, timeout=TIMEOUT_SECONDS, allow_redirects=True)
            redirect_chain = [RedirectHop(url=r.url, status_code=r.status_code) for r in response.history]
            html = response.text if "text/html" in response.headers.get("Content-Type", "") else None
            internal_links: List[str] = []
            if html:
                soup = BeautifulSoup(html, "html.parser")
                for a in soup.find_all("a", href=True):
                    linked = _normalize_url(urllib.parse.urljoin(url, a["href"]), base_netloc)
                    if linked is None:
                        continue
                    internal_links.append(linked)
                    if linked not in visited and linked not in queued:
                        queue.append((linked, depth + 1))
                        queued.add(linked)
            pages.append(
                CrawledPage(
                    url=url,
                    status_code=response.status_code,
                    html=html,
                    internal_links=internal_links,
                    depth=depth,
                    redirect_chain=redirect_chain,
                )
            )
        except requests.RequestException as exc:
            logger.warning("Crawl failed for %s: %s", url, exc)
            pages.append(CrawledPage(url=url, status_code=None, html=None, error=str(exc), depth=depth))

        time.sleep(CRAWL_DELAY_SECONDS)

    logger.info("Crawled %d page(s) starting from %s", len(pages), base_url)
    return pages


def fetch_sitemap_urls(base_url: str) -> List[str]:
    """Fetches /sitemap.xml and extracts every <loc> URL. This is the
    second, independent discovery source detect_orphaned_pages needs — a
    pure link-following crawl can never find a page nothing links to by
    definition, so sitemap.xml (which lists pages regardless of whether
    anything on-site links to them) is what makes that check possible at
    all. Never raises — returns an empty list if there's no sitemap or
    it can't be fetched/parsed."""
    sitemap_url = base_url.rstrip("/") + "/sitemap.xml"
    try:
        response = requests.get(sitemap_url, timeout=TIMEOUT_SECONDS, headers={"User-Agent": USER_AGENT})
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.info("No usable sitemap at %s (%s)", sitemap_url, exc)
        return []

    # A plain regex over <loc>...</loc> rather than an XML parser: this
    # codebase deliberately avoids adding lxml, and sitemap.xml's format
    # is regular enough that this is reliable without one.
    import re

    return re.findall(r"<loc>\s*(.*?)\s*</loc>", response.text, re.IGNORECASE)
