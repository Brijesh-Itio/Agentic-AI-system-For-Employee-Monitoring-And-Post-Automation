"""MODULE 5.6 — Reports routes. Scoped to the logged-in user.

GET endpoints are fully functional against the dar_reports/weekly_reports
tables (created in module 5's schema). POST /dar/generate now calls module
7's real Ollama-powered generator. POST /weekly/generate stays 501: no
module in DEVELOPMENT.md's 24-module build order defines a narrative weekly
report generator (module 2.7 only computes trend statistics), so faking one
here would be building ahead of spec rather than honestly reflecting it.
"""
import logging
from datetime import date as date_type

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.auth import get_current_user
from api.database import DarReport, User, WeeklyReport, get_db
from api.schemas import DarReportOut, WeeklyReportOut

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/dar/today", response_model=DarReportOut)
def get_today_dar(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    row = (
        db.query(DarReport)
        .filter(DarReport.user_id == current_user.id, DarReport.date == date_type.today())
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="No DAR generated for today yet")
    return row


@router.get("/dar/date/{target_date}", response_model=DarReportOut)
def get_dar_by_date(
    target_date: date_type, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    row = (
        db.query(DarReport)
        .filter(DarReport.user_id == current_user.id, DarReport.date == target_date)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail=f"No DAR found for {target_date}")
    return row


@router.get("/dar/all", response_model=list[DarReportOut])
def get_all_dars(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return (
        db.query(DarReport)
        .filter(DarReport.user_id == current_user.id)
        .order_by(DarReport.date.desc())
        .all()
    )


@router.post("/dar/generate", response_model=DarReportOut)
def generate_dar_now(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    from ai.dar_generator import generate_and_save_dar

    content = generate_and_save_dar(user_id=current_user.id)
    if content is None:
        raise HTTPException(status_code=502, detail="Ollama unreachable or timed out during DAR generation")

    row = (
        db.query(DarReport)
        .filter(DarReport.user_id == current_user.id, DarReport.date == date_type.today())
        .first()
    )
    return row


@router.get("/weekly/latest", response_model=WeeklyReportOut)
def get_latest_weekly_report(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    row = (
        db.query(WeeklyReport)
        .filter(WeeklyReport.user_id == current_user.id)
        .order_by(WeeklyReport.week_start.desc())
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="No weekly report generated yet")
    return row


@router.post("/weekly/generate")
def generate_weekly_report_now():
    raise HTTPException(
        status_code=501,
        detail="Weekly narrative report generation is not defined in any build module yet "
        "(module 2.7 only computes trend statistics, not a written report)",
    )


@router.post("/dar/date/{target_date}/send", response_model=DarReportOut)
def send_dar_by_date(
    target_date: date_type, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """13.4 — email-resend button. Reuses module 8's real Gmail sender."""
    row = (
        db.query(DarReport)
        .filter(DarReport.user_id == current_user.id, DarReport.date == target_date)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail=f"No DAR found for {target_date}")

    from automation.email.sender import send_dar_email

    sent = send_dar_email(target_date, current_user.id)
    if not sent:
        raise HTTPException(
            status_code=502,
            detail="Failed to send — check Gmail is configured (GMAIL_ADDRESS/GMAIL_APP_PASSWORD in .env)",
        )

    db.refresh(row)
    return row
