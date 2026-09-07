"""
MODULE 26.6 — GA4 (Google Analytics Data API) client.

Pulls per-page traffic (sessions, bounce rate, conversions) via the
Analytics Data API's runReport endpoint, authenticated through
automation/seo/google_auth.py's shared service-account flow — same
pattern as gsc_client.py.
"""
import logging
from dataclasses import dataclass
from typing import List, Optional

import requests

from ai.llm.retry import with_retry
from automation.seo.google_auth import get_access_token

logger = logging.getLogger(__name__)

TIMEOUT_SECONDS = 30
SCOPE = ["https://www.googleapis.com/auth/analytics.readonly"]


@dataclass
class Ga4PageRow:
    page_path: str
    sessions: int
    bounce_rate: float
    conversions: float


def fetch_traffic_by_page(
    start_date: str = "7daysAgo", end_date: str = "today", limit: int = 100, property_id: Optional[str] = None
) -> Optional[List[Ga4PageRow]]:
    """start_date/end_date accept GA4's own relative date syntax
    ("7daysAgo", "today", "yesterday") as well as YYYY-MM-DD — passed
    straight through to the API. Never raises — returns None on failure,
    same graceful-degrade convention as gsc_client.py. property_id is the
    property to query — callers decide whether falling back to the
    global GA4_PROPERTY_ID .env default is safe (see gsc_client.py's
    matching note and agent.database.count_active_seo_sites' docstring:
    this function deliberately doesn't fall back to settings on its own,
    since a wrong-but-real property would silently return real data
    attributed to the wrong site rather than failing loudly)."""
    if not property_id:
        logger.error("GA4 not configured — set GA4_PROPERTY_ID in .env")
        return None

    token = get_access_token(SCOPE)
    if token is None:
        return None

    url = f"https://analyticsdata.googleapis.com/v1beta/{property_id}:runReport"
    body = {
        "dateRanges": [{"startDate": start_date, "endDate": end_date}],
        "dimensions": [{"name": "pagePath"}],
        "metrics": [{"name": "sessions"}, {"name": "bounceRate"}, {"name": "conversions"}],
        "limit": limit,
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
        logger.exception("GA4 runReport failed (property=%s)", property_id)
        return None

    rows = []
    for row in data.get("rows", []):
        dims = row.get("dimensionValues", [])
        metrics = row.get("metricValues", [])
        rows.append(
            Ga4PageRow(
                page_path=dims[0]["value"] if dims else "",
                sessions=int(metrics[0]["value"]) if len(metrics) > 0 else 0,
                bounce_rate=float(metrics[1]["value"]) if len(metrics) > 1 else 0.0,
                conversions=float(metrics[2]["value"]) if len(metrics) > 2 else 0.0,
            )
        )
    return rows
