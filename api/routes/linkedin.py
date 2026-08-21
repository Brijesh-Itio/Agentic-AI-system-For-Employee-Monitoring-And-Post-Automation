"""MODULE 5 — LinkedIn routes.

GET endpoints are fully functional against the post_log table (schema owned
by agent/database.py). POST /post stays 501: module 18's content_writer.py,
image_finder.py and poster.py are all still empty stubs, so there is no
Playwright automation yet for this route to call — faking a success here
would hide that module 18 hasn't been built rather than honestly reflect it.
"""
import logging
from datetime import date as date_type, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from api.database import PostLog, get_db
from api.schemas import LinkedInStatusOut, PostLogOut

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/linkedin", tags=["linkedin"])

# 18.6's rate-limit rule. Belongs in automation/config.py once module 18
# actually exists to read it; hardcoded here to match DEVELOPMENT.md's
# documented defaults in the meantime.
MIN_POST_INTERVAL_MINUTES = 30
DAILY_POST_LIMIT = 3


@router.get("/posts", response_model=list[PostLogOut])
def list_posts(db: Session = Depends(get_db)):
    return db.query(PostLog).order_by(PostLog.date.desc(), PostLog.time.desc()).all()


@router.get("/status", response_model=LinkedInStatusOut)
def linkedin_status(db: Session = Depends(get_db)):
    last_post = db.query(PostLog).filter(PostLog.status == "success").order_by(PostLog.id.desc()).first()
    posts_today = (
        db.query(func.count(PostLog.id))
        .filter(PostLog.date == date_type.today(), PostLog.status == "success")
        .scalar()
        or 0
    )

    last_post_at = None
    minutes_until_next_allowed = 0
    can_post_now = posts_today < DAILY_POST_LIMIT
    if last_post is not None:
        last_post_at = datetime.fromisoformat(f"{last_post.date.isoformat()}T{last_post.time}")
        elapsed_minutes = (datetime.now() - last_post_at).total_seconds() / 60
        if elapsed_minutes < MIN_POST_INTERVAL_MINUTES:
            can_post_now = False
            minutes_until_next_allowed = int(MIN_POST_INTERVAL_MINUTES - elapsed_minutes)

    return LinkedInStatusOut(
        can_post_now=can_post_now,
        last_post_at=last_post_at,
        minutes_until_next_allowed=minutes_until_next_allowed,
        posts_today=posts_today,
        daily_limit=DAILY_POST_LIMIT,
    )


@router.post("/post", status_code=501)
def post_now():
    raise HTTPException(
        status_code=501,
        detail="LinkedIn automation is not built yet — module 18's content_writer.py, "
        "image_finder.py and poster.py are all empty. Nothing exists yet for this route "
        "to call.",
    )
