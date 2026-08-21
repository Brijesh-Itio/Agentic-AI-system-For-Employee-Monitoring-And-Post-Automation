"""MODULE 5 — Email routes.

GET endpoints are fully functional against campaign_log (module 8.4's
send_campaign_email already writes to it). POST /campaign/run stays 501:
module 19's writer.py (RAG personalisation) and campaign.py (orchestration)
are both empty, so there is no bulk-send logic yet for this route to
trigger — module 8 only provides the per-lead send-and-log primitive.
"""
import logging
from datetime import date as date_type

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from api.database import CampaignLog, get_db
from api.schemas import CampaignLogOut, CampaignStatsOut

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/email", tags=["email"])

# 19.6's daily send cap. Belongs in automation/config.py once module 19
# actually exists to read it; hardcoded here to match DEVELOPMENT.md's
# documented default in the meantime.
DAILY_EMAIL_LIMIT = 500


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


@router.post("/campaign/run", status_code=501)
def run_campaign():
    raise HTTPException(
        status_code=501,
        detail="Bulk email campaigns are not built yet — module 19's writer.py "
        "(RAG personalisation) and campaign.py (orchestration) are both empty. "
        "Module 8's send_campaign_email() exists as the per-lead primitive they'll "
        "call once built.",
    )


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
