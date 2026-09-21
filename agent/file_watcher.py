"""
Layer 1 — File activity watcher.

Monitors configured shared-drive/project folders (agent.config.FILE_WATCH_ROOTS)
for documents being created, modified, or deleted, and logs each event to
file_activity_logs — real signal for what someone actually worked on that a
window-title-only tracker can't see (e.g. "Excel — Q3_Budget_Final.xlsx"
tells you *an* Excel file was open; a file-system event tells you that file
specifically was saved).

Off by default: with FILE_WATCH_ROOTS empty (the default — nothing
configured), start() logs that fact and does nothing else. No dependency on
this ever running is assumed anywhere else in the codebase.
"""
import logging
import threading
import time
from pathlib import Path
from typing import Optional

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from agent import database
from agent.config import FILE_WATCH_EXTENSIONS, FILE_WATCH_ROOTS, USER_ID

logger = logging.getLogger(__name__)

# Watchdog can fire several modify events for one real save (temp-file
# swap, multiple write() calls); without this, a single Ctrl+S could log
# 3-4 near-identical rows for the same file.
_DEBOUNCE_SECONDS = 5.0


class _FileActivityHandler(FileSystemEventHandler):
    def __init__(self, watched_root: str, user_id: str):
        self.watched_root = watched_root    
        self.user_id = user_id
        self._last_logged: dict[str, float] = {}

    def _should_log(self, path: str) -> bool:
        if Path(path).suffix.lower() not in FILE_WATCH_EXTENSIONS:
            return False
        now = time.monotonic()
        last = self._last_logged.get(path)
        if last is not None and now - last < _DEBOUNCE_SECONDS:
            return False
        self._last_logged[path] = now
        return True

    def _log(self, path: str, event_type: str) -> None:
        if not self._should_log(path):
            return
        try:
            from datetime import datetime

            database.insert_file_activity(
                file_path=path,
                event_type=event_type,
                timestamp=datetime.now(),
                watched_root=self.watched_root,
                user_id=self.user_id,
            )
        except Exception:
            logger.exception("Failed to log file activity for %s", path)

    def on_created(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            self._log(event.src_path, "created")

    def on_modified(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            self._log(event.src_path, "modified")

    def on_deleted(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            self._log(event.src_path, "deleted")


class FileActivityWatcher:
    """Wraps one watchdog Observer scheduled against every configured root."""

    def __init__(self, user_id: str = USER_ID, roots: Optional[list[str]] = None):
        self.user_id = user_id
        self.roots = roots if roots is not None else FILE_WATCH_ROOTS
        self._observer: Optional[Observer] = None
        self._stop_event = threading.Event()

    def start(self) -> None:
        database.init_db()
        if not self.roots:
            logger.info("FileActivityWatcher: no FILE_WATCH_ROOTS configured — staying off")
            return

        self._observer = Observer()
        watched_any = False
        for root in self.roots:
            path = Path(root)
            if not path.is_dir():
                logger.warning("FileActivityWatcher: %s is not a real directory — skipping", root)
                continue
            handler = _FileActivityHandler(watched_root=root, user_id=self.user_id)
            self._observer.schedule(handler, str(path), recursive=True)
            watched_any = True

        if not watched_any:
            logger.warning("FileActivityWatcher: none of the configured roots exist — staying off")
            self._observer = None
            return

        self._observer.start()
        logger.info("FileActivityWatcher started (watching %d root(s))", len(self.roots))

    def stop(self) -> None:
        self._stop_event.set()
        if self._observer is not None:
            self._observer.stop()
            self._observer.join(timeout=5)
        logger.info("FileActivityWatcher stopped")


if __name__ == "__main__":
    from agent.logging_config import setup_logging

    setup_logging()
    logger.info("Module test: starting FileActivityWatcher (Ctrl+C to stop)")
    watcher = FileActivityWatcher()
    watcher.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        watcher.stop()
