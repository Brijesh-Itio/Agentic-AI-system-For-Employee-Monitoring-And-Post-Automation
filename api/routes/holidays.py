"""Org-wide holiday calendar routes.

Not in DEVELOPMENT.md's original module list — added on request so HR (or
admin) can declare company holidays/paid holidays on specific dates, which
attendance.py then treats as automatic week-offs for everyone (see
api/routes/attendance.py's `_build_summary`), and so every other user gets
notified (in-app alert + email, same pipeline module 14's alerts already
use) the moment one is added.

Read access is open to any logged-in user (everyone needs to see the
holiday calendar); write access (create/delete) is HR/admin-only.
"""
import logging
from datetime import date as date_type, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from agent import database as agent_db
from ai.tools.activity_tools import trigger_alert
from api.auth import get_current_user, require_hr
from api.database import CompanyHoliday, User, get_db
from api.schemas import CompanyHolidayCreate, CompanyHolidayOut

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/holidays", tags=["holidays"])


@router.get("", response_model=list[CompanyHolidayOut])
def list_holidays(
    start: date_type | None = None,
    end: date_type | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    # Defaults to a wide-ish window (this year and next) rather than
    # requiring the caller to always pass a range — the calendar/attendance
    # pages both just want "everything relevant", not a specific month.
    start = start or date_type(date_type.today().year, 1, 1)
    end = end or date_type(date_type.today().year + 1, 12, 31)
    return (
        db.query(CompanyHoliday)
        .filter(CompanyHoliday.date >= start, CompanyHoliday.date <= end)
        .order_by(CompanyHoliday.date.asc())
        .all()
    )


@router.post("", response_model=CompanyHolidayOut)
def create_holiday(
    payload: CompanyHolidayCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_hr),
):
    holiday_id = agent_db.insert_company_holiday(
        payload.date, payload.title, payload.holiday_type, payload.description, current_user.id
    )

    label = "Paid Holiday" if payload.holiday_type == "paid_holiday" else "Holiday"
    # %-d (no leading zero) is a glibc/macOS strftime extension only — it
    # raises ValueError("Invalid format string") on Windows' C runtime,
    # which this whole stack runs on. day/year are pulled in directly
    # instead of relying on a platform-specific strftime code.
    date_label = f"{payload.date.strftime('%A, %B')} {payload.date.day}, {payload.date.year}"
    message = f"{label} announced: {payload.title} on {date_label}."
    _notify_everyone(db, message, exclude_user_id=current_user.id)

    row = db.query(CompanyHoliday).filter(CompanyHoliday.id == holiday_id).first()
    return row


@router.delete("/{holiday_id}")
def delete_holiday(
    holiday_id: int, db: Session = Depends(get_db), _: User = Depends(require_hr)
):
    row = db.query(CompanyHoliday).filter(CompanyHoliday.id == holiday_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Holiday not found")
    agent_db.delete_company_holiday(holiday_id)
    return {"deleted": True}


def _notify_everyone(db: Session, message: str, exclude_user_id: str) -> None:
    """Fans the same alert out to every user (in-app + email, via module
    14's existing trigger_alert — each recipient's own alert_preferences
    still apply). Every other alert type in this codebase emails one fixed
    admin inbox regardless of user_id, which is wrong here: a holiday
    announcement needs to reach each real employee's own address, so their
    individual `users.email` is passed through explicitly."""
    for user in db.query(User).all():
        if user.id == exclude_user_id:
            continue
        try:
            trigger_alert("holiday_announcement", message, user_id=user.id, recipient=user.email)
        except Exception:
            logger.exception("Failed to notify %s of holiday announcement", user.id)
