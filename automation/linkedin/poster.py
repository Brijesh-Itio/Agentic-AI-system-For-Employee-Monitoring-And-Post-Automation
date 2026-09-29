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

Company Page posting (LINKEDIN_PAGE_URL, blank by default): when set, every
post is published to that Company Page instead of the logged-in account's
personal profile, by driving the Page's admin "create post" surface
(_company_admin_post_url) rather than /feed/. The logged-in account
(LINKEDIN_EMAIL) must be an admin of that Page. Verified live 2026-09-29
(DOM probe + a real failure screenshot) that this is NOT the same
composer shape as personal posting despite using the same trigger text
("Start a post"): the Page admin composer opens as a modal directly in
the top-level page (an older Quill editor, div.ql-editor) with no
sharing/compose iframe at all, unlike the personal feed's iframe +
Tiptap/ProseMirror editor. _open_composer's expect_iframe flag and the
editor_selector branch in post_to_linkedin exist because of this — an
earlier version assumed the two shared one composer shape, which made
every Page post open the composer successfully and then time out anyway
waiting for an iframe that Page posting never creates. Image attach on
the Page admin composer remains unverified and degrades to a text-only
post if it fails, rather than failing the whole publish.
"""
import asyncio
import logging
import re
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
    LINKEDIN_PAGE_URL as LINKEDIN_PAGE_URL_ENV_DEFAULT,
    LINKEDIN_PASSWORD,
    MIN_POST_INTERVAL_MINUTES,
)

logger = logging.getLogger(__name__)

LINKEDIN_FEED_URL = "https://www.linkedin.com/feed/"
LINKEDIN_LOGIN_URL = "https://www.linkedin.com/login"
NAV_TIMEOUT_MS = 45_000

# Trigger button text for opening the composer. Verified live 2026-09-29
# against a real Company Page admin view: "Start a post" is present there
# too (a DOM probe found 0 matches for "Create post" and 1 for "Start a
# post"), so both surfaces share the same trigger text.
_PROFILE_COMPOSER_TRIGGERS = ("Start a post",)
_PAGE_COMPOSER_TRIGGERS = ("Start a post",)

# The Page admin composer's editor, scoped to its own container. A bare
# '.ql-editor[contenteditable="true"]' is NOT unique on this page — verified
# live 2026-09-29 (a real "strict mode violation: ... resolved to 2
# elements" failure): the admin view can have a second, unrelated .ql-editor
# open at the same time for a comment box on a background post ("Comment as
# <page>…"), which also happens to use Quill. The real composer's editor
# sits under a `share-creation-state__text-editor` container (the same
# family of class the click-interception fix already found — see
# _open_composer's docstring); the comment box sits under
# `comments-comment-box-comment__text-editor` instead. [class*=...] matches
# the stable BEM-style prefix regardless of the random hash suffix LinkedIn
# appends to it.
_PAGE_EDITOR_SELECTOR = '[class*="share-creation-state__text-editor"] .ql-editor[contenteditable="true"]'

# Same app_settings key api/routes/seo.py's /social/linkedin-page-url
# endpoints read/write — the Social tab's "LinkedIn Page URL" field edits
# this row directly, so a change there applies to the very next post with
# no backend restart needed.
_LINKEDIN_PAGE_URL_SETTING_KEY = "linkedin_page_url"


def _resolve_page_url() -> str:
    """The UI-set value (app_settings, via the Social tab) takes priority
    over LINKEDIN_PAGE_URL in .env; falls back to the .env default only
    when the UI has never touched this setting (row doesn't exist yet).
    Only used for the single default (.env) account — a connected
    seo_linkedin_accounts row carries its own page_url instead, see
    post_to_linkedin's account parameter."""
    stored = database.get_app_setting(_LINKEDIN_PAGE_URL_SETTING_KEY)
    return stored if stored is not None else LINKEDIN_PAGE_URL_ENV_DEFAULT


# User instruction, multi-account LinkedIn — one session file per connected
# account (agent/database.py's seo_linkedin_accounts.session_path stores
# exactly this path), instead of the single global LINKEDIN_COOKIES_PATH.
# Deterministic from the account id so there's no user-facing filesystem
# detail to configure or get wrong.
LINKEDIN_SESSIONS_DIR = DATA_DIR / "linkedin_sessions"


def session_path_for_account(account_id: int) -> Path:
    return LINKEDIN_SESSIONS_DIR / f"{account_id}.json"


def _company_admin_post_url(page_url: str) -> str:
    """Normalizes a LinkedIn Company Page URL (e.g.
    https://www.linkedin.com/company/example-inc/, with or without a
    trailing slash or extra path segments) into that Page's admin
    "create post" surface. Posting from here goes out as the Page itself
    rather than the logged-in account's personal profile — the account in
    LINKEDIN_EMAIL must be an admin of the Page for this to work."""
    from urllib.parse import urlparse

    parsed = urlparse(page_url if "://" in page_url else f"https://{page_url}")
    match = re.search(r"/company/([^/]+)", parsed.path)
    slug = match.group(1) if match else parsed.path.strip("/").split("/")[-1]
    return f"https://www.linkedin.com/company/{slug}/admin/page-posts/published/"

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


def _short_exception_detail(exc: Exception, max_length: int = 220) -> str:
    """A raw Playwright TimeoutError's str() is its message PLUS a full
    step-by-step "Call log:" trace (every retried click attempt, every
    selector state check) — genuinely useful for debugging but several KB
    of internal detail, wrong to hand back as a user-facing error message
    (confirmed live: this is exactly the wall of text a real timeout
    produced in the UI's failure toast). logger.exception already puts the
    complete exception in the server log at the point this is called, so
    trimming here loses nothing — only the short first line ever needs to
    reach a human reading the post's status."""
    text = str(exc).strip().split("\nCall log:")[0].strip()
    text = text.splitlines()[0].strip() if text else text
    if len(text) > max_length:
        text = text[: max_length - 1].rstrip() + "…"
    return text or exc.__class__.__name__


class PostResult(TypedDict):
    status: str  # "success" | "failure"
    detail: str
    post_id: Optional[str]


# ── 18.6 Rate limiting ──

def _rate_limit_status(account_id: Optional[int] = None) -> tuple[bool, str]:
    """Returns (can_post_now, reason_if_not). Real check against the
    actual post_log table, not an in-memory guess — matches api/routes/
    linkedin.py's /status endpoint so the two never disagree.

    account_id scopes the check to one connected account's own post_log
    rows once multi-account is in use — otherwise account B would be
    incorrectly throttled by account A's posts. None (the default .env
    account, or an install that has never added a second account) keeps
    counting every NULL-account row together, unchanged from before
    multi-account support existed."""
    from datetime import datetime, date as date_cls

    conn = database.get_connection()
    account_filter = "linkedin_account_id IS ?" if account_id is None else "linkedin_account_id = ?"

    today = date_cls.today().isoformat()
    posts_today = conn.execute(
        f"SELECT COUNT(*) AS c FROM post_log WHERE date = ? AND status = 'success' AND platform = 'linkedin' AND {account_filter}",
        (today, account_id),
    ).fetchone()["c"]
    if posts_today >= DAILY_POST_LIMIT:
        return False, f"Daily post limit reached ({posts_today}/{DAILY_POST_LIMIT})"

    last = conn.execute(
        f"SELECT date, time FROM post_log WHERE status = 'success' AND platform = 'linkedin' AND {account_filter} ORDER BY id DESC LIMIT 1",
        (account_id,),
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


def _log_post(
    topic: str, content: str, status: str, post_id: Optional[str], error: Optional[str],
    account_id: Optional[int] = None,
) -> None:
    from datetime import datetime

    now = datetime.now()
    with database.write_cursor() as cur:
        cur.execute(
            """
            INSERT INTO post_log (date, time, topic, content, post_id, platform, status, likes, comments, error, linkedin_account_id)
            VALUES (?, ?, ?, ?, ?, 'linkedin', ?, 0, 0, ?, ?)
            """,
            (now.date().isoformat(), now.strftime("%H:%M:%S"), topic, content, post_id, status, error, account_id),
        )


# ── 18.5 Session management ──

def _credentials_configured(email: str = LINKEDIN_EMAIL, password: str = LINKEDIN_PASSWORD) -> bool:
    return bool(email and password)


def _goto(page: Page, url: str) -> None:
    """LinkedIn's pages keep background network activity going indefinitely
    (websockets, analytics beacons, infinite-scroll prefetch), so
    Playwright's default wait_until="load" can time out even when the page
    is fully usable — domcontentloaded is the reliable signal here."""
    page.goto(url, timeout=NAV_TIMEOUT_MS, wait_until="domcontentloaded")


def _is_login_page(page: Page) -> bool:
    return "login" in page.url or "authwall" in page.url or page.locator('input[name="session_key"]').count() > 0


def _login(page: Page, email: str, password: str, save_to: Path) -> bool:
    """First-time (or session-expired) login. Saves the resulting session to
    `save_to` so subsequent runs skip this entirely — the single default
    LINKEDIN_COOKIES_PATH for the .env account, or one connected account's
    own session_path (session_path_for_account) for multi-account."""
    _goto(page, LINKEDIN_LOGIN_URL)
    page.fill('input[name="session_key"]', email)
    page.fill('input[name="session_password"]', password)
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

    save_to.parent.mkdir(parents=True, exist_ok=True)
    page.context.storage_state(path=str(save_to))
    logger.info("LinkedIn login successful, session saved to %s", save_to)
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


def _open_composer(
    page: Page,
    timeout_ms: int,
    trigger_texts: tuple = _PROFILE_COMPOSER_TRIGGERS,
    expect_iframe: bool = True,
):
    """Click the composer trigger and wait for the editor to become usable,
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
    point, so a retry can't produce a duplicate post.

    expect_iframe distinguishes the two composer shapes found live
    2026-09-29 by comparing a failure screenshot (which showed the
    composer modal genuinely open) against a DOM probe of the same page:
    the personal feed's composer renders inside a sharing/compose iframe
    (Tiptap/ProseMirror editor) — _wait_for_compose_frame's job — while a
    Company Page's admin composer renders the SAME modal directly in the
    top-level page instead (an older Quill editor, 0 sharing/compose
    frames found). Passing False here skips the iframe wait entirely and
    waits for that top-level editor instead, returning `page` itself so
    callers can keep using the same .locator()/.get_by_role() calls either
    way. Getting this branch wrong was the actual cause of every Company
    Page publish failing: the click worked and the modal opened, but the
    old code kept waiting for an iframe that Page posting never creates,
    re-clicking a composer that was already open until it timed out."""
    last_error: Optional[PlaywrightTimeoutError] = None
    for attempt in range(1, 4):
        for trigger_text in trigger_texts:
            try:
                page.get_by_text(trigger_text, exact=False).first.click(timeout=timeout_ms)
                if not expect_iframe:
                    editor = page.locator(_PAGE_EDITOR_SELECTOR)
                    editor.wait_for(timeout=timeout_ms)
                    return page
                return _wait_for_compose_frame(page, timeout_ms)
            except PlaywrightTimeoutError as exc:
                last_error = exc
        logger.warning(
            "LinkedIn poster: composer didn't attach on attempt %d/3 (tried %s) — retrying",
            attempt,
            trigger_texts,
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


def post_to_linkedin(
    content: str,
    topic: str,
    image_path: Optional[Path] = None,
    *,
    account_id: Optional[int] = None,
    email: Optional[str] = None,
    password: Optional[str] = None,
    page_url: Optional[str] = None,
    session_path: Optional[Path] = None,
) -> PostResult:
    """account_id/email/password/page_url/session_path: set together by the
    multi-account caller (ai/seo/social_scheduler.py, once a post's
    linkedin_account_id resolves to a seo_linkedin_accounts row) to post
    through that specific connected account instead of the single default
    from .env/LINKEDIN_COOKIES_PATH/the global linkedin_page_url setting —
    all left None (the default) for existing single-account installs,
    unchanged behaviour."""
    can_post, reason = _rate_limit_status(account_id)
    if not can_post:
        logger.info("LinkedIn poster: refusing to post — %s", reason)
        return {"status": "failure", "detail": reason, "post_id": None}

    email = email if email is not None else LINKEDIN_EMAIL
    password = password if password is not None else LINKEDIN_PASSWORD
    cookies_path = session_path if session_path is not None else LINKEDIN_COOKIES_PATH

    if not _credentials_configured(email, password):
        detail = "LinkedIn email/password not set — cannot log in"
        _log_post(topic, content, "failed", None, detail, account_id)
        return {"status": "failure", "detail": detail, "post_id": None}

    # A configured Page URL (blank by default) switches every post from the
    # personal profile feed to a Company Page's admin composer instead —
    # see _company_admin_post_url. Resolved once per call so a change made
    # in the Social tab UI takes effect on the very next post, no restart.
    page_url = page_url if page_url is not None else _resolve_page_url()
    is_page_post = bool(page_url)
    target_url = _company_admin_post_url(page_url) if is_page_post else LINKEDIN_FEED_URL
    composer_triggers = _PAGE_COMPOSER_TRIGGERS if is_page_post else _PROFILE_COMPOSER_TRIGGERS

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
            storage_state = str(cookies_path) if cookies_path.exists() else None
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
                _goto(page, target_url)
                if _is_login_page(page):
                    if not _login(page, email, password, cookies_path):
                        detail = "Login failed (bad credentials or a challenge requiring a human)"
                        _log_post(topic, content, "failed", None, detail, account_id)
                        return {"status": "failure", "detail": detail, "post_id": None}
                    _goto(page, target_url)

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
                # see its own docstring for why that matters for unattended
                # runs, and for why expect_iframe differs by mode: personal
                # profile posting opens an iframe, Company Page posting opens
                # the same modal directly in the top-level page instead
                # (verified live 2026-09-29). compose_frame is a Frame for
                # profile posts, plain `page` for Page posts — both support
                # the same .locator()/.get_by_role() calls used below.
                compose_frame = _open_composer(
                    page, NAV_TIMEOUT_MS, trigger_texts=composer_triggers, expect_iframe=not is_page_post
                )

                # Image attach MUST happen before typing, not after: verified
                # live that clicking "Add media" swaps the whole composer for a
                # media-upload screen and the original text editor is removed
                # from the DOM entirely; any text typed beforehand is silently
                # discarded, not merged back in.
                if image_path is not None and image_path.exists():
                    try:
                        # The file input doesn't exist in the DOM at all until
                        # the media button is clicked — LinkedIn renders it
                        # lazily rather than keeping a hidden input around.
                        # The button's accessible label differs by surface:
                        # personal profile posting uses "Media" (fixed
                        # 2026-09-17 when LinkedIn renamed it from "Add
                        # media"); the Company Page admin composer still
                        # uses the older "Add media" label (verified live
                        # 2026-09-29 via a real headless run — dumped every
                        # composer-toolbar button's aria-label directly,
                        # confirmed the file input and a "Next" button both
                        # appear the same way afterward, same as the profile
                        # flow). Everything after this click (the file
                        # input, the "Next" button) is identical between the
                        # two surfaces — only the trigger label differs.
                        media_button_label = "Add media" if is_page_post else "Media"
                        compose_frame.get_by_label(media_button_label, exact=True).click(timeout=NAV_TIMEOUT_MS)
                        compose_frame.set_input_files('input[type="file"]', str(image_path), timeout=NAV_TIMEOUT_MS)
                        page.wait_for_timeout(2_000)  # let the image preview upload/render
                        compose_frame.get_by_role("button", name="Next", exact=True).click(timeout=NAV_TIMEOUT_MS)
                    except Exception:
                        if not is_page_post:
                            raise
                        # Belt-and-suspenders even now that the Page media
                        # flow is verified: degrade to a text-only post
                        # rather than failing the whole publish if LinkedIn's
                        # admin UI drifts again later, same graceful-degrade
                        # convention as a broken image URL elsewhere in this
                        # codebase.
                        logger.warning(
                            "LinkedIn Page poster: image attach failed — posting text-only instead",
                            exc_info=True,
                        )

                # Personal profile posting uses LinkedIn's newer Tiptap/
                # ProseMirror editor inside compose_frame (an iframe);
                # Company Page admin posting uses the older Quill editor
                # (div.ql-editor) directly on the page — both verified live,
                # see _open_composer's docstring for how these were told
                # apart. Page mode uses _PAGE_EDITOR_SELECTOR rather than a
                # bare .ql-editor match — see its own comment for why a bare
                # match isn't unique on this page (a second Quill editor can
                # exist for a background post's comment box).
                editor_selector = _PAGE_EDITOR_SELECTOR if is_page_post else '.tiptap.ProseMirror[contenteditable="true"]'
                editor = compose_frame.locator(editor_selector)
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

                _log_post(topic, content, "success", post_id, None, account_id)
                logger.info(
                    "Posted to LinkedIn successfully as %s (post_id=%s)",
                    "Company Page" if is_page_post else "personal profile",
                    post_id,
                )
                return {"status": "success", "detail": "Posted successfully", "post_id": post_id}

            except Exception as exc:
                logger.exception("LinkedIn poster failed")
                _save_failure_screenshot(page)
                detail = f"Unexpected error: {_short_exception_detail(exc)}"
                _log_post(topic, content, "failed", None, detail, account_id)
                return {"status": "failure", "detail": detail, "post_id": None}

    except Exception as exc:
        # Only reachable for failures outside the inner try (e.g. the
        # browser itself never launched) — page doesn't exist yet here, so
        # there's nothing to screenshot.
        logger.exception("LinkedIn poster failed before a page was available")
        detail = f"Unexpected error: {_short_exception_detail(exc)}"
        _log_post(topic, content, "failed", None, detail, account_id)
        return {"status": "failure", "detail": detail, "post_id": None}
    finally:
        if browser is not None:
            try:
                browser.close()
            except Exception:
                pass  # already closed, or the playwright driver itself already tore down
        if previous_policy is not None:
            asyncio.set_event_loop_policy(previous_policy)


class LoginResult(TypedDict):
    status: str  # "success" | "failure"
    detail: str


def login_linkedin_account(account_id: int, email: str, password: str) -> LoginResult:
    """User instruction, multi-account LinkedIn — the one place a real
    Playwright login actually runs for a specific seo_linkedin_accounts
    row: drives a real login with that account's own email/password,
    saves the resulting session to its own file (session_path_for_account),
    and records the path on the account row (agent.database.
    set_linkedin_account_session) only on success. Never called
    automatically — a human triggers this explicitly (POST
    /api/seo/linkedin-accounts/{id}/login), same "posting/logging in is
    public and effectively irreversible, needs the account owner's
    explicit go-ahead at the moment it happens" stance this module's own
    top docstring already states for post_to_linkedin. Re-runnable any
    time a saved session stops working — this always does a fresh login
    rather than checking whether an old session might still be valid,
    since checking that would itself need a real page load and this is
    already a deliberate, infrequent, human-triggered action."""
    if not _credentials_configured(email, password):
        return {"status": "failure", "detail": "Email/password required"}

    session_path = session_path_for_account(account_id)

    browser = None
    previous_policy = None
    if sys.platform == "win32":
        previous_policy = asyncio.get_event_loop_policy()
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_context().new_page()
            try:
                if _login(page, email, password, session_path):
                    database.set_linkedin_account_session(account_id, str(session_path))
                    return {"status": "success", "detail": "Logged in — this account is ready to post through."}
                return {
                    "status": "failure",
                    "detail": "Login did not reach the feed — likely wrong credentials, or a CAPTCHA/2FA "
                    "challenge only a human can complete. Try again after checking the credentials, or "
                    "log into this account normally in a real browser first to clear any challenge.",
                }
            except Exception as exc:
                logger.exception("LinkedIn account login failed (account_id=%s)", account_id)
                _save_failure_screenshot(page)
                return {"status": "failure", "detail": f"Unexpected error: {_short_exception_detail(exc)}"}
    finally:
        if browser is not None:
            try:
                browser.close()
            except Exception:
                pass
        if previous_policy is not None:
            asyncio.set_event_loop_policy(previous_policy)


if __name__ == "__main__":
    from agent.logging_config import setup_logging

    setup_logging()
    logger.warning(
        "Module 18.4 manual test would post to a REAL LinkedIn account. "
        "Refusing to run automatically — call post_to_linkedin() explicitly if you mean it."
    )
