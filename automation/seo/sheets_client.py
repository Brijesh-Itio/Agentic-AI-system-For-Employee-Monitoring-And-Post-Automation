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

SPREADSHEET_ID_SETTING_KEY = "seo_sheets_spreadsheet_id"
# Comma-joined tab names already confirmed present in the spreadsheet —
# lets get_or_create_spreadsheet skip the extra spreadsheets.get/
# batchUpdate round-trip on every single _log_to_sheet call (one per
# pipeline log line) and only pay for it once, the first time after TABS
# gains a new entry this installation hasn't seen yet.
SPREADSHEET_TABS_ENSURED_SETTING_KEY = "seo_sheets_tabs_ensured"
SPREADSHEET_TITLE = "WorkPulse AI — SEO Command Centre"

TABS = [
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


def _add_missing_tabs(spreadsheet_id: str, token: str) -> list:
    """Reads the spreadsheet's current tabs, adds whichever of TABS isn't
    already there, then ensures EVERY tab (newly added or already
    existing) has its correct header via _ensure_tab_headers. Shared by
    get_or_create_spreadsheet's self-heal path (a spreadsheet created
    before TABS grew a new entry) and adopt_existing_spreadsheet (a
    human-created sheet that never had any of TABS to begin with). Raises
    on the tab-creation step — callers decide how to degrade
    (get_or_create_spreadsheet treats it as non-fatal and returns the id
    anyway; the pipeline still functions, just without the new tabs until
    this succeeds on a later call). Header-writing never raises — see
    _ensure_tab_headers."""
    def _do_get():
        response = requests.get(f"{SHEETS_BASE_URL}/{spreadsheet_id}", headers=_headers(token), timeout=TIMEOUT_SECONDS)
        response.raise_for_status()
        return response

    meta = with_retry(_do_get, max_attempts=3, retry_on=(requests.RequestException,)).json()
    existing_titles = {s["properties"]["title"] for s in meta.get("sheets", [])}
    missing = [name for name in TABS if name not in existing_titles]

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


def get_or_create_spreadsheet(share_with_email: Optional[str] = None) -> Optional[str]:
    """Never raises — returns None on any failure (no service account,
    Sheets/Drive API not enabled for the project, network), matching
    this codebase's graceful-degrade convention. share_with_email
    defaults to settings.SEO_SHEETS_SHARE_EMAIL (configurable, not
    hardcoded — a real Google account, set by whoever runs this app) and
    is only used the moment the spreadsheet is first created; call
    share_spreadsheet() directly to (re-)share an already-existing one,
    e.g. after changing SEO_SHEETS_SHARE_EMAIL."""
    share_with_email = share_with_email or settings.SEO_SHEETS_SHARE_EMAIL or None
    existing_id = database.get_app_setting(SPREADSHEET_ID_SETTING_KEY)
    if existing_id:
        _ensure_tabs_cached(existing_id)
        return existing_id

    token = get_access_token(SCOPES)
    if token is None:
        return None

    body = {
        "properties": {"title": SPREADSHEET_TITLE},
        "sheets": [{"properties": {"title": name}} for name in TABS],
    }

    def _do_create():
        response = requests.post(SHEETS_BASE_URL, json=body, headers=_headers(token), timeout=TIMEOUT_SECONDS)
        response.raise_for_status()
        return response

    try:
        response = with_retry(_do_create, max_attempts=3, retry_on=(requests.RequestException,))
        spreadsheet_id = response.json().get("spreadsheetId")
    except Exception:
        logger.exception("Failed to create the SEO command-centre spreadsheet")
        return None

    if not spreadsheet_id:
        return None

    database.set_app_setting(SPREADSHEET_ID_SETTING_KEY, spreadsheet_id)
    database.set_app_setting(SPREADSHEET_TABS_ENSURED_SETTING_KEY, ",".join(TABS))

    # Header rows — best-effort, a failure here doesn't invalidate the
    # spreadsheet itself.
    for tab_name, header_row in TAB_HEADERS.items():
        append_row(tab_name, header_row)

    if share_with_email:
        share_spreadsheet(spreadsheet_id, share_with_email)

    logger.info("Created SEO command-centre spreadsheet: %s", spreadsheet_id)
    return spreadsheet_id


def _ensure_tabs_cached(spreadsheet_id: str) -> None:
    """Best-effort, cached self-heal for get_or_create_spreadsheet: skips
    entirely once every current TABS entry has been confirmed present
    (the common case, checked via app_settings rather than re-querying
    the Sheets API on every call), otherwise adds whatever's missing and
    updates the cache. Never raises — a failure here just means the new
    tabs stay missing until a later call succeeds; it must not break the
    pipeline log line that triggered this check."""
    ensured = database.get_app_setting(SPREADSHEET_TABS_ENSURED_SETTING_KEY)
    if ensured and set(TABS) <= set(ensured.split(",")):
        return

    token = get_access_token(SCOPES)
    if token is None:
        return

    try:
        _add_missing_tabs(spreadsheet_id, token)
        database.set_app_setting(SPREADSHEET_TABS_ENSURED_SETTING_KEY, ",".join(TABS))
    except Exception:
        logger.exception("Could not confirm/add tabs for spreadsheet %s — will retry on a later call", spreadsheet_id)


def adopt_existing_spreadsheet(spreadsheet_id: str) -> bool:
    """Module 36 follow-up — service accounts created after April 2025
    have zero Google Drive storage quota, so spreadsheets.create is
    rejected with a 403 no matter how the scopes/APIs are configured
    (verified live this session). The real fix: a human creates a
    normal Google Sheet in their own Drive (which has quota) and shares
    it with the service account as Editor — the service account can
    then read/write an EXISTING file it doesn't own without needing any
    quota of its own. This adopts that sheet: adds any of TABS that
    don't already exist in it (leaving whatever's already there alone,
    including a default 'Sheet1'), writes each new tab's header row,
    and remembers the id the same way get_or_create_spreadsheet would
    have. Never raises — returns False on failure (not shared with the
    service account yet, wrong id, network)."""
    token = get_access_token(SCOPES)
    if token is None:
        return False

    try:
        missing = _add_missing_tabs(spreadsheet_id, token)
    except Exception:
        logger.exception("Could not adopt spreadsheet %s — check it's shared with the service account", spreadsheet_id)
        return False

    database.set_app_setting(SPREADSHEET_ID_SETTING_KEY, spreadsheet_id)
    database.set_app_setting(SPREADSHEET_TABS_ENSURED_SETTING_KEY, ",".join(TABS))

    logger.info("Adopted existing spreadsheet %s — added tabs: %s", spreadsheet_id, missing or "(none needed)")
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

    spreadsheet_id = database.get_app_setting(SPREADSHEET_ID_SETTING_KEY)
    if not spreadsheet_id:
        logger.warning("append_rows(%s): no spreadsheet created yet — call get_or_create_spreadsheet() first", sheet_name)
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
