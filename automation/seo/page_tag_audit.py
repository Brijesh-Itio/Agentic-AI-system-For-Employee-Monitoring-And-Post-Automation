"""
MODULE 44 — Single-page tag audit.

Where technical_audit.py's detectors run a full site crawl, this checks
one specific page's SEO/meta tags in isolation — title, meta description,
canonical, robots, viewport, html lang, Open Graph, Twitter Card,
structured data, and the page's H1 — and classifies each one as missing,
present, duplicated, or invalid. That's a different, complementary report
shape from the crawl-wide issue queue: a human pasting in one URL wants
"what does this page's <head> actually look like right now," not a
site-wide backlog entry per problem.

Deterministic, no LLM; read-only against the live URL — this module never
writes anything, matching every other detector in this package.
"""
import json
import logging
import urllib.parse
from dataclasses import dataclass, field
from typing import Callable, List, Optional

import requests
from bs4 import BeautifulSoup

from automation.seo.crawler import USER_AGENT
from automation.seo.technical_audit import HREFLANG_RE, json_ld_nodes

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT_SECONDS = 20

# SEO-guideline length ranges — the same thresholds search engines are
# commonly documented to truncate around, not arbitrary numbers.
TITLE_MIN_LEN, TITLE_MAX_LEN = 10, 60
DESCRIPTION_MIN_LEN, DESCRIPTION_MAX_LEN = 50, 160
_TWITTER_CARD_VALUES = {"summary", "summary_large_image", "app", "player"}


@dataclass
class TagFinding:
    tag: str
    detail: str
    values: List[str] = field(default_factory=list)


@dataclass
class PageTagAuditReport:
    url: str
    fetch_error: Optional[str]
    missing_tags: List[TagFinding]
    existing_tags: List[TagFinding]
    duplicate_tags: List[TagFinding]
    invalid_tags: List[TagFinding]
    # Module 45 — the flat "one value per column" shape the Google Sheets
    # Meta Tag Audit tab needs, computed from the same parsed page as the
    # missing/existing/duplicate/invalid buckets above rather than a
    # second fetch. "" (never None) for anything not found.
    tag_values: dict = field(default_factory=dict)


def extract_tag_values(soup: BeautifulSoup) -> dict:
    """Raw tag VALUES, not a missing/duplicate/invalid classification —
    the flat row shape a spreadsheet export needs. Covers the exact set
    module 45 was asked to auto-fill into Google Sheets: title,
    description, keywords, author, publisher, copyright, subject,
    robots, canonical, a summarized og: block, the hreflang="x-default"
    alternate link (the one hreflang entry meant to catch every visitor
    no other language variant matches), and the @type(s) declared in any
    JSON-LD block (reusing technical_audit.py's json_ld_nodes so a
    @graph-wrapped block is read the same correct, already-verified way
    as everywhere else in this codebase). Every value is "" when absent
    — never None — so a caller can drop these straight into a sheet row."""

    def meta_content(name: str) -> str:
        el = soup.find("meta", attrs={"name": name})
        return (el.get("content") or "").strip() if el else ""

    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else ""

    canonical_tag = soup.find("link", rel="canonical")
    canonical = (canonical_tag.get("href") or "").strip() if canonical_tag else ""

    og_parts = []
    for prop in ("og:title", "og:description", "og:image", "og:url", "og:type"):
        el = soup.find("meta", property=prop)
        content = (el.get("content") or "").strip() if el else ""
        if content:
            og_parts.append(f"{prop}={content}")
    og_summary = "; ".join(og_parts)

    hreflang_x_default = ""
    for link in soup.find_all("link", rel="alternate"):
        if (link.get("hreflang") or "").strip().lower() == "x-default":
            hreflang_x_default = (link.get("href") or "").strip()
            break

    ld_types: List[str] = []
    for script in soup.find_all("script", type="application/ld+json"):
        raw = script.string or script.get_text() or ""
        if not raw.strip():
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        for node in json_ld_nodes(data):
            node_type = node.get("@type")
            if isinstance(node_type, str):
                ld_types.append(node_type)
            elif isinstance(node_type, list):
                ld_types.extend(str(t) for t in node_type)

    return {
        "title": title,
        "description": meta_content("description"),
        "keywords": meta_content("keywords"),
        "author": meta_content("author"),
        "publisher": meta_content("publisher"),
        "copyright": meta_content("copyright"),
        "subject": meta_content("subject"),
        "robots": meta_content("robots"),
        "canonical": canonical,
        "og_tags": og_summary,
        "hreflang_x_default": hreflang_x_default,
        "json_ld": ", ".join(ld_types),
    }


def _validate_title(value: str) -> Optional[str]:
    n = len(value.strip())
    if n == 0:
        return "Title is empty."
    if n < TITLE_MIN_LEN:
        return f"Title is only {n} characters (recommended {TITLE_MIN_LEN}-{TITLE_MAX_LEN})."
    if n > TITLE_MAX_LEN:
        return f"Title is {n} characters — search engines typically truncate past {TITLE_MAX_LEN}."
    return None


def _validate_keywords(value: str) -> Optional[str]:
    if not value.strip():
        return "Meta keywords content is empty."
    return None


def _validate_description(value: str) -> Optional[str]:
    n = len(value.strip())
    if n == 0:
        return "Meta description content is empty."
    if n < DESCRIPTION_MIN_LEN:
        return f"Meta description is only {n} characters (recommended {DESCRIPTION_MIN_LEN}-{DESCRIPTION_MAX_LEN})."
    if n > DESCRIPTION_MAX_LEN:
        return f"Meta description is {n} characters — search engines typically truncate past {DESCRIPTION_MAX_LEN}."
    return None


def _validate_canonical(value: str) -> Optional[str]:
    if not value.strip():
        return "Canonical href is empty."
    parsed = urllib.parse.urlsplit(value)
    if not parsed.scheme or not parsed.netloc:
        return f'Canonical href "{value}" is not a valid absolute URL.'
    return None


def _validate_viewport(value: str) -> Optional[str]:
    if "width=device-width" not in value.replace(" ", ""):
        return f'Viewport content "{value}" is missing width=device-width.'
    return None


def _validate_robots(value: str) -> Optional[str]:
    if not value.strip():
        return "Robots meta content is empty."
    return None


def _validate_og_content(value: str) -> Optional[str]:
    if not value.strip():
        return "Content is empty."
    return None


def _validate_twitter_card(value: str) -> Optional[str]:
    if value.strip().lower() not in _TWITTER_CARD_VALUES:
        return f'twitter:card value "{value}" is not one of {sorted(_TWITTER_CARD_VALUES)}.'
    return None


def _validate_h1(value: str) -> Optional[str]:
    if not value.strip():
        return "The <h1> element has no text."
    return None


def _classify(
    tag: str,
    elements: list,
    extract: Callable,
    validate: Optional[Callable[[str], Optional[str]]],
) -> "tuple[str, TagFinding]":
    """Buckets one logical tag (elements is every matching element found
    for it) into exactly one of missing/existing/duplicate/invalid —
    duplication is checked before validity since "there are two of these"
    is itself the finding worth surfacing, regardless of what either one
    contains."""
    if not elements:
        return "missing", TagFinding(tag=tag, detail=f"No {tag} found.")
    values = [extract(el) for el in elements]
    if len(elements) > 1:
        return "duplicate", TagFinding(
            tag=tag, detail=f"{len(elements)} {tag} tags found (should be exactly one).", values=values
        )
    value = values[0]
    reason = validate(value) if validate else None
    if reason:
        return "invalid", TagFinding(tag=tag, detail=reason, values=values)
    return "existing", TagFinding(tag=tag, detail="Present and looks valid.", values=values)


def _audit_structured_data(soup: BeautifulSoup) -> "tuple[str, TagFinding]":
    """Structured data gets its own logic rather than _classify: multiple
    JSON-LD <script> blocks on one page is normal (Article + BreadcrumbList
    + WebSite, say), so block *count* is never a duplicate finding here —
    only a block that fails to parse, or a node genuinely missing @type,
    is. Reuses technical_audit.py's json_ld_nodes so a @graph-wrapped
    block (context declared once, inherited by each node) isn't
    misclassified as invalid the same way that module's own detector
    once was, before being fixed and verified against a real site."""
    scripts = soup.find_all("script", type="application/ld+json")
    if not scripts:
        return "missing", TagFinding(tag="Structured data (JSON-LD)", detail='No <script type="application/ld+json"> block found.')

    problems: List[str] = []
    found_types: List[str] = []
    for i, script in enumerate(scripts):
        raw = script.string or script.get_text() or ""
        if not raw.strip():
            problems.append(f"Block {i + 1} is empty.")
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            problems.append(f"Block {i + 1} is not valid JSON ({exc.msg}).")
            continue
        has_context = (isinstance(data, dict) and "@context" in data) or (
            isinstance(data, list) and any(isinstance(item, dict) and "@context" in item for item in data)
        )
        if not has_context:
            problems.append(f"Block {i + 1} has no @context.")
        nodes = json_ld_nodes(data)
        if not nodes:
            problems.append(f"Block {i + 1} does not contain a recognizable JSON-LD object.")
            continue
        missing_type = sum(1 for node in nodes if "@type" not in node)
        if missing_type:
            problems.append(f"Block {i + 1} has {missing_type} node(s) missing @type.")
        found_types.extend(str(node["@type"]) for node in nodes if "@type" in node)

    if problems:
        return "invalid", TagFinding(tag="Structured data (JSON-LD)", detail="; ".join(problems), values=found_types)
    return "existing", TagFinding(
        tag="Structured data (JSON-LD)",
        detail=f"{len(scripts)} block(s) found, all valid.",
        values=found_types or [f"{len(scripts)} block(s)"],
    )


def _audit_html_lang(soup: BeautifulSoup) -> "tuple[str, TagFinding]":
    """A single attribute, not a repeatable element — handled directly
    rather than through _classify since "absent" and "present but
    malformed" need different buckets (missing vs. invalid), not the
    single validate-or-not path _classify assumes."""
    html_tag = soup.find("html")
    if html_tag is None:
        return "missing", TagFinding(tag="HTML lang attribute", detail="No <html> tag found on the page.")
    lang_value = html_tag.get("lang", "") or ""
    if not lang_value.strip():
        return "missing", TagFinding(tag="HTML lang attribute", detail="The <html> tag has no lang attribute.")
    if not HREFLANG_RE.match(lang_value.strip()):
        return "invalid", TagFinding(
            tag="HTML lang attribute", detail=f'lang="{lang_value}" is not a valid language code.', values=[lang_value]
        )
    return "existing", TagFinding(tag="HTML lang attribute", detail="Present and looks valid.", values=[lang_value])


def run_page_tag_audit(url: str) -> PageTagAuditReport:
    """Never raises — a fetch failure comes back as fetch_error set and
    every bucket empty, matching this codebase's graceful-degrade
    convention; the caller (api/routes/seo.py) turns that into a 502."""
    try:
        response = requests.get(url, timeout=REQUEST_TIMEOUT_SECONDS, headers={"User-Agent": USER_AGENT})
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.info("page_tag_audit: failed to fetch %s (%s)", url, exc)
        return PageTagAuditReport(url=url, fetch_error=str(exc), missing_tags=[], existing_tags=[], duplicate_tags=[], invalid_tags=[])

    soup = BeautifulSoup(response.text, "html.parser")
    buckets: dict = {"missing": [], "existing": [], "duplicate": [], "invalid": []}

    def add(tag: str, elements: list, extract: Callable, validate: Optional[Callable] = None) -> None:
        kind, finding = _classify(tag, elements, extract, validate)
        buckets[kind].append(finding)

    add("Title tag", soup.find_all("title"), lambda el: el.get_text(strip=True), _validate_title)
    add(
        "Meta description",
        soup.find_all("meta", attrs={"name": "description"}),
        lambda el: el.get("content", ""),
        _validate_description,
    )
    add(
        "Meta keywords",
        soup.find_all("meta", attrs={"name": "keywords"}),
        lambda el: el.get("content", ""),
        _validate_keywords,
    )
    add("Canonical URL", soup.find_all("link", rel="canonical"), lambda el: el.get("href", ""), _validate_canonical)
    add("Meta robots", soup.find_all("meta", attrs={"name": "robots"}), lambda el: el.get("content", ""), _validate_robots)
    add("Meta viewport", soup.find_all("meta", attrs={"name": "viewport"}), lambda el: el.get("content", ""), _validate_viewport)

    lang_kind, lang_finding = _audit_html_lang(soup)
    buckets[lang_kind].append(lang_finding)

    add(
        "Open Graph title (og:title)",
        soup.find_all("meta", property="og:title"),
        lambda el: el.get("content", ""),
        _validate_og_content,
    )
    add(
        "Open Graph description (og:description)",
        soup.find_all("meta", property="og:description"),
        lambda el: el.get("content", ""),
        _validate_og_content,
    )
    add(
        "Open Graph image (og:image)",
        soup.find_all("meta", property="og:image"),
        lambda el: el.get("content", ""),
        _validate_og_content,
    )
    add(
        "Open Graph URL (og:url)",
        soup.find_all("meta", property="og:url"),
        lambda el: el.get("content", ""),
        _validate_og_content,
    )

    add(
        "Twitter card type (twitter:card)",
        soup.find_all("meta", attrs={"name": "twitter:card"}),
        lambda el: el.get("content", ""),
        _validate_twitter_card,
    )
    add(
        "Twitter title (twitter:title)",
        soup.find_all("meta", attrs={"name": "twitter:title"}),
        lambda el: el.get("content", ""),
        _validate_og_content,
    )
    add(
        "Twitter description (twitter:description)",
        soup.find_all("meta", attrs={"name": "twitter:description"}),
        lambda el: el.get("content", ""),
        _validate_og_content,
    )
    add(
        "Twitter image (twitter:image)",
        soup.find_all("meta", attrs={"name": "twitter:image"}),
        lambda el: el.get("content", ""),
        _validate_og_content,
    )

    add("H1 heading", soup.find_all("h1"), lambda el: el.get_text(strip=True), _validate_h1)

    schema_kind, schema_finding = _audit_structured_data(soup)
    buckets[schema_kind].append(schema_finding)

    return PageTagAuditReport(
        url=url,
        fetch_error=None,
        missing_tags=buckets["missing"],
        existing_tags=buckets["existing"],
        duplicate_tags=buckets["duplicate"],
        invalid_tags=buckets["invalid"],
        tag_values=extract_tag_values(soup),
    )
