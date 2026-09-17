"""
MODULE 26.6 — GA4 (Google Analytics Data API) client.

Pulls per-page traffic (sessions, bounce rate, conversions) via the
Analytics Data API's runReport endpoint, authenticated through
automation/seo/google_auth.py's shared service-account flow — same
pattern as gsc_client.py.

Module 51 extends the original page-only pull with the same
dimension/date breakdowns gsc_client.py grew for the GSC Performance
dashboard (Module 48/50): traffic source, country, device, and a daily
timeseries — the data behind the "Analytics Performance" panel that
mirrors "Search Console Performance" tab-for-tab, reusing this client's
own established metric set (sessions, bounce rate, conversions) rather
than introducing a new one.
"""
import logging
from dataclasses import dataclass
from datetime import date as date_cls
from typing import List, Optional, Union

import requests

from ai.llm.retry import with_retry
from automation.seo.google_auth import get_access_token

logger = logging.getLogger(__name__)

TIMEOUT_SECONDS = 30
SCOPE = ["https://www.googleapis.com/auth/analytics.readonly"]

# The metrics this client pulls for every dimension below — kept
# identical across all of them so a page/source/country/device row and
# a daily timeseries row all read the same way. Module 54 grew this
# from the original 3 (see module 26.6's original docstring) to the 10
# below — enough to back a real, honestly-populated version of GA4's own
# switchable Home-report metric picker (grouped here as User: active/
# new/total users; Session: sessions/engaged sessions/engagement rate/
# avg. session duration; Event: event count/conversions) rather than
# faking GA4's fuller Ecommerce/Revenue/Page-screen categories this app
# doesn't fetch data for.
_METRICS = [
    {"name": "sessions"},
    {"name": "bounceRate"},
    {"name": "conversions"},
    {"name": "activeUsers"},
    {"name": "newUsers"},
    {"name": "totalUsers"},
    {"name": "eventCount"},
    {"name": "engagementRate"},
    {"name": "engagedSessions"},
    {"name": "averageSessionDuration"},
]


@dataclass
class Ga4PageRow:
    page_path: str
    sessions: int
    bounce_rate: float
    conversions: float
    active_users: int = 0
    new_users: int = 0
    total_users: int = 0
    event_count: int = 0
    engagement_rate: float = 0.0
    engaged_sessions: int = 0
    avg_session_duration: float = 0.0


@dataclass
class Ga4DimensionRow:
    """Shared row shape for the source/country/device dimensions below —
    none of them need a semantically distinct field name; `key` is
    whatever that dimension's value is (a source like "google", a
    country name, or "desktop"/"mobile"/"tablet")."""
    key: str
    sessions: int
    bounce_rate: float
    conversions: float
    active_users: int = 0
    new_users: int = 0
    total_users: int = 0
    event_count: int = 0
    engagement_rate: float = 0.0
    engaged_sessions: int = 0
    avg_session_duration: float = 0.0


@dataclass
class Ga4DateRow:
    date: str
    sessions: int
    bounce_rate: float
    conversions: float
    active_users: int = 0
    new_users: int = 0
    total_users: int = 0
    event_count: int = 0
    engagement_rate: float = 0.0
    engaged_sessions: int = 0
    avg_session_duration: float = 0.0


@dataclass
class Ga4RealtimeCountryRow:
    country: str
    active_users: int


def _run_report(
    dimension: str,
    start_date: Union[str, date_cls],
    end_date: Union[str, date_cls],
    limit: int,
    property_id: Optional[str],
) -> Optional[list]:
    """Shared runReport POST every dimension pull in this module builds
    on — same endpoint, auth, and fixed metric set (_METRICS), only the
    requested dimension and the resulting rows' shape differ. Never
    raises — returns None on failure, same graceful-degrade convention
    as gsc_client.py's _query_search_analytics. start_date/end_date
    accept GA4's own relative date syntax ("7daysAgo", "today") as well
    as a date object or "YYYY-MM-DD" string — passed straight through
    (as .isoformat() for a date object) to the API. property_id is the
    property to query — callers decide whether falling back to the
    global GA4_PROPERTY_ID .env default is safe, same reasoning as
    gsc_client.py's site_url parameter."""
    if not property_id:
        logger.error("GA4 not configured — set GA4_PROPERTY_ID in .env")
        return None

    token = get_access_token(SCOPE)
    if token is None:
        return None

    start = start_date.isoformat() if isinstance(start_date, date_cls) else start_date
    end = end_date.isoformat() if isinstance(end_date, date_cls) else end_date

    url = f"https://analyticsdata.googleapis.com/v1beta/{property_id}:runReport"
    body = {
        "dateRanges": [{"startDate": start, "endDate": end}],
        "dimensions": [{"name": dimension}],
        "metrics": _METRICS,
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
        logger.exception("GA4 runReport failed (property=%s, dimension=%s)", property_id, dimension)
        return None

    return data.get("rows", [])


def fetch_traffic_by_page(
    start_date: Union[str, date_cls] = "7daysAgo",
    end_date: Union[str, date_cls] = "today",
    limit: int = 100,
    property_id: Optional[str] = None,
) -> Optional[List[Ga4PageRow]]:
    """Page-dimension pull — see _run_report for the shared request/
    auth/error-handling every dimension pull here builds on."""
    rows = _run_report("pagePath", start_date, end_date, limit, property_id)
    if rows is None:
        return None
    result = []
    for row in rows:
        dims = row.get("dimensionValues", [])
        metrics = row.get("metricValues", [])
        result.append(
            Ga4PageRow(
                page_path=dims[0]["value"] if dims else "",
                sessions=int(metrics[0]["value"]) if len(metrics) > 0 else 0,
                bounce_rate=float(metrics[1]["value"]) if len(metrics) > 1 else 0.0,
                conversions=float(metrics[2]["value"]) if len(metrics) > 2 else 0.0,
                active_users=int(metrics[3]["value"]) if len(metrics) > 3 else 0,
                new_users=int(metrics[4]["value"]) if len(metrics) > 4 else 0,
                total_users=int(metrics[5]["value"]) if len(metrics) > 5 else 0,
                event_count=int(metrics[6]["value"]) if len(metrics) > 6 else 0,
                engagement_rate=float(metrics[7]["value"]) if len(metrics) > 7 else 0.0,
                engaged_sessions=int(metrics[8]["value"]) if len(metrics) > 8 else 0,
                avg_session_duration=float(metrics[9]["value"]) if len(metrics) > 9 else 0.0,
            )
        )
    return result


def _fetch_by_dimension(
    dimension: str,
    start_date: Union[str, date_cls],
    end_date: Union[str, date_cls],
    limit: int,
    property_id: Optional[str],
) -> Optional[List[Ga4DimensionRow]]:
    rows = _run_report(dimension, start_date, end_date, limit, property_id)
    if rows is None:
        return None
    result = []
    for row in rows:
        dims = row.get("dimensionValues", [])
        metrics = row.get("metricValues", [])
        result.append(
            Ga4DimensionRow(
                key=dims[0]["value"] if dims else "",
                sessions=int(metrics[0]["value"]) if len(metrics) > 0 else 0,
                bounce_rate=float(metrics[1]["value"]) if len(metrics) > 1 else 0.0,
                conversions=float(metrics[2]["value"]) if len(metrics) > 2 else 0.0,
                active_users=int(metrics[3]["value"]) if len(metrics) > 3 else 0,
                new_users=int(metrics[4]["value"]) if len(metrics) > 4 else 0,
                total_users=int(metrics[5]["value"]) if len(metrics) > 5 else 0,
                event_count=int(metrics[6]["value"]) if len(metrics) > 6 else 0,
                engagement_rate=float(metrics[7]["value"]) if len(metrics) > 7 else 0.0,
                engaged_sessions=int(metrics[8]["value"]) if len(metrics) > 8 else 0,
                avg_session_duration=float(metrics[9]["value"]) if len(metrics) > 9 else 0.0,
            )
        )
    return result


def fetch_traffic_by_source(
    start_date: Union[str, date_cls] = "7daysAgo",
    end_date: Union[str, date_cls] = "today",
    limit: int = 100,
    property_id: Optional[str] = None,
) -> Optional[List[Ga4DimensionRow]]:
    """Source-dimension pull (GA4's own `sessionSource` values — e.g.
    "google", "(direct)", "facebook.com" — already human-readable, no
    code-to-label mapping needed unlike GSC's country codes)."""
    return _fetch_by_dimension("sessionSource", start_date, end_date, limit, property_id)


def fetch_traffic_by_country(
    start_date: Union[str, date_cls] = "7daysAgo",
    end_date: Union[str, date_cls] = "today",
    limit: int = 100,
    property_id: Optional[str] = None,
) -> Optional[List[Ga4DimensionRow]]:
    """Country-dimension pull — GA4's `country` values are already full
    country names (e.g. "India"), unlike GSC's ISO alpha-3 codes."""
    return _fetch_by_dimension("country", start_date, end_date, limit, property_id)


def fetch_traffic_by_device(
    start_date: Union[str, date_cls] = "7daysAgo",
    end_date: Union[str, date_cls] = "today",
    limit: int = 100,
    property_id: Optional[str] = None,
) -> Optional[List[Ga4DimensionRow]]:
    """Device-dimension pull — GA4's `deviceCategory` values are
    "desktop", "mobile", "tablet" (lowercase, unlike GSC's UPPERCASE)."""
    return _fetch_by_dimension("deviceCategory", start_date, end_date, limit, property_id)


def fetch_traffic_by_date(
    start_date: Union[str, date_cls] = "7daysAgo",
    end_date: Union[str, date_cls] = "today",
    limit: int = 1000,
    property_id: Optional[str] = None,
) -> Optional[List[Ga4DateRow]]:
    """Date-dimension pull — one row per real calendar day, the data a
    trend chart needs. GA4's `date` dimension comes back as "YYYYMMDD"
    (e.g. "20250910"); reformatted to "YYYY-MM-DD" here so it matches
    gsc_client.fetch_search_analytics_by_date's row shape and the
    frontend's shared day-label formatter. limit defaults far higher
    than the other dimensions since even a 3-month range is only ~90
    rows, well under any real pagination concern, and a truncated trend
    chart would be actively misleading."""
    rows = _run_report("date", start_date, end_date, limit, property_id)
    if rows is None:
        return None
    result = []
    for row in rows:
        dims = row.get("dimensionValues", [])
        metrics = row.get("metricValues", [])
        raw_date = dims[0]["value"] if dims else ""
        iso_date = f"{raw_date[0:4]}-{raw_date[4:6]}-{raw_date[6:8]}" if len(raw_date) == 8 else raw_date
        result.append(
            Ga4DateRow(
                date=iso_date,
                sessions=int(metrics[0]["value"]) if len(metrics) > 0 else 0,
                bounce_rate=float(metrics[1]["value"]) if len(metrics) > 1 else 0.0,
                conversions=float(metrics[2]["value"]) if len(metrics) > 2 else 0.0,
                active_users=int(metrics[3]["value"]) if len(metrics) > 3 else 0,
                new_users=int(metrics[4]["value"]) if len(metrics) > 4 else 0,
                total_users=int(metrics[5]["value"]) if len(metrics) > 5 else 0,
                event_count=int(metrics[6]["value"]) if len(metrics) > 6 else 0,
                engagement_rate=float(metrics[7]["value"]) if len(metrics) > 7 else 0.0,
                engaged_sessions=int(metrics[8]["value"]) if len(metrics) > 8 else 0,
                avg_session_duration=float(metrics[9]["value"]) if len(metrics) > 9 else 0.0,
            )
        )
    return sorted(result, key=lambda r: r.date)


@dataclass
class Ga4EventRow:
    event_name: str
    event_count: int
    total_users: int
    active_users: int
    total_revenue: float
    event_count_per_active_user: float


# Event-name breakdown uses its own metric set rather than _METRICS —
# activeUsers here means something different from the page/source/
# country/device pulls above (per GA4's own definition: how many active
# users triggered THIS specific event at least once, not how many were
# active on the property overall), and totalRevenue only applies at
# this event-dimension level (a per-page or per-day revenue total isn't
# part of this client's scope).
_EVENT_METRICS = [
    {"name": "eventCount"},
    {"name": "totalUsers"},
    {"name": "activeUsers"},
    {"name": "totalRevenue"},
]


def fetch_events(
    start_date: Union[str, date_cls] = "7daysAgo",
    end_date: Union[str, date_cls] = "today",
    limit: int = 25,
    property_id: Optional[str] = None,
) -> Optional[List[Ga4EventRow]]:
    """GA4's own "Events: Event name" report (Life cycle > Engagement >
    Events in the real GA4 UI) — event_count_per_active_user is computed
    here (eventCount / activeUsers) rather than being its own API
    metric, matching how the real report's own column is derived; 0.0
    when a row's activeUsers is 0 rather than dividing by zero. Ordered
    by event count descending, matching the real report's default sort.
    Never raises — returns None on failure, same graceful-degrade
    convention as every other pull in this module."""
    if not property_id:
        logger.error("GA4 not configured — set GA4_PROPERTY_ID in .env")
        return None

    token = get_access_token(SCOPE)
    if token is None:
        return None

    start = start_date.isoformat() if isinstance(start_date, date_cls) else start_date
    end = end_date.isoformat() if isinstance(end_date, date_cls) else end_date

    url = f"https://analyticsdata.googleapis.com/v1beta/{property_id}:runReport"
    body = {
        "dateRanges": [{"startDate": start, "endDate": end}],
        "dimensions": [{"name": "eventName"}],
        "metrics": _EVENT_METRICS,
        "limit": limit,
        "orderBys": [{"metric": {"metricName": "eventCount"}, "desc": True}],
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
        logger.exception("GA4 events runReport failed (property=%s)", property_id)
        return None

    result = []
    for row in data.get("rows", []):
        dims = row.get("dimensionValues", [])
        metrics = row.get("metricValues", [])
        event_count = int(metrics[0]["value"]) if len(metrics) > 0 else 0
        active_users = int(metrics[2]["value"]) if len(metrics) > 2 else 0
        result.append(
            Ga4EventRow(
                event_name=dims[0]["value"] if dims else "",
                event_count=event_count,
                total_users=int(metrics[1]["value"]) if len(metrics) > 1 else 0,
                active_users=active_users,
                total_revenue=float(metrics[3]["value"]) if len(metrics) > 3 else 0.0,
                event_count_per_active_user=(event_count / active_users) if active_users > 0 else 0.0,
            )
        )
    return result


@dataclass
class Ga4RealtimeMinuteRow:
    minutes_ago: int
    active_users: int


@dataclass
class Ga4RealtimeDimensionRow:
    """Shared row shape for the audience/device/page realtime
    breakdowns below — see Ga4DimensionRow's own docstring for the same
    reasoning applied to the non-realtime dimension pulls."""
    key: str
    value: int


def _run_realtime_report(
    dimension: str, metric: str, property_id: Optional[str], limit: int = 10
) -> Optional[list]:
    """Shared runRealtimeReport POST every realtime pull in this module
    builds on — a different endpoint from _run_report's runReport (no
    date range at all; Google itself defines "realtime" as the trailing
    ~30-minute window server-side), but the same auth and graceful-
    degrade convention. Never raises — returns None on failure."""
    if not property_id:
        logger.error("GA4 not configured — set GA4_PROPERTY_ID in .env")
        return None

    token = get_access_token(SCOPE)
    if token is None:
        return None

    url = f"https://analyticsdata.googleapis.com/v1beta/{property_id}:runRealtimeReport"
    body = {"dimensions": [{"name": dimension}], "metrics": [{"name": metric}], "limit": limit}

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
        logger.exception("GA4 runRealtimeReport failed (property=%s, dimension=%s)", property_id, dimension)
        return None

    return data.get("rows", [])


def fetch_realtime_active_users(property_id: Optional[str] = None) -> Optional[List[Ga4RealtimeCountryRow]]:
    """GA4's own "Active users in last 30 minutes" tile plus its country
    breakdown (the real GA4 "Realtime overview" report's map legend).
    Rows are sorted by active users descending, matching the real GA4
    UI's own country table ordering; summing active_users across every
    row reproduces the UI's total (including a "(not set)" row for
    traffic GA4 couldn't geolocate, the same honest behavior the real
    Realtime report shows)."""
    rows = _run_realtime_report("country", "activeUsers", property_id, limit=250)
    if rows is None:
        return None
    result = []
    for row in rows:
        dims = row.get("dimensionValues", [])
        metrics = row.get("metricValues", [])
        result.append(
            Ga4RealtimeCountryRow(
                country=dims[0]["value"] if dims else "(not set)",
                active_users=int(metrics[0]["value"]) if metrics else 0,
            )
        )
    return sorted(result, key=lambda r: r.active_users, reverse=True)


def fetch_realtime_active_users_by_minute(property_id: Optional[str] = None) -> Optional[List[Ga4RealtimeMinuteRow]]:
    """Module 52 follow-up — the "Active users per minute" bar chart on
    GA4's own Realtime overview report, via the `minutesAgo` realtime
    dimension (Google's own values are "00".."29", each row one minute
    in the trailing 30-minute window). Sorted oldest-first (minutes_ago
    29 down to 0) so a left-to-right bar chart reads "-30 min" -> "-1
    min", matching the real report's own axis direction. A minute with
    zero active users simply has no row (GA4 omits empty buckets, not a
    failure) — callers that need a dense 0..29 series should fill gaps
    themselves rather than assume every minute is present."""
    rows = _run_realtime_report("minutesAgo", "activeUsers", property_id, limit=30)
    if rows is None:
        return None
    result = []
    for row in rows:
        dims = row.get("dimensionValues", [])
        metrics = row.get("metricValues", [])
        result.append(
            Ga4RealtimeMinuteRow(
                minutes_ago=int(dims[0]["value"]) if dims else 0,
                active_users=int(metrics[0]["value"]) if metrics else 0,
            )
        )
    return sorted(result, key=lambda r: r.minutes_ago, reverse=True)


def fetch_realtime_by_device(property_id: Optional[str] = None, limit: int = 10) -> Optional[List[Ga4RealtimeDimensionRow]]:
    """Active users by device category right now — `deviceCategory` is a
    documented realtime dimension; unlike GA4's UI-only "First user
    source" tile (not a Data API realtime dimension at all — omitted
    here rather than faked against an endpoint that doesn't support
    it), device breakdown is real, verifiable data."""
    rows = _run_realtime_report("deviceCategory", "activeUsers", property_id, limit=limit)
    if rows is None:
        return None
    result = []
    for row in rows:
        dims = row.get("dimensionValues", [])
        metrics = row.get("metricValues", [])
        result.append(
            Ga4RealtimeDimensionRow(
                key=dims[0]["value"] if dims else "",
                value=int(metrics[0]["value"]) if metrics else 0,
            )
        )
    return sorted(result, key=lambda r: r.value, reverse=True)


def fetch_realtime_by_page(property_id: Optional[str] = None, limit: int = 10) -> Optional[List[Ga4RealtimeDimensionRow]]:
    """GA4's own "Views by Page title and screen name" realtime tile —
    `unifiedScreenName` dimension, `screenPageViews` metric (both
    documented realtime-report fields)."""
    rows = _run_realtime_report("unifiedScreenName", "screenPageViews", property_id, limit=limit)
    if rows is None:
        return None
    result = []
    for row in rows:
        dims = row.get("dimensionValues", [])
        metrics = row.get("metricValues", [])
        result.append(
            Ga4RealtimeDimensionRow(
                key=dims[0]["value"] if dims else "(not set)",
                value=int(metrics[0]["value"]) if metrics else 0,
            )
        )
    return sorted(result, key=lambda r: r.value, reverse=True)


def fetch_realtime_by_audience(property_id: Optional[str] = None, limit: int = 10) -> Optional[List[Ga4RealtimeDimensionRow]]:
    """GA4's own "Active users by Audience" realtime tile —
    `audienceName` dimension. Returns an empty list (not an error) for a
    property with no GA4 Audiences configured — a real, honest outcome
    (the real GA4 UI shows "No data available" for the same reason), not
    a failure."""
    rows = _run_realtime_report("audienceName", "activeUsers", property_id, limit=limit)
    if rows is None:
        return None
    result = []
    for row in rows:
        dims = row.get("dimensionValues", [])
        metrics = row.get("metricValues", [])
        result.append(
            Ga4RealtimeDimensionRow(
                key=dims[0]["value"] if dims else "",
                value=int(metrics[0]["value"]) if metrics else 0,
            )
        )
    return sorted(result, key=lambda r: r.value, reverse=True)
