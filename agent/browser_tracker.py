"""
MODULE 4 — Browser and Website Tracker

Two complementary sources feed one session manager:
  - Window-title reader (4.1): best-effort fallback that infers a domain
    from the Chrome/Edge window title alone (no URL is visible there).
  - Chrome extension receiver (4.3): the accurate source — the extension
    (see extension/) posts the real document.URL on every tab change.

When the extension is actively reporting, its data is authoritative and
the title-based guesses are suppressed, since a real URL beats a heuristic
guess from a window title every time.

Sub-modules implemented (in order):
    4.1 Window title reader
    4.3 URL receiver endpoint
    4.4 Website session logger
    4.5 Top sites calculator
"""
import json
import logging
import re
import threading
from datetime import datetime, date as date_cls
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Optional
from urllib.parse import urlparse

from agent import database
from agent.app_tracker import get_active_window_info
from agent.config import USER_ID

logger = logging.getLogger(__name__)

BROWSER_PROCESSES = {"chrome.exe", "msedge.exe"}

# How long an extension report stays "authoritative" before the title-based
# fallback is allowed to take over again (e.g. extension not installed/idle).
EXTENSION_FALLBACK_WINDOW_SECONDS = 10
URL_RECEIVER_PORT = 8001

_TITLE_SUFFIX_RE = re.compile(r"\s*-\s*(Google Chrome|Microsoft\s*Edge)\s*$", re.IGNORECASE)

# 4.1 — best-effort domain inference from a window title alone (no URL is
# available at this layer). Deliberately coarse; the extension supersedes it.
_KNOWN_SITE_HINTS = {
    "youtube": "youtube.com",
    "github": "github.com",
    "stack overflow": "stackoverflow.com",
    "gmail": "mail.google.com",
    "linkedin": "linkedin.com",
    "facebook": "facebook.com",
    "instagram": "instagram.com",
    "chatgpt": "chat.openai.com",
    "claude": "claude.ai",
    "notion": "notion.so",
    "slack": "slack.com",
    "twitter": "x.com",
    "reddit": "reddit.com",
    "google docs": "docs.google.com",
    "google sheets": "sheets.google.com",
    "google drive": "drive.google.com",
    "google calendar": "calendar.google.com",
    "google": "google.com",
}


def parse_browser_title(raw_title: str) -> str:
    """Strip the trailing ' - Google Chrome' / ' - Microsoft Edge' suffix."""
    return _TITLE_SUFFIX_RE.sub("", raw_title or "").strip()


def infer_domain_from_title(page_title: str) -> Optional[str]:
    if not page_title:
        return None
    lowered = page_title.lower()
    for hint, domain in _KNOWN_SITE_HINTS.items():
        if hint in lowered:
            return domain
    return None


def extract_domain(url: str) -> Optional[str]:
    if not url:
        return None
    netloc = urlparse(url).netloc
    return netloc[4:] if netloc.startswith("www.") else (netloc or None)


class WebsiteSessionManager:
    """Owns the single "currently open website session" and decides which
    source (title reader vs. extension) is allowed to update it."""

    def __init__(self, user_id: str = USER_ID):
        self.user_id = user_id
        self._lock = threading.Lock()

        self._current_url: Optional[str] = None
        self._current_domain: Optional[str] = None
        self._current_title: Optional[str] = None
        self._session_start: Optional[datetime] = None

        self._last_extension_report: Optional[datetime] = None

    def report(
        self, domain: Optional[str], url: Optional[str], title: Optional[str], source: str
    ) -> None:
        now = datetime.now()
        with self._lock:
            if source == "title" and self._extension_is_authoritative(now):
                return  # accurate extension data recently seen; ignore the guess

            if source == "extension":
                self._last_extension_report = now

            if domain != self._current_domain:
                self._close_current(now)
                if domain is not None:
                    self._open(domain, url, title, now)
            else:
                # Same domain: keep the freshest url/title (e.g. new page on same site).
                self._current_url = url or self._current_url
                self._current_title = title or self._current_title

    def close_if_open(self) -> None:
        """Called when the active window leaves the browser entirely."""
        with self._lock:
            self._close_current(datetime.now())

    def _extension_is_authoritative(self, now: datetime) -> bool:
        if self._last_extension_report is None:
            return False
        return (now - self._last_extension_report).total_seconds() < EXTENSION_FALLBACK_WINDOW_SECONDS

    def _open(self, domain: str, url: Optional[str], title: Optional[str], at: datetime) -> None:
        self._current_domain = domain
        self._current_url = url
        self._current_title = title
        self._session_start = at
        logger.debug("Website session opened: %s", domain)

    def _close_current(self, at: datetime) -> None:
        if self._current_domain is None or self._session_start is None:
            return
        try:
            # 4.4 website session logger
            database.insert_website_session(
                url=self._current_url,
                domain=self._current_domain,
                page_title=self._current_title,
                start_time=self._session_start,
                end_time=at,
                user_id=self.user_id,
            )
            logger.info(
                "Website session closed: %s (%ds)",
                self._current_domain,
                int((at - self._session_start).total_seconds()),
            )
        except Exception:
            logger.exception("Failed to persist website session for %s", self._current_domain)

        self._current_domain = None
        self._current_url = None
        self._current_title = None
        self._session_start = None


class _TitleWatcher:
    """4.1 — polls the active window every second; when it's a browser,
    infers a domain from the title and reports it as a fallback source."""

    def __init__(self, session_manager: WebsiteSessionManager, poll_interval_seconds: float = 1.0):
        self.session_manager = session_manager
        self.poll_interval_seconds = poll_interval_seconds
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run_loop, name="BrowserTitleWatcherThread", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5)

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self.poll()
            except Exception:
                logger.exception("Browser title watcher poll failed; continuing")
            self._stop_event.wait(self.poll_interval_seconds)

    def poll(self) -> None:
        info = get_active_window_info()
        if info is None:
            return
        app_name, window_title = info

        if app_name not in BROWSER_PROCESSES:
            self.session_manager.close_if_open()
            return

        page_title = parse_browser_title(window_title)
        domain = infer_domain_from_title(page_title)
        self.session_manager.report(domain=domain, url=None, title=page_title, source="title")


class _UrlReceiverHandler(BaseHTTPRequestHandler):
    session_manager: WebsiteSessionManager = None  # set by _make_handler

    def log_message(self, format, *args):  # noqa: A002 - stdlib signature
        logger.debug("URL receiver: " + format, *args)

    def _send_cors_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self) -> None:  # noqa: N802 - stdlib method name
        self.send_response(204)
        self._send_cors_headers()
        self.end_headers()

    def do_POST(self) -> None:  # noqa: N802 - stdlib method name
        if self.path != "/url":
            self.send_response(404)
            self._send_cors_headers()
            self.end_headers()
            return

        try:
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length) if length else b""
            payload = json.loads(body or b"{}")
            url = payload.get("url")
            title = payload.get("title")

            domain = extract_domain(url) if url else None
            self.session_manager.report(domain=domain, url=url, title=title, source="extension")

            self.send_response(200)
            self._send_cors_headers()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status": "ok"}')
        except Exception:
            logger.exception("Failed to handle incoming URL payload from extension")
            self.send_response(500)
            self._send_cors_headers()
            self.end_headers()


def _make_handler(session_manager: WebsiteSessionManager):
    return type("BoundUrlReceiverHandler", (_UrlReceiverHandler,), {"session_manager": session_manager})


class _UrlReceiverServer:
    """4.3 — local HTTP server the Chrome extension posts URLs to."""

    def __init__(self, session_manager: WebsiteSessionManager, port: int = URL_RECEIVER_PORT):
        self.port = port
        handler_cls = _make_handler(session_manager)
        self._httpd = ThreadingHTTPServer(("localhost", port), handler_cls)
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self._httpd.serve_forever, name="UrlReceiverThread", daemon=True)
        self._thread.start()
        logger.info("URL receiver listening on http://localhost:%d/url", self.port)

    def stop(self) -> None:
        self._httpd.shutdown()
        self._httpd.server_close()
        if self._thread is not None:
            self._thread.join(timeout=5)
        logger.info("URL receiver stopped")


class BrowserTracker:
    """Owns the session manager, the title-watcher thread, and the URL
    receiver HTTP server."""

    def __init__(self, user_id: str = USER_ID):
        self.session_manager = WebsiteSessionManager(user_id)
        self.title_watcher = _TitleWatcher(self.session_manager)
        self.url_receiver = _UrlReceiverServer(self.session_manager)

    def start(self) -> None:
        database.init_db()
        self.title_watcher.start()
        self.url_receiver.start()
        logger.info("BrowserTracker started")

    def stop(self) -> None:
        self.title_watcher.stop()
        self.session_manager.close_if_open()
        self.url_receiver.stop()
        logger.info("BrowserTracker stopped")


# ── 4.5 top sites calculator ──

def calculate_top_sites(day: date_cls, user_id: str = USER_ID, limit: int = 10) -> list:
    rows = database.get_top_sites_for_date(day, user_id, limit)
    top_sites = [
        {"domain": r["domain"], "total_seconds": r["total_seconds"], "visits": r["visits"]}
        for r in rows
    ]
    try:
        database.set_daily_top_sites_json(day, json.dumps(top_sites), user_id)
    except Exception:
        logger.exception("Failed to persist top sites JSON")
    return top_sites


if __name__ == "__main__":
    import time
    from agent.logging_config import setup_logging

    setup_logging()
    tracker = BrowserTracker()
    tracker.start()
    logger.info("Module 4 manual test running. Browse in Chrome/Edge, Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        tracker.stop()
