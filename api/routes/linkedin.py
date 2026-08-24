"""MODULE 5 — LinkedIn routes.

GET endpoints are fully functional against the post_log table (schema
owned by agent/database.py). POST /post calls module 18's real pipeline
(content_writer -> image_finder -> poster) via the module 16.3 sub-agent —
requires LINKEDIN_EMAIL/LINKEDIN_PASSWORD in .env to actually succeed;
otherwise it fails with a clear reason rather than a fake success.

The pipeline genuinely takes minutes (real Ollama calls, real local image
generation, a real browser session), so POST /post runs it as a background
job — reusing module 17's jobs table/thread pattern rather than a second
one — and returns immediately with a job id the frontend polls via the
existing GET /api/command/status/{job_id} for live stage progress (text
generating -> image generating -> posting) instead of one opaque wait.
"""
import logging
import threading
import uuid
from datetime import date as date_type, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from api.database import PostLog, get_db
from api.schemas import JobOut, LinkedInStatusOut, PostLogOut
from automation.config import DAILY_POST_LIMIT, MIN_POST_INTERVAL_MINUTES

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/linkedin", tags=["linkedin"])


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


def _run_post_job(job_id: str, topic: str | None) -> None:
    from api.routes.command import _append_log, _update_job
    from ai.sub_agents import linkedin_agent

    _update_job(job_id, status="running", progress=5)

    def on_progress(label: str, pct: int) -> None:
        _update_job(job_id, progress=pct)
        _append_log(job_id, label)

    try:
        result = linkedin_agent.run(topic=topic, on_progress=on_progress)
        if result["status"] != "success":
            raise RuntimeError(result["detail"])
        _update_job(
            job_id, status="completed", progress=100, result=result["detail"],
            completed_at=datetime.now().isoformat(sep=" "),
        )
        _append_log(job_id, result["detail"])
    except Exception as exc:
        logger.exception("LinkedIn post job %s failed", job_id)
        _update_job(job_id, status="failed", result=str(exc), completed_at=datetime.now().isoformat(sep=" "))
        _append_log(job_id, f"Failed: {exc}")


@router.post("/post", response_model=JobOut, status_code=202)
def post_now(topic: str | None = None, db: Session = Depends(get_db)):
    """Kicks off the full module 18 pipeline (write -> generate image ->
    post) as a background job and returns immediately — poll
    GET /api/command/status/{job_id} for live progress. Same jobs table
    module 17 already built; this route just creates a job of a different
    "action" rather than duplicating the job-tracking machinery."""
    from api.routes.command import _create_job, get_job_status

    job_id = str(uuid.uuid4())
    _create_job(job_id, command=f"post to linkedin{f' about {topic}' if topic else ''}", action="post")

    thread = threading.Thread(target=_run_post_job, args=(job_id, topic), daemon=True)
    thread.start()

    return get_job_status(job_id, db)
