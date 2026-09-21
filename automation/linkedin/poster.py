"""
MODULE 18.4 / 18.5 / 18.6 — LinkedIn Browser Poster, Session Management,
Rate Limiting

Posts to LinkedIn via a persistent Playwright browser context — no
LinkedIn API, no developer account, matching DEVELOPMENT.md's zero-API
rule for this module (unlike 18.3's image search, this one really is
Playwright browser automation end to end).

Not verified against a real LinkedIn session: doing so requires actually
logging into a real account, which needs the account owner's explicit
go-ahead at the moment it happens (posting is public and effectively
irreversible), not something to do unattended while writing this code.
The selectors below follow LinkedIn's current (2026) share-box structure
as closely as documentation/inspection allows, but LinkedIn's DOM changes
without notice and a first real run may need selector adjustments.
"""
import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, TypedDict

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError, sync_playwright

from agent import database
from agent.config import DATA_DIR
from automation.config import (
    DAILY_POST_LIMIT,
    LINKEDIN_COOKIES_PATH,
    LINKEDIN_EMAIL,
    LINKEDIN_PASSWORD,
    MIN_POST_INTERVAL_MINUTES,
)

logger = logging.getLogger(__name__)

LINKEDIN_FEED_URL = "https://www.linkedin.com/feed/"
LINKEDIN_LOGIN_URL = "https://www.linkedin.com/login"
NAV_TIMEOUT_MS = 45_000

FAILURE_SCREENSHOTS_DIR = DATA_DIR / "linkedin_failures"


def _save_failure_screenshot(page: Optional[Page]) -> None:
    """Best-effort diagnostic aid: LinkedIn's DOM changes without notice
    (already hit twice — the composer trigger and the Next button both
    needed live re-inspection to fix), so a screenshot at the moment of
    failure turns the next selector break into a quick look instead of
    another live reproduction session. Never raises — a failed screenshot
    is not itself a reason to lose the real error."""
    if page is None:
        return
    try:
        FAILURE_SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
        path = FAILURE_SCREENSHOTS_DIR / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        page.screenshot(path=str(path))
        logger.error("LinkedIn poster failure screenshot saved to %s", path)
    except Exception:
        logger.exception("Failed to save LinkedIn poster failure screenshot")


class PostResult(TypedDict):
    status: str  # "success" | "failure"
    detail: str
    post_id: Optional[str]


# ── 18.6 Rate limiting ──

def _rate_limit_status() -> tuple[bool, str]:
    """Returns (can_post_now, reason_if_not). Real check against the
    actual post_log table, not an in-memory guess — matches api/routes/
    linkedin.py's /status endpoint so the two never disagree."""
    from datetime import datetime, date as date_cls

    conn = database.get_connection()

    today = date_cls.today().isoformat()
    posts_today = conn.execute(
        "SELECT COUNT(*) AS c FROM post_log WHERE date = ? AND status = 'success'", (today,)
    ).fetchone()["c"]
    if posts_today >= DAILY_POST_LIMIT:
        return False, f"Daily post limit reached ({posts_today}/{DAILY_POST_LIMIT})"

    last = conn.execute(
        "SELECT date, time FROM post_log WHERE status = 'success' ORDER BY id DESC LIMIT 1"
    ).fetchone()
    if last is not None:
        last_at = datetime.fromisoformat(f"{last['date']}T{last['time']}")
        elapsed_minutes = (datetime.now() - last_at).total_seconds() / 60
        if elapsed_minutes < MIN_POST_INTERVAL_MINUTES:
            return False, (
                f"Last post was {int(elapsed_minutes)}m ago, "
                f"minimum gap is {MIN_POST_INTERVAL_MINUTES}m"
            )

    return True, ""


def _log_post(topic: str, content: str, status: str, post_id: Optional[str], error: Optional[str]) -> None:
    from datetime import datetime

    now = datetime.now()
    with database.write_cursor() as cur:
        cur.execute(
            """
            INSERT INTO post_log (date, time, topic, content, post_id, platform, status, likes, comments, error)
            VALUES (?, ?, ?, ?, ?, 'linkedin', ?, 0, 0, ?)
            """,
            (now.date().isoformat(), now.strftime("%H:%M:%S"), topic, content, post_id, status, error),
        )


# ── 18.5 Session management ──

def _credentials_configured() -> bool:
    return bool(LINKEDIN_EMAIL and LINKEDIN_PASSWORD)


def _goto(page: Page, url: str) -> None:
    """LinkedIn's pages keep background network activity going indefinitely
    (websockets, analytics beacons, infinite-scroll prefetch), so
    Playwright's default wait_until="load" can time out even when the page
    is fully usable — domcontentloaded is the reliable signal here."""
    page.goto(url, timeout=NAV_TIMEOUT_MS, wait_until="domcontentloaded")


def _is_login_page(page: Page) -> bool:
    return "login" in page.url or "authwall" in page.url or page.locator('input[name="session_key"]').count() > 0


def _login(page: Page) -> bool:
    """First-time (or session-expired) login. Saves the resulting session
    to LINKEDIN_COOKIES_PATH so subsequent runs skip this entirely."""
    if not _credentials_configured():
        logger.error("LinkedIn login required but LINKEDIN_EMAIL/LINKEDIN_PASSWORD not set in .env")
        return False

    _goto(page, LINKEDIN_LOGIN_URL)
    page.fill('input[name="session_key"]', LINKEDIN_EMAIL)
    page.fill('input[name="session_password"]', LINKEDIN_PASSWORD)
    page.click('button[type="submit"]')

    try:
        page.wait_for_url(f"{LINKEDIN_FEED_URL}**", timeout=NAV_TIMEOUT_MS)
    except PlaywrightTimeoutError:
        logger.error(
            "LinkedIn login did not reach the feed — likely a CAPTCHA/2FA challenge that "
            "needs a human to complete once, interactively (not something this automation "
            "can or should try to bypass)"
        )
        return False

    page.context.storage_state(path=str(LINKEDIN_COOKIES_PATH))
    logger.info("LinkedIn login successful, session saved to %s", LINKEDIN_COOKIES_PATH)
    return True


# ── 18.4 LinkedIn browser poster ──

def _wait_for_compose_frame(page: Page, timeout_ms: int):
    """The compose iframe attaches asynchronously after the "Start a
    post" click — searching page.frames immediately can lose the race
    (verified live: a StopIteration when checked with no wait at all,
    reliable once given ~2-3s). Polls instead of a fixed sleep so this
    isn't tuned to one observed timing."""
    import time

    deadline = time.monotonic() + timeout_ms / 1000
    while time.monotonic() < deadline:
        for f in page.frames:
            if "sharing/compose" in f.url:
                return f
        page.wait_for_timeout(200)
    raise PlaywrightTimeoutError(f"compose iframe (sharing/compose) never attached within {timeout_ms}ms")


def _open_composer(page: Page, timeout_ms: int):
    """Click "Start a post" and wait for the compose iframe to attach,
    retrying the click itself (not just the wait) up to 3 total attempts.
    Fixed 2026-09-18: a scheduled/unattended publish hit a real, one-off
    case where the click didn't open the composer at all (confirmed by a
    failure screenshot showing the untouched feed, "Start a post" bar
    still idle) — re-running the identical click immediately afterward
    worked fine, so this was LinkedIn being momentarily slow/unresponsive
    to that one click, not a broken selector. A scheduled post has no
    human present to notice and click "Retry publish", so it needs to
    absorb this kind of transient miss on its own rather than fail the
    whole run over what a second click would have fixed. Safe to retry
    the click itself: nothing has been typed or attached yet at this
    point, so a retry can't produce a duplicate post."""
    last_error: Optional[PlaywrightTimeoutError] = None
    for attempt in range(1, 4):
        try:
            page.get_by_text("Start a post", exact=False).first.click(timeout=timeout_ms)
            return _wait_for_compose_frame(page, timeout_ms)
        except PlaywrightTimeoutError as exc:
            last_error = exc
            logger.warning(
                "LinkedIn poster: compose frame didn't attach on attempt %d/3 (%s) — retrying", attempt, exc
            )
    raise last_error


def _extract_post_id(page: Page) -> Optional[str]:
    """Best-effort: LinkedIn doesn't redirect to the new post's URL, so
    this reads the most recent activity URN from the feed's own DOM
    rather than guessing — absence just means the id is unknown, not a
    failure of the post itself."""
    try:
        first_post = page.locator("div.feed-shared-update-v2").first
        urn = first_post.get_attribute("data-urn", timeout=5_000)
        return urn
    except PlaywrightTimeoutError:
        return None


def post_to_linkedin(content: str, topic: str, image_path: Optional[Path] = None) -> PostResult:
    can_post, reason = _rate_limit_status()
    if not can_post:
        logger.info("LinkedIn poster: refusing to post — %s", reason)
        return {"status": "failure", "detail": reason, "post_id": None}

    if not _credentials_configured():
        detail = "LINKEDIN_EMAIL/LINKEDIN_PASSWORD not set in .env — cannot log in"
        _log_post(topic, content, "failed", None, detail)
        return {"status": "failure", "detail": detail, "post_id": None}

    browser = None
    page = None
    # Windows-only: uvicorn forces WindowsSelectorEventLoopPolicy process-wide
    # for its own HTTP server (see uvicorn/loops/asyncio.py) — but a Selector
    # loop can't launch subprocesses, and Playwright's sync API needs a real
    # subprocess to start Chromium, so every call here failed with a bare
    # NotImplementedError (str(exc) == "", hence the empty "Unexpected
    # error:" the UI showed). The policy is process-global, not thread-local,
    # so this is scoped as tightly as possible: swapped in only for this
    # call, restored in `finally` below so uvicorn's own loop is unaffected.
    previous_policy = None
    if sys.platform == "win32":
        previous_policy = asyncio.get_event_loop_policy()
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            storage_state = str(LINKEDIN_COOKIES_PATH) if LINKEDIN_COOKIES_PATH.exists() else None
            context = browser.new_context(storage_state=storage_state)
            page = context.new_page()

            # Everything below is wrapped in its own try/except *inside* the
            # `with sync_playwright()` block, not around it — a with-block
            # exits (tearing down Playwright's driver connection) before an
            # exception raised inside it reaches an outer `except`, which is
            # why _save_failure_screenshot() used to always fail with
            # "Event loop is closed! Is Playwright already stopped?" instead
            # of ever actually saving a screenshot. Catching it here means
            # the page/browser are still alive when the screenshot is taken.
            try:
                _goto(page, LINKEDIN_FEED_URL)
                if _is_login_page(page):
                    if not _login(page):
                        detail = "Login failed (bad credentials or a challenge requiring a human)"
                        _log_post(topic, content, "failed", None, detail)
                        return {"status": "failure", "detail": detail, "post_id": None}
                    _goto(page, LINKEDIN_FEED_URL)

                # LinkedIn's "Start a post" trigger uses randomised CSS-module
                # class hashes that change on every deploy (verified live via
                # DOM inspection — the old share-box-feed-entry__trigger class
                # no longer exists) — its visible text is the stable target.
                #
                # LinkedIn now renders the whole composer inside an iframe at
                # linkedin.com/sharing/compose (verified live: page.locator
                # against the top-level page found 0 of every editor/button
                # selector below — they all genuinely exist, just not in this
                # frame). Every composer interaction from here on has to go
                # through compose_frame, not page, or it silently finds nothing
                # and times out — which is exactly what was happening before
                # this fix (Locator.wait_for: Timeout ... exceeded, waiting for
                # a selector that only ever existed one frame away).
                # _open_composer retries the click itself, not just the wait —
                # see its own docstring for why that matters for unattended runs.
                compose_frame = _open_composer(page, NAV_TIMEOUT_MS)

                # Image attach MUST happen before typing, not after: verified
                # live that clicking "Add media" swaps the whole composer for a
                # media-upload screen and the original text editor is removed
                # from the DOM entirely; any text typed beforehand is silently
                # discarded, not merged back in.
                if image_path is not None and image_path.exists():
                    # The file input doesn't exist in the DOM at all until the
                    # media button is clicked — LinkedIn renders it lazily
                    # rather than keeping a hidden input around. Fixed
                    # 2026-09-17: this button's accessible label was "Add
                    # media" at some earlier point but is now just "Media"
                    # (verified live via a real headless run — dumped every
                    # compose-toolbar button's aria-label directly rather than
                    # guessing from a screenshot; a real failure in production
                    # was timing out on the old label). Everything after this
                    # click (the file input, the "Next" button) was verified
                    # working as-is in that same live run — only this one
                    # label had drifted.
                    compose_frame.get_by_label("Media", exact=True).click(timeout=NAV_TIMEOUT_MS)
                    compose_frame.set_input_files('input[type="file"]', str(image_path), timeout=NAV_TIMEOUT_MS)
                    page.wait_for_timeout(2_000)  # let the image preview upload/render
                    compose_frame.get_by_role("button", name="Next", exact=True).click(timeout=NAV_TIMEOUT_MS)

                # LinkedIn migrated its composer from Quill (div.ql-editor) to
                # Tiptap/ProseMirror (verified live: 0 matches for .ql-editor
                # or any [contenteditable] on the top-level page; exactly 1
                # match inside compose_frame, class="tiptap ProseMirror
                # <hashes>"). "tiptap"/"ProseMirror" are the editor library's
                # own stable class names, unlike the random hash suffixes
                # alongside them.
                editor = compose_frame.locator('.tiptap.ProseMirror[contenteditable="true"]')
                editor.wait_for(timeout=NAV_TIMEOUT_MS)
                editor.click()
                # .type() simulates a real keystroke per character with no
                # explicit timeout override, so it inherits Playwright's
                # default 30s action timeout — verified live that a ~2000-
                # character post blows past that (content this long isn't
                # a hypothetical edge case; the LLM draft it's typing here
                # routinely runs long). .fill() sets the value in one
                # operation instead — verified live on this exact editor:
                # 0.06s for the same content, byte-for-byte match.
                editor.fill(content)

                # Same story as the Post button: every class on it is a
                # random per-deploy hash (verified live via DOM dump — no
                # stable class survives), so its visible text "Post" is the
                # only durable target, same reasoning as "Start a post" above.
                compose_frame.get_by_role("button", name="Post", exact=True).click(timeout=NAV_TIMEOUT_MS)
                page.wait_for_timeout(3_000)  # let the post publish before reading the feed back

                post_id = _extract_post_id(page)

                _log_post(topic, content, "success", post_id, None)
                logger.info("Posted to LinkedIn successfully (post_id=%s)", post_id)
                return {"status": "success", "detail": "Posted successfully", "post_id": post_id}

            except Exception as exc:
                logger.exception("LinkedIn poster failed")
                _save_failure_screenshot(page)
                _log_post(topic, content, "failed", None, str(exc))
                return {"status": "failure", "detail": f"Unexpected error: {exc}", "post_id": None}

    except Exception as exc:
        # Only reachable for failures outside the inner try (e.g. the
        # browser itself never launched) — page doesn't exist yet here, so
        # there's nothing to screenshot.
        logger.exception("LinkedIn poster failed before a page was available")
        _log_post(topic, content, "failed", None, str(exc))
        return {"status": "failure", "detail": f"Unexpected error: {exc}", "post_id": None}
    finally:
        if browser is not None:
            try:
                browser.close()
            except Exception:
                pass  # already closed, or the playwright driver itself already tore down
        if previous_policy is not None:
            asyncio.set_event_loop_policy(previous_policy)


if __name__ == "__main__":
    from agent.logging_config import setup_logging

    setup_logging()
    logger.warning(
        "Module 18.4 manual test would post to a REAL LinkedIn account. "
        "Refusing to run automatically — call post_to_linkedin() explicitly if you mean it."
    )
