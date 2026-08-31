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
LOG_DIR = DATA_DIR / "logs"

# Single shared SQLite file at the project root — both the agent process
# and the FastAPI process (api/config.py) point at this same path, since
# locally they run side-by-side on one machine and the API reads what the
# agent tracks (module 5 reads this data; module 24 later syncs it to a
# central Postgres for multi-agent/team deployments).
LOCAL_DB_PATH = PROJECT_ROOT / "workpulse.db"

DATA_DIR.mkdir(parents=True, exist_ok=True)
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

# ── Attendance policy ──
# A check-in (daily_stats.work_start) counts as on-time only inside one of
# these two sanctioned punch-in windows — the normal morning shift, or a
# half-day-start afternoon shift for someone working the second half of the
# day. Outside both windows counts as a late arrival, independent of how
# much of the day was worked afterwards.
MORNING_PUNCH_IN_WINDOW = ("09:15", "09:31")
AFTERNOON_PUNCH_IN_WINDOW = ("13:45", "14:00")
# A check-out (daily_stats.work_end) inside this window is a sanctioned
# early departure after a half day (paired with a MORNING_PUNCH_IN_WINDOW
# check-in) — informational for attendance display, doesn't affect the
# hours-based full/half/absent classification in classify_attendance().
HALF_DAY_PUNCH_OUT_WINDOW = ("13:44", "14:00")
# Fires the late-arrival warning (in-app alert + email) once a user's late
# check-ins for the current calendar month reach this count.
MONTHLY_LATE_WARNING_THRESHOLD = 3

# Check-in (daily_stats.work_start) is recorded the first time the active
# window's process name or title matches one of these keywords (case
# insensitive) — not on the day's first general keyboard/mouse input.
# Matches both a native desktop app (process name, e.g. a "ZohoMail.exe")
# and a browser tab (window title, e.g. "Zoho Mail - Inbox - Google
# Chrome"), so opening Zoho either way counts. Add more keywords here if
# another app should also count as a check-in trigger later.
CHECK_IN_APP_KEYWORDS = ["zoho"]

# ── Calendar / meeting-aware idle detection ──
# Optional — entirely off (no behaviour change) until a real .ics file
# exists at this path. Export your calendar (Outlook: "Save Calendar As" ->
# iCalendar Format; Google Calendar: Settings -> a calendar's "Secret
# address in iCal format"; Zoho Calendar: Export) to this path, or point
# WORKPULSE_CALENDAR_ICS_PATH at wherever your calendar app keeps an
# auto-updating .ics export so re-syncs pick up new meetings automatically.
CALENDAR_ICS_PATH = os.environ.get(
    "WORKPULSE_CALENDAR_ICS_PATH", str(DATA_DIR / "calendar.ics")
)
CALENDAR_SYNC_INTERVAL_SECONDS = 300  # re-read the .ics file every 5 minutes

# ── DAR ──
DAR_GENERATION_TIME = "18:00"

# ── Sync ──
SYNC_INTERVAL_SECONDS = 60
SYNC_BATCH_SIZE = 200

# ── Logging ──
LOG_LEVEL = os.environ.get("WORKPULSE_LOG_LEVEL", "INFO")
LOG_FILE = LOG_DIR / "agent.log"
