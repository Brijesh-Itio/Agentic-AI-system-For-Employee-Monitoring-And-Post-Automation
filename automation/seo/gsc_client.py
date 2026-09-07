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


def fetch_search_analytics(
    start_date: date_cls, end_date: date_cls, row_limit: int = 100, site_url: Optional[str] = None
) -> Optional[List[GscQueryRow]]:
    """Never raises — returns None on failure (unconfigured, auth,
    network, or an unverified/mistyped site property), matching this
    codebase's graceful-degrade convention. site_url is the property to
    query — callers decide whether falling back to the global
    GSC_SITE_URL .env default is safe (agent.database.count_active_seo_
    sites() <= 1; see its docstring for why that check matters — this
    function deliberately does NOT fall back to settings on its own,
    since a wrong-but-real property would silently return real data
    attributed to the wrong site rather than failing loudly)."""
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
        "dimensions": ["query"],
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
        logger.exception("GSC searchAnalytics.query failed (site=%s)", site_url)
        return None

    rows = data.get("rows", [])
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
