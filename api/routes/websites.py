"""MODULE 5.4 — Website routes."""
import logging
from datetime import date as date_type

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from agent.database import get_top_sites_for_date
from api.config import settings
from api.database import Website, get_db
from api.schemas import TopSiteOut, WebsiteOut

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/websites", tags=["websites"])


def _sessions_for_date(db: Session, day: date_type):
    return (
        db.query(Website)
        .filter(Website.user_id == settings.DEFAULT_USER_ID, Website.date == day)
        .order_by(Website.start_time.asc())
        .all()
    )


@router.get("/today", response_model=list[WebsiteOut])
def get_today_websites(db: Session = Depends(get_db)):
    return _sessions_for_date(db, date_type.today())


@router.get("/top", response_model=list[TopSiteOut])
def get_top_sites(limit: int = 10):
    rows = get_top_sites_for_date(date_type.today(), settings.DEFAULT_USER_ID, limit)
    return [
        TopSiteOut(domain=r["domain"], total_seconds=r["total_seconds"] or 0, visits=r["visits"])
        for r in rows
    ]


@router.get("/date/{target_date}", response_model=list[WebsiteOut])
def get_websites_by_date(target_date: date_type, db: Session = Depends(get_db)):
    return _sessions_for_date(db, target_date)
