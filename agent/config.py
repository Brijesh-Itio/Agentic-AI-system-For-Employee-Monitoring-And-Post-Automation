"""
Agent configuration — all desktop agent settings live here.
Never hardcode credentials, thresholds, or paths in business logic files.
"""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# ── Paths ──
# `Path(__file__)` is only meaningful for a real source checkout — inside a
# PyInstaller-frozen .exe (module 23), every module's __file__ resolves
# into a temp extraction directory that's wiped and recreated on every
# single launch (sys._MEIPASS), not a stable location. Deriving DATA_DIR/
# LOCAL_DB_PATH/LOG_FILE from that in frozen mode meant the packaged agent
# silently wrote its database and logs into a fresh, ephemeral temp folder
# every run — real code, running successfully, just never touching the
# real workpulse.db the API/dashboard actually read from. Frozen builds
# instead anchor everything next to the .exe itself (sys.executable),
# matching where agent/runtime_config.py already puts workpulse-config.json.
if getattr(sys, "frozen", False):
    AGENT_ROOT = Path(sys.executable).resolve().parent
    PROJECT_ROOT = AGENT_ROOT
else:
    AGENT_ROOT = Path(__file__).resolve().parent
    PROJECT_ROOT = AGENT_ROOT.parent

# Loads the same top-level .env the API backend reads (module 5's
# pydantic-settings does this automatically; the agent process is plain
# os.environ, so it needs this explicit call to see WORKPULSE_*/MINIO_*
# values from .env instead of only real OS environment variables).
load_dotenv(PROJECT_ROOT / ".env")
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
# Overridable so module 23's packaged .exe can apply workpulse-config.json
# settings (via env vars it sets before this module is first imported).
BLUR_SCREENSHOTS = os.environ.get("WORKPULSE_BLUR_SCREENSHOTS", "false").lower() == "true"
SCREENSHOT_INTERVAL_MINUTES = int(os.environ.get("WORKPULSE_SCREENSHOT_INTERVAL_MINUTES", "5"))
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
