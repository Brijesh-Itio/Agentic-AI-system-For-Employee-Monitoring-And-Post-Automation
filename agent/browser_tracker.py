"""
MODULE 4 — Browser and Website Tracker

No Chrome extension (module 22 was built and then deliberately dropped —
window titles are the only signal, by choice, not a fallback for a missing
extension). A real URL is never visible from a window title, so this module
does the best it can with two layers:

  - A large table of known site name -> domain mappings (4.1), covering the
    sites people actually spend time on daily.
  - A generic regex scan for anything that looks like a bare domain
    (`word.tld`) appearing in the title, which many sites include directly
    (e.g. "Issue #42 - example.com").

Anything that matches neither layer is still tracked — never silently
dropped — under a normalised bucket derived from the page title itself, so
total browser time and the Analytics/Timeline views stay complete even for
sites this module doesn't specifically recognise. Known-site and regex
matches carry a real domain and feed accurate top-sites rankings; the
generic bucket exists so time isn't lost, not so it looks like a domain.

Sub-modules implemented (in order):
    4.1 Window title reader
    4.4 Website session logger
    4.5 Top sites calculator
"""
import json
import logging
import re
import threading
from datetime import datetime, date as date_cls
from typing import Optional

from agent import database
from agent.app_tracker import get_active_window_info
from agent.config import USER_ID

logger = logging.getLogger(__name__)

BROWSER_PROCESSES = {"chrome.exe", "msedge.exe"}

_TITLE_SUFFIX_RE = re.compile(r"\s*-\s*(Google Chrome|Microsoft\s*Edge)\s*$", re.IGNORECASE)

# 4.1 — best-effort domain inference from a window title alone (no URL is
# available at this layer). Ordered roughly by how commonly each shows up in
# workday browsing; checked as a substring match against the lowercased title.
_KNOWN_SITE_HINTS = {
    # Search / mail / docs
    "gmail": "mail.google.com",
    "google docs": "docs.google.com",
    "google sheets": "sheets.google.com",
    "google slides": "slides.google.com",
    "google drive": "drive.google.com",
    "google calendar": "calendar.google.com",
    "google meet": "meet.google.com",
    "google maps": "maps.google.com",
    "google translate": "translate.google.com",
    "outlook": "outlook.com",
    "bing": "bing.com",
    "duckduckgo": "duckduckgo.com",
    "yahoo": "yahoo.com",
    "google": "google.com",
    # Dev tools
    "github": "github.com",
    "gitlab": "gitlab.com",
    "bitbucket": "bitbucket.org",
    "stack overflow": "stackoverflow.com",
    "npm": "npmjs.com",
    "pypi": "pypi.org",
    "vercel": "vercel.com",
    "netlify": "netlify.app",
    "railway": "railway.app",
    "digitalocean": "digitalocean.com",
    "aws console": "aws.amazon.com",
    "azure portal": "portal.azure.com",
    "cloudflare": "cloudflare.com",
    "figma": "figma.com",
    "jira": "atlassian.net",
    "confluence": "atlassian.net",
    "postman": "postman.com",
    "docker hub": "hub.docker.com",
    "huggingface": "huggingface.co",
    "npm registry": "npmjs.com",
    # AI tools
    "chatgpt": "chat.openai.com",
    "claude": "claude.ai",
    "gemini": "gemini.google.com",
    "perplexity": "perplexity.ai",
    "midjourney": "midjourney.com",
    # Work / productivity
    "notion": "notion.so",
    "slack": "slack.com",
    "microsoft teams": "teams.microsoft.com",
    "zoom": "zoom.us",
    "trello": "trello.com",
    "asana": "asana.com",
    "monday.com": "monday.com",
    "airtable": "airtable.com",
    "canva": "canva.com",
    "dropbox": "dropbox.com",
    "onedrive": "onedrive.live.com",
    "linkedin": "linkedin.com",
    "indeed": "indeed.com",
    "glassdoor": "glassdoor.com",
    "upwork": "upwork.com",
    "fiverr": "fiverr.com",
    # Social / entertainment (distraction category)
    "youtube": "youtube.com",
    "facebook": "facebook.com",
    "instagram": "instagram.com",
    "twitter": "x.com",
    " x.com": "x.com",
    "reddit": "reddit.com",
    "tiktok": "tiktok.com",
    "pinterest": "pinterest.com",
    "netflix": "netflix.com",
    "twitch": "twitch.tv",
    "spotify": "spotify.com",
    "whatsapp": "web.whatsapp.com",
    "telegram": "web.telegram.org",
    "discord": "discord.com",
    "quora": "quora.com",
    # Reference / news
    "wikipedia": "wikipedia.org",
    "medium": "medium.com",
    "dev.to": "dev.to",
    "hacker news": "news.ycombinator.com",
    # Commerce
    "amazon": "amazon.com",
    "flipkart": "flipkart.com",
    "paypal": "paypal.com",
    "stripe dashboard": "dashboard.stripe.com",
}

_BARE_DOMAIN_RE = re.compile(
    r"\b([a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.(?:com|org|net|io|co|ai|dev|app|so|us|in|gov|edu))\b",
    re.IGNORECASE,
)

# Titles that vary per-page but belong to the same underlying app shouldn't
# fragment into dozens of one-second "sites" — anything left of the first
# separator is usually the stable app/site name (e.g. "Inbox (3) - My Company
# Mail" -> "My Company Mail").
_TITLE_SEPARATOR_RE = re.compile(r"\s+[-–|]\s+")


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
    match = _BARE_DOMAIN_RE.search(page_title)
    if match:
        return match.group(1).lower()
    return None


def fallback_site_bucket(page_title: str) -> Optional[str]:
    """When no real domain can be inferred, group by the stable-looking part
    of the title (usually the last segment, e.g. "Article - Site Name") so
    repeated visits to the same untracked site still aggregate together
    instead of the page title alone (which changes every navigation)."""
    if not page_title:
        return None
    segments = [s.strip() for s in _TITLE_SEPARATOR_RE.split(page_title) if s.strip()]
    bucket = segments[-1] if len(segments) > 1 else page_title.strip()
    bucket = bucket[:80]
    return bucket or None


class WebsiteSessionManager:
    """Owns the single "currently open website session"."""

    def __init__(self, user_id: str = USER_ID):
        self.user_id = user_id
        self._lock = threading.Lock()

        self._current_domain: Optional[str] = None
        self._current_title: Optional[str] = None
        self._session_start: Optional[datetime] = None

    def report(self, domain: Optional[str], title: Optional[str]) -> None:
        now = datetime.now()
        with self._lock:
            if domain != self._current_domain:
                self._close_current(now)
                if domain is not None:
                    self._open(domain, title, now)
            else:
                # Same site: keep the freshest title (e.g. new page on same site).
                self._current_title = title or self._current_title

    def close_if_open(self) -> None:
        """Called when the active window leaves the browser entirely."""
        with self._lock:
            self._close_current(datetime.now())

    def _open(self, domain: str, title: Optional[str], at: datetime) -> None:
        self._current_domain = domain
        self._current_title = title
        self._session_start = at
        logger.debug("Website session opened: %s", domain)

    def _close_current(self, at: datetime) -> None:
        if self._current_domain is None or self._session_start is None:
            return
        try:
            # 4.4 website session logger
            database.insert_website_session(
                url=None,
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
        self._current_title = None
        self._session_start = None


class _TitleWatcher:
    """4.1 — polls the active window every second; when it's a browser,
    infers a domain (or a generic fallback bucket) from the title."""

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
        domain = infer_domain_from_title(page_title) or fallback_site_bucket(page_title)
        self.session_manager.report(domain=domain, title=page_title)


class BrowserTracker:
    """Owns the session manager and the title-watcher thread."""

    def __init__(self, user_id: str = USER_ID):
        self.session_manager = WebsiteSessionManager(user_id)
        self.title_watcher = _TitleWatcher(self.session_manager)

    def start(self) -> None:
        database.init_db()
        self.title_watcher.start()
        logger.info("BrowserTracker started (window-title tracking, no browser extension)")

    def stop(self) -> None:
        self.title_watcher.stop()
        self.session_manager.close_if_open()
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
