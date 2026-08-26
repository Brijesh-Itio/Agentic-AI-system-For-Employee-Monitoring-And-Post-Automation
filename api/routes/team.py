"""MODULE 5 / 21.1-21.2 — Team routes, now role-gated.

Every tracking table already carries a user_id column, so per-user querying
works today without any migration. What module 21 actually adds on top is
the users table (registering who those ids belong to) and the aggregation
queries below. The AI team analysis (21.4) and comparison chart (21.5) stay
out of scope here — they belong to module 21's own build step, not module 5.

RBAC (added after module 21, see DEVELOPMENT.md "Login & Role-Based
Access"): team-wide views (overview, analysis, the full user list) need
`manager` or `admin` — an `employee` has no business seeing everyone else's
data. Per-member activity is the one exception: an employee can always see
their *own* history, matching what their personal dashboard already shows
them; only looking at someone *else's* activity requires oversight.
Creating/deactivating accounts and changing roles is `admin`-only — that's
"the boss" controlling who exists and what they can do, not something a
manager should be able to grant themselves or a peer.
"""
import logging
from datetime import date as date_type, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from typing import Optional

from agent import database as agent_db
from ai.team_analysis import analyse_team
from api.auth import get_current_user, get_optional_current_user, hash_password, require_admin, require_oversight
from api.config import settings
from api.database import ActivityLog, AgentHeartbeat, DailyStats, User, get_db
from api.schemas import (
    FeatureFlagUpdate,
    SetPasswordRequest,
    TeamAnalysisOut,
    TeamMemberStatusOut,
    UserCreate,
    UserOut,
    UserProfileUpdate,
    UserRoleUpdate,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/team", tags=["team"])


def _to_user_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        name=user.name,
        email=user.email,
        role=user.role,
        organisation_id=user.organisation_id,
        created_at=user.created_at,
        has_password=bool(user.password_hash),
    )


@router.get("/users", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db), _: User = Depends(require_oversight)):
    users = db.query(User).order_by(User.created_at.asc()).all()
    return [_to_user_out(u) for u in users]


@router.post("/users", response_model=UserOut, status_code=201)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    is_bootstrap = db.query(User).count() == 0
    if not is_bootstrap and (current_user is None or current_user.role != "admin"):
        # Same 403 whether unauthenticated or authenticated-but-not-admin —
        # this endpoint just isn't open once accounts already exist.
        raise HTTPException(status_code=403, detail="Requires admin — only the first account can self-register")

    if db.query(User).filter(User.id == payload.id).first() is not None:
        raise HTTPException(status_code=409, detail=f"User {payload.id} already exists")

    data = payload.model_dump(exclude={"password"})
    if is_bootstrap:
        # The very first account is always the admin ("the boss") — there's
        # no one else yet to have granted that role.
        data["role"] = "admin"
        logger.info("Bootstrap: creating first account %s as admin", payload.id)
    row = User(**data, created_at=datetime.now())
    if payload.password:
        row.password_hash = hash_password(payload.password)
    db.add(row)
    db.commit()
    db.refresh(row)
    return _to_user_out(row)


@router.delete("/users/{user_id}", status_code=204)
def delete_user(user_id: str, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account while logged in as it")
    row = db.query(User).filter(User.id == user_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail=f"No user {user_id}")
    db.delete(row)
    db.commit()


@router.patch("/users/{user_id}/profile", response_model=UserOut)
def update_user_profile(
    user_id: str, payload: UserProfileUpdate, db: Session = Depends(get_db), _: User = Depends(require_admin)
):
    """Admin-only edit of name/email — e.g. correcting a typo'd email so
    Google SSO can match it, or fixing a name. Never touches tracked data:
    every table (activity_logs, screenshots, dar_reports, attendance, ...)
    keys off the account's immutable `id`, not name or email, so the
    member's full history stays exactly where it is regardless."""
    row = db.query(User).filter(User.id == user_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail=f"No user {user_id}")

    if payload.name is not None:
        name = payload.name.strip()
        if not name:
            raise HTTPException(status_code=422, detail="Name can't be blank")
        row.name = name

    if payload.email is not None:
        email = payload.email.strip() or None
        if email and db.query(User).filter(User.email == email, User.id != user_id).first() is not None:
            raise HTTPException(status_code=409, detail="That email is already in use by another account")
        row.email = email

    db.commit()
    db.refresh(row)
    return _to_user_out(row)


@router.patch("/users/{user_id}/role", response_model=UserOut)
def update_user_role(
    user_id: str, payload: UserRoleUpdate, db: Session = Depends(get_db), _: User = Depends(require_admin)
):
    row = db.query(User).filter(User.id == user_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail=f"No user {user_id}")
    row.role = payload.role
    db.commit()
    db.refresh(row)
    return _to_user_out(row)


@router.post("/users/{user_id}/password", status_code=204)
def set_user_password(
    user_id: str, payload: SetPasswordRequest, db: Session = Depends(get_db), _: User = Depends(require_admin)
):
    """Admin sets or resets any account's login password — e.g. for a user
    created before this feature existed, or one who's locked out."""
    row = db.query(User).filter(User.id == user_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail=f"No user {user_id}")
    if len(payload.password) < 6:
        raise HTTPException(status_code=422, detail="Password must be at least 6 characters")
    row.password_hash = hash_password(payload.password)
    db.commit()


def _member_status(db: Session, user: User, today: date_type) -> TeamMemberStatusOut:
    # "active" vs "idle" is decided by agent_heartbeat (touched every ~15s
    # independent of app switches) — activity_logs.end_time is never NULL
    # (a session only gets written once it *closes*, always with both
    # timestamps already set), so checking it for "still open" here always
    # evaluated false and could never actually report "active".
    heartbeat = db.query(AgentHeartbeat).filter(AgentHeartbeat.user_id == user.id).first()
    latest_session = (
        db.query(ActivityLog)
        .filter(ActivityLog.user_id == user.id, ActivityLog.date == today)
        .order_by(ActivityLog.start_time.desc())
        .first()
    )
    stats = db.query(DailyStats).filter(DailyStats.user_id == user.id, DailyStats.date == today).first()

    status = "offline"
    if heartbeat is not None:
        age_seconds = (datetime.now() - heartbeat.last_seen).total_seconds()
        status = "active" if age_seconds <= settings.AGENT_HEARTBEAT_WINDOW_SECONDS else "idle"
    current_app = latest_session.app_name if latest_session else None

    return TeamMemberStatusOut(
        user=_to_user_out(user),
        status=status,
        focus_score=stats.focus_score if stats else None,
        active_hours_today=round((stats.total_active_seconds or 0) / 3600, 2) if stats else 0.0,
        current_app=current_app,
    )


@router.get("/overview", response_model=list[TeamMemberStatusOut])
def team_overview(db: Session = Depends(get_db), _: User = Depends(require_oversight)):
    today = date_type.today()
    return [_member_status(db, user, today) for user in db.query(User).all()]


@router.get("/member/{user_id}/activity", response_model=list)
def member_activity(
    user_id: str,
    target_date: date_type | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """21.3 — individual member view. Anyone can view their own activity;
    viewing someone else's requires manager/admin oversight."""
    if user_id != current_user.id and current_user.role not in ("manager", "admin"):
        raise HTTPException(status_code=403, detail="Not authorised to view this user's activity")
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


@router.get("/member/{user_id}/features", response_model=dict[str, bool])
def get_member_features(user_id: str, db: Session = Depends(get_db), _: User = Depends(require_oversight)):
    """Module 21 extension — which automatic monitoring features an admin
    has enabled for this employee. Any feature never explicitly toggled
    reads back as enabled (see agent_db.get_feature_flags's default)."""
    if db.query(User).filter(User.id == user_id).first() is None:
        raise HTTPException(status_code=404, detail=f"No user {user_id}")
    return agent_db.get_feature_flags(user_id)


@router.put("/member/{user_id}/features/{feature}", response_model=dict[str, bool])
def set_member_feature(
    user_id: str,
    feature: str,
    payload: FeatureFlagUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Admin-only, same as role changes and password resets — a manager
    gets oversight of what's already tracked, not control over whether
    tracking happens at all."""
    if feature not in agent_db.DEFAULT_FEATURE_TYPES:
        raise HTTPException(
            status_code=400, detail=f"Unknown feature. Must be one of {agent_db.DEFAULT_FEATURE_TYPES}"
        )
    if db.query(User).filter(User.id == user_id).first() is None:
        raise HTTPException(status_code=404, detail=f"No user {user_id}")
    agent_db.set_feature_flag(feature, payload.enabled, user_id)
    return agent_db.get_feature_flags(user_id)


@router.get("/analysis", response_model=TeamAnalysisOut)
def team_analysis(window_days: int = 7, _: User = Depends(require_oversight)):
    """21.4 — weekly Ollama-powered team analysis, computed on demand."""
    return analyse_team(window_days=window_days)
