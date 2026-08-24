"""Attendance sub-module.

Entirely derived from data that already exists (daily_stats, itself built
from real activity_logs tracking) — there is no separate "clock in/out"
button anywhere, matching how work_start/work_end already work elsewhere
in this codebase. agent/attendance.py owns the actual policy (what counts
as a working day, what counts as full/half/absent); this file is just the
month-range query plus RBAC around it.
"""
import calendar
import logging
from datetime import date as date_type

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from agent.attendance import classify_attendance, week_off_reason
from agent.time_intelligence import TimeIntelligenceEngine
from api.auth import get_current_user, require_oversight
from api.database import DailyStats, User, get_db
from api.schemas import AttendanceDayOut, AttendanceSummaryOut

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/attendance", tags=["attendance"])


def _month_range(month: str) -> tuple[date_type, date_type]:
    try:
        year, mon = (int(part) for part in month.split("-"))
        first = date_type(year, mon, 1)
    except (ValueError, TypeError):
        raise HTTPException(status_code=422, detail="month must be YYYY-MM")
    last_day = calendar.monthrange(year, mon)[1]
    return first, date_type(year, mon, last_day)


def _build_summary(db: Session, user_id: str, month: str) -> AttendanceSummaryOut:
    first, last = _month_range(month)
    today = date_type.today()

    rows_by_date = {
        row.date: row
        for row in db.query(DailyStats).filter(
            DailyStats.user_id == user_id, DailyStats.date >= first, DailyStats.date <= last
        )
    }

    days: list[AttendanceDayOut] = []
    counts = {"full_day": 0, "half_day": 0, "absent": 0, "week_off": 0}

    day = first
    while day <= last:
        row = rows_by_date.get(day)
        active_seconds = row.total_active_seconds if row else 0
        status = classify_attendance(day, active_seconds or 0, today)
        if status in counts:
            counts[status] += 1

        days.append(
            AttendanceDayOut(
                date=day,
                status=status,
                week_off_reason=week_off_reason(day),
                check_in=row.work_start if row else None,
                check_out=row.work_end if row else None,
                active_seconds=active_seconds or 0,
                active_hours_formatted=TimeIntelligenceEngine.format_hours_minutes(active_seconds or 0),
                focus_score=row.focus_score if row else None,
            )
        )
        day = date_type.fromordinal(day.toordinal() + 1)

    return AttendanceSummaryOut(
        month=month,
        full_days=counts["full_day"],
        half_days=counts["half_day"],
        absents=counts["absent"],
        week_offs=counts["week_off"],
        days=days,
    )


@router.get("/me", response_model=AttendanceSummaryOut)
def my_attendance(month: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return _build_summary(db, current_user.id, month)


@router.get("/{user_id}", response_model=AttendanceSummaryOut)
def member_attendance(
    user_id: str, month: str, db: Session = Depends(get_db), _: User = Depends(require_oversight)
):
    """Manager/admin view of someone else's attendance — same oversight
    rule as team.py's per-member activity endpoint."""
    if db.query(User).filter(User.id == user_id).first() is None:
        raise HTTPException(status_code=404, detail=f"No user {user_id}")
    return _build_summary(db, user_id, month)
