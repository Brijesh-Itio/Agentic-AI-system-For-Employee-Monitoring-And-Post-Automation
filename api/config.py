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

    # ── Ollama / AI stack (module 6+) ──
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen3:1.7b"
    OLLAMA_FAST_MODEL: str = "phi3:mini"
    OLLAMA_TIMEOUT_SECONDS: int = 120  # classification calls (fast=True)
    # Full narrative generation (DAR, etc.) genuinely takes longer than
    # classification — observed ~167s for a full DAR on CPU inference.
    OLLAMA_GENERATE_TIMEOUT_SECONDS: int = 300

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
