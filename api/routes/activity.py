"""MODULE 5.2 — Activity routes.

Scoped to the logged-in user (api.auth.get_current_user), not a hardcoded
identity — an employee only ever sees their own tracked activity here.
"""
import logging
from datetime import date as date_type

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from api.auth import get_current_user
from api.database import ActivityLog, HourlyScore, IdlePeriod, User, get_db
from api.schemas import ActivityLogOut, AppSummaryOut, ContextSwitchingHourOut, IdlePeriodOut

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/activity", tags=["activity"])


def _sessions_for_date(db: Session, day: date_type, user_id: str):
    return (
        db.query(ActivityLog)
        .filter(ActivityLog.user_id == user_id, ActivityLog.date == day)
        .order_by(ActivityLog.start_time.asc())
        .all()
    )


@router.get("/today", response_model=list[ActivityLogOut])
def get_today_activity(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return _sessions_for_date(db, date_type.today(), current_user.id)


@router.get("/date/{target_date}", response_model=list[ActivityLogOut])
def get_activity_by_date(
    target_date: date_type, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    return _sessions_for_date(db, target_date, current_user.id)


@router.get("/apps/summary", response_model=list[AppSummaryOut])
def get_apps_summary(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    today = date_type.today()
    rows = (
        db.query(
            ActivityLog.app_name,
            ActivityLog.category,
            func.sum(ActivityLog.duration_seconds).label("total_seconds"),
            func.count(ActivityLog.id).label("sessions"),
        )
        .filter(ActivityLog.user_id == current_user.id, ActivityLog.date == today)
        .group_by(ActivityLog.app_name)
        .order_by(func.sum(ActivityLog.duration_seconds).desc())
        .all()
    )
    return [
        AppSummaryOut(
            app_name=r.app_name,
            total_seconds=r.total_seconds or 0,
            category=r.category or "uncategorised",
            sessions=r.sessions,
        )
        for r in rows
    ]


@router.get("/apps/top", response_model=list[AppSummaryOut])
def get_top_apps(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user), limit: int = 10
):
    return get_apps_summary(db, current_user)[:limit]


@router.get("/context-switching", response_model=list[ContextSwitchingHourOut])
def get_context_switching(
    target_date: date_type | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Hourly context switching score for a date (defaults to today), from
    module 2's rolled-up hourly_scores (each rollover captures the switch
    count for its hour). `target_date` added for module 10's Timeline view,
    which needs this for whatever day is selected, not just today."""
    day = target_date or date_type.today()
    rows = (
        db.query(HourlyScore.hour, HourlyScore.switch_count)
        .filter(HourlyScore.user_id == current_user.id, HourlyScore.date == day)
        .order_by(HourlyScore.hour.asc())
        .all()
    )
    return [ContextSwitchingHourOut(hour=r.hour, switch_count=r.switch_count or 0) for r in rows]


@router.get("/idle/date/{target_date}", response_model=list[IdlePeriodOut])
def get_idle_periods_by_date(
    target_date: date_type, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """Not in module 5's original route list — added for module 10's idle
    period markers, which need the raw idle_periods rows module 2 already
    tracks."""
    rows = (
        db.query(IdlePeriod)
        .filter(IdlePeriod.user_id == current_user.id, IdlePeriod.date == target_date)
        .order_by(IdlePeriod.start_time.asc())
        .all()
    )
    return rows
