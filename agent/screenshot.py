"""
MODULE 3 — Screenshot System

Captures full-screen screenshots on a schedule, overlays a timestamp,
optionally blurs the manager-facing copy while retaining an unblurred
original for audit, generates thumbnails, and logs metadata to SQLite.

Sub-modules implemented (in order):
    3.1 Screen capture
    3.2 Timestamp overlay
    3.3 Blur option
    3.4 Scheduler
    3.5 Screenshot metadata logger
    3.6 Thumbnail generator
    3.7 Manual capture endpoint
"""
import logging
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

import schedule
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from PIL import ImageGrab

from agent import database
from agent.config import (
    BLUR_SCREENSHOTS,
    SCREENSHOT_INTERVAL_MINUTES,
    SCREENSHOT_JPEG_QUALITY,
    SCREENSHOTS_DIR,
    THUMBNAIL_SIZE,
    USER_ID,
)

logger = logging.getLogger(__name__)

_BLUR_RADIUS = 8


# ── 3.1 Screen capture ──

def capture_raw_screenshot() -> Image.Image:
    """Grab the full screen as an RGB PIL image."""
    image = ImageGrab.grab()
    return image.convert("RGB")


def _day_dir(day) -> Path:
    d = SCREENSHOTS_DIR / day.isoformat()
    d.mkdir(parents=True, exist_ok=True)
    return d


def _unique_base_name(day_dir: Path, base_name: str) -> str:
    """The naming convention is second-granularity (HH-MM-SS), so two
    captures within the same second — e.g. rapid manual "Capture Now"
    clicks — would otherwise collide and overwrite each other."""
    candidate = base_name
    suffix = 2
    while (day_dir / f"{candidate}.jpg").exists():
        candidate = f"{base_name}-{suffix}"
        suffix += 1
    return candidate


# ── 3.2 Timestamp overlay ──

def _load_font(size: int = 20) -> ImageFont.FreeTypeFont:
    for candidate in ("arial.ttf", "C:/Windows/Fonts/arial.ttf"):
        try:
            return ImageFont.truetype(candidate, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


def add_timestamp_overlay(image: Image.Image, at: datetime) -> Image.Image:
    """Draw the date/time in the bottom-right corner over a semi-transparent
    black rectangle, white readable text. Mutates and returns `image`."""
    draw = ImageDraw.Draw(image, "RGBA")
    font = _load_font(20)
    text = at.strftime("%Y-%m-%d %H:%M:%S")

    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    padding = 10
    margin = 16
    rect_w = text_w + padding * 2
    rect_h = text_h + padding * 2

    x1 = image.width - margin
    y1 = image.height - margin
    x0 = x1 - rect_w
    y0 = y1 - rect_h

    draw.rectangle([x0, y0, x1, y1], fill=(0, 0, 0, 160))
    draw.text((x0 + padding, y0 + padding - bbox[1]), text, fill=(255, 255, 255, 255), font=font)
    return image


# ── 3.3 Blur option ──

def apply_blur(image: Image.Image, radius: int = _BLUR_RADIUS) -> Image.Image:
    return image.filter(ImageFilter.GaussianBlur(radius=radius))


# ── 3.6 Thumbnail generator ──

def generate_thumbnail(image: Image.Image, size=THUMBNAIL_SIZE) -> Image.Image:
    return image.resize(size, Image.LANCZOS)


# ── 3.7 Manual capture endpoint (also used by the 3.4 scheduler) ──

def capture_now(user_id: str = USER_ID) -> dict:
    """Capture, process, persist and log one screenshot. Safe to call from
    the scheduler thread or on-demand from the FastAPI backend."""
    now = datetime.now()
    day_dir = _day_dir(now.date())
    base_name = _unique_base_name(day_dir, now.strftime("%H-%M-%S"))

    try:
        raw = capture_raw_screenshot()
    except Exception:
        logger.exception("Screen capture failed")
        raise

    original_path: Optional[str] = None
    is_blurred = False

    if BLUR_SCREENSHOTS:
        # Blur the raw frame first so the timestamp text stays sharp,
        # then overlay separately onto the unblurred audit copy.
        original = add_timestamp_overlay(raw.copy(), now)
        original_file = day_dir / f"{base_name}_original.jpg"
        original.save(original_file, "JPEG", quality=SCREENSHOT_JPEG_QUALITY)
        original_path = str(original_file)

        main_image = add_timestamp_overlay(apply_blur(raw), now)
        is_blurred = True
    else:
        main_image = add_timestamp_overlay(raw, now)

    main_file = day_dir / f"{base_name}.jpg"
    main_image.save(main_file, "JPEG", quality=SCREENSHOT_JPEG_QUALITY)

    thumbnail = generate_thumbnail(main_image)
    thumbnail_file = day_dir / f"{base_name}_thumb.jpg"
    thumbnail.save(thumbnail_file, "JPEG", quality=SCREENSHOT_JPEG_QUALITY)

    try:
        screenshot_id = database.insert_screenshot(
            file_path=str(main_file),
            thumbnail_path=str(thumbnail_file),
            timestamp=now,
            is_blurred=is_blurred,
            original_path=original_path,
            user_id=user_id,
        )
    except Exception:
        logger.exception("Failed to log screenshot metadata")
        raise

    logger.info("Screenshot captured: %s (blurred=%s)", main_file, is_blurred)

    # 24.4 — optional MinIO mirror; no-op (and no dependency needed) unless
    # MINIO_* env vars are set. Local file remains the source of truth either way.
    from agent import cloud_storage

    if cloud_storage.is_configured():
        cloud_url = cloud_storage.upload_screenshot(str(main_file), f"{now.date().isoformat()}/{main_file.name}")
        if cloud_url:
            database.set_screenshot_cloud_url(screenshot_id, cloud_url)

    return {
        "id": screenshot_id,
        "file_path": str(main_file),
        "thumbnail_path": str(thumbnail_file),
        "original_path": original_path,
        "timestamp": now.isoformat(),
        "is_blurred": is_blurred,
    }


# ── 3.4 Scheduler ──

class ScreenshotScheduler:
    """Runs screenshot capture on its own thread, independent of the app
    tracker, so neither blocks the other."""

    def __init__(self, interval_minutes: int = SCREENSHOT_INTERVAL_MINUTES, user_id: str = USER_ID):
        self.user_id = user_id
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        # A private Scheduler(), not the bare `schedule` module — see
        # time_intelligence.py's TimeIntelligenceEngine for why: every
        # scheduler class polling the shared global default scheduler from
        # its own thread made this job fire once per polling thread,
        # producing the duplicate screenshots seen live (2-3 near-identical
        # captures within milliseconds of each other, every 5 minutes).
        self._scheduler = schedule.Scheduler()
        self._scheduler.every(interval_minutes).minutes.do(self._safe_capture)

    def _safe_capture(self) -> None:
        try:
            capture_now(self.user_id)
        except Exception:
            logger.exception("Scheduled screenshot capture failed; will retry next interval")

    def start(self) -> None:
        database.init_db()
        self._thread = threading.Thread(target=self._run_loop, name="ScreenshotSchedulerThread", daemon=True)
        self._thread.start()
        logger.info("ScreenshotScheduler started (interval=%smin)", SCREENSHOT_INTERVAL_MINUTES)

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
        logger.info("ScreenshotScheduler stopped")

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self._scheduler.run_pending()
            except Exception:
                logger.exception("Screenshot scheduler tick failed; continuing")
            self._stop_event.wait(1)


if __name__ == "__main__":
    import time
    from agent.logging_config import setup_logging

    setup_logging()
    logger.info("Module 3 manual test: capturing one screenshot now.")
    result = capture_now()
    logger.info("Result: %s", result)
