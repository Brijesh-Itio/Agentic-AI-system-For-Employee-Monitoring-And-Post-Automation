"""
MODULE 2.1 — Idle detector

Low-level idle-time primitive shared by the time intelligence engine.
Uses win32api.GetLastInputInfo() — the canonical Windows API for elapsed
time since the last keyboard or mouse event system-wide. This alone covers
both input sources without the overhead/risk of a global keyboard hook.
"""
import logging
import threading
from datetime import datetime, timedelta
from typing import Callable, List, Optional

import win32api

from agent.config import IDLE_THRESHOLD_SECONDS

logger = logging.getLogger(__name__)

# Callback signatures: (idle_start: datetime) -> None / (idle_start, idle_end) -> None
IdleStartCallback = Callable[[datetime], None]
IdleEndCallback = Callable[[datetime, datetime], None]


def get_idle_seconds() -> float:
    """Seconds elapsed since the last keyboard or mouse input, system-wide."""
    last_input_tick = win32api.GetLastInputInfo()
    current_tick = win32api.GetTickCount()
    idle_ms = current_tick - last_input_tick
    return max(0.0, idle_ms / 1000.0)


class IdleDetector:
    """Polls system idle time and fires callbacks on idle-start / idle-end
    transitions once the configured threshold (default 5 minutes) is crossed.
    """

    def __init__(
        self,
        threshold_seconds: int = IDLE_THRESHOLD_SECONDS,
        poll_interval_seconds: float = 1.0,
    ):
        self.threshold_seconds = threshold_seconds
        self.poll_interval_seconds = poll_interval_seconds

        self._is_idle = False
        self._idle_start: Optional[datetime] = None

        self._on_idle_start: List[IdleStartCallback] = []
        self._on_idle_end: List[IdleEndCallback] = []

        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def on_idle_start(self, callback: IdleStartCallback) -> None:
        self._on_idle_start.append(callback)

    def on_idle_end(self, callback: IdleEndCallback) -> None:
        self._on_idle_end.append(callback)

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run_loop, name="IdleDetectorThread", daemon=True)
        self._thread.start()
        logger.info("IdleDetector started (threshold=%ss)", self.threshold_seconds)

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
        logger.info("IdleDetector stopped")

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self.poll()
            except Exception:
                logger.exception("IdleDetector poll cycle failed; continuing")
            self._stop_event.wait(self.poll_interval_seconds)

    def poll(self) -> float:
        """Check for an idle-state transition. Returns the current idle
        seconds so callers (e.g. TimeIntelligenceEngine) can reuse the
        reading instead of calling the Win32 API a second time."""
        idle_seconds = get_idle_seconds()
        now = datetime.now()

        if not self._is_idle and idle_seconds >= self.threshold_seconds:
            # Idle period actually began `idle_seconds` ago, not now.
            self._idle_start = now - timedelta(seconds=idle_seconds)
            self._is_idle = True
            logger.info("Idle period started at %s", self._idle_start)
            for cb in self._on_idle_start:
                self._safe_call(cb, self._idle_start)

        elif self._is_idle and idle_seconds < self.threshold_seconds:
            idle_end = now
            idle_start = self._idle_start or idle_end
            self._is_idle = False
            self._idle_start = None
            logger.info(
                "Idle period ended at %s (duration=%ds)",
                idle_end,
                int((idle_end - idle_start).total_seconds()),
            )
            for cb in self._on_idle_end:
                self._safe_call(cb, idle_start, idle_end)

        return idle_seconds

    @staticmethod
    def _safe_call(cb, *args) -> None:
        try:
            cb(*args)
        except Exception:
            logger.exception("IdleDetector callback failed")

    @property
    def is_idle(self) -> bool:
        return self._is_idle
