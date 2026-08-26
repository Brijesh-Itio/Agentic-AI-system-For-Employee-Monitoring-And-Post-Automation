"""MODULE 5.3 — Screenshots routes.

Scoped to the logged-in user — an employee only ever sees their own
screenshots; viewing/serving someone else's requires oversight (manager/
admin), same rule as team.py's member activity endpoint.
"""
import logging
from datetime import date as date_type
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from api.auth import get_current_user
from api.database import Screenshot, User, get_db
from api.schemas import CaptureScreenshotOut, ScreenshotOut

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/screenshots", tags=["screenshots"])


def _to_out(row: Screenshot) -> ScreenshotOut:
    return ScreenshotOut(
        id=row.id,
        file_path=row.file_path,
        thumbnail_path=row.thumbnail_path,
        original_path=row.original_path,
        timestamp=row.timestamp,
        date=row.date,
        is_blurred=bool(row.is_blurred),
        cloud_url=row.cloud_url,
    )


def _require_access(row_user_id: str, current_user: User) -> None:
    if row_user_id != current_user.id and current_user.role not in ("manager", "admin"):
        raise HTTPException(status_code=403, detail="Not authorised to view this user's screenshots")


@router.get("/today", response_model=list[ScreenshotOut])
def get_today_screenshots(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    rows = (
        db.query(Screenshot)
        .filter(Screenshot.user_id == current_user.id, Screenshot.date == date_type.today())
        .order_by(Screenshot.timestamp.asc())
        .all()
    )
    return [_to_out(r) for r in rows]


@router.get("/date/{target_date}", response_model=list[ScreenshotOut])
def get_screenshots_by_date(
    target_date: date_type, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    rows = (
        db.query(Screenshot)
        .filter(Screenshot.user_id == current_user.id, Screenshot.date == target_date)
        .order_by(Screenshot.timestamp.asc())
        .all()
    )
    return [_to_out(r) for r in rows]


@router.get("/member/{user_id}/today", response_model=list[ScreenshotOut])
def get_member_today_screenshots(
    user_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    _require_access(user_id, current_user)
    rows = (
        db.query(Screenshot)
        .filter(Screenshot.user_id == user_id, Screenshot.date == date_type.today())
        .order_by(Screenshot.timestamp.asc())
        .all()
    )
    return [_to_out(r) for r in rows]


@router.get("/member/{user_id}/date/{target_date}", response_model=list[ScreenshotOut])
def get_member_screenshots_by_date(
    user_id: str,
    target_date: date_type,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_access(user_id, current_user)
    rows = (
        db.query(Screenshot)
        .filter(Screenshot.user_id == user_id, Screenshot.date == target_date)
        .order_by(Screenshot.timestamp.asc())
        .all()
    )
    return [_to_out(r) for r in rows]


@router.get("/{screenshot_id}", response_model=ScreenshotOut)
def get_screenshot(
    screenshot_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    row = db.query(Screenshot).filter(Screenshot.id == screenshot_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Screenshot not found")
    _require_access(row.user_id, current_user)
    return _to_out(row)


@router.post("/capture", response_model=CaptureScreenshotOut)
def capture_screenshot_now(current_user: User = Depends(get_current_user)):
    from agent.screenshot import capture_now

    try:
        result = capture_now(current_user.id)
    except Exception:
        logger.exception("Manual screenshot capture failed")
        raise HTTPException(status_code=500, detail="Screenshot capture failed")

    return CaptureScreenshotOut(
        id=result["id"],
        file_path=result["file_path"],
        thumbnail_path=result["thumbnail_path"],
        original_path=result["original_path"],
        timestamp=result["timestamp"],
        is_blurred=result["is_blurred"],
    )


@router.get("/file/{filename}")
def get_screenshot_file(
    filename: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """Serve a screenshot image by filename. Resolved via the DB rather than
    joining user input onto the filesystem path directly, to prevent path
    traversal (`..`, absolute paths, etc.) from ever reaching disk I/O."""
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    row = (
        db.query(Screenshot)
        .filter(
            (Screenshot.file_path.like(f"%{filename}"))
            | (Screenshot.thumbnail_path.like(f"%{filename}"))
            | (Screenshot.original_path.like(f"%{filename}"))
        )
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Screenshot file not found")
    _require_access(row.user_id, current_user)

    # original_path included so module 12.4's blur toggle can fetch the
    # unblurred audit copy, not just the blurred/manager-facing version.
    candidate_paths = [row.file_path, row.thumbnail_path, row.original_path]
    for candidate in candidate_paths:
        if candidate and Path(candidate).name == filename and Path(candidate).exists():
            return FileResponse(candidate)

    raise HTTPException(status_code=404, detail="Screenshot file not found on disk")
