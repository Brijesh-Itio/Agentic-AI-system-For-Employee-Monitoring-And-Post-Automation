"""
Agent configuration — all desktop agent settings live here.
Never hardcode credentials, thresholds, or paths in business logic files.
"""
import os
from pathlib import Path

# ── Paths ──
AGENT_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = AGENT_ROOT.parent
DATA_DIR = AGENT_ROOT / "data"
SCREENSHOTS_DIR = DATA_DIR / "screenshots"
LOG_DIR = DATA_DIR / "logs"

# Single shared SQLite file at the project root — both the agent process
# and the FastAPI process (api/config.py) point at this same path, since
# locally they run side-by-side on one machine and the API reads what the
# agent tracks (module 5 reads this data; module 24 later syncs it to a
# central Postgres for multi-agent/team deployments).
LOCAL_DB_PATH = PROJECT_ROOT / "workpulse.db"

DATA_DIR.mkdir(parents=True, exist_ok=True)
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

# ── Identity / API ──
API_URL = os.environ.get("WORKPULSE_API_URL", "http://localhost:8000")
USER_ID = os.environ.get("WORKPULSE_USER_ID", "local")

# ── Tracking intervals ──
ACTIVE_WINDOW_POLL_SECONDS = 1
SCREENSHOT_INTERVAL_MINUTES = 5
IDLE_THRESHOLD_SECONDS = 300          # 5 minutes
LONG_BREAK_THRESHOLD_SECONDS = 900    # 15 minutes
SHORT_BREAK_MIN_SECONDS = 300         # 5 minutes floor for a "short" break

# ── Context switching ──
CONTEXT_SWITCH_WINDOW_SECONDS = 300   # 5-minute rolling window
CONTEXT_SWITCH_HIGH_THRESHOLD = 10    # switches per window to flag "high"

# ── Work hours ──
WORK_HOURS_START = "09:00"
WORK_HOURS_END = "19:00"

# ── Screenshot behaviour ──
BLUR_SCREENSHOTS = False
SCREENSHOT_JPEG_QUALITY = 85
THUMBNAIL_SIZE = (320, 180)

# ── DAR ──
DAR_GENERATION_TIME = "18:00"

# ── Sync ──
SYNC_INTERVAL_SECONDS = 60
SYNC_BATCH_SIZE = 200

# ── Logging ──
LOG_LEVEL = os.environ.get("WORKPULSE_LOG_LEVEL", "INFO")
LOG_FILE = LOG_DIR / "agent.log"
