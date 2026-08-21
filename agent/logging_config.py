"""Shared logging setup for every agent entry point (main.py, and each
tracker module's standalone test run). Rotating file handler keeps the
agent's log directory bounded on a machine that runs for months."""
import logging
from logging.handlers import RotatingFileHandler

from agent.config import LOG_FILE, LOG_LEVEL

_configured = False


def setup_logging() -> None:
    global _configured
    if _configured:
        return

    root = logging.getLogger()
    root.setLevel(LOG_LEVEL)

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = RotatingFileHandler(
        LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(fmt)
    root.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(fmt)
    root.addHandler(console_handler)

    _configured = True
