"""
MODULE 19.6 — Campaign Runner

Orchestrates the full campaign: load leads (19.1), write personalised
emails (19.2), send with a delay between sends (19.3, reusing module 8's
real Gmail sender), respecting the daily send cap. Module 19.5's
follow-up scheduling is a separate, explicitly time-triggered concern
(see follow_up() below) rather than folded into every run.
"""
import logging
import time
from datetime import date as date_cls, timedelta 
from typing import TypedDict  

from agent import database
from automation.config import DAILY_EMAIL_LIMIT
from automation.email.logger import get_campaign_log_for_date  
from automation.email.sender import send_campaign_email
from automation.email.writer import write_email
from automation.leads.store import load_leads_for_campaign

logger = logging.getLogger(__name__)

DELAY_BETWEEN_SENDS_SECONDS = 3
FOLLOW_UP_AFTER_DAYS = 3


class CampaignResult(TypedDict):
    attempted: int
    sent: int 
    skipped_unpersonalisable: int
    failed: int


def run_campaign(limit: int | None = None) -> CampaignResult:
    today = date_cls.today()
    sent_today = len(get_campaign_log_for_date(today))
    remaining_today = max(0, DAILY_EMAIL_LIMIT - sent_today)
    batch_limit = min(limit, remaining_today) if limit is not None else remaining_today

    if batch_limit <= 0:
        logger.info("Campaign runner: daily limit already reached (%d/%d today)", sent_today, DAILY_EMAIL_LIMIT)
        return {"attempted": 0, "sent": 0, "skipped_unpersonalisable": 0, "failed": 0}

    leads = load_leads_for_campaign(batch_limit)
    if not leads:
        logger.info("Campaign runner: no leads pending outreach")
        return {"attempted": 0, "sent": 0, "skipped_unpersonalisable": 0, "failed": 0}
  
    sent = 0
    skipped = 0
    failed = 0

    for i, lead in enumerate(leads):   
        written = write_email(lead)
        if written is None:
            skipped += 1
            logger.warning("Campaign runner: skipping %s — writer.py couldn't produce a personalised email", lead["email"])
            continue

        ok = send_campaign_email(
            lead_email=lead["email"],
            lead_name=lead.get("name") or "",
            company=lead.get("company") or "",
            subject=written["subject"],
            body=written["body"],
        )
        if ok:
            sent += 1 
        else:
            failed += 1

        if i < len(leads) - 1:
            time.sleep(DELAY_BETWEEN_SENDS_SECONDS)

    logger.info(
        "Campaign runner: %d attempted, %d sent, %d skipped (unpersonalisable), %d failed",
        len(leads), sent, skipped, failed,
    )
    return {"attempted": len(leads), "sent": sent, "skipped_unpersonalisable": skipped, "failed": failed}


# ── 19.5 Follow-up scheduler ─

def run_follow_ups() -> CampaignResult:
    """Leads sent to >= FOLLOW_UP_AFTER_DAYS ago with follow_up_sent = 0.
    Reply detection isn't possible with this stack (smtplib only sends —
    no IMAP/inbox polling is anywhere in DEVELOPMENT.md's tech stack), so
    this follows up with everyone past the window rather than pretending
    to know who replied."""
    cutoff = (date_cls.today() - timedelta(days=FOLLOW_UP_AFTER_DAYS)).isoformat()
    conn = database.get_connection()
    rows = conn.execute(
        """
        SELECT * FROM campaign_log
        WHERE status = 'sent' AND follow_up_sent = 0 AND date <= ?
        ORDER BY id ASC
        """,
        (cutoff,),
    ).fetchall()

    if not rows:
        logger.info("Follow-up scheduler: nothing due")
        return {"attempted": 0, "sent": 0, "skipped_unpersonalisable": 0, "failed": 0}

    sent = 0
    failed = 0
    for i, row in enumerate(rows):
        lead = dict(row)
        subject = f"Following up: {lead['subject']}" if lead.get("subject") else "Following up"
        body = (
            f"Hi {lead['name'] or ''},\n\n"
            f"Wanted to follow up on my note from {lead['date']} — still happy to connect if useful.\n\n"
            "No worries at all if the timing isn't right."
        )
        ok = send_campaign_email(
            lead_email=lead["email"], lead_name=lead.get("name") or "",
            company=lead.get("company") or "", subject=subject, body=body,
        )
        if ok:
            sent += 1  
            with database.write_cursor() as cur:
                cur.execute("UPDATE campaign_log SET follow_up_sent = 1 WHERE id = ?", (lead["id"],))
        else:
            failed += 1

        if i < len(rows) - 1:
            time.sleep(DELAY_BETWEEN_SENDS_SECONDS)  

    logger.info("Follow-up scheduler: %d attempted, %d sent, %d failed", len(rows), sent, failed)
    return {"attempted": len(rows), "sent": sent, "skipped_unpersonalisable": 0, "failed": failed}


if __name__ == "__main__":
    from agent.logging_config import setup_logging

    setup_logging()
    logger.info("Module 19.6 manual test: running campaign")
    print(run_campaign())
