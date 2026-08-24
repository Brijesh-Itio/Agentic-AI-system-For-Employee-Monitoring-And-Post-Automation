"""
MODULE 20.2 / 20.3 — LinkedIn Public Profile Reader & Lead Enricher

20.2: visits a LinkedIn profile URL *without logging in* (avoiding
account risk, per spec) and extracts whatever is visible in the public
preview. LinkedIn gates most profile content behind an "authwall" for
anonymous visitors — this reports exactly what was actually visible
rather than assuming full access.

20.3: for a lead with a company name, searches for their company website
(via search_google — subject to the same blocking already documented in
finder.py) and looks for a contact/about page to extract an email
pattern. Stores whatever is found as RAG context via ai/rag.py.
"""
import logging
import re
from typing import Optional, TypedDict

from playwright.sync_api import sync_playwright

logger = logging.getLogger(__name__)

PAGE_LOAD_TIMEOUT_MS = 20_000
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")


class PublicProfile(TypedDict):
    name: Optional[str]
    headline: Optional[str]
    location: Optional[str]
    company: Optional[str]
    authwalled: bool


# ── 20.2 LinkedIn public profile reader ──

def read_public_profile(profile_url: str) -> PublicProfile:
    """Never logs in — visits the URL as an anonymous visitor only.
    LinkedIn authwalls most profile detail for anonymous traffic; when
    that happens this returns authwalled=True with everything else None,
    rather than guessing at content that was never actually visible."""
    empty: PublicProfile = {"name": None, "headline": None, "location": None, "company": None, "authwalled": False}

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(profile_url, timeout=PAGE_LOAD_TIMEOUT_MS)
            page.wait_for_timeout(2_000)

            if "authwall" in page.url or page.locator("form.authwall-content-block, div.authwall").count() > 0:
                logger.info("LinkedIn authwalled anonymous access to %s — no profile data visible", profile_url)
                browser.close()
                return {**empty, "authwalled": True}

            def _text(selector: str) -> Optional[str]:
                try:
                    return page.locator(selector).first.inner_text(timeout=3_000).strip()
                except Exception:
                    return None

            name = _text("h1")
            headline = _text('div.text-body-medium, [data-generated-suggestion-target] + div')
            location = _text("span.text-body-small")
            browser.close()

            result: PublicProfile = {
                "name": name, "headline": headline, "location": location, "company": None, "authwalled": False,
            }
            logger.info("LinkedIn public profile read for %s: name=%r", profile_url, name)
            return result

    except Exception:
        logger.exception("LinkedIn public profile read failed for %s", profile_url)
        return empty


# ── 20.3 Lead enricher ──

def enrich_lead(lead: dict) -> Optional[str]:
    """Best-effort: finds the lead's company site and looks for a contact
    email pattern. Returns the enrichment text to store as RAG context, or
    None if nothing could be found (company unknown, search blocked, no
    contact page reachable) — never fabricates a plausible-looking result."""
    company = lead.get("company")
    if not company:
        return None

    from automation.leads.finder import search_google

    results = search_google(f"{company} official website contact")
    if not results:
        logger.info("Lead enricher: no search results for company %r (search likely blocked)", company)
        return None

    site_url = results[0]["source_url"]
    if not site_url:
        return None

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(site_url, timeout=PAGE_LOAD_TIMEOUT_MS)
            page.wait_for_timeout(1_500)
            body_text = page.inner_text("body", timeout=5_000)
            browser.close()

            email_match = _EMAIL_RE.search(body_text)
            if not email_match:
                logger.info("Lead enricher: no email pattern found on %s", site_url)
                return None

            enrichment = f"Company website: {site_url}\nContact email found: {email_match.group(0)}"
            logger.info("Lead enricher: enriched %s from %s", lead.get("email") or lead.get("name"), site_url)
            return enrichment

    except Exception:
        logger.exception("Lead enricher: failed to read company site %s", site_url)
        return None


if __name__ == "__main__":
    from agent.logging_config import setup_logging

    setup_logging()
    logger.info("Module 20.2 manual test: reading a public LinkedIn profile")
    print(read_public_profile("https://www.linkedin.com/in/satyanadella/"))
