"""
MODULE 36 — Google Sheets live command-centre integration.

Closes the "no Google Sheets integration" gap found in a verification
audit against the SEO blueprint. Reuses the exact same service-account
credentials already live-verified for GSC/GA4 (automation/seo/
google_auth.py) — no new credential setup needed, just a broader scope
(spreadsheets + drive.file, so the same account can create a sheet AND
share it with a real Google account, since a service account has no
normal "My Drive" a human can just open).

Real REST calls against the Sheets API v4 and Drive API v3, no SDK —
verified against Google's current API reference docs this session, not
guessed:
  - POST https://sheets.googleapis.com/v4/spreadsheets            (create)
  - POST .../spreadsheets/{id}/values/{range}:append               (write)
  - POST https://www.googleapis.com/drive/v3/files/{id}/permissions (share)

One spreadsheet total, not one per site — matches the blueprint's own
"live SEO command centre" framing (one dashboard, not N dashboards). Its
id is created once and remembered in app_settings (agent/database.py)
so repeated calls reuse the same sheet rather than creating a new one
every time.
"""
import logging
import urllib.parse
from typing import Optional

import requests

from agent import database
from ai.llm.retry import with_retry
from api.config import settings
from automation.seo.google_auth import get_access_token

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]
SHEETS_BASE_URL = "https://sheets.googleapis.com/v4/spreadsheets"
DRIVE_BASE_URL = "https://www.googleapis.com/drive/v3/files"
TIMEOUT_SECONDS = 30

# Module 56 — separate spreadsheets instead of one shared one: "main"
# (the automated daily pipeline's own logs — Rank Tracker, CWV, Issue
# Log, etc.), "gsc", "ga4", and (Module 57) "overview" — one per
# interactive "Export to Sheets" dashboard. Google gives service
# accounts created after April 2025 zero Drive storage quota (see
# adopt_existing_spreadsheet's docstring), so none of these can actually
# be auto-created by this app — each is adopted the same way, just
# against its own kind. Every per-spreadsheet setting below is keyed by
# kind rather than being a single flat constant.
SPREADSHEET_KINDS = ("main", "gsc", "ga4", "overview")

SPREADSHEET_ID_SETTING_KEYS = {
    "main": "seo_sheets_spreadsheet_id",
    "gsc": "seo_sheets_gsc_spreadsheet_id",
    "ga4": "seo_sheets_ga4_spreadsheet_id",
    "overview": "seo_sheets_overview_spreadsheet_id",
}
# Comma-joined tab names already confirmed present in the spreadsheet —
# lets get_or_create_spreadsheet skip the extra spreadsheets.get/
# batchUpdate round-trip on every single _log_to_sheet call (one per
# pipeline log line) and only pay for it once, the first time after this
# kind's own tab list gains a new entry this installation hasn't seen yet.
SPREADSHEET_TABS_ENSURED_SETTING_KEYS = {
    "main": "seo_sheets_tabs_ensured",
    "gsc": "seo_sheets_gsc_tabs_ensured",
    "ga4": "seo_sheets_ga4_tabs_ensured",
    "overview": "seo_sheets_overview_tabs_ensured",
}
SPREADSHEET_TITLES = {
    "main": "WorkPulse AI — SEO Command Centre",
    "gsc": "WorkPulse AI — Search Console",
    "ga4": "WorkPulse AI — Analytics (GA4)",
    "overview": "WorkPulse AI — Overview Report",
}
# The tab a bare "open spreadsheet" link should deep-link into for each
# kind — see _sheet_open_url in api/routes/seo.py.
SPREADSHEET_DEFAULT_TAB = {
    "main": "Meta Tag Audit",
    "gsc": "GSC Queries",
    "ga4": "GA4 Pages",
    "overview": "Overview Top Queries",
}

_MAIN_TABS = [
    "Rank Tracker",
    "CWV Monitor",
    "Content Pipeline",
    "Issue Log",
    "Link Monitor",
    "Daily Digest Archive",
    # Module 39 — page-dimension GSC data, automated index-drop alerts,
    # and the CTR-opportunity meta-rewrite queue.
    "Page CTR Tracker",
    "Index Alerts",
    "Meta Rewrite Queue",
    # Module 45 — one row per page audited (whole-site or single-page),
    # the flat tag-value export requested on top of the pending-issue
    # queue: what a page's own <head> tags actually say right now, not
    # just which ones are broken.
    "Meta Tag Audit",
]

# Module 57 — the site Overview dashboard's own "download this report"
# button (Top Search Queries / Top Traffic Pages / CTR by Page / Rank
# Alerts). Overwritten on each export (see overwrite_rows), not
# appended — a clean current snapshot, same convention as the GSC/GA4
# dimension exports. Its own dedicated spreadsheet — this dashboard
# blends GSC and GA4 data, so it doesn't belong in either of their
# spreadsheets, and a human adopts it the same way as gsc/ga4 (see
# /sheets/adopt).
_OVERVIEW_TABS = [
    "Overview Top Queries",
    "Overview Top Traffic Pages",
    "Overview CTR by Page",
    "Overview Rank Alerts",
]

# Module 50/50-followup — a manual "Export to Google Sheets" button on
# the GSC Performance report (Queries/Pages/Countries/Devices/Search
# Appearance), distinct from Rank Tracker/Page CTR Tracker above (which
# the automated daily pipeline writes to on its own schedule, and stays
# in the "main" spreadsheet — this app's own logs, not a GSC export).
# One clean tab per dimension, matching the real Search Console UI's own
# per-dimension tables, overwritten on each export (see overwrite_rows)
# rather than appended. Module 56 moved these into their own dedicated
# spreadsheet, separate from GA4's.
_GSC_TABS = [
    "GSC Performance Export",
    "GSC Chart",
    "GSC Queries",
    "GSC Pages",
    "GSC Countries",
    "GSC Devices",
    "GSC Search Appearance",
]

# Module 51/51-followup — GA4's own "Export to Google Sheets", the same
# one-clean-tab-per-dimension treatment as _GSC_TABS above. Module 55
# added "GA4 Events" (GA4's own "Events: Event name" report); module 56
# moved all of these into their own dedicated spreadsheet, separate from
# GSC's.
_GA4_TABS = [
    "GA4 Chart",
    "GA4 Pages",
    "GA4 Sources",
    "GA4 Countries",
    "GA4 Devices",
    "GA4 Events",
]

TABS_BY_KIND = {"main": _MAIN_TABS, "gsc": _GSC_TABS, "ga4": _GA4_TABS, "overview": _OVERVIEW_TABS}
# Every tab name across all kinds, flattened — used by
# _ensure_tab_headers/_TAB_KIND below, which don't care which kind a tab
# belongs to, just whether it's present in the spreadsheet they're
# looking at.
TABS = _MAIN_TABS + _GSC_TABS + _GA4_TABS + _OVERVIEW_TABS
# Reverse lookup so append_rows/overwrite_rows/write_chart_tab can take
# just a tab name (same call signature every existing caller already
# uses) and resolve which spreadsheet it actually belongs in, instead of
# every caller needing to know/pass a kind.
_TAB_KIND = {tab: kind for kind, tabs in TABS_BY_KIND.items() for tab in tabs}


def _kind_for_tab(tab_name: str) -> str:
    return _TAB_KIND.get(tab_name, "main")

# Each tab's header row, written once when the tab is created — matches
# the PDF blueprint's own column descriptions for each sheet.
TAB_HEADERS = {
    "Rank Tracker": ["Date", "Site", "Query", "Clicks", "Impressions", "Position"],
    "CWV Monitor": ["Date", "Site", "URL", "Performance Score", "LCP (ms)", "CLS", "INP (ms)"],
    "Content Pipeline": ["Date", "Site", "Topic", "Title", "Status", "Structure Passed"],
    "Issue Log": ["Date", "Site", "Rule", "Severity", "Status", "Message"],
    "Link Monitor": ["Date", "Site", "Source URL", "Anchor Text", "Status"],
    "Daily Digest Archive": ["Date", "Site", "Narrative"],
    "Page CTR Tracker": ["Date", "Site", "Page", "Clicks", "Impressions", "CTR", "Position"],
    "Index Alerts": ["Date", "Site", "URL", "Previous Status", "New Status"],
    "Meta Rewrite Queue": ["Date", "Site", "Page", "Impressions", "Clicks", "CTR"],
    "Meta Tag Audit": [
        "Date",
        "Site",
        "URL",
        "Title",
        "Description",
        "Keywords",
        "Author",
        "Publisher",
        "Copyright",
        "Subject",
        "Robots",
        "Canonical",
        "OG Tags",
        "Hreflang x-default",
        "JSON-LD Types",
    ],
    "Overview Top Queries": ["Query", "Clicks", "Impressions", "CTR", "Avg. Position"],
    "Overview Top Traffic Pages": ["Page", "Sessions", "Bounce Rate", "Conversions"],
    "Overview CTR by Page": ["Page", "Clicks", "Impressions", "CTR", "Avg. Position"],
    "Overview Rank Alerts": ["Query", "Previous Position", "Current Position", "Delta"],
    "GSC Performance Export": [
        "Exported At",
        "Site",
        "View",
        "Date Range",
        "Row",
        "Clicks",
        "Impressions",
        "CTR",
        "Avg. Position",
    ],
    "GSC Chart": ["Date", "Clicks", "Impressions", "CTR", "Avg. Position"],
    "GSC Queries": ["Query", "Clicks", "Impressions", "CTR", "Avg. Position"],
    "GSC Pages": ["Page", "Clicks", "Impressions", "CTR", "Avg. Position"],
    "GSC Countries": ["Country", "Clicks", "Impressions", "CTR", "Avg. Position"],
    "GSC Devices": ["Device", "Clicks", "Impressions", "CTR", "Avg. Position"],
    "GSC Search Appearance": ["Search Appearance", "Clicks", "Impressions", "CTR", "Avg. Position"],
    "GA4 Chart": ["Date", "Sessions", "Bounce Rate", "Conversions"],
    "GA4 Pages": ["Page", "Sessions", "Bounce Rate", "Conversions"],
    "GA4 Sources": ["Source", "Sessions", "Bounce Rate", "Conversions"],
    "GA4 Countries": ["Country", "Sessions", "Bounce Rate", "Conversions"],
    "GA4 Devices": ["Device", "Sessions", "Bounce Rate", "Conversions"],
    "GA4 Events": ["Event Name", "Event Count", "Total Users", "Event Count Per Active User", "Total Revenue"],
}


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _ensure_tab_headers(spreadsheet_id: str, token: str) -> list:
    """Ensures every tab in TABS has its correct header row at row 1 —
    self-healing, not just "write it once when the tab is first added."
    Verified live that a real gap existed here: adopt_existing_spreadsheet
    only ever wrote a header for a tab _add_missing_tabs newly created;
    a tab that already existed at adoption time (or in one real case, a
    tab that existed but had a data row appended to it before its header
    write ever ran) was silently left with no header at all, forever,
    since nothing ever re-checked it. This checks row 1 of every tab
    against TAB_HEADERS and fixes whatever doesn't match:
      - row 1 empty or wrong → not holding real data → header written
        directly into it.
      - row 1 already holds real data (the actual case found live: an
        audit row had landed in A1 because no header write had ever
        succeeded for that tab) → a fresh row is inserted above it first
        via batchUpdate, so the header is added without destroying that
        data.
    Never raises — logs and skips whatever tab it can't fix, so one bad
    tab doesn't block the others. Returns the list of tab names actually
    changed."""
    def _do_get():
        response = requests.get(f"{SHEETS_BASE_URL}/{spreadsheet_id}", headers=_headers(token), timeout=TIMEOUT_SECONDS)
        response.raise_for_status()
        return response

    try:
        meta = with_retry(_do_get, max_attempts=3, retry_on=(requests.RequestException,)).json()
    except Exception:
        logger.exception("_ensure_tab_headers: could not read spreadsheet %s metadata", spreadsheet_id)
        return []

    sheet_props_by_title = {s["properties"]["title"]: s["properties"] for s in meta.get("sheets", [])}

    fixed = []
    for tab_name, header in TAB_HEADERS.items():
        props = sheet_props_by_title.get(tab_name)
        if props is None:
            continue  # doesn't exist yet — the caller creates it separately

        last_col = chr(ord("A") + len(header) - 1)
        quoted_range = urllib.parse.quote(f"'{tab_name}'!A1:{last_col}1", safe="")

        try:
            row1_response = requests.get(
                f"{SHEETS_BASE_URL}/{spreadsheet_id}/values/{quoted_range}", headers=_headers(token), timeout=TIMEOUT_SECONDS
            )
            row1_response.raise_for_status()
            current_row1 = (row1_response.json().get("values") or [[]])[0]
        except Exception:
            logger.exception("_ensure_tab_headers: could not read row 1 of %r", tab_name)
            continue

        if current_row1 == header:
            continue

        if current_row1:
            try:
                insert_response = requests.post(
                    f"{SHEETS_BASE_URL}/{spreadsheet_id}:batchUpdate",
                    json={
                        "requests": [
                            {
                                "insertDimension": {
                                    "range": {"sheetId": props["sheetId"], "dimension": "ROWS", "startIndex": 0, "endIndex": 1}
                                }
                            }
                        ]
                    },
                    headers=_headers(token),
                    timeout=TIMEOUT_SECONDS,
                )
                insert_response.raise_for_status()
            except Exception:
                logger.exception("_ensure_tab_headers: could not insert a header row for %r", tab_name)
                continue

        try:
            update_response = requests.put(
                f"{SHEETS_BASE_URL}/{spreadsheet_id}/values/{quoted_range}",
                params={"valueInputOption": "RAW"},
                json={"values": [header]},
                headers=_headers(token),
                timeout=TIMEOUT_SECONDS,
            )
            update_response.raise_for_status()
            fixed.append(tab_name)
        except Exception:
            logger.exception("_ensure_tab_headers: could not write header for %r", tab_name)

    return fixed


def _add_missing_tabs(spreadsheet_id: str, token: str, tabs: list) -> list:
    """Reads the spreadsheet's current tabs, adds whichever of `tabs`
    isn't already there, then ensures EVERY tab (newly added or already
    existing, across all three kinds — see _ensure_tab_headers) has its
    correct header. Shared by get_or_create_spreadsheet's self-heal path
    (a spreadsheet created before its kind's tab list grew a new entry)
    and adopt_existing_spreadsheet (a human-created sheet that never had
    any of `tabs` to begin with). Raises on the tab-creation step —
    callers decide how to degrade (get_or_create_spreadsheet treats it
    as non-fatal and returns the id anyway; the pipeline still
    functions, just without the new tabs until this succeeds on a later
    call). Header-writing never raises — see _ensure_tab_headers."""
    def _do_get():
        response = requests.get(f"{SHEETS_BASE_URL}/{spreadsheet_id}", headers=_headers(token), timeout=TIMEOUT_SECONDS)
        response.raise_for_status()
        return response

    meta = with_retry(_do_get, max_attempts=3, retry_on=(requests.RequestException,)).json()
    existing_titles = {s["properties"]["title"] for s in meta.get("sheets", [])}
    missing = [name for name in tabs if name not in existing_titles]

    if missing:
        add_requests = [{"addSheet": {"properties": {"title": name}}} for name in missing]

        def _do_batch_update():
            response = requests.post(
                f"{SHEETS_BASE_URL}/{spreadsheet_id}:batchUpdate",
                json={"requests": add_requests},
                headers=_headers(token),
                timeout=TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            return response

        with_retry(_do_batch_update, max_attempts=3, retry_on=(requests.RequestException,))

    _ensure_tab_headers(spreadsheet_id, token)

    return missing


def get_tab_url(spreadsheet_id: str, tab_name: str) -> Optional[str]:
    """A deep link straight into one specific tab (…#gid=<id>), not just
    the spreadsheet root. Real, observed reason this matters: opening the
    bare spreadsheet URL lands on whatever tab the browser last had
    active — for a first-time visitor that's index-0 ("Sheet1", a human's
    own pre-existing blank tab in the adopt-an-existing-sheet flow), which
    made a spreadsheet with real data on "Meta Tag Audit" look completely
    empty. Never raises — returns None on any failure (network, tab not
    found), in which case a caller should fall back to the bare
    spreadsheet URL rather than break the link entirely."""
    token = get_access_token(SCOPES)
    if token is None:
        return None
    try:
        response = requests.get(f"{SHEETS_BASE_URL}/{spreadsheet_id}", headers=_headers(token), timeout=TIMEOUT_SECONDS)
        response.raise_for_status()
        meta = response.json()
    except Exception:
        logger.exception("get_tab_url: could not read spreadsheet %s metadata", spreadsheet_id)
        return None

    for sheet in meta.get("sheets", []):
        props = sheet.get("properties", {})
        if props.get("title") == tab_name:
            return f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit#gid={props['sheetId']}"
    return None


def get_or_create_spreadsheet(kind: str = "main", share_with_email: Optional[str] = None) -> Optional[str]:
    """Never raises — returns None on any failure (no service account,
    Sheets/Drive API not enabled for the project, network — and in
    practice, for a first-ever call, the zero-Drive-quota rejection
    adopt_existing_spreadsheet's docstring covers), matching this
    codebase's graceful-degrade convention. kind selects which of the
    three spreadsheets (SPREADSHEET_KINDS) — defaults to "main" so every
    pre-existing caller that never passed a kind keeps working exactly
    as before. share_with_email defaults to settings.SEO_SHEETS_SHARE_EMAIL
    (configurable, not hardcoded — a real Google account, set by whoever
    runs this app) and is only used the moment the spreadsheet is first
    created; call share_spreadsheet() directly to (re-)share an already-
    existing one, e.g. after changing SEO_SHEETS_SHARE_EMAIL."""
    share_with_email = share_with_email or settings.SEO_SHEETS_SHARE_EMAIL or None
    id_key = SPREADSHEET_ID_SETTING_KEYS[kind]
    tabs = TABS_BY_KIND[kind]

    existing_id = database.get_app_setting(id_key)
    if existing_id:
        _ensure_tabs_cached(existing_id, kind)
        return existing_id

    token = get_access_token(SCOPES)
    if token is None:
        return None

    body = {
        "properties": {"title": SPREADSHEET_TITLES[kind]},
        "sheets": [{"properties": {"title": name}} for name in tabs],
    }

    def _do_create():
        response = requests.post(SHEETS_BASE_URL, json=body, headers=_headers(token), timeout=TIMEOUT_SECONDS)
        response.raise_for_status()
        return response

    try:
        response = with_retry(_do_create, max_attempts=3, retry_on=(requests.RequestException,))
        spreadsheet_id = response.json().get("spreadsheetId")
    except Exception:
        logger.exception("Failed to create the %r spreadsheet", kind)
        return None

    if not spreadsheet_id:
        return None

    database.set_app_setting(id_key, spreadsheet_id)
    database.set_app_setting(SPREADSHEET_TABS_ENSURED_SETTING_KEYS[kind], ",".join(tabs))

    # Header rows — best-effort, a failure here doesn't invalidate the
    # spreadsheet itself. Only this kind's own tabs — append_row below
    # resolves each tab name back to its owning spreadsheet on its own,
    # so writing every kind's headers here would just be wasted calls.
    for tab_name in tabs:
        append_row(tab_name, TAB_HEADERS[tab_name])

    if share_with_email:
        share_spreadsheet(spreadsheet_id, share_with_email)

    logger.info("Created %r spreadsheet: %s", kind, spreadsheet_id)
    return spreadsheet_id


def _ensure_tabs_cached(spreadsheet_id: str, kind: str = "main") -> None:
    """Best-effort, cached self-heal for get_or_create_spreadsheet: skips
    entirely once every one of this kind's tabs has been confirmed
    present (the common case, checked via app_settings rather than
    re-querying the Sheets API on every call), otherwise adds whatever's
    missing and updates the cache. Never raises — a failure here just
    means the new tabs stay missing until a later call succeeds; it must
    not break the pipeline log line that triggered this check."""
    tabs = TABS_BY_KIND[kind]
    tabs_ensured_key = SPREADSHEET_TABS_ENSURED_SETTING_KEYS[kind]
    ensured = database.get_app_setting(tabs_ensured_key)
    if ensured and set(tabs) <= set(ensured.split(",")):
        return

    token = get_access_token(SCOPES)
    if token is None:
        return

    try:
        _add_missing_tabs(spreadsheet_id, token, tabs)
        database.set_app_setting(tabs_ensured_key, ",".join(tabs))
    except Exception:
        logger.exception("Could not confirm/add tabs for spreadsheet %s — will retry on a later call", spreadsheet_id)


def adopt_existing_spreadsheet(spreadsheet_id: str, kind: str = "main") -> bool:
    """Module 36 follow-up — service accounts created after April 2025
    have zero Google Drive storage quota, so spreadsheets.create is
    rejected with a 403 no matter how the scopes/APIs are configured
    (verified live this session). The real fix: a human creates a
    normal Google Sheet in their own Drive (which has quota) and shares
    it with the service account as Editor — the service account can
    then read/write an EXISTING file it doesn't own without needing any
    quota of its own. This adopts that sheet for the given kind: adds
    any of that kind's own tabs that don't already exist in it (leaving
    whatever's already there alone, including a default 'Sheet1'),
    writes each new tab's header row, and remembers the id the same way
    get_or_create_spreadsheet would have. Module 56 — kind defaults to
    "main" so the one spreadsheet already adopted before this module
    keeps working without every caller needing an update; the GSC/GA4
    "Export to Sheets" flows now adopt their own separate sheets by
    passing kind="gsc"/"ga4" explicitly. Never raises — returns False on
    failure (not shared with the service account yet, wrong id,
    network)."""
    token = get_access_token(SCOPES)
    if token is None:
        return False

    tabs = TABS_BY_KIND[kind]
    try:
        missing = _add_missing_tabs(spreadsheet_id, token, tabs)
    except Exception:
        logger.exception("Could not adopt spreadsheet %s — check it's shared with the service account", spreadsheet_id)
        return False

    database.set_app_setting(SPREADSHEET_ID_SETTING_KEYS[kind], spreadsheet_id)
    database.set_app_setting(SPREADSHEET_TABS_ENSURED_SETTING_KEYS[kind], ",".join(tabs))

    logger.info("Adopted existing spreadsheet %s as %r — added tabs: %s", spreadsheet_id, kind, missing or "(none needed)")
    return True


def share_spreadsheet(spreadsheet_id: str, email: str) -> bool:
    """Grants writer access to a real Google account — required for a
    human to ever see this sheet at all, since a service account has no
    normal Drive a person can browse to. Never raises — returns False on
    failure."""
    token = get_access_token(SCOPES)
    if token is None:
        return False

    def _do_share():
        response = requests.post(
            f"{DRIVE_BASE_URL}/{spreadsheet_id}/permissions",
            json={"role": "writer", "type": "user", "emailAddress": email},
            headers=_headers(token),
            timeout=TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return response

    try:
        with_retry(_do_share, max_attempts=3, retry_on=(requests.RequestException,))
        return True
    except Exception:
        logger.exception("Failed to share spreadsheet %s with %s", spreadsheet_id, email)
        return False


def append_rows(sheet_name: str, rows: list) -> bool:
    """Appends multiple rows to the named tab in ONE API call — used
    wherever many rows need writing at once (e.g. one row per page from
    a whole-site audit) so logging a 30-page crawl doesn't cost 30
    sequential HTTP round-trips. Never raises — returns False on any
    failure (spreadsheet not yet created, tab doesn't exist, auth
    failure), so a caller can log/skip rather than let a Sheets hiccup
    break the pipeline step that's trying to log to it. rows=[] is a
    no-op success, not a failure — nothing to write isn't an error."""
    if not rows:
        return True

    kind = _kind_for_tab(sheet_name)
    spreadsheet_id = database.get_app_setting(SPREADSHEET_ID_SETTING_KEYS[kind])
    if not spreadsheet_id:
        logger.warning(
            "append_rows(%s): no %r spreadsheet created yet — call get_or_create_spreadsheet(%r) first", sheet_name, kind, kind
        )
        return False

    token = get_access_token(SCOPES)
    if token is None:
        return False

    url = f"{SHEETS_BASE_URL}/{spreadsheet_id}/values/{sheet_name}:append"

    def _do_append():
        response = requests.post(
            url,
            params={"valueInputOption": "USER_ENTERED"},
            json={"values": [[str(cell) for cell in row] for row in rows]},
            headers=_headers(token),
            timeout=TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return response

    try:
        with_retry(_do_append, max_attempts=3, retry_on=(requests.RequestException,))
        return True
    except Exception:
        logger.exception("Failed to append %d row(s) to %r", len(rows), sheet_name)
        return False


def append_row(sheet_name: str, row: list) -> bool:
    """Appends one row to the named tab — see append_rows for the
    multi-row version this delegates to."""
    return append_rows(sheet_name, [row])


def overwrite_rows(sheet_name: str, header: list, rows: list) -> bool:
    """Replaces a tab's ENTIRE contents with header + rows — a clean
    current-state snapshot (matches the real Search Console UI's own
    per-dimension tables), unlike append_rows/append_row which keep
    growing a historical log. Used by the GSC "Export to Sheets" feature's
    per-dimension tabs (GSC Queries/Pages/Countries/Devices/Search
    Appearance): every export re-clears the tab first so stale rows from
    a previous export/date-range never linger next to fresh ones. Never
    raises — returns False on any failure (spreadsheet not yet created,
    tab doesn't exist, auth failure)."""
    kind = _kind_for_tab(sheet_name)
    spreadsheet_id = database.get_app_setting(SPREADSHEET_ID_SETTING_KEYS[kind])
    if not spreadsheet_id:
        logger.warning(
            "overwrite_rows(%s): no %r spreadsheet created yet — call get_or_create_spreadsheet(%r) first", sheet_name, kind, kind
        )
        return False

    token = get_access_token(SCOPES)
    if token is None:
        return False

    quoted_tab = urllib.parse.quote(f"'{sheet_name}'", safe="")
    quoted_a1 = urllib.parse.quote(f"'{sheet_name}'!A1", safe="")

    def _do_clear():
        response = requests.post(
            f"{SHEETS_BASE_URL}/{spreadsheet_id}/values/{quoted_tab}:clear",
            headers=_headers(token),
            timeout=TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return response

    def _do_write():
        response = requests.put(
            f"{SHEETS_BASE_URL}/{spreadsheet_id}/values/{quoted_a1}",
            params={"valueInputOption": "USER_ENTERED"},
            json={"values": [header] + [[str(cell) for cell in row] for row in rows]},
            headers=_headers(token),
            timeout=TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return response

    try:
        with_retry(_do_clear, max_attempts=3, retry_on=(requests.RequestException,))
        with_retry(_do_write, max_attempts=3, retry_on=(requests.RequestException,))
        return True
    except Exception:
        logger.exception("Failed to overwrite %r with %d row(s)", sheet_name, len(rows))
        return False


def write_chart_tab(sheet_name: str, header: list, rows: list, chart_title: str, series_cols: list) -> bool:
    """overwrite_rows, plus a real embedded Google Sheets line chart on
    that same tab — column 0 is the chart's domain (e.g. Date),
    series_cols are 0-based column indices to plot as series (e.g. [1, 2]
    for Clicks/Impressions). Matches the real Search Console UI's own
    "Export > Google Sheets" feature, which puts a "Chart" tab first,
    ahead of the per-dimension tabs. Any chart already on the tab from a
    previous export is deleted first, so re-exporting a new date range
    doesn't pile up stale charts next to the fresh one. Never raises —
    returns False on any failure; a chart-embed failure doesn't undo the
    already-written data rows."""
    if not overwrite_rows(sheet_name, header, rows):
        return False
    if not rows:
        return True  # nothing to plot yet — the header-only tab is still a success

    spreadsheet_id = database.get_app_setting(SPREADSHEET_ID_SETTING_KEYS[_kind_for_tab(sheet_name)])
    if not spreadsheet_id:
        return False

    token = get_access_token(SCOPES)
    if token is None:
        return False

    try:
        meta_response = requests.get(
            f"{SHEETS_BASE_URL}/{spreadsheet_id}",
            params={"fields": "sheets(properties,charts)"},
            headers=_headers(token),
            timeout=TIMEOUT_SECONDS,
        )
        meta_response.raise_for_status()
        meta = meta_response.json()
    except Exception:
        logger.exception("write_chart_tab: could not read spreadsheet metadata for %r", sheet_name)
        return False

    sheet = next((s for s in meta.get("sheets", []) if s["properties"]["title"] == sheet_name), None)
    if sheet is None:
        logger.warning("write_chart_tab: tab %r not found after overwrite_rows — cannot embed chart", sheet_name)
        return False
    sheet_id = sheet["properties"]["sheetId"]

    batch_requests = [{"deleteEmbeddedObject": {"objectId": chart["chartId"]}} for chart in sheet.get("charts", [])]

    end_row_index = len(rows) + 1  # +1 for the header row; Sheets API row indices are 0-based, end exclusive

    def _series_range(col: int) -> dict:
        return {"sourceRange": {"sources": [{"sheetId": sheet_id, "startRowIndex": 0, "endRowIndex": end_row_index, "startColumnIndex": col, "endColumnIndex": col + 1}]}}

    batch_requests.append(
        {
            "addChart": {
                "chart": {
                    "spec": {
                        "title": chart_title,
                        "basicChart": {
                            "chartType": "LINE",
                            "legendPosition": "BOTTOM_LEGEND",
                            "headerCount": 1,
                            "domains": [{"domain": _series_range(0)}],
                            "series": [{"series": _series_range(col), "targetAxis": "LEFT_AXIS"} for col in series_cols],
                        },
                    },
                    "position": {"overlayPosition": {"anchorCell": {"sheetId": sheet_id, "rowIndex": 0, "columnIndex": len(header) + 1}}},
                }
            }
        }
    )

    def _do_batch_update():
        response = requests.post(
            f"{SHEETS_BASE_URL}/{spreadsheet_id}:batchUpdate",
            json={"requests": batch_requests},
            headers=_headers(token),
            timeout=TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return response

    try:
        with_retry(_do_batch_update, max_attempts=3, retry_on=(requests.RequestException,))
        return True
    except Exception:
        logger.exception("write_chart_tab: could not (re)embed chart on %r", sheet_name)
        return False
