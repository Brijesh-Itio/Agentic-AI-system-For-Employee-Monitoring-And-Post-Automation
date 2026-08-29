"""
MODULE 19.4 — Campaign Logger

Module 8.4's send_campaign_email() already writes every send attempt to
campaign_log after the fact (success or failure). This module owns the
*before*-send question 19.4 also asks for: has this lead already been
contacted, so the runner never sends the same lead two campaign emails.
"""
import logging

from agent import database   

logger = logging.getLogger(__name__)       

 
def already_contacted(email: str) -> bool:
    """A failed attempt never reached the lead's inbox, so it doesn't count
    as contacted — only a successful send should block a retry."""
    conn = database.get_connection()
    row = conn.execute(
        "SELECT 1 FROM campaign_log WHERE email = ? AND status = 'sent' LIMIT 1", (email,)
    ).fetchone()
    return row is not None


def get_campaign_log_for_date(day) -> list[dict]:
    conn = database.get_connection()
    rows = conn.execute(
        "SELECT * FROM campaign_log WHERE date = ? ORDER BY id ASC", (day.isoformat(),)
    ).fetchall()
    return [dict(r) for r in rows] 
