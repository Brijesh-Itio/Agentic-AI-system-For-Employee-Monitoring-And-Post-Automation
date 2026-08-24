"""MODULE 5.7 — Status routes."""
import importlib.util
import logging
from datetime import datetime

import requests
from fastapi import APIRouter, Depends
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from api.auth import get_current_user
from api.config import settings
from api.database import AgentHeartbeat, ActivityLog, User, get_db
from api.schemas import StatusComponentOut, SystemStatusOut

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/status", tags=["status"])


def _check_ollama() -> StatusComponentOut:
    try:
        resp = requests.get(f"{settings.OLLAMA_BASE_URL}/api/tags", timeout=2)
        if resp.status_code == 200:
            return StatusComponentOut(connected=True, detail="Ollama reachable")
        return StatusComponentOut(connected=False, detail=f"Ollama returned HTTP {resp.status_code}")
    except requests.RequestException as exc:
        return StatusComponentOut(connected=False, detail=f"Ollama unreachable: {exc.__class__.__name__}")


def _check_agent(db: Session, user_id: str) -> StatusComponentOut:
    """Liveness is agent_heartbeat (touched every ~15s regardless of app
    switches), not activity_logs — a row there only appears once a session
    *closes*, so staying on one app/window for a while used to make a
    perfectly healthy agent falsely report offline."""
    try:
        row = db.query(AgentHeartbeat).filter(AgentHeartbeat.user_id == user_id).first()
    except SQLAlchemyError:
        return StatusComponentOut(connected=False, detail="Could not query agent_heartbeat")

    if row is None:
        return StatusComponentOut(connected=False, detail="No heartbeat recorded yet for this account")

    age_seconds = (datetime.now() - row.last_seen).total_seconds()
    if age_seconds <= settings.AGENT_HEARTBEAT_WINDOW_SECONDS:
        return StatusComponentOut(connected=True, detail="Agent actively tracking")
    return StatusComponentOut(
        connected=False, detail=f"Last heartbeat {int(age_seconds)}s ago — agent may be stopped"
    )


def _check_database(db: Session) -> StatusComponentOut:
    try:
        db.query(ActivityLog).limit(1).all()
        return StatusComponentOut(connected=True, detail="SQLite reachable")
    except SQLAlchemyError as exc:
        return StatusComponentOut(connected=False, detail=f"Database error: {exc.__class__.__name__}")


def _check_gmail() -> StatusComponentOut:
    if not settings.GMAIL_ADDRESS or not settings.GMAIL_APP_PASSWORD:
        return StatusComponentOut(
            connected=False, detail="Not configured — set GMAIL_ADDRESS/GMAIL_APP_PASSWORD in .env"
        )
    from automation.email.sender import test_gmail_connection

    return StatusComponentOut(
        connected=test_gmail_connection(), detail="Gmail SMTP check via automation.email.sender"
    )


def _check_playwright() -> StatusComponentOut:
    if importlib.util.find_spec("playwright") is None:
        return StatusComponentOut(connected=False, detail="playwright package not installed yet")
    return StatusComponentOut(connected=True, detail="playwright package installed")


@router.get("", response_model=SystemStatusOut)
def get_system_status(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return SystemStatusOut(
        ollama=_check_ollama(),
        agent=_check_agent(db, current_user.id),
        database=_check_database(db),
        gmail=_check_gmail(),
        playwright=_check_playwright(),
    )
