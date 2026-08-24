"""MODULE 14.5/14.6 — Alerts routes. Scoped to the logged-in user.

Not in DEVELOPMENT.md's original api/routes/ file list, but the
notification bell (14.5) and alert preferences (14.6) both need
somewhere to read/write this data — no existing route file's scope
covers it.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from agent import database as agent_db
from agent.database import DEFAULT_ALERT_TYPES
from api.auth import get_current_user
from api.database import Alert, User, get_db
from api.schemas import AlertOut, AlertPreferenceOut, AlertPreferenceUpdate

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/alerts", tags=["alerts"])


@router.get("", response_model=list[AlertOut])
def get_alerts(limit: int = 50, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return (
        db.query(Alert)
        .filter(Alert.user_id == current_user.id)
        .order_by(Alert.triggered_at.desc())
        .limit(limit)
        .all()
    )


@router.get("/unread-count")
def get_unread_count(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    count = (
        db.query(func.count(Alert.id))
        .filter(Alert.user_id == current_user.id, Alert.dismissed_at.is_(None))
        .scalar()
    ) or 0
    return {"unread_count": count}


@router.post("/{alert_id}/dismiss", response_model=AlertOut)
def dismiss_alert(
    alert_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    row = db.query(Alert).filter(Alert.id == alert_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Alert not found")
    if row.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorised to dismiss this alert")
    agent_db.dismiss_alert(alert_id)
    db.refresh(row)
    return row


@router.get("/preferences", response_model=dict[str, AlertPreferenceOut])
def get_preferences(current_user: User = Depends(get_current_user)):
    prefs = agent_db.get_alert_preferences(current_user.id)
    return {k: AlertPreferenceOut(**v) for k, v in prefs.items()}


@router.put("/preferences/{alert_type}", response_model=AlertPreferenceOut)
def update_preference(
    alert_type: str, update: AlertPreferenceUpdate, current_user: User = Depends(get_current_user)
):
    if alert_type not in DEFAULT_ALERT_TYPES:
        raise HTTPException(status_code=400, detail=f"Unknown alert type. Must be one of {DEFAULT_ALERT_TYPES}")
    agent_db.set_alert_preference(alert_type, update.enabled, update.threshold_value, current_user.id)
    prefs = agent_db.get_alert_preferences(current_user.id)
    return AlertPreferenceOut(**prefs[alert_type])
