"""
Semrush Domain Overview + Backlinks Overview client.

Two genuinely different Semrush API endpoints, each verified against
developer.semrush.com's current documentation this session rather than
guessed — following this codebase's own documented Ahrefs precedent (see
automation/seo/backlinks/factory.py's module docstring: "shipping a
plausible-but-wrong integration would be worse than being upfront that it
isn't built yet"):

- Domain Overview (`domain_ranks`, https://api.semrush.com/) — organic
  keywords/traffic, paid (Adwords) keyword counts, Semrush Rank.
  10 API units/line.
- Backlinks Overview (`backlinks_overview`,
  https://api.semrush.com/analytics/v1/) — Authority Score, total
  backlinks, referring domains. 40 API units/call.
- Backlinks (`backlinks`) — individual backlink rows (source/target URL,
  anchor text, nofollow, first/last seen). Referring Domains
  (`backlinks_refdomains`) — one row per linking domain. Batch Comparison
  (`backlinks_comparison`) — this site vs one or more competitor domains
  side by side, the real API this codebase's "Backlink Gap" panel is
  built on. All three: https://api.semrush.com/analytics/v1/, unit cost
  scales with rows returned (display_limit caps it).

This is deliberately not a BacklinkProvider (automation/seo/backlinks/
base.py): that interface returns a List[Mention] — individual pages
linking in, discovered incrementally. These are whole-domain aggregate
stats refreshed periodically, the same shape as pagespeed_client.py's
fetch_page_speed, not a mention list — hence its own client and its own
storage table (seo_semrush_metrics) rather than bolting onto
BacklinkProvider.

IMPORTANT — unlike PageSpeed/GSC/GA4, this is NOT a free integration.
Semrush's own docs describe a purchased "API units" balance tied to a
paid subscription plan; no free tier is documented anywhere. A blank
SEMRUSH_API_KEY means "off" (same convention as every other optional
integration here), but a configured key can still fail with an
insufficient-units error — callers surface that rather than pretending
this is always available.
"""
import csv
import io
import logging
from dataclasses import dataclass
from typing import Optional

import requests

from ai.llm.retry import with_retry  # generic backoff helper, not LLM-specific
from api.config import settings

logger = logging.getLogger(__name__)

TIMEOUT_SECONDS = 30
DOMAIN_OVERVIEW_URL = "https://api.semrush.com/"
BACKLINKS_OVERVIEW_URL = "https://api.semrush.com/analytics/v1/"


@dataclass
class SemrushDomainMetrics:
    authority_score: Optional[float]
    organic_traffic: Optional[int]
    organic_keywords: Optional[int]
    paid_keywords: Optional[int]
    referring_domains: Optional[int]
    backlinks_total: Optional[int]
    semrush_rank: Optional[int]
    raw: dict


@dataclass
class SemrushBacklinkRow:
    source_url: str
    target_url: str
    anchor: str
    nofollow: bool
    first_seen: str
    last_seen: str
    page_authority_score: Optional[float]


@dataclass
class SemrushReferringDomain:
    domain: str
    authority_score: Optional[float]
    backlinks_num: Optional[int]
    country: str
    first_seen: str
    last_seen: str


@dataclass
class SemrushGapRow:
    target: str
    authority_score: Optional[float]
    backlinks_num: Optional[int]
    referring_domains_num: Optional[int]


def _parse_csv_rows(text: str) -> list[dict]:
    """Semrush returns ';'-delimited CSV with a header line matching
    export_columns; an error response is a plain-text line starting with
    'ERROR' instead. Never raises — [] means 'no usable data'."""
    text = text.strip()
    if not text or text.upper().startswith("ERROR"):
        logger.warning("Semrush API returned an error body: %s", text[:200])
        return []
    rows = list(csv.reader(io.StringIO(text), delimiter=";"))
    if len(rows) < 2:
        return []
    header = rows[0]
    return [dict(zip(header, row)) for row in rows[1:]]


def _parse_csv_row(text: str) -> Optional[dict]:
    rows = _parse_csv_rows(text)
    return rows[0] if rows else None


def _get(url: str, params: dict) -> Optional[str]:
    def _do_request():
        response = requests.get(url, params=params, timeout=TIMEOUT_SECONDS)
        response.raise_for_status()
        return response

    try:
        response = with_retry(_do_request, max_attempts=3, retry_on=(requests.RequestException,))
        return response.text
    except Exception:
        logger.exception("Semrush request failed (url=%s, type=%s)", url, params.get("type"))
        return None


def _fetch_domain_overview(domain: str) -> Optional[dict]:
    text = _get(
        DOMAIN_OVERVIEW_URL,
        {
            "key": settings.SEMRUSH_API_KEY,
            "type": "domain_ranks",
            "domain": domain,
            "database": settings.SEMRUSH_DATABASE or "us",
            "export_columns": "Or,Ot,Ad,Rk",
        },
    )
    return _parse_csv_row(text) if text is not None else None


def _fetch_backlinks_overview(domain: str) -> Optional[dict]:
    text = _get(
        BACKLINKS_OVERVIEW_URL,
        {
            "key": settings.SEMRUSH_API_KEY,
            "type": "backlinks_overview",
            "target": domain,
            "target_type": "root_domain",
            "export_columns": "ascore,total,domains_num",
        },
    )
    return _parse_csv_row(text) if text is not None else None


def _to_int(value: Optional[str]) -> Optional[int]:
    try:
        return int(float(value)) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def _to_float(value: Optional[str]) -> Optional[float]:
    try:
        return float(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def is_configured() -> bool:
    return bool(settings.SEMRUSH_API_KEY)


def fetch_domain_metrics(domain: str) -> Optional[SemrushDomainMetrics]:
    """Never raises — returns None when SEMRUSH_API_KEY is unset or both
    underlying calls fail, same graceful-degrade convention as
    pagespeed_client.fetch_page_speed. Spends real purchased API units
    (10 + 40) each time this runs — not something to poll casually."""
    if not is_configured():
        logger.info("SEMRUSH_API_KEY not configured — skipping Semrush domain metrics")
        return None

    overview = _fetch_domain_overview(domain) or {}
    backlinks = _fetch_backlinks_overview(domain) or {}
    if not overview and not backlinks:
        return None

    return SemrushDomainMetrics(
        authority_score=_to_float(backlinks.get("ascore")),
        organic_traffic=_to_int(overview.get("Ot")),
        organic_keywords=_to_int(overview.get("Or")),
        paid_keywords=_to_int(overview.get("Ad")),
        referring_domains=_to_int(backlinks.get("domains_num")),
        backlinks_total=_to_int(backlinks.get("total")),
        semrush_rank=_to_int(overview.get("Rk")),
        raw={"domain_overview": overview, "backlinks_overview": backlinks},
    )


def fetch_backlinks_list(domain: str, limit: int = 50) -> list[SemrushBacklinkRow]:
    """Never raises — [] on any failure/unconfigured. Unit cost scales
    with rows returned, so limit is capped rather than left open-ended."""
    if not is_configured():
        return []
    text = _get(
        BACKLINKS_OVERVIEW_URL,
        {
            "key": settings.SEMRUSH_API_KEY,
            "type": "backlinks",
            "target": domain,
            "target_type": "root_domain",
            "export_columns": "source_url,target_url,anchor,nofollow,first_seen,last_seen,page_ascore",
            "display_limit": min(max(limit, 1), 200),
        },
    )
    if text is None:
        return []
    return [
        SemrushBacklinkRow(
            source_url=row.get("source_url", ""),
            target_url=row.get("target_url", ""),
            anchor=row.get("anchor", ""),
            nofollow=row.get("nofollow") in ("1", "true", "True"),
            first_seen=row.get("first_seen", ""),
            last_seen=row.get("last_seen", ""),
            page_authority_score=_to_float(row.get("page_ascore")),
        )
        for row in _parse_csv_rows(text)
    ]


def fetch_referring_domains(domain: str, limit: int = 50) -> list[SemrushReferringDomain]:
    """Never raises — [] on any failure/unconfigured. Unit cost scales
    with rows returned, so limit is capped rather than left open-ended."""
    if not is_configured():
        return []
    text = _get(
        BACKLINKS_OVERVIEW_URL,
        {
            "key": settings.SEMRUSH_API_KEY,
            "type": "backlinks_refdomains",
            "target": domain,
            "target_type": "root_domain",
            "export_columns": "domain,domain_ascore,backlinks_num,country,first_seen,last_seen",
            "display_limit": min(max(limit, 1), 200),
        },
    )
    if text is None:
        return []
    return [
        SemrushReferringDomain(
            domain=row.get("domain", ""),
            authority_score=_to_float(row.get("domain_ascore")),
            backlinks_num=_to_int(row.get("backlinks_num")),
            country=row.get("country", ""),
            first_seen=row.get("first_seen", ""),
            last_seen=row.get("last_seen", ""),
        )
        for row in _parse_csv_rows(text)
    ]


def fetch_backlink_gap(domains: list[str]) -> list[SemrushGapRow]:
    """This site plus one or more competitor domains, aggregate backlink
    stats side by side — the real, verified API this codebase's Backlink
    Gap panel is built on (`backlinks_comparison`). Note this returns
    aggregate stats per domain, not Semrush's own UI's per-URL overlap
    detail — a real but narrower dataset than what "Backlink Gap" shows
    in Semrush's own product. Never raises — [] on failure/unconfigured."""
    if not is_configured() or not domains:
        return []
    text = _get(
        BACKLINKS_OVERVIEW_URL,
        {
            "key": settings.SEMRUSH_API_KEY,
            "type": "backlinks_comparison",
            "targets[]": domains,
            "target_types[]": ["root_domain"] * len(domains),
            "export_columns": "target,ascore,backlinks_num,domains_num",
        },
    )
    if text is None:
        return []
    return [
        SemrushGapRow(
            target=row.get("target", ""),
            authority_score=_to_float(row.get("ascore")),
            backlinks_num=_to_int(row.get("backlinks_num")),
            referring_domains_num=_to_int(row.get("domains_num")),
        )
        for row in _parse_csv_rows(text)
    ]
