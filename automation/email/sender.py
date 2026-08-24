"""
MODULE 8 — Gmail Email Delivery

Sends every kind of outbound email (DAR, alerts, campaign outreach) through
Gmail SMTP + smtplib — zero external email API, works from any network with
no IP whitelisting, per DEVELOPMENT.md's non-negotiable stack.

Sub-modules implemented (in order):
    8.1 Gmail SMTP connector
    8.2 DAR email sender
    8.3 Alert email sender
    8.4 Campaign email sender (send-and-log building block; module 19 owns
        the bulk lead-loading/RAG-writing orchestration on top of this)
    8.5 Connection tester
"""
import logging
import smtplib
from datetime import date as date_cls, datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from agent import database
from api.config import settings

logger = logging.getLogger(__name__)

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SEND_TIMEOUT_SECONDS = 30

ALERT_TYPES = {"focus", "distraction", "wellbeing", "manager"}


def _default_recipient() -> str:
    return settings.REPORT_RECIPIENT_EMAIL or settings.GMAIL_ADDRESS


def _credentials_configured() -> bool:
    return bool(settings.GMAIL_ADDRESS and settings.GMAIL_APP_PASSWORD)


# ── 8.1 Gmail SMTP connector ──

def _open_connection() -> smtplib.SMTP:
    """Gmail App Password required (not the account password) — generated
    under Google Account > Security > 2-Step Verification > App Passwords."""
    conn = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=SEND_TIMEOUT_SECONDS)
    conn.starttls()
    conn.login(settings.GMAIL_ADDRESS, settings.GMAIL_APP_PASSWORD)
    return conn


def _send_plain_email(to_address: str, subject: str, body: str) -> bool:
    if not _credentials_configured():
        logger.error("Gmail not configured — set GMAIL_ADDRESS/GMAIL_APP_PASSWORD in .env")
        return False
    if not to_address:
        logger.error("No recipient address available for email %r", subject)
        return False

    message = MIMEMultipart()
    message["From"] = settings.GMAIL_ADDRESS
    message["To"] = to_address
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain"))

    try:
        with _open_connection() as conn:
            conn.sendmail(settings.GMAIL_ADDRESS, [to_address], message.as_string())
        logger.info("Email sent to %s: %s", to_address, subject)
        return True
    except Exception:
        logger.exception("Failed to send email to %s (subject=%r)", to_address, subject)
        return False


# ── 8.2 DAR email sender ──

def send_dar_email(day: date_cls, user_id: str = "local", recipient: Optional[str] = None) -> bool:
    conn = database.get_connection()
    row = conn.execute(
        "SELECT content, productivity_score FROM dar_reports WHERE user_id = ? AND date = ?",
        (user_id, day.isoformat()),
    ).fetchone()

    if row is None:
        logger.error("No DAR found for %s; cannot send email", day)
        return False

    score = row["productivity_score"]
    score_str = f"{score:.0f}%" if score is not None else "N/A"
    subject = f"Daily Activity Report — {day.isoformat()} (Score: {score_str})"

    sent = _send_plain_email(recipient or _default_recipient(), subject, row["content"])
    if sent:
        try:
            with database.write_cursor() as cur:
                cur.execute(
                    "UPDATE dar_reports SET emailed_at = CURRENT_TIMESTAMP WHERE user_id = ? AND date = ?",
                    (user_id, day.isoformat()),
                )
        except Exception:
            logger.exception("DAR sent but failed to record emailed_at for %s", day)
    return sent


# ── 8.3 Alert email sender ──

def send_alert_email(
    alert_type: str,
    reason: str,
    recipient: Optional[str] = None,
    dashboard_url: str = "http://localhost:5173",
) -> bool:
    if alert_type not in ALERT_TYPES:
        logger.warning("Unrecognised alert_type %r — sending anyway", alert_type)

    now = datetime.now()
    subject = f"WorkPulse Alert: {alert_type.replace('_', ' ').title()}"
    body = (
        f"Alert type: {alert_type}\n"
        f"Reason: {reason}\n"
        f"Time: {now.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        f"View dashboard: {dashboard_url}"
    )
    return _send_plain_email(recipient or _default_recipient(), subject, body)


# ── 8.4 Campaign email sender ──

def send_campaign_email(
    lead_email: str, lead_name: str, company: str, subject: str, body: str
) -> bool:
    sent = _send_plain_email(lead_email, subject, body)
    now = datetime.now()
    try:
        with database.write_cursor() as cur:
            cur.execute(
                """
                INSERT INTO campaign_log (date, time, name, email, company, subject, status, error, follow_up_sent)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
                """,
                (
                    now.date().isoformat(),
                    now.strftime("%H:%M:%S"),
                    lead_name,
                    lead_email,
                    company,
                    subject,
                    "sent" if sent else "failed",
                    None if sent else "SMTP send failed — see agent log for details",
                ),
            )
    except Exception:
        logger.exception("Failed to write campaign_log entry for %s", lead_email)
    return sent


# ── 8.5 Connection tester ──   

def test_gmail_connection() -> bool:
    if not _credentials_configured():
        return False
    try:
        with _open_connection():
            pass
        return True
    except Exception:
        logger.exception("Gmail connection test failed")
        return False


if __name__ == "__main__":
    from agent.logging_config import setup_logging

    setup_logging()
    logger.info("Module 8 manual test: testing Gmail connection")
    ok = test_gmail_connection()
    logger.info("Connection OK: %s", ok)
    if ok:
        sent = _send_plain_email(_default_recipient(), "WorkPulse AI test email", "This is a test email from Module 8.")
        logger.info("Test email sent: %s", sent)
