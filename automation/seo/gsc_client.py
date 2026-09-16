"""
MODULE 26.5 — Google Search Console client.

Pulls Search Analytics data (queries, clicks, impressions, CTR, average
position) via the Search Console API's searchAnalytics.query endpoint,
authenticated through automation/seo/google_auth.py's service-account
flow. Scoped to what the SEO blueprint's GSC feature actually needs —
rank/impressions/CTR tracking; index coverage and sitemap status are a
separate, later concern (a future technical/indexing pipeline module).
"""
import logging
import urllib.parse
from dataclasses import dataclass
from datetime import date as date_cls
from typing import List, Optional

import requests

from ai.llm.retry import with_retry
from automation.seo.google_auth import get_access_token

logger = logging.getLogger(__name__)

TIMEOUT_SECONDS = 30
SCOPE = ["https://www.googleapis.com/auth/webmasters.readonly"]


@dataclass
class GscQueryRow:
    query: str
    clicks: int
    impressions: int
    ctr: float
    position: float


@dataclass
class GscPageRow:
    page: str
    clicks: int
    impressions: int
    ctr: float
    position: float


@dataclass
class GscDimensionRow:
    """Shared row shape for the three single-value dimensions below
    (country, device, searchAppearance) — unlike query/page, none of
    these need a semantically distinct field name; `key` is whatever
    that dimension's value is (a country code, "MOBILE"/"DESKTOP"/
    "TABLET", or a search-appearance type like "AMP_BLUE_LINK")."""
    key: str
    clicks: int
    impressions: int
    ctr: float
    position: float


def _query_search_analytics(
    start_date: date_cls, end_date: date_cls, dimension: str, row_limit: int, site_url: Optional[str]
) -> Optional[list]:
    """Shared searchAnalytics.query POST for both dimensions this module
    supports (query, page) — same endpoint and auth, only the requested
    dimension and the resulting rows' shape differ. Never raises — returns
    None on failure (unconfigured, auth, network, or an unverified/
    mistyped site property), matching this codebase's graceful-degrade
    convention. site_url is the property to query — callers decide whether
    falling back to the global GSC_SITE_URL .env default is safe
    (agent.database.count_active_seo_sites() <= 1; see its docstring for
    why that check matters — this function deliberately does NOT fall back
    to settings on its own, since a wrong-but-real property would silently
    return real data attributed to the wrong site rather than failing
    loudly)."""
    if not site_url:
        logger.error("GSC not configured — set GSC_SITE_URL in .env")
        return None

    token = get_access_token(SCOPE)
    if token is None:
        return None

    encoded_site = urllib.parse.quote(site_url, safe="")
    url = f"https://www.googleapis.com/webmasters/v3/sites/{encoded_site}/searchAnalytics/query"
    body = {
        "startDate": start_date.isoformat(),
        "endDate": end_date.isoformat(),
        "dimensions": [dimension],
        "rowLimit": row_limit,
    }

    def _do_request():
        response = requests.post(
            url, json=body, headers={"Authorization": f"Bearer {token}"}, timeout=TIMEOUT_SECONDS
        )
        response.raise_for_status()
        return response

    try:
        response = with_retry(_do_request, max_attempts=3, retry_on=(requests.RequestException,))
        data = response.json()
    except Exception:
        logger.exception("GSC searchAnalytics.query failed (site=%s, dimension=%s)", site_url, dimension)
        return None

    return data.get("rows", [])


def fetch_search_analytics(
    start_date: date_cls, end_date: date_cls, row_limit: int = 100, site_url: Optional[str] = None
) -> Optional[List[GscQueryRow]]:
    """Query-dimension pull — see _query_search_analytics for the shared
    request/auth/error-handling this and fetch_search_analytics_by_page
    both build on."""
    rows = _query_search_analytics(start_date, end_date, "query", row_limit, site_url)
    if rows is None:
        return None
    return [
        GscQueryRow(
            query=(row.get("keys") or [""])[0],
            clicks=int(row.get("clicks", 0)),
            impressions=int(row.get("impressions", 0)),
            ctr=float(row.get("ctr", 0.0)),
            position=float(row.get("position", 0.0)),
        )
        for row in rows
    ]


def fetch_search_analytics_by_page(
    start_date: date_cls, end_date: date_cls, row_limit: int = 100, site_url: Optional[str] = None
) -> Optional[List[GscPageRow]]:
    """Page-dimension pull — per-URL clicks/impressions/CTR/position,
    the data the query-dimension pull above can't give you (a query row
    says nothing about which page ranked for it). Feeds both "CTR by page"
    reporting and the meta-rewrite opportunity detector (ai/seo_master_
    agent.py's meta_opportunity_node), which needs a real page URL to
    draft a rewrite against."""
    rows = _query_search_analytics(start_date, end_date, "page", row_limit, site_url)
    if rows is None:
        return None
    return [
        GscPageRow(
            page=(row.get("keys") or [""])[0],
            clicks=int(row.get("clicks", 0)),
            impressions=int(row.get("impressions", 0)),
            ctr=float(row.get("ctr", 0.0)),
            position=float(row.get("position", 0.0)),
        )
        for row in rows
    ]


def _fetch_by_dimension(
    dimension: str, start_date: date_cls, end_date: date_cls, row_limit: int, site_url: Optional[str]
) -> Optional[List[GscDimensionRow]]:
    rows = _query_search_analytics(start_date, end_date, dimension, row_limit, site_url)
    if rows is None:
        return None
    return [
        GscDimensionRow(
            key=(row.get("keys") or [""])[0],
            clicks=int(row.get("clicks", 0)),
            impressions=int(row.get("impressions", 0)),
            ctr=float(row.get("ctr", 0.0)),
            position=float(row.get("position", 0.0)),
        )
        for row in rows
    ]


def fetch_search_analytics_by_country(
    start_date: date_cls, end_date: date_cls, row_limit: int = 100, site_url: Optional[str] = None
) -> Optional[List[GscDimensionRow]]:
    """Country-dimension pull (ISO 3166-1 alpha-3 codes, Google's own
    convention for this field — e.g. "usa", "gbr", not "US"/"GB")."""
    return _fetch_by_dimension("country", start_date, end_date, row_limit, site_url)


def fetch_search_analytics_by_device(
    start_date: date_cls, end_date: date_cls, row_limit: int = 100, site_url: Optional[str] = None
) -> Optional[List[GscDimensionRow]]:
    """Device-dimension pull — Google's own values are "DESKTOP",
    "MOBILE", "TABLET"."""
    return _fetch_by_dimension("device", start_date, end_date, row_limit, site_url)


def fetch_search_analytics_by_search_appearance(
    start_date: date_cls, end_date: date_cls, row_limit: int = 100, site_url: Optional[str] = None
) -> Optional[List[GscDimensionRow]]:
    """Search-appearance-dimension pull — which rich-result/SERP feature
    type each impression came from (e.g. "AMP_BLUE_LINK", "RICHCARD",
    "VIDEO"). Returns an empty list (not an error) for a property with no
    rows using any non-default search appearance — a real, common,
    honest outcome, not a failure."""
    return _fetch_by_dimension("searchAppearance", start_date, end_date, row_limit, site_url)
