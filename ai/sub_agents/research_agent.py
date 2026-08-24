"""
MODULE 16.5 — Research Sub-Agent

Runs module 20's real pipeline: searches Google for the target profile
(20.1), reads whatever's publicly visible for any LinkedIn results found
(20.2), enriches with a company-site email lookup (20.3), and stores/dedupes
into the real leads table (20.4/20.5). Google and LinkedIn both actively
block automated access (verified empirically — CAPTCHA and authwall
respectively, not assumed) — so this reports real zero-lead runs honestly
rather than fabricate results that were never actually found.
"""
import logging
from typing import TypedDict

from agent.config import USER_ID

logger = logging.getLogger(__name__)


class ResearchResult(TypedDict):
    status: str  # "success" | "failure"
    detail: str
    leads_found: int


def run(target_profile: str, user_id: str = USER_ID) -> ResearchResult:
    from automation.leads.enricher import enrich_lead, read_public_profile
    from automation.leads.finder import search_google
    from automation.leads.store import store_lead

    search_results = search_google(target_profile)
    if not search_results:
        detail = (
            f"Google search for {target_profile!r} returned no results — Google's anti-bot "
            "detection blocks automated search traffic (verified: redirects to a reCAPTCHA "
            "interstitial), so this is expected more often than not, not a bug."
        )
        logger.info("Research sub-agent: %s", detail)
        return {"status": "failure", "detail": detail, "leads_found": 0}

    stored = 0
    for result in search_results:
        name = result["name"]
        email = result["email"]
        company = None

        if "linkedin.com/in/" in (result.get("source_url") or ""):
            profile = read_public_profile(result["source_url"])
            if not profile["authwalled"]:
                name = profile["name"] or name
                company = profile["company"]

        rag_context = None
        lead_for_enrich = {"company": company, "email": email, "name": name}
        if company:
            rag_context = enrich_lead(lead_for_enrich)

        store_lead(
            name=name, company=company, email=email,
            notes=result.get("snippet"), source="google_search", rag_context=rag_context,
        )
        stored += 1

    detail = f"Found and stored {stored} lead(s) for {target_profile!r}"
    logger.info("Research sub-agent: %s", detail)
    return {"status": "success", "detail": detail, "leads_found": stored}


if __name__ == "__main__":
    from agent.logging_config import setup_logging

    setup_logging()
    logger.info("Module 16.5 manual test: running research sub-agent")
    print(run(target_profile="AI automation founders"))
