"""
MODULE 16.2 — Reporting Sub-Agent

Generates the DAR (module 7) and emails it (module 8). Weekly report
generation on Mondays is honestly skipped rather than faked: no module in
DEVELOPMENT.md's 24-module build order defines a narrative weekly report
generator (module 2.7 only computes trend statistics), matching the same
honest 501 already returned by api/routes/reports.py's
/weekly/generate endpoint.
"""
import logging
from datetime import date as date_cls
from typing import Optional, TypedDict

from agent.config import USER_ID

logger = logging.getLogger(__name__)


class ReportingResult(TypedDict):
    status: str  # "success" | "failure"
    detail: str
    dar_content: Optional[str]
    emailed: bool


def run(day: Optional[date_cls] = None, user_id: str = USER_ID, send_email: bool = True) -> ReportingResult:
    day = day or date_cls.today()

    from ai.dar_generator import generate_and_save_dar

    content = generate_and_save_dar(day, user_id)
    if content is None:
        detail = "generate_and_save_dar returned None (Ollama unreachable or timed out)"
        logger.error("Reporting sub-agent: %s", detail)
        return {"status": "failure", "detail": detail, "dar_content": None, "emailed": False}

    emailed = False
    if send_email:
        from automation.email.sender import send_dar_email

        emailed = send_dar_email(day, user_id)
        if not emailed:
            logger.warning(
                "Reporting sub-agent: DAR generated for %s but email send failed "
                "(check GMAIL_ADDRESS/GMAIL_APP_PASSWORD)", day
            )

    if day.weekday() == 0:  # Monday
        logger.info(
            "Reporting sub-agent: skipping weekly report for %s — no narrative weekly "
            "generator is defined in the build plan (module 2.7 computes stats only)",
            day,
        )

    detail = f"DAR generated for {day.isoformat()}" + (", emailed" if emailed else ", not emailed")
    logger.info("Reporting sub-agent: %s", detail)
    return {"status": "success", "detail": detail, "dar_content": content, "emailed": emailed}


if __name__ == "__main__":
    from agent.logging_config import setup_logging

    setup_logging()
    logger.info("Module 16.2 manual test: running reporting sub-agent")
    result = run(send_email=False)
    print("status:", result["status"], "| detail:", result["detail"])
