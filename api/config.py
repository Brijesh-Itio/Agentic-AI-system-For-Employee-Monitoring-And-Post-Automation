"""
API configuration — all FastAPI backend settings and credentials live here.
Never hardcode credentials in route or business-logic files.
"""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

API_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = API_ROOT.parent

# Same physical SQLite file the desktop agent writes to (agent/config.py).
DATABASE_PATH = PROJECT_ROOT / "workpulse.db"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(PROJECT_ROOT / ".env"), extra="ignore")

    # ── Database ──
    DATABASE_URL: str = f"sqlite:///{DATABASE_PATH}"

    # ── Security ──
    SECRET_KEY: str = "change-this-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    # ── CORS ──
    CORS_ORIGINS: list[str] = ["http://localhost:5173"]

    # ── Gmail (module 8) ──
    GMAIL_ADDRESS: str = ""
    GMAIL_APP_PASSWORD: str = ""
    # Where DAR/alert emails go. Defaults to GMAIL_ADDRESS (send-to-self),
    # matching module 8's own test ("send a test email to yourself").
    REPORT_RECIPIENT_EMAIL: str = ""

    # ── LinkedIn (module 18) ──
    # Only used for the *first* login, which saves a session cookie file
    # (LINKEDIN_COOKIES_PATH in automation/config.py) — every run after
    # that reuses the saved session instead of logging in again.
    LINKEDIN_EMAIL: str = ""
    LINKEDIN_PASSWORD: str = ""

    # ── Pexels image search (module 18.3, fallback only) ──
    # Free API key, not Playwright scraping: Pexels/Pixabay both sit behind
    # Cloudflare bot-detection that blocks headless browsers outright (a
    # "Verify you are human" wall, not a missing selector) — verified
    # empirically, not assumed. Kept as a stock-photo fallback for when
    # FastSD CPU (below) is unavailable or produces nothing usable.
    PEXELS_API_KEY: str = ""

    # ── FastSD CPU local image generation (module 18.3, primary) ──
    # A second local-inference server, same pattern as Ollama: runs on this
    # machine, not a paid/third-party API, matching the zero-API-cost goal.
    # Not part of the Railway/cloud deployment (that stays lightweight) —
    # like Ollama, it only ever needs to run wherever automation actually
    # executes. Default port 8100 (not 8000) to avoid colliding with this
    # backend's own uvicorn server.
    FASTSD_API_URL: str = "http://127.0.0.1:8100"
    FASTSD_TIMEOUT_SECONDS: int = 600

    # ── Ollama / AI stack (module 6+) ──
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen3:1.7b"
    OLLAMA_FAST_MODEL: str = "phi3:mini"
    OLLAMA_TIMEOUT_SECONDS: int = 120  # classification calls (fast=True)
    # Full narrative generation (DAR, etc.) genuinely takes longer than
    # classification — observed ~167s for a full DAR on CPU inference, but
    # AI-drafted task-log entries measured at ~275s under real load, only
    # ~25s under the old 300s budget — raised for real margin under load.
    OLLAMA_GENERATE_TIMEOUT_SECONDS: int = 420

    # ── ChromaDB (module 6+) ──
    CHROMADB_PATH: str = str(PROJECT_ROOT / "chromadb")

    # ── Server ──
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    # ── Identity ──
    DEFAULT_USER_ID: str = "local"

    # Heuristic window for the /api/status "agent running" check: the agent
    # closes at least one activity session roughly every few seconds while
    # tracking, so no fresh row within this window means it's likely down.
    AGENT_HEARTBEAT_WINDOW_SECONDS: int = 30


settings = Settings()
