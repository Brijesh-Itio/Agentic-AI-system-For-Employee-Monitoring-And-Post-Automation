"""
MODULE 23.4 — workpulse-config.json for the packaged .exe.

The packaged agent has no .env file and no terminal to export environment
variables in, so it reads a plain JSON config file living next to the .exe
instead (or next to the project root when run from source, for local
testing of the same code path). Nothing here is loaded automatically —
`agent/tray_main.py` (the packaged entry point) is the only caller, and it
applies the loaded values as environment variables *before* importing
`agent.main` / `agent.config`, so every other module keeps reading plain
env vars exactly as it already does from source.

Deliberately excludes Gmail credentials, even though the module 23 spec
text mentions them: this config file describes the *desktop tracking
agent* only, which never sends email itself — only the FastAPI backend
(module 8, its own `.env`) does. Writing unused SMTP credentials in
cleartext onto every employee's disk for a feature this process can't even
use would be a real security smell, not spec fidelity, so it's left out.
"""
import json
import logging
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

CONFIG_FILENAME = "workpulse-config.json"


@dataclass
class RuntimeConfig:
    api_url: str = "http://localhost:8000"
    user_id: str = "local"
    user_name: str = ""
    blur_screenshots: bool = False
    screenshot_interval_minutes: int = 5


def config_dir() -> Path:
    """Directory the .exe (or, from source, the project root) lives in."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def config_path() -> Path:
    return config_dir() / CONFIG_FILENAME


def load_runtime_config() -> Optional[RuntimeConfig]:
    path = config_path()
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return RuntimeConfig(**{**asdict(RuntimeConfig()), **data})
    except (json.JSONDecodeError, TypeError, OSError):
        logger.exception("Failed to read %s — treating as first run", path)
        return None


def save_runtime_config(config: RuntimeConfig) -> None:
    path = config_path()
    path.write_text(json.dumps(asdict(config), indent=2), encoding="utf-8")
    logger.info("Saved %s", path)


def apply_to_environment(config: RuntimeConfig) -> None:
    """Sets the env vars agent/config.py already reads — must run before
    agent.config (or anything importing it) is imported for the first time."""
    import os

    os.environ["WORKPULSE_API_URL"] = config.api_url
    os.environ["WORKPULSE_USER_ID"] = config.user_id
    os.environ["WORKPULSE_BLUR_SCREENSHOTS"] = "true" if config.blur_screenshots else "false"
    os.environ["WORKPULSE_SCREENSHOT_INTERVAL_MINUTES"] = str(config.screenshot_interval_minutes)
