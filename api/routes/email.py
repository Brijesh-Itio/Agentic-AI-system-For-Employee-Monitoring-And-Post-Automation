"""MODULE 5 — Email routes.

GET endpoints are fully functional against campaign_log (module 8.4's
send_campaign_email already writes to it). POST /campaign/run calls
module 19's real pipeline (lead loader -> RAG writer -> Gmail sender) —
requires GMAIL_ADDRESS/GMAIL_APP_PASSWORD in .env to actually send;
otherwise leads still get written for, just not sent.
"""
import logging
from datetime import date as date_type

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from api.database import CampaignLog, get_db
from api.schemas import CampaignLogOut, CampaignStatsOut
from automation.config import DAILY_EMAIL_LIMIT

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/email", tags=["email"])


@router.get("/campaigns", response_model=list[CampaignLogOut])
def list_campaign_log(db: Session = Depends(get_db)):
    return db.query(CampaignLog).order_by(CampaignLog.date.desc(), CampaignLog.time.desc()).all()


@router.get("/campaigns/stats", response_model=CampaignStatsOut)
def campaign_stats(db: Session = Depends(get_db)):
    total_sent = db.query(func.count(CampaignLog.id)).filter(CampaignLog.status == "sent").scalar() or 0
    total_failed = db.query(func.count(CampaignLog.id)).filter(CampaignLog.status == "failed").scalar() or 0
    sent_today = (
        db.query(func.count(CampaignLog.id))
        .filter(CampaignLog.date == date_type.today(), CampaignLog.status == "sent")
        .scalar()
        or 0
    )
    return CampaignStatsOut(
        total_sent=total_sent,
        total_failed=total_failed,
        sent_today=sent_today,
        daily_limit=DAILY_EMAIL_LIMIT,
    )


@router.post("/campaign/run")
def trigger_campaign(limit: int | None = None):
    """Synchronous, like /api/reports/dar/generate — a real Ollama call per
    lead plus real SMTP sends, so this can take a while for a large batch."""
    from automation.email.campaign import run_campaign as run_campaign_pipeline

    return run_campaign_pipeline(limit)


@router.post("/follow-ups/run")
def trigger_follow_ups():
    from automation.email.campaign import run_follow_ups

    return run_follow_ups()


@router.post("/test-connection")
def test_connection():
    from automation.email.sender import test_gmail_connection

    ok = test_gmail_connection()
    if not ok:
        raise HTTPException(
            status_code=502,
            detail="Gmail connection failed — check GMAIL_ADDRESS/GMAIL_APP_PASSWORD in .env",
        )
    return {"connected": True}
