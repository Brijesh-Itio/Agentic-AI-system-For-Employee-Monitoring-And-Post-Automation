"""
MODULE 20.1 — Google Search Scraper

Uses Playwright to search Google for a target-profile query and parses
the results page for names, company names, and any visible email
addresses. Random 2-5s delays between page loads, per spec, to look less
like a bot hammering the endpoint.

Google actively detects and blocks automated search traffic (CAPTCHA,
"unusual traffic" interstitials, IP-based rate limiting) — this is
attempted for real and reports honestly what happens, the same way
automation/linkedin/image_finder.py did before switching to an API for
that one piece. No official free API exists for this (Google's Custom
Search API is paid beyond a small free tier), so unlike image search,
there is no drop-in alternative if scraping is blocked.
"""
import logging
import random
import re
import time
from typing import TypedDict

from playwright.sync_api import sync_playwright

logger = logging.getLogger(__name__)

GOOGLE_SEARCH_URL = "https://www.google.com/search"
PAGE_LOAD_TIMEOUT_MS = 20_000
MIN_DELAY_SECONDS = 2.0
MAX_DELAY_SECONDS = 5.0

_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")


class FoundLead(TypedDict):
    name: str
    snippet: str
    email: str | None
    source_url: str


def search_google(query: str, max_results: int = 10) -> list[FoundLead]:
    """Returns whatever real results could be parsed — an empty list means
    either no matches or Google blocked the request; both are logged
    distinctly so the caller (and whoever reads the log) knows which."""
    leads: list[FoundLead] = []

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
                )
            )
            page.goto(f"{GOOGLE_SEARCH_URL}?q={query}", timeout=PAGE_LOAD_TIMEOUT_MS)
            time.sleep(random.uniform(MIN_DELAY_SECONDS, MAX_DELAY_SECONDS))

            if page.locator("form#captcha-form, div#recaptcha").count() > 0 or "sorry" in page.url:
                logger.warning("Google search blocked by CAPTCHA/anti-bot interstitial for query %r", query)
                browser.close()
                return []

            results = page.locator("div.g")
            count = min(results.count(), max_results)
            if count == 0:
                logger.info("Google search returned 0 parseable results for %r (page may have changed layout)", query)

            for i in range(count):
                block = results.nth(i)
                try:
                    title = block.locator("h3").first.inner_text(timeout=2_000)
                except Exception:
                    continue
                snippet = ""
                try:
                    snippet = block.inner_text(timeout=2_000)
                except Exception:
                    pass
                link = block.locator("a").first.get_attribute("href") or ""
                email_match = _EMAIL_RE.search(snippet)

                leads.append(
                    {
                        "name": title,
                        "snippet": snippet[:500],
                        "email": email_match.group(0) if email_match else None,
                        "source_url": link,
                    }
                )

            browser.close()
            logger.info("Google search for %r returned %d parseable result(s)", query, len(leads)) 
            return leads

    except Exception:
        logger.exception("Google search failed for query %r", query)
        return []


if __name__ == "__main__":
    from agent.logging_config import setup_logging

    setup_logging()
    logger.info("Module 20.1 manual test: searching Google")
    for lead in search_google('"agentic AI" founder site:linkedin.com'):
        print(lead)
