"""
MODULE 1 — Desktop App Tracker

Reads the active Windows application every second, detects session
boundaries, persists completed sessions to SQLite, maintains a daily
app-switch counter, and flags high-context-switching windows.

Sub-modules implemented (in order):
    1.1 Active window reader
    1.2 Session detector
    1.3 SQLite writer
    1.4 App switch counter
    1.5 Context switching detector
"""
import logging
import threading
import time
from collections import deque
from datetime import datetime
from typing import Optional, Tuple

import psutil
import win32gui
import win32process

from agent import database
from agent.config import (
    ACTIVE_WINDOW_POLL_SECONDS,
    CONTEXT_SWITCH_HIGH_THRESHOLD,
    CONTEXT_SWITCH_WINDOW_SECONDS,
    USER_ID,
)

logger = logging.getLogger(__name__)


# ── 1.1 Active window reader ──

def get_active_window_info() -> Optional[Tuple[str, str]]:
    """Return (process_name, window_title) for the current foreground window.

    Returns None if no window is focused or the process can't be resolved
    (e.g. a privileged system window) — a common, expected condition, so we
    log at DEBUG rather than ERROR.
    """
    try:
        hwnd = win32gui.GetForegroundWindow()
        if not hwnd:
            return None

        window_title = win32gui.GetWindowText(hwnd) or ""

        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        if not pid:
            return None

        process = psutil.Process(pid)
        app_name = process.name()
        return app_name, window_title
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        logger.debug("Active window process could not be resolved", exc_info=True)
        return None
    except Exception:
        logger.exception("Unexpected error reading active window")
        return None


class AppTracker:
    """Polls the foreground window and tracks app sessions in real time."""

    def __init__(self, user_id: str = USER_ID):
        self.user_id = user_id
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

        # 1.2 session state
        self._current_app: Optional[str] = None
        self._current_title: Optional[str] = None
        self._session_start: Optional[datetime] = None

        # 1.5 context-switching state
        self._switch_timestamps: deque = deque()
        self._window_currently_flagged = False

        # Liveness heartbeat — independent of session boundaries, see
        # agent_heartbeat's schema comment in agent/database.py.
        self._last_heartbeat_at: Optional[float] = None

    # ── lifecycle ──

    def start(self) -> None:
        database.init_db()
        self._thread = threading.Thread(
            target=self._run_loop, name="AppTrackerThread", daemon=True
        )
        self._thread.start()
        logger.info("AppTracker started (poll interval=%ss)", ACTIVE_WINDOW_POLL_SECONDS)

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
        self._close_current_session()
        logger.info("AppTracker stopped")

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self.poll()
            except Exception:
                logger.exception("AppTracker poll cycle failed; continuing")
            self._stop_event.wait(ACTIVE_WINDOW_POLL_SECONDS)

    # ── 1.2 session detector ──

    _HEARTBEAT_INTERVAL_SECONDS = 15

    def _maybe_touch_heartbeat(self) -> None:
        now = time.monotonic()
        if self._last_heartbeat_at is not None and now - self._last_heartbeat_at < self._HEARTBEAT_INTERVAL_SECONDS:
            return
        self._last_heartbeat_at = now
        try:
            database.touch_heartbeat(self.user_id)
        except Exception:
            logger.exception("Failed to update agent heartbeat")

    def poll(self) -> None:
        self._maybe_touch_heartbeat()

        info = get_active_window_info()
        if info is None:
            return

        app_name, window_title = info

        if self._current_app is None:
            self._open_session(app_name, window_title)
            return

        if app_name != self._current_app:
            self._close_current_session(is_switch=True)
            self._open_session(app_name, window_title)
        else:
            # Same app: keep the most recent window title for this session.
            self._current_title = window_title

    def _open_session(self, app_name: str, window_title: str) -> None:
        self._current_app = app_name
        self._current_title = window_title
        self._session_start = datetime.now()
        logger.debug("Session opened: %s", app_name)

    def _close_current_session(self, is_switch: bool = False) -> None:
        if self._current_app is None or self._session_start is None:
            return

        end_time = datetime.now()
        try:
            # 1.3 SQLite writer
            database.insert_activity_session(
                app_name=self._current_app,
                window_title=self._current_title,
                start_time=self._session_start,
                end_time=end_time,
                user_id=self.user_id,
            )
            logger.info(
                "Session closed: %s (%ds)",
                self._current_app,
                int((end_time - self._session_start).total_seconds()),
            )
        except Exception:
            logger.exception("Failed to persist activity session for %s", self._current_app)

        if is_switch:
            self._register_switch(end_time)

        self._current_app = None
        self._current_title = None
        self._session_start = None

    # ── 1.4 app switch counter + 1.5 context switching detector ──

    def _register_switch(self, at: datetime) -> None:
        try:
            database.increment_app_switch_count(at.date(), self.user_id)
        except Exception:
            logger.exception("Failed to increment daily app switch counter")

        self._switch_timestamps.append(at)
        self._evaluate_context_switching(at)

    def _evaluate_context_switching(self, now: datetime) -> None:
        window_start = now.timestamp() - CONTEXT_SWITCH_WINDOW_SECONDS
        while self._switch_timestamps and self._switch_timestamps[0].timestamp() < window_start:
            self._switch_timestamps.popleft()

        switch_count = len(self._switch_timestamps)
        is_high = switch_count > CONTEXT_SWITCH_HIGH_THRESHOLD

        if is_high and not self._window_currently_flagged:
            try:
                database.insert_context_switch_flag(
                    day=now.date(),
                    window_start=datetime.fromtimestamp(window_start),
                    window_end=now,
                    switch_count=switch_count,
                    is_high_switching=True,
                    user_id=self.user_id,
                )
                logger.warning(
                    "High context switching flagged: %d switches in %ds window",
                    switch_count,
                    CONTEXT_SWITCH_WINDOW_SECONDS,
                )
            except Exception:
                logger.exception("Failed to persist context switch flag")
            self._window_currently_flagged = True
        elif not is_high:
            self._window_currently_flagged = False


if __name__ == "__main__":
    from agent.logging_config import setup_logging

    setup_logging()
    tracker = AppTracker()
    tracker.start()
    logger.info("Module 1 manual test running. Switch between apps, Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        tracker.stop()
