"""
MODULE 18.5 — One-time interactive LinkedIn login

Run this manually once (`python -m automation.linkedin.login_setup`) to
establish a real, human-driven LinkedIn session. It opens a real, visible
browser window and auto-fills your LINKEDIN_EMAIL/LINKEDIN_PASSWORD from
.env into the real login form — you don't retype anything, but if
LinkedIn shows a CAPTCHA or 2FA challenge, complete that step yourself in
the window (this script never tries to solve those). Once you're past
login, this saves the session to LINKEDIN_COOKIES_PATH. Every automated
post after that reuses this session — poster.py never logs in itself
again, which sidesteps LinkedIn's bot detection around the login flow
entirely (the part that's been unreliable to automate headlessly).
"""
import logging
import time

from playwright.sync_api import sync_playwright

from automation.config import LINKEDIN_COOKIES_PATH, LINKEDIN_EMAIL, LINKEDIN_PASSWORD
from automation.linkedin.poster import LINKEDIN_LOGIN_URL

logger = logging.getLogger(__name__)

POLL_INTERVAL_SECONDS = 3
MAX_WAIT_SECONDS = 10 * 60  # 10 minutes — plenty of time for a CAPTCHA/2FA prompt


def _looks_logged_in(page) -> bool:
    """Broader than an exact feed-URL match — LinkedIn can land you on a
    handful of different pages right after login (feed, a "welcome back"
    interstitial, checkpoint-cleared redirect, etc.), so this checks
    "no longer on a login/checkpoint page" instead of one exact URL."""
    url = page.url
    if "login" in url or "checkpoint" in url or "authwall" in url:
        return False
    return True


def _find_logged_in_page(context):
    """Checks every open tab, not just the one the login form was
    submitted on — observed in practice that LinkedIn can navigate a
    *different* tab to the feed after login while the original tab's
    `page` object stays stuck reporting a stale URL, which made the
    single-page poll below never detect a real, completed login."""
    for candidate in context.pages:
        try:
            if _looks_logged_in(candidate):
                return candidate
        except Exception:
            continue
    return None


def _has_session_cookie(context) -> bool:
    """LinkedIn's actual proof of a successful login is the `li_at` session
    cookie it sets server-side — checking for that directly sidesteps a
    real, observed quirk where Playwright's page.url stays stuck reporting
    /login/ long after the visible browser has genuinely navigated to the
    feed (a client-side-routing edge case, not something url/title polling
    can reliably catch)."""
    try:
        return any(c["name"] == "li_at" for c in context.cookies())
    except Exception:
        return False


def run() -> None:
    if not LINKEDIN_EMAIL or not LINKEDIN_PASSWORD:
        print("LINKEDIN_EMAIL/LINKEDIN_PASSWORD not set in .env — set those first.")
        return

    print("Opening a real browser window and filling in your credentials from .env…")
    print("If LinkedIn shows a CAPTCHA or verification step, complete it yourself in that window.")
    print(f"Waiting up to {MAX_WAIT_SECONDS // 60} minutes.")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        page.goto(LINKEDIN_LOGIN_URL, wait_until="domcontentloaded")

        # LinkedIn has used different field selectors across form revisions
        # over time — try the current ones first, fall back to the older
        # session_key/session_password pair before giving up on auto-fill.
        email_selectors = ['input#username', 'input[name="session_key"]']
        password_selectors = ['input#password', 'input[name="session_password"]']
        filled = False
        for email_sel, pw_sel in zip(email_selectors, password_selectors):
            try:
                page.fill(email_sel, LINKEDIN_EMAIL, timeout=5_000)
                page.fill(pw_sel, LINKEDIN_PASSWORD, timeout=5_000)
                page.click('button[type="submit"]', timeout=5_000)
                filled = True
                break
            except Exception:
                continue
        if not filled:
            print("Could not auto-fill the login form (LinkedIn's page may have changed) — "
                  "log in manually in the window instead.")

        elapsed = 0
        while elapsed < MAX_WAIT_SECONDS:
            try:
                with open("login_debug.log", "a", encoding="utf-8") as debug_f:
                    debug_f.write(f"[{elapsed}s] pages={[p.url for p in context.pages]}\n")
                    debug_f.flush()
            except Exception:
                pass  # a page mid-navigation can transiently fail this — never let it kill the poll loop
            if _has_session_cookie(context) or _find_logged_in_page(context) is not None:
                context.storage_state(path=str(LINKEDIN_COOKIES_PATH))
                print(f"Logged in — session saved to {LINKEDIN_COOKIES_PATH}")
                print("poster.py will reuse this automatically from now on.")
                browser.close()
                return
            time.sleep(POLL_INTERVAL_SECONDS)
            elapsed += POLL_INTERVAL_SECONDS

        print("Timed out waiting for login to complete — closing without saving. Run this again when ready.")
        browser.close()


if __name__ == "__main__":
    from agent.logging_config import setup_logging

    setup_logging()
    run()
