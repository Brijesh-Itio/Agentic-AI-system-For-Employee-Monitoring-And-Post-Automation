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
}


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def _add_missing_tabs(spreadsheet_id: str, token: str) -> list:
    """Reads the spreadsheet's current tabs, adds whichever of TABS isn't
    already there, and writes each new tab's header row. Shared by
    get_or_create_spreadsheet's self-heal path (a spreadsheet created
    before TABS grew a new entry) and adopt_existing_spreadsheet (a
    human-created sheet that never had any of TABS to begin with). Raises
    on failure — callers decide how to degrade (get_or_create_spreadsheet
    treats it as non-fatal and returns the id anyway; the pipeline still
    functions, just without the new tabs until this succeeds on a later
    call)."""
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

        for tab_name in missing:
            append_row(tab_name, TAB_HEADERS[tab_name])

    return missing


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


def append_row(sheet_name: str, row: list) -> bool:
    """Appends one row to the named tab. Never raises — returns False on
    any failure (spreadsheet not yet created, tab doesn't exist, auth
    failure), so a caller can log/skip rather than let a Sheets hiccup
    break the pipeline step that's trying to log to it."""
    spreadsheet_id = database.get_app_setting(SPREADSHEET_ID_SETTING_KEY)
    if not spreadsheet_id:
        logger.warning("append_row(%s): no spreadsheet created yet — call get_or_create_spreadsheet() first", sheet_name)
        return False

    token = get_access_token(SCOPES)
    if token is None:
        return False

    url = f"{SHEETS_BASE_URL}/{spreadsheet_id}/values/{sheet_name}:append"

    def _do_append():
        response = requests.post(
            url,
            params={"valueInputOption": "USER_ENTERED"},
            json={"values": [[str(cell) for cell in row]]},
            headers=_headers(token),
            timeout=TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return response

    try:
        with_retry(_do_append, max_attempts=3, retry_on=(requests.RequestException,))
        return True
    except Exception:
        logger.exception("Failed to append a row to %r", sheet_name)
        return False
