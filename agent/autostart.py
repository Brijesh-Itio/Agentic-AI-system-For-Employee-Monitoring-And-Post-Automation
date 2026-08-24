"""
MODULE 23.3 — Auto-start on Windows.

Adds/removes a per-user (HKCU) Run key so the packaged .exe launches
automatically at Windows login, without needing admin rights (HKCU, not
HKLM). Only meaningful when actually frozen by PyInstaller — running from
source (`python agent/main.py`) never touches the registry.
"""
import logging
import sys

logger = logging.getLogger(__name__)

RUN_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_VALUE_NAME = "WorkPulseAgent"


def _winreg():
    try:
        import winreg
        return winreg
    except ImportError:
        return None


def is_frozen() -> bool:
    """True only inside a PyInstaller-built .exe, never when run from source."""
    return getattr(sys, "frozen", False)


def enable_autostart(exe_path: str) -> bool:
    winreg = _winreg()
    if winreg is None:
        logger.warning("winreg unavailable (not Windows) — skipping autostart registration")
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, RUN_VALUE_NAME, 0, winreg.REG_SZ, f'"{exe_path}"')
        logger.info("Autostart enabled: %s", exe_path)
        return True
    except OSError:
        logger.exception("Failed to enable autostart")
        return False


def disable_autostart() -> bool:
    winreg = _winreg()
    if winreg is None:
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, RUN_VALUE_NAME)
        logger.info("Autostart disabled")
        return True
    except FileNotFoundError:
        return True  # already not registered
    except OSError:
        logger.exception("Failed to disable autostart")
        return False


def is_autostart_enabled() -> bool:
    winreg = _winreg()
    if winreg is None:
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, winreg.KEY_READ) as key:
            winreg.QueryValueEx(key, RUN_VALUE_NAME)
            return True
    except FileNotFoundError:
        return False
    except OSError:
        logger.exception("Failed to read autostart registry state")
        return False
