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
import json
import logging
import re
import socket
import ssl
import urllib.parse
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
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


def detect_missing_alt_tags(pages: List[CrawledPage]) -> List[TechnicalIssue]:
    """Module 40 — every <img> missing an alt attribute (or with an
    empty one) is both an accessibility gap and a missed keyword/context
    signal for image search. One issue per page, listing every offending
    src, rather than one per image — a page with 20 unlabeled images
    doesn't need 20 separate rows in the approval queue."""
    issues = []
    for page in pages:
        if not page.html or page.status_code != 200:
            continue
        soup = BeautifulSoup(page.html, "html.parser")
        missing = [img.get("src", "(no src)") for img in soup.find_all("img") if not (img.get("alt") or "").strip()]
        if missing:
            issues.append(
                TechnicalIssue(
                    rule="missing_alt_tags",
                    severity="warning",
                    url=page.url,
                    message=f"{len(missing)} <img> tag(s) missing alt text: {', '.join(missing[:5])}"
                    + (f" (+{len(missing) - 5} more)" if len(missing) > 5 else ""),
                    suggested_fix="Add a descriptive alt attribute to each image listed — what the image shows, not a keyword-stuffed phrase.",
                )
            )
    return issues


def detect_non_webp_images(pages: List[CrawledPage]) -> List[TechnicalIssue]:
    """Module 40 — <img src>/<img srcset> still pointing at .jpg/.jpeg/
    .png. Same JPG/PNG detection convention as automation/seo/
    webp_bulk_converter.py's own scan, so this issue and that tool agree
    on what counts as convertible. This detector only reports the gap;
    the actual fix is that tool (Server → Convert Page Images to WebP)."""
    issues = []
    for page in pages:
        if not page.html or page.status_code != 200:
            continue
        soup = BeautifulSoup(page.html, "html.parser")
        found = set()
        for img in soup.find_all("img"):
            for candidate in [img.get("src")] + [
                e.strip().split()[0] for e in (img.get("srcset") or "").split(",") if e.strip()
            ]:
                if candidate and re.search(r"\.(jpe?g|png)$", candidate, re.IGNORECASE):
                    found.add(candidate)
        if found:
            issues.append(
                TechnicalIssue(
                    rule="non_webp_images",
                    severity="warning",
                    url=page.url,
                    message=f"{len(found)} JPG/PNG image(s) not yet in a modern format: {', '.join(list(found)[:5])}"
                    + (f" (+{len(found) - 5} more)" if len(found) > 5 else ""),
                    suggested_fix="Use the Convert Page Images to WebP tool (Overview tab) on this page's URL — it converts these to WebP and rewrites the page automatically.",
                )
            )
    return issues


def detect_unsafe_target_blank(pages: List[CrawledPage]) -> List[TechnicalIssue]:
    """Module 40 — <a target="_blank"> without rel="noopener"/
    "noreferrer" lets the opened page's JS reach back into window.opener
    (reposition/phish the original tab) and forces the original page to
    share its render process with an unknown destination — a real,
    well-documented performance/security gap, not just a lint nitpick."""
    issues = []
    for page in pages:
        if not page.html or page.status_code != 200:
            continue
        soup = BeautifulSoup(page.html, "html.parser")
        unsafe = []
        for a in soup.find_all("a", target="_blank"):
            rel = (a.get("rel") or [])
            rel_str = " ".join(rel) if isinstance(rel, list) else str(rel)
            if "noopener" not in rel_str and "noreferrer" not in rel_str:
                unsafe.append(a.get("href", "(no href)"))
        if unsafe:
            issues.append(
                TechnicalIssue(
                    rule="unsafe_target_blank",
                    severity="info",
                    url=page.url,
                    message=f'{len(unsafe)} target="_blank" link(s) missing rel="noopener": {", ".join(unsafe[:5])}'
                    + (f" (+{len(unsafe) - 5} more)" if len(unsafe) > 5 else ""),
                    suggested_fix='Add rel="noopener noreferrer" to every target="_blank" link listed.',
                )
            )
    return issues


def detect_missing_meta_viewport(pages: List[CrawledPage]) -> List[TechnicalIssue]:
    """Module 40 — the one tag mobile-responsive CSS actually depends
    on; without it, mobile browsers render at desktop width and scale
    down, defeating any responsive design the page otherwise has."""
    issues = []
    for page in pages:
        if not page.html or page.status_code != 200:
            continue
        soup = BeautifulSoup(page.html, "html.parser")
        if soup.find("meta", attrs={"name": "viewport"}) is None:
            issues.append(
                TechnicalIssue(
                    rule="missing_meta_viewport",
                    severity="warning",
                    url=page.url,
                    message="No <meta name=\"viewport\"> tag found",
                    suggested_fix='Add <meta name="viewport" content="width=device-width, initial-scale=1"> to the <head>.',
                )
            )
    return issues


def detect_render_blocking_resources(pages: List[CrawledPage]) -> List[TechnicalIssue]:
    """Module 40 — <script> tags in <head> with neither async nor
    defer, and <link rel="stylesheet"> in <head> with no media
    attribute that would let the browser deprioritize it — both force
    the browser to stop parsing the page and fetch+run/apply the
    resource before it can render anything, the textbook definition of
    render-blocking. Body-placed scripts are already non-blocking by
    position, so only <head> contents are checked."""
    issues = []
    for page in pages:
        if not page.html or page.status_code != 200:
            continue
        soup = BeautifulSoup(page.html, "html.parser")
        head = soup.find("head")
        if head is None:
            continue
        blocking = []
        for script in head.find_all("script", src=True):
            # async/defer are boolean HTML attributes — BeautifulSoup
            # parses a bare `async` into attrs={"async": ""}, an empty
            # string that's falsy in Python; checking key presence
            # (not truthiness of the value) is the only correct test.
            if "async" not in script.attrs and "defer" not in script.attrs:
                blocking.append(script.get("src"))
        for link in head.find_all("link", rel="stylesheet"):
            if not link.get("media") or link.get("media") == "all":
                blocking.append(link.get("href"))
        if blocking:
            issues.append(
                TechnicalIssue(
                    rule="render_blocking_resources",
                    severity="warning",
                    url=page.url,
                    message=f"{len(blocking)} render-blocking resource(s) in <head>: {', '.join(str(b) for b in blocking[:5])}"
                    + (f" (+{len(blocking) - 5} more)" if len(blocking) > 5 else ""),
                    suggested_fix="Add async or defer to head <script> tags, and move non-critical stylesheets to load asynchronously (or inline critical CSS and defer the rest).",
                )
            )
    return issues


def detect_missing_favicon(pages: List[CrawledPage]) -> List[TechnicalIssue]:
    """Module 40 — checked against the homepage only (pages[0], the
    crawl's start URL) since a favicon is a site-wide concern, not a
    per-page one; the browser looks for one <link rel="icon"> or falls
    back to /favicon.ico regardless of which page is open."""
    if not pages or not pages[0].html or pages[0].status_code != 200:
        return []
    soup = BeautifulSoup(pages[0].html, "html.parser")
    has_link_icon = soup.find("link", rel=lambda v: v and "icon" in v.lower()) is not None
    if has_link_icon:
        return []
    try:
        base = urllib.parse.urlsplit(pages[0].url)
        favicon_url = f"{base.scheme}://{base.netloc}/favicon.ico"
        response = requests.get(favicon_url, timeout=10, headers={"User-Agent": USER_AGENT})
        if response.ok and "image" in response.headers.get("Content-Type", ""):
            return []
    except requests.RequestException:
        pass
    return [
        TechnicalIssue(
            rule="missing_favicon",
            severity="info",
            url=pages[0].url,
            message="No favicon found (<link rel=\"icon\"> missing and /favicon.ico not reachable)",
            suggested_fix='Add a favicon.ico at the site root, or reference one explicitly: <link rel="icon" href="/favicon.ico">.',
        )
    ]


def detect_missing_analytics(pages: List[CrawledPage]) -> List[TechnicalIssue]:
    """Module 40 — checked against the homepage only, same reasoning as
    the favicon check: analytics is installed site-wide via one
    template, not per-page. Looks for the well-known GA script patterns
    (gtag.js / analytics.js / the GA4 "G-XXXX" or UA-XXXX measurement
    id) rather than a specific plugin's markup, so it matches however
    the site actually integrated it (theme, plugin, GTM)."""
    if not pages or not pages[0].html or pages[0].status_code != 200:
        return []
    html = pages[0].html
    if re.search(r"gtag\(|googletagmanager\.com/gtag|google-analytics\.com/analytics\.js|UA-\d{4,}|G-[A-Z0-9]{6,}", html):
        return []
    return [
        TechnicalIssue(
            rule="missing_analytics",
            severity="info",
            url=pages[0].url,
            message="No Google Analytics (or GA4/gtag.js) script detected",
            suggested_fix="Add a GA4 measurement id via gtag.js, or install Google Tag Manager, so traffic/behavior data is actually collected.",
        )
    ]


def detect_missing_hsts(pages: List[CrawledPage]) -> List[TechnicalIssue]:
    """Module 40 — a real header check, not an HTML one: fetches the
    homepage itself (CrawledPage doesn't retain response headers) to
    read Strict-Transport-Security directly off the live response."""
    if not pages:
        return []
    try:
        response = requests.get(pages[0].url, timeout=10, headers={"User-Agent": USER_AGENT})
    except requests.RequestException:
        return []
    if "Strict-Transport-Security" in response.headers:
        return []
    return [
        TechnicalIssue(
            rule="missing_hsts",
            severity="info",
            url=pages[0].url,
            message="No Strict-Transport-Security header — HTTPS isn't enforced at the browser level",
            suggested_fix='Add "Strict-Transport-Security: max-age=31536000; includeSubDomains" to the server\'s response headers (via web server config, not something WordPress\'s content layer controls).',
        )
    ]


def detect_soft_404(pages: List[CrawledPage]) -> List[TechnicalIssue]:
    """Module 40 — requests a deliberately-nonexistent path and checks
    the server actually returns HTTP 404 for it, not 200. A "soft 404"
    (a real missing-page message served with status 200) tricks search
    engines into indexing broken pages as if they were real content —
    the opposite problem from "no custom 404 page," and the one that
    actually costs rankings, so this checks status code, not page
    styling (which this codebase has no reliable way to judge anyway)."""
    if not pages:
        return []
    base = urllib.parse.urlsplit(pages[0].url)
    probe_url = f"{base.scheme}://{base.netloc}/this-page-should-not-exist-workpulse-check/"
    try:
        response = requests.get(probe_url, timeout=10, headers={"User-Agent": USER_AGENT}, allow_redirects=True)
    except requests.RequestException:
        return []
    if response.status_code == 404:
        return []
    return [
        TechnicalIssue(
            rule="soft_404",
            severity="warning",
            url=probe_url,
            message=f"A nonexistent URL returned HTTP {response.status_code} instead of 404 — this is a \"soft 404\"",
            suggested_fix="Configure the server/CMS to return a real HTTP 404 status for missing pages (a custom-styled 404 page is fine, as long as the status code is still 404, not 200).",
        )
    ]


def detect_noindex_tags(pages: List[CrawledPage]) -> List[TechnicalIssue]:
    """Module 41 — a page reachable via normal crawling (internal links,
    HTTP 200) but carrying <meta name="robots" content="noindex"> (or
    "none") won't show up in search results at all, even though nothing
    about how it was found suggests that's deliberate. This can't tell
    intentional noindex (a thank-you page, an internal search results
    page) from an accidental one left over from staging — severity is
    "info" precisely because a human has to make that call, not this
    detector."""
    issues = []
    for page in pages:
        if not page.html or page.status_code != 200:
            continue
        soup = BeautifulSoup(page.html, "html.parser")
        meta = soup.find("meta", attrs={"name": "robots"})
        content = (meta.get("content") or "").lower() if meta else ""
        if "noindex" in content or content == "none":
            issues.append(
                TechnicalIssue(
                    rule="noindex_tag",
                    severity="info",
                    url=page.url,
                    message=f'Page is marked noindex (<meta name="robots" content="{meta.get("content")}">) but is reachable via normal internal links',
                    suggested_fix="If this page should appear in search results, remove noindex from its robots meta tag. If it's deliberate (a thank-you/staging page), no action needed.",
                )
            )
    return issues


def detect_heading_hierarchy(pages: List[CrawledPage]) -> List[TechnicalIssue]:
    """Module 41 — three real, well-documented heading problems: no H1 at
    all (search engines lose the page's primary topic signal), more than
    one H1 (dilutes that same signal — one page, one main heading is the
    convention every major SEO guide agrees on), and a skipped level
    (an H1 followed directly by an H3 with no H2 between) which breaks
    the hierarchy screen readers and search engines both rely on to
    understand a page's outline."""
    issues = []
    for page in pages:
        if not page.html or page.status_code != 200:
            continue
        soup = BeautifulSoup(page.html, "html.parser")
        headings = soup.find_all(re.compile(r"^h[1-6]$"))
        levels = [int(h.name[1]) for h in headings]
        h1_count = levels.count(1)

        problems: List[str] = []
        if h1_count == 0:
            problems.append("no <h1> found")
        elif h1_count > 1:
            problems.append(f"{h1_count} <h1> tags found (should be exactly one)")
        for prev, curr in zip(levels, levels[1:]):
            if curr - prev > 1:
                problems.append(f"heading level skips from h{prev} to h{curr} (no h{prev + 1} in between)")
                break
        if problems:
            issues.append(
                TechnicalIssue(
                    rule="heading_hierarchy",
                    severity="warning",
                    url=page.url,
                    message="Heading structure problems: " + "; ".join(problems),
                    suggested_fix="Use exactly one <h1> per page as the main heading, and keep heading levels sequential (don't skip from h1 straight to h3, etc.).",
                )
            )
    return issues


def detect_mixed_content(pages: List[CrawledPage]) -> List[TechnicalIssue]:
    """Module 41 — an https:// page that still loads a resource over
    plain http:// gets it blocked outright by modern browsers (for
    scripts/stylesheets) or flagged "not fully secure" (for images),
    since the encrypted page can no longer vouch for the plaintext
    resource. Only checked on pages actually served over https."""
    issues = []
    for page in pages:
        if not page.html or page.status_code != 200 or not page.url.startswith("https://"):
            continue
        soup = BeautifulSoup(page.html, "html.parser")
        insecure = set()
        for tag, attr in (("img", "src"), ("script", "src"), ("link", "href"), ("iframe", "src")):
            for el in soup.find_all(tag):
                value = el.get(attr)
                if value and value.startswith("http://"):
                    insecure.add(value)
        if insecure:
            issues.append(
                TechnicalIssue(
                    rule="mixed_content",
                    severity="warning",
                    url=page.url,
                    message=f"{len(insecure)} resource(s) loaded over insecure http:// on an https:// page: {', '.join(list(insecure)[:5])}"
                    + (f" (+{len(insecure) - 5} more)" if len(insecure) > 5 else ""),
                    suggested_fix="Change each listed resource URL to https:// (or a protocol-relative // URL) so it loads securely on this https:// page.",
                )
            )
    return issues


def detect_insecure_http_redirect(pages: List[CrawledPage]) -> List[TechnicalIssue]:
    """Module 41 — a real request, not an HTML check: fetches the
    plain-http:// version of the homepage and confirms it actually
    redirects to https://. Skipped entirely if the site's own homepage
    wasn't crawled over https to begin with (nothing to enforce)."""
    if not pages or not pages[0].url.startswith("https://"):
        return []
    http_url = "http://" + pages[0].url[len("https://"):]
    try:
        response = requests.get(http_url, timeout=10, headers={"User-Agent": USER_AGENT}, allow_redirects=True)
    except requests.RequestException:
        return []
    if response.url.startswith("https://"):
        return []
    return [
        TechnicalIssue(
            rule="insecure_http_not_redirected",
            severity="critical",
            url=http_url,
            message=f"http:// version of the homepage does not redirect to https:// (landed on {response.url})",
            suggested_fix="Add a server-level 301 redirect from http:// to https:// for the whole site (e.g. in .htaccess or the web server config), so visitors and search engines are never served the insecure version.",
        )
    ]


def detect_ssl_certificate(pages: List[CrawledPage]) -> List[TechnicalIssue]:
    """Module 41 — connects directly at the TLS layer (not via requests,
    which would just raise generically on an untrusted/expired cert) to
    read the certificate's own notAfter date, so an about-to-expire
    certificate is flagged before it actually breaks the site."""
    if not pages or not pages[0].url.startswith("https://"):
        return []
    host = urllib.parse.urlsplit(pages[0].url).netloc.split(":")[0]
    try:
        context = ssl.create_default_context()
        with socket.create_connection((host, 443), timeout=10) as sock:
            with context.wrap_socket(sock, server_hostname=host) as tls_sock:
                cert = tls_sock.getpeercert()
    except ssl.SSLCertVerificationError as exc:
        return [
            TechnicalIssue(
                rule="ssl_certificate",
                severity="critical",
                url=pages[0].url,
                message=f"SSL certificate for {host} failed verification: {exc}",
                suggested_fix="Renew or reinstall a valid SSL certificate for this domain via the hosting provider/certificate authority (e.g. Let's Encrypt, cPanel AutoSSL).",
            )
        ]
    except (socket.error, ssl.SSLError, OSError) as exc:
        logger.info("detect_ssl_certificate: could not connect to %s:443 (%s)", host, exc)
        return []

    not_after = cert.get("notAfter")
    if not not_after:
        return []
    try:
        expires = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
    except ValueError:
        return []
    days_left = (expires - datetime.now(timezone.utc)).days
    if days_left > 14:
        return []
    severity = "critical" if days_left < 0 else "warning"
    status = "already expired" if days_left < 0 else f"expires in {days_left} day(s)"
    return [
        TechnicalIssue(
            rule="ssl_certificate",
            severity=severity,
            url=pages[0].url,
            message=f"SSL certificate for {host} {status} (notAfter: {not_after})",
            suggested_fix="Renew the SSL certificate before it expires — most hosts (cPanel AutoSSL, Let's Encrypt) can auto-renew if configured, otherwise renew manually with the certificate authority.",
        )
    ]


def _json_ld_nodes(data) -> List[dict]:
    """A "@graph"-wrapped block (the common Yoast/RankMath pattern seen
    live on a real WordPress site this session) declares @context ONCE
    on the wrapper and lists several typed nodes underneath that inherit
    it — per the JSON-LD spec, those nodes are NOT individually invalid
    for lacking their own @context. Returns the nodes that actually need
    a @type check; @context is checked once against the outer data,
    separately, by the caller."""
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        graph = data.get("@graph")
        if isinstance(graph, list):
            return [item for item in graph if isinstance(item, dict)]
        return [data]
    return []


def detect_invalid_schema(pages: List[CrawledPage]) -> List[TechnicalIssue]:
    """Module 41 — goes past detect_missing_schema's presence-only check
    to validate what's actually inside each JSON-LD block: it must at
    least parse as JSON, declare @context once (whether on the block
    itself or, for a list of independent top-level objects, on at least
    one of them), and give every node a @type — or search engines
    silently ignore it as if nothing were there at all, same practical
    effect as having no structured data, just harder to notice."""
    issues = []
    for page in pages:
        if not page.html or page.status_code != 200:
            continue
        soup = BeautifulSoup(page.html, "html.parser")
        problems: List[str] = []
        for i, script in enumerate(soup.find_all("script", type="application/ld+json")):
            raw = script.string or script.get_text() or ""
            if not raw.strip():
                problems.append(f"block {i + 1} is empty")
                continue
            try:
                data = json.loads(raw)
            except json.JSONDecodeError as exc:
                problems.append(f"block {i + 1} is not valid JSON ({exc.msg})")
                continue
            has_context = (isinstance(data, dict) and "@context" in data) or (
                isinstance(data, list) and any(isinstance(item, dict) and "@context" in item for item in data)
            )
            if not has_context:
                problems.append(f"block {i + 1} has no @context")
            nodes = _json_ld_nodes(data)
            if not nodes:
                problems.append(f"block {i + 1} does not contain a recognizable JSON-LD object")
            else:
                missing_type = sum(1 for node in nodes if "@type" not in node)
                if missing_type:
                    problems.append(f"block {i + 1} has {missing_type} node(s) missing @type")
        if problems:
            issues.append(
                TechnicalIssue(
                    rule="invalid_schema",
                    severity="warning",
                    url=page.url,
                    message="JSON-LD structured data problems: " + "; ".join(problems),
                    suggested_fix="Fix each JSON-LD block so it's valid JSON and includes both @context (usually \"https://schema.org\") and @type (e.g. \"Article\", \"Product\") — validate with Google's Rich Results Test.",
                )
            )
    return issues


# SEO-guideline thresholds for detect_url_structure — a length past which
# search results commonly truncate the URL, and a query-parameter count
# past which a URL is more likely tracking/faceted-navigation cruft than
# a real distinct page worth indexing on its own.
_MAX_RECOMMENDED_URL_LENGTH = 115
_MAX_RECOMMENDED_QUERY_PARAMS = 2


def detect_url_structure(pages: List[CrawledPage]) -> List[TechnicalIssue]:
    """Module 41 — flags URLs that work against common SEO guidance even
    though they're perfectly valid HTTP: uppercase letters (case-
    sensitive duplicate risk on most servers), spaces/underscores
    (search engines treat _ as a joiner, not a word separator, unlike -),
    an overly long path, or more query parameters than a real distinct
    page is likely to need."""
    issues = []
    for page in pages:
        if page.status_code != 200:
            continue
        parsed = urllib.parse.urlsplit(page.url)
        problems: List[str] = []
        if any(c.isupper() for c in parsed.path):
            problems.append("contains uppercase letters")
        if "_" in parsed.path:
            problems.append("uses underscores instead of hyphens as word separators")
        if " " in parsed.path or "%20" in parsed.path:
            problems.append("contains a space")
        if len(page.url) > _MAX_RECOMMENDED_URL_LENGTH:
            problems.append(f"is {len(page.url)} characters long (recommended max: {_MAX_RECOMMENDED_URL_LENGTH})")
        query_params = urllib.parse.parse_qs(parsed.query)
        if len(query_params) > _MAX_RECOMMENDED_QUERY_PARAMS:
            problems.append(f"has {len(query_params)} query parameters (recommended max: {_MAX_RECOMMENDED_QUERY_PARAMS})")
        if problems:
            issues.append(
                TechnicalIssue(
                    rule="url_structure",
                    severity="info",
                    url=page.url,
                    message="URL structure: " + "; ".join(problems),
                    suggested_fix="Use lowercase, hyphen-separated URLs and keep query parameters minimal; where possible, 301-redirect the messier URL to a clean canonical version.",
                )
            )
    return issues


def detect_temporary_redirect_overuse(pages: List[CrawledPage]) -> List[TechnicalIssue]:
    """Module 41 — a 302/303/307 ("temporary") redirect tells search
    engines the original URL might come back, so they keep it indexed
    instead of transferring its ranking signals to the destination —
    the wrong behavior for a redirect that's actually permanent (a
    moved page, an old URL scheme). Flags any hop using a temporary
    status code; whether it's a bug depends on intent, which is why
    this stays "warning", not "critical"."""
    issues = []
    for page in pages:
        temporary_hops = [h for h in page.redirect_chain if h.status_code in (302, 303, 307)]
        if not temporary_hops:
            continue
        hop_desc = ", ".join(f"{h.url} (HTTP {h.status_code})" for h in temporary_hops)
        issues.append(
            TechnicalIssue(
                rule="temporary_redirect_overuse",
                severity="warning",
                url=page.url,
                message=f"Reached via a temporary redirect (302/303/307), not a permanent 301: {hop_desc}",
                suggested_fix=f"If {page.url} is the permanent, intended destination, change the redirect to a 301 (permanent) so search engines transfer ranking signals to it instead of keeping the old URL indexed.",
            )
        )
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
    detect_missing_alt_tags,
    detect_non_webp_images,
    detect_unsafe_target_blank,
    detect_missing_meta_viewport,
    detect_render_blocking_resources,
    detect_missing_favicon,
    detect_missing_analytics,
    detect_missing_hsts,
    detect_soft_404,
    detect_noindex_tags,
    detect_heading_hierarchy,
    detect_mixed_content,
    detect_insecure_http_redirect,
    detect_ssl_certificate,
    detect_invalid_schema,
    detect_url_structure,
    detect_temporary_redirect_overuse,
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
