"""MODULE 5 / 21.1-21.2 — Team routes.

Every tracking table already carries a user_id column, so per-user querying
works today without any migration. What module 21 actually adds on top is
the users table (registering who those ids belong to) and the aggregation
queries below. The AI team analysis (21.4) and comparison chart (21.5) stay
out of scope here — they belong to module 21's own build step, not module 5.
"""
import logging
from datetime import date as date_type, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from api.config import settings
from api.database import ActivityLog, DailyStats, User, get_db
from api.schemas import TeamMemberStatusOut, UserCreate, UserOut

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/team", tags=["team"])


@router.get("/users", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db)):
    return db.query(User).order_by(User.created_at.asc()).all()


@router.post("/users", response_model=UserOut, status_code=201)
def create_user(payload: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.id == payload.id).first() is not None:
        raise HTTPException(status_code=409, detail=f"User {payload.id} already exists")
    row = User(**payload.model_dump(), created_at=datetime.now())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _member_status(db: Session, user: User, today: date_type) -> TeamMemberStatusOut:
    latest_session = (
        db.query(ActivityLog)
        .filter(ActivityLog.user_id == user.id, ActivityLog.date == today)
        .order_by(ActivityLog.start_time.desc())
        .first()
    )
    stats = db.query(DailyStats).filter(DailyStats.user_id == user.id, DailyStats.date == today).first()

    status = "offline"
    current_app = None
    if latest_session is not None:
        reference = latest_session.end_time or latest_session.start_time
        age_seconds = (datetime.now() - reference).total_seconds()
        if age_seconds <= settings.AGENT_HEARTBEAT_WINDOW_SECONDS and latest_session.end_time is None:
            status = "active"
            current_app = latest_session.app_name
        else:
            status = "idle"
            current_app = latest_session.app_name

    return TeamMemberStatusOut(
        user=user,
        status=status,
        focus_score=stats.focus_score if stats else None,
        active_hours_today=round((stats.total_active_seconds or 0) / 3600, 2) if stats else 0.0,
        current_app=current_app,
    )


@router.get("/overview", response_model=list[TeamMemberStatusOut])
def team_overview(db: Session = Depends(get_db)):
    today = date_type.today()
    return [_member_status(db, user, today) for user in db.query(User).all()]


@router.get("/member/{user_id}/activity", response_model=list)
def member_activity(user_id: str, target_date: date_type | None = None, db: Session = Depends(get_db)):
    """21.3 — individual member view, reusing module 5.2's per-user filtering."""
    if db.query(User).filter(User.id == user_id).first() is None:
        raise HTTPException(status_code=404, detail=f"No user {user_id}")
    day = target_date or date_type.today()
    rows = (
        db.query(ActivityLog)
        .filter(ActivityLog.user_id == user_id, ActivityLog.date == day)
        .order_by(ActivityLog.start_time.asc())
        .all()
    )
    return [
        {
            "id": r.id,
            "app_name": r.app_name,
            "window_title": r.window_title,
            "start_time": r.start_time,
            "end_time": r.end_time,
            "duration_seconds": r.duration_seconds,
            "category": r.category,
        }
        for r in rows
    ]
