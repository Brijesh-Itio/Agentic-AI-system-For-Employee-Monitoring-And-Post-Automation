"""
MODULE 2.8 — Calendar tracker (".ics tracker", Layer 1)

Reads a local .ics calendar export on an interval and upserts its timed
events into the shared `calendar_events` table (already scaffolded in
agent/database.py — this module is what actually populates it), so
time_intelligence.py can tell a real scheduled meeting apart from someone
genuinely being away when deciding what counts as idle time.

Entirely optional and off by default: nothing changes until a real file
exists at CALENDAR_ICS_PATH. No calendar API, no OAuth, no credentials —
matching this project's zero-external-API rule, meeting data comes from a
plain .ics export the user places on disk (Outlook/Google Calendar/Zoho
Calendar/any calendar app can produce one), the same free, standard,
zero-cost format DAR import/export already uses for CSV.

Known limitation: this parses each VEVENT's own literal DTSTART/DTEND, not
a full RRULE recurrence expansion — a recurring meeting is only recognised
on the date(s) actually present as individual VEVENT blocks in the file.
Most calendar apps' "export upcoming N days" flows already expand
recurring meetings into individual VEVENTs, which is what this relies on;
re-syncing periodically (CALENDAR_SYNC_INTERVAL_SECONDS) picks up newly
exported occurrences without needing a restart.
"""
import json
import logging
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

import schedule
from icalendar import Calendar

from agent import database
from agent.config import CALENDAR_ICS_PATH, CALENDAR_SYNC_INTERVAL_SECONDS, USER_ID

logger = logging.getLogger(__name__)


def _to_naive_local(value) -> Optional[datetime]:
    """icalendar hands back either a timezone-aware datetime (timed event)
    or a plain date (all-day event, value has no .hour). Every other
    datetime this codebase stores is naive local time (datetime.now()), so
    a timed event's value is converted to local time and stripped of
    tzinfo to compare correctly; an all-day event returns None — it has no
    real time-of-day window, so it can't excuse a specific idle period."""
    if not isinstance(value, datetime):
        return None
    if value.tzinfo is not None:
        value = value.astimezone()
    return value.replace(tzinfo=None)


def _clean_address(value) -> Optional[str]:
    if value is None:
        return None
    text = str(value)
    return text[7:] if text.lower().startswith("mailto:") else text


def _attendees_json(raw) -> str:
    if raw is None:
        items = []
    elif isinstance(raw, list):
        items = [_clean_address(a) for a in raw]
    else:
        items = [_clean_address(raw)]
    return json.dumps([a for a in items if a])


def parse_ics_events(ics_bytes: bytes) -> list:
    """Pure parsing: raw .ics bytes -> a list of dicts ready for
    database.upsert_calendar_event(**event). Skips anything without a
    resolvable timed start (all-day events, malformed VEVENTs)."""
    events = []
    calendar = Calendar.from_ical(ics_bytes)
    for component in calendar.walk("VEVENT"):
        dtstart_prop = component.get("dtstart")
        start_time = _to_naive_local(dtstart_prop.dt) if dtstart_prop else None
        if start_time is None:
            continue

        dtend_prop = component.get("dtend")
        end_time = _to_naive_local(dtend_prop.dt) if dtend_prop else None
        if end_time is None:
            duration_prop = component.get("duration")
            if duration_prop is not None:
                end_time = start_time + duration_prop.dt

        uid = str(component.get("uid")) if component.get("uid") else None
        subject = str(component.get("summary")) if component.get("summary") else "Untitled meeting"
        location = str(component.get("location")) if component.get("location") else None

        events.append({
            "uid": uid,
            "subject": subject,
            "start_time": start_time,
            "end_time": end_time,
            "organizer": _clean_address(component.get("organizer")),
            "attendees_json": _attendees_json(component.get("attendee")),
            "location": location,
        })
    return events


class CalendarTracker:
    """Periodically re-reads CALENDAR_ICS_PATH and upserts its events."""

    def __init__(self, user_id: str = USER_ID, ics_path: str = CALENDAR_ICS_PATH):
        self.user_id = user_id
        self.ics_path = Path(ics_path)

        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

        # Private Scheduler() instance — see time_intelligence.py's
        # TimeIntelligenceEngine for why the bare `schedule` module's
        # shared default scheduler is avoided everywhere in this codebase.
        self._scheduler = schedule.Scheduler()
        self._scheduler.every(CALENDAR_SYNC_INTERVAL_SECONDS).seconds.do(self.sync_now)

    def start(self) -> None:
        database.init_db()
        self.sync_now()  # pick up an existing file immediately, don't wait a full interval
        self._thread = threading.Thread(target=self._run_loop, name="CalendarTrackerThread", daemon=True)
        self._thread.start()
        logger.info(
            "CalendarTracker started (watching %s every %ss)",
            self.ics_path, CALENDAR_SYNC_INTERVAL_SECONDS,
        )

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
        logger.info("CalendarTracker stopped")

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self._scheduler.run_pending()
            except Exception:
                logger.exception("CalendarTracker tick failed; continuing")
            self._stop_event.wait(1.0)

    def sync_now(self) -> int:
        """Re-reads the .ics file and upserts every timed event found.
        Returns the number of events upserted (0 if the file doesn't exist
        yet — the expected, no-op state until the user places one there)."""
        if not self.ics_path.exists():
            logger.debug("No calendar file at %s yet — meeting-aware idle detection stays off", self.ics_path)
            return 0

        try:
            ics_bytes = self.ics_path.read_bytes()
            events = parse_ics_events(ics_bytes)
        except Exception:
            logger.exception("Failed to parse calendar file %s", self.ics_path)
            return 0

        upserted = 0
        for event in events:
            try:
                database.upsert_calendar_event(
                    user_id=self.user_id,
                    uid=event["uid"],
                    subject=event["subject"],
                    start_time=event["start_time"],
                    end_time=event["end_time"],
                    organizer=event["organizer"],
                    attendees_json=event["attendees_json"],
                    location=event["location"],
                    source_file=str(self.ics_path),
                )
                upserted += 1
            except Exception:
                logger.exception("Failed to upsert calendar event %s", event.get("subject"))

        if upserted:
            logger.info("Calendar synced: %d event(s) from %s", upserted, self.ics_path)
        return upserted


if __name__ == "__main__":
    from agent.logging_config import setup_logging

    setup_logging()
    tracker = CalendarTracker()
    count = tracker.sync_now()
    print(f"Synced {count} event(s) from {tracker.ics_path}")
