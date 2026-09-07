"""
MODULE 28.2 — Technical SEO issue detectors.

Deterministic checks over a completed crawl (automation/seo/crawler.py)
— no LLM involved; these are structural facts about the HTML, not
judgement calls. Each TechnicalIssue carries a severity and a ready-to-
apply suggested fix, matching the blueprint's "auto-detect, human
approves before apply" design. Deliberately detect-only: nothing here
writes to the live site. Actually applying a fix (editing a canonical
tag, redirect rule, etc. on the real CMS) is out of scope for this pass
the same way module 27.3 didn't guess at SEO-plugin-specific CMS meta
fields — a wrong automatic edit to a live site's <head> is exactly the
"catastrophic misapplication" risk the blueprint itself calls out, so
apply stays a human action once a real site's plugin stack is known.
"""
import logging
import re
import urllib.parse
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup

from automation.seo.crawler import CrawledPage, USER_AGENT

logger = logging.getLogger(__name__)

ROBOTS_TXT_TIMEOUT_SECONDS = 15
# ISO 639 language[-ISO 3166 region] (e.g. "en", "en-US", "zh-Hans") or the
# special "x-default" value — the actual legal shape of an hreflang attribute.
_HREFLANG_RE = re.compile(r"^([a-zA-Z]{2,3}(-[a-zA-Z]{2,4})?(-[a-zA-Z]{2})?|x-default)$")
# Pages more than this many clicks from the homepage are considered buried
# — the common SEO guideline (important content should be crawlable/
# discoverable within a few clicks of the homepage).
DEFAULT_MAX_CRAWL_DEPTH = 3


@dataclass
class TechnicalIssue:
    rule: str
    severity: str  # "critical" | "warning" | "info"
    url: str
    message: str
    suggested_fix: str


def detect_broken_links(pages: List[CrawledPage]) -> List[TechnicalIssue]:
    status_by_url = {p.url: p.status_code for p in pages}
    issues = []
    for page in pages:
        for link in page.internal_links:
            status = status_by_url.get(link)
            if status is not None and status >= 400:
                issues.append(
                    TechnicalIssue(
                        rule="broken_link",
                        severity="critical",
                        url=page.url,
                        message=f"Links to {link} which returned HTTP {status}",
                        suggested_fix=(
                            f"Update or remove the link to {link} on {page.url}, or fix "
                            f"whatever is causing {link} to return {status}."
                        ),
                    )
                )
    return issues


def detect_missing_canonical(pages: List[CrawledPage]) -> List[TechnicalIssue]:
    issues = []
    for page in pages:
        if not page.html or page.status_code != 200:
            continue
        soup = BeautifulSoup(page.html, "html.parser")
        if soup.find("link", rel="canonical") is None:
            issues.append(
                TechnicalIssue(
                    rule="missing_canonical",
                    severity="warning",
                    url=page.url,
                    message='No <link rel="canonical"> tag found',
                    suggested_fix=f'Add <link rel="canonical" href="{page.url}"> to the page <head>.',
                )
            )
    return issues


def detect_duplicate_titles(pages: List[CrawledPage]) -> List[TechnicalIssue]:
    titles: Dict[str, List[str]] = defaultdict(list)
    for page in pages:
        if not page.html or page.status_code != 200:
            continue
        soup = BeautifulSoup(page.html, "html.parser")
        title_tag = soup.find("title")
        title = title_tag.get_text(strip=True) if title_tag else None
        if title:
            titles[title].append(page.url)

    issues = []
    for title, urls in titles.items():
        if len(urls) > 1:
            for url in urls:
                issues.append(
                    TechnicalIssue(
                        rule="duplicate_title",
                        severity="warning",
                        url=url,
                        message=f'Title "{title}" is duplicated across {len(urls)} pages: {", ".join(urls)}',
                        suggested_fix=(
                            f"Write a unique <title> for {url} that distinguishes it from the "
                            f"other {len(urls) - 1} page(s) sharing this title."
                        ),
                    )
                )
    return issues


def detect_missing_meta_description(pages: List[CrawledPage]) -> List[TechnicalIssue]:
    issues = []
    for page in pages:
        if not page.html or page.status_code != 200:
            continue
        soup = BeautifulSoup(page.html, "html.parser")
        meta = soup.find("meta", attrs={"name": "description"})
        if meta is None or not (meta.get("content") or "").strip():
            issues.append(
                TechnicalIssue(
                    rule="missing_meta_description",
                    severity="warning",
                    url=page.url,
                    message="No meta description found (or it's empty)",
                    suggested_fix=f'Add <meta name="description" content="..."> to the <head> of {page.url}.',
                )
            )
    return issues


def detect_missing_schema(pages: List[CrawledPage]) -> List[TechnicalIssue]:
    issues = []
    for page in pages:
        if not page.html or page.status_code != 200:
            continue
        soup = BeautifulSoup(page.html, "html.parser")
        if soup.find("script", type="application/ld+json") is None:
            issues.append(
                TechnicalIssue(
                    rule="missing_schema",
                    severity="info",
                    url=page.url,
                    message="No JSON-LD structured data found",
                    suggested_fix=(
                        f"Add appropriate schema.org JSON-LD markup (Article, Product, FAQPage, "
                        f"etc.) to {page.url}."
                    ),
                )
            )
    return issues


def detect_orphaned_pages(pages: List[CrawledPage], known_urls: Optional[List[str]] = None) -> List[TechnicalIssue]:
    """Orphan = a URL WorkPulse knows about (via sitemap.xml, passed as
    known_urls) that no crawled page ever links to.

    A pure link-following crawl cannot detect this on its own: every page
    it finds was, by construction, reached via a link from some other
    crawled page, so comparing crawled pages against each other can never
    surface a page nothing links to — it would already be missing from
    the crawl entirely. sitemap.xml (crawler.fetch_sitemap_urls) is the
    second, independent discovery source this check actually needs.
    Returns no issues when known_urls isn't supplied, rather than
    silently reporting a check that can't run as "all clear"."""
    if not known_urls:
        return []

    linked_urls = set()
    for page in pages:
        linked_urls.update(page.internal_links)

    issues = []
    for url in known_urls:
        if url not in linked_urls:
            issues.append(
                TechnicalIssue(
                    rule="orphaned_page",
                    severity="info",
                    url=url,
                    message="Listed in sitemap.xml but not linked from any crawled page",
                    suggested_fix=f"Add at least one internal link to {url} from a relevant, already-linked page.",
                )
            )
    return issues


def detect_redirect_chains(pages: List[CrawledPage]) -> List[TechnicalIssue]:
    """Flags any page reached only after one or more redirect hops.
    `requests` follows redirects transparently, so this relies entirely on
    crawler.py recording each hop in CrawledPage.redirect_chain. A single
    hop is still worth a look (best practice is linking directly to the
    final URL); 2+ hops is the classic "redirect chain" anti-pattern and
    gets a stronger severity."""
    issues = []
    for page in pages:
        hops = page.redirect_chain
        if not hops:
            continue
        chain_desc = " -> ".join([h.url for h in hops] + [page.url])
        issues.append(
            TechnicalIssue(
                rule="redirect_chain",
                severity="warning" if len(hops) >= 2 else "info",
                url=page.url,
                message=(
                    f"Reached only after {len(hops)} redirect hop(s): {chain_desc}"
                    if len(hops) >= 2
                    else f"Reached via a redirect from {hops[0].url} (HTTP {hops[0].status_code})"
                ),
                suggested_fix=(
                    f"Update internal links and any server-side redirect rules to point directly "
                    f"to {page.url}, skipping the intermediate hop(s)."
                ),
            )
        )
    return issues


def detect_crawl_depth(pages: List[CrawledPage], max_depth: int = DEFAULT_MAX_CRAWL_DEPTH) -> List[TechnicalIssue]:
    """Flags pages buried deeper than `max_depth` clicks from the crawl's
    start URL (homepage) — the common guideline that important pages
    should stay easily discoverable via on-site navigation."""
    issues = []
    for page in pages:
        if page.status_code == 200 and page.depth > max_depth:
            issues.append(
                TechnicalIssue(
                    rule="crawl_depth",
                    severity="info",
                    url=page.url,
                    message=f"Page is {page.depth} clicks deep from the homepage (recommended max: {max_depth})",
                    suggested_fix=(
                        f"Add an internal link to {page.url} from a higher-level page (navigation, "
                        f"homepage, or a related-content block) to bring it within {max_depth} clicks."
                    ),
                )
            )
    return issues


def detect_hreflang_errors(pages: List[CrawledPage]) -> List[TechnicalIssue]:
    """Two real, structural hreflang mistakes: (1) a malformed hreflang
    code (not a valid ISO language[-region] tag or "x-default"), and (2)
    a missing reciprocal link — hreflang tags are only valid to search
    engines when every page in the set links back to every other, so A
    pointing at B without B pointing back at A is a known, common bug."""
    # Every crawled, fetchable page's alternate-hreflang links, including
    # an empty list for a page that declares none at all — a reciprocal
    # check against a page with zero hreflang tags must still fail, so
    # that page has to be a known key, not simply absent from the map.
    all_page_entries: Dict[str, List[tuple]] = {}
    for page in pages:
        if not page.html or page.status_code != 200:
            continue
        soup = BeautifulSoup(page.html, "html.parser")
        entries = []
        for tag in soup.find_all("link", rel="alternate"):
            hreflang = tag.get("hreflang")
            href = tag.get("href")
            if hreflang:
                entries.append((hreflang, href))
        all_page_entries[page.url] = entries

    issues = []
    for url, entries in all_page_entries.items():
        if not entries:
            continue
        problems: List[str] = []
        for hreflang, href in entries:
            if not _HREFLANG_RE.match(hreflang):
                problems.append(f'invalid hreflang value "{hreflang}"')
            elif href and href in all_page_entries:
                reciprocal = any(target_href == url for _, target_href in all_page_entries[href])
                if not reciprocal:
                    problems.append(f'{href} does not link back to this page (hreflang="{hreflang}")')
        if problems:
            issues.append(
                TechnicalIssue(
                    rule="hreflang_error",
                    severity="warning",
                    url=url,
                    message="hreflang problems found: " + "; ".join(problems),
                    suggested_fix=(
                        "Fix each malformed hreflang code (must be a valid ISO language[-region] tag "
                        'or "x-default"), and make sure every page in the alternate-language set links '
                        "back to every other page in the set."
                    ),
                )
            )
    return issues


def _parse_robots_disallow_rules(robots_txt: str) -> List[str]:
    """Returns Disallow paths from the User-agent: * block only — the
    rules that apply to crawlers in general, which is what matters for
    catching an accidental block of indexable content."""
    disallow: List[str] = []
    applies_to_all = False
    for line in robots_txt.splitlines():
        line = line.split("#", 1)[0].strip()
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip().lower()
        value = value.strip()
        if key == "user-agent":
            applies_to_all = value == "*"
        elif key == "disallow" and applies_to_all and value:
            disallow.append(value)
    return disallow


def detect_robots_conflicts(
    pages: List[CrawledPage], base_url: str, known_urls: Optional[List[str]] = None
) -> List[TechnicalIssue]:
    """Fetches robots.txt and flags real conflicts: a blanket "Disallow: /"
    (blocks the whole site from crawlers), or specific indexable pages —
    ones actually reachable on the live site or listed in sitemap.xml —
    that a Disallow rule blocks from being crawled at all."""
    robots_url = base_url.rstrip("/") + "/robots.txt"
    try:
        response = requests.get(robots_url, timeout=ROBOTS_TXT_TIMEOUT_SECONDS, headers={"User-Agent": USER_AGENT})
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.info("No usable robots.txt at %s (%s)", robots_url, exc)
        return []

    disallow_rules = _parse_robots_disallow_rules(response.text)
    if not disallow_rules:
        return []

    if "/" in disallow_rules:
        return [
            TechnicalIssue(
                rule="robots_conflict",
                severity="critical",
                url=robots_url,
                message='robots.txt disallows "/" for all crawlers, blocking the entire site from search engines',
                suggested_fix=(
                    'Remove or narrow the blanket "Disallow: /" rule in robots.txt, unless blocking '
                    "the whole site from search engines is actually intended."
                ),
            )
        ]

    issues = []
    urls_to_check = {p.url for p in pages if p.status_code == 200} | set(known_urls or [])
    for url in urls_to_check:
        path = urllib.parse.urlsplit(url).path or "/"
        for rule in disallow_rules:
            if path.startswith(rule):
                issues.append(
                    TechnicalIssue(
                        rule="robots_conflict",
                        severity="warning",
                        url=url,
                        message=f'robots.txt disallows "{rule}", which blocks this indexable page from being crawled',
                        suggested_fix=(
                            f'Either remove/narrow the "Disallow: {rule}" rule in robots.txt, or drop '
                            f"{url} from the sitemap/internal links if it's meant to stay unindexed."
                        ),
                    )
                )
                break
    return issues


_ALL_DETECTORS = (
    detect_broken_links,
    detect_missing_canonical,
    detect_duplicate_titles,
    detect_missing_meta_description,
    detect_missing_schema,
    detect_redirect_chains,
    detect_crawl_depth,
    detect_hreflang_errors,
)


def run_all_detectors(
    pages: List[CrawledPage], known_urls: Optional[List[str]] = None, base_url: Optional[str] = None
) -> List[TechnicalIssue]:
    """Runs every detector, isolating failures so one bad detector can't
    hide the others' findings. known_urls (sitemap.xml URLs) is optional
    — orphan detection is simply skipped without it, rather than failing.
    base_url is optional too — robots.txt conflict detection is skipped
    without it (needed to locate /robots.txt)."""
    issues: List[TechnicalIssue] = []
    for detector in _ALL_DETECTORS:
        try:
            issues.extend(detector(pages))
        except Exception:
            logger.exception("Technical SEO detector %s failed", detector.__name__)

    try:
        issues.extend(detect_orphaned_pages(pages, known_urls))
    except Exception:
        logger.exception("Technical SEO detector detect_orphaned_pages failed")

    if base_url:
        try:
            issues.extend(detect_robots_conflicts(pages, base_url, known_urls))
        except Exception:
            logger.exception("Technical SEO detector detect_robots_conflicts failed")

    return issues
