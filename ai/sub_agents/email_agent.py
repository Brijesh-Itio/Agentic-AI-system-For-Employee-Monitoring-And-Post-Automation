"""
MODULE 16.4 — Email Sub-Agent

Runs module 19's real campaign pipeline: loads leads needing outreach
(19.1), writes RAG-personalised emails (19.2), and sends them via
Gmail (19.3). Actually sending requires GMAIL_ADDRESS/GMAIL_APP_PASSWORD
in .env — without it, this still does the real work of finding and
writing for pending leads, and fails honestly on the send step.
"""
import logging
from typing import TypedDict

from agent.config import USER_ID

logger = logging.getLogger(__name__)


class EmailResult(TypedDict):
    status: str  # "success" | "failure"
    detail: str
    leads_pending: int
    sent: int


def run(user_id: str = USER_ID) -> EmailResult:
    from automation.email.campaign import run_campaign

    result = run_campaign()
    if result["attempted"] == 0:
        detail = "No leads pending outreach"
        logger.info("Email sub-agent: %s", detail)
        return {"status": "success", "detail": detail, "leads_pending": 0, "sent": 0}

    detail = (
        f"{result['attempted']} lead(s) processed: {result['sent']} sent, "
        f"{result['skipped_unpersonalisable']} skipped (writer couldn't personalise), "
        f"{result['failed']} failed to send"
    )
    status = "success" if result["sent"] > 0 or result["attempted"] == result["skipped_unpersonalisable"] else "failure"
    logger.info("Email sub-agent: %s", detail)
    return {"status": status, "detail": detail, "leads_pending": result["attempted"], "sent": result["sent"]}


if __name__ == "__main__":
    from agent.logging_config import setup_logging

    setup_logging()
    logger.info("Module 16.4 manual test: running email sub-agent")
    print(run())
