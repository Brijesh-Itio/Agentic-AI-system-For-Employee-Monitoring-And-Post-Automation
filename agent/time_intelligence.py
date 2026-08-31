"""
MODULE 2 — Time Intelligence Engine

Extracts meaningful time metrics from raw activity data: idle detection
(delegated to idle_detector.py), break classification, work-day boundaries,
focus scores, longest focus session, and weekly trends.

Sub-modules implemented (in order):
    2.1 Idle detector           -> agent/idle_detector.py
    2.2 Work day detector
    2.3 Break classifier
    2.4 Focus score calculator
    2.5 Productive hours counter
    2.6 Longest focus session detector
    2.7 Weekly trends calculator
    2.8 Meeting-aware idle exclusion -> calendar_events, via agent/calendar_tracker.py
"""
import logging
import threading
import time
from datetime import date as date_cls, datetime, timedelta
from typing import Optional

import schedule

from agent import database
from agent.browser_tracker import BROWSER_PROCESSES
from agent.config import (
    DAR_GENERATION_TIME,
    LONG_BREAK_THRESHOLD_SECONDS,
    SHORT_BREAK_MIN_SECONDS,
    USER_ID,
)
from agent.idle_detector import IdleDetector

logger = logging.getLogger(__name__)

# Weekly trends are calculated once a day, at the same evening checkpoint
# the DAR is generated (module 7), since both summarise "the day that just
# finished" and only Monday's run actually needs the full week rollup.
WEEKLY_TRENDS_TIME = DAR_GENERATION_TIME

GAP_TOLERANCE_SECONDS = 2  # accounts for sub-second rounding between adjacent rows


def subtract_meeting_overlap(idle_start: datetime, idle_end: datetime, meetings: list) -> list:
    """Pure interval-subtraction: idle_start..idle_end minus whatever
    portion of it overlaps any calendar_events row in `meetings` (each with
    string start_time/end_time columns, as returned by
    database.get_calendar_events_overlapping). Returns the list of
    remaining (start, end) datetime tuples that are genuinely idle — not
    explained by a scheduled meeting — in chronological order.

    A meeting covering the whole idle window returns []. No meetings
    returns [(idle_start, idle_end)] unchanged. A meeting covering the
    middle of the window returns two remaining pieces, one on each side.
    """
    if not meetings:
        return [(idle_start, idle_end)]

    intervals = sorted(
        (
            max(idle_start, datetime.fromisoformat(m["start_time"])),
            min(idle_end, datetime.fromisoformat(m["end_time"])),
        )
        for m in meetings
    )

    # Merge overlapping/adjacent meeting intervals first so back-to-back or
    # double-booked meetings don't get subtracted as separate gaps.
    merged: list = []
    for start, end in intervals:
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))

    remaining = []
    cursor = idle_start
    for meeting_start, meeting_end in merged:
        if meeting_start > cursor:
            remaining.append((cursor, meeting_start))
        cursor = max(cursor, meeting_end)
    if cursor < idle_end:
        remaining.append((cursor, idle_end))

    return [(s, e) for s, e in remaining if e > s]


def compute_focus_runs(day: date_cls, user_id: str = USER_ID) -> list:
    """Walks a day's activity_logs (with website-aware category resolution
    for browser rows) and returns every contiguous productive run — not
    just the longest. Shared by module 2.6 (longest focus session) and
    module 11.5 (focus sessions summary), so "what counts as one continuous
    focus run" is defined in exactly one place.

    Each run dict: {start, end, duration_seconds, interrupted_by_distraction}
    — the last flag is True when the row that ended the run (not a time
    gap) was itself a distraction, useful for "sessions interrupted by
    distraction" reporting.
    """
    conn = database.get_connection()
    rows = conn.execute(
        """
        SELECT app_name, category, start_time, end_time, duration_seconds
        FROM activity_logs
        WHERE user_id = ? AND date = ?
        ORDER BY start_time ASC
        """,
        (user_id, day.isoformat()),
    ).fetchall()

    website_rows = conn.execute(
        """
        SELECT category, start_time, end_time
        FROM websites WHERE user_id = ? AND date = ?
        """,
        (user_id, day.isoformat()),
    ).fetchall()

    def effective_category(row) -> str:
        if row["app_name"] not in BROWSER_PROCESSES:
            return row["category"]
        # Same website-aware reasoning as the hourly scorer: a browser
        # row's own category is too coarse. Resolve it from whichever
        # website(s) overlapped that time window instead.
        row_start, row_end = row["start_time"], row["end_time"]
        overlapping = [
            w for w in website_rows
            if w["start_time"] < row_end and (w["end_time"] or row_end) > row_start
        ]
        if not overlapping:
            return "uncategorised"
        if any(w["category"] == "distraction" for w in overlapping):
            return "distraction"
        if all(w["category"] == "productive" for w in overlapping):
            return "productive"
        return "neutral"

    runs = []
    run_start = run_end = None
    run_end_dt: Optional[datetime] = None
    run_duration = 0

    def flush(interrupted: bool) -> None:
        if run_start is not None and run_duration > 0:
            runs.append({
                "start": datetime.fromisoformat(run_start),
                "end": datetime.fromisoformat(run_end),
                "duration_seconds": run_duration,
                "interrupted_by_distraction": interrupted,
            })

    for row in rows:
        category = effective_category(row)
        productive_now = category == "productive"
        row_start_dt = datetime.fromisoformat(row["start_time"])
        has_gap = run_end_dt is not None and (row_start_dt - run_end_dt).total_seconds() > GAP_TOLERANCE_SECONDS

        if productive_now and run_start is not None and not has_gap:
            run_end = row["end_time"]
            run_end_dt = datetime.fromisoformat(row["end_time"])
            run_duration += row["duration_seconds"] or 0
        else:
            flush(interrupted=(not productive_now and category == "distraction"))
            if productive_now:
                run_start = row["start_time"]
                run_end = row["end_time"]
                run_end_dt = datetime.fromisoformat(row["end_time"])
                run_duration = row["duration_seconds"] or 0
            else:
                run_start = run_end = run_end_dt = None
                run_duration = 0

    flush(interrupted=False)  # trailing run, if any, wasn't interrupted — the day just ended
    return runs


class TimeIntelligenceEngine:
    def __init__(self, user_id: str = USER_ID, poll_interval_seconds: float = 1.0):
        self.user_id = user_id
        self.poll_interval_seconds = poll_interval_seconds

        self.idle_detector = IdleDetector(poll_interval_seconds=poll_interval_seconds)
        self.idle_detector.on_idle_start(self._on_idle_start)
        self.idle_detector.on_idle_end(self._on_idle_end)

        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._last_processed_hour: Optional[datetime] = None  # (date, hour) tuple key
        self._last_work_end_touch_at: Optional[float] = None  # monotonic, for _maybe_touch_work_end

        # A private Scheduler(), not the bare `schedule` module: every
        # scheduler class in this codebase runs its own polling thread, and
        # `schedule.every()`/`schedule.run_pending()` with no instance both
        # operate on one shared global default scheduler — verified live
        # that this made every due job (e.g. the 5-minute screenshot
        # capture) fire once per thread that happened to poll it, producing
        # near-simultaneous duplicate screenshots/rescores/posts. A private
        # instance means this thread only ever sees and runs its own jobs.
        self._scheduler = schedule.Scheduler()
        self._scheduler.every().day.at(WEEKLY_TRENDS_TIME).do(self.calculate_weekly_trends)

    # ── lifecycle ──

    def start(self) -> None:
        database.init_db()
        self._thread = threading.Thread(
            target=self._run_loop, name="TimeIntelligenceThread", daemon=True
        )
        self._thread.start()
        logger.info("TimeIntelligenceEngine started")

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
        logger.info("TimeIntelligenceEngine stopped")

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self._tick()
            except Exception:
                logger.exception("TimeIntelligenceEngine tick failed; continuing")
            self._stop_event.wait(self.poll_interval_seconds)

    _WORK_END_TOUCH_INTERVAL_SECONDS = 30

    def _tick(self) -> None:
        idle_seconds = self.idle_detector.poll()
        now = datetime.now()

        # 2.2 work day detector — work_end keeps advancing on any fresh
        # input. work_start (check-in) is no longer set here: it's now
        # recorded by app_tracker.py's check-in trigger, the first time the
        # active window matches CHECK_IN_APP_KEYWORDS (e.g. opening Zoho),
        # not on the day's first general keyboard/mouse input.
        if idle_seconds < self.poll_interval_seconds:
            self._maybe_touch_work_end(now)

        self._maybe_roll_hourly_score(now)
        self._scheduler.run_pending()

    def _maybe_touch_work_end(self, now: datetime) -> None:
        """Keeps work_end advancing as a live "last seen active" watermark
        while the user is active, throttled to once per 30s (matching the
        heartbeat pattern in app_tracker.py) rather than writing every poll.

        Without this, work_end was only ever set from _on_idle_end when a
        break >=15min ended (LONG_BREAK_THRESHOLD_SECONDS), stamped at
        idle_start — the moment the break began. That value then stayed
        frozen until the *next* qualifying break, so a lunch break (e.g.
        1:45-2:15) made the dashboard show "work ended 1:45 PM" for the
        entire rest of the afternoon even while actively working, wrongly
        reading as a checkout. Advancing work_end continuously while active
        means it naturally resumes climbing the moment work picks back up.
        """
        monotonic_now = time.monotonic()
        if (
            self._last_work_end_touch_at is not None
            and monotonic_now - self._last_work_end_touch_at < self._WORK_END_TOUCH_INTERVAL_SECONDS
        ):
            return
        self._last_work_end_touch_at = monotonic_now
        try:
            database.set_work_end(now.date(), now, self.user_id)
        except Exception:
            logger.exception("Failed to persist live work_end")

    # ── 2.2 work day detector + 2.3 break classifier (idle callbacks) ──

    def _on_idle_start(self, idle_start: datetime) -> None:
        logger.debug("Idle started at %s", idle_start)

    def _on_idle_end(self, idle_start: datetime, idle_end: datetime) -> None:
        duration_seconds = int((idle_end - idle_start).total_seconds())

        # Meeting-aware idle detection: check the calendar first. Whatever
        # portion of this idle window overlaps a scheduled meeting is a
        # person holding their laptop through a call, not actually away —
        # it's excluded entirely (no idle_seconds, no break row). Only the
        # leftover, non-meeting portion(s) of the window are treated as a
        # real idle period, exactly like before this feature existed.
        try:
            meetings = database.get_calendar_events_overlapping(idle_start, idle_end, self.user_id)
        except Exception:
            logger.exception("Failed to check calendar for meeting overlap; treating idle period as normal")
            meetings = []

        segments = subtract_meeting_overlap(idle_start, idle_end, meetings)
        excused_seconds = duration_seconds - sum(int((e - s).total_seconds()) for s, e in segments)
        if excused_seconds > 0:
            subjects = ", ".join(sorted({m["subject"] for m in meetings})) or "scheduled meeting"
            logger.info(
                "Excused %ds of idle time (%s) — %s to %s",
                excused_seconds, subjects, idle_start, idle_end,
            )

        for seg_start, seg_end in segments:
            self._record_idle_segment(seg_start, seg_end)

    def _record_idle_segment(self, idle_start: datetime, idle_end: datetime) -> None:
        """The original (pre-calendar) idle-end handling, applied to one
        genuinely-idle segment — a full idle period when there's no meeting
        overlap at all, or a leftover slice before/after one when there is."""
        duration_seconds = int((idle_end - idle_start).total_seconds())
        if duration_seconds <= 0:
            return

        try:
            database.insert_idle_period(idle_start, idle_end, self.user_id)
            database.update_daily_idle_seconds(idle_start.date(), duration_seconds, self.user_id)
        except Exception:
            logger.exception("Failed to persist idle period")

        # 2.3 break classifier — the idle detector only fires once the
        # threshold (5min) is crossed, so every detected idle period already
        # qualifies as at least a "short" break; true micro-breaks (<5min)
        # never reach here by construction. A meeting-trimmed leftover
        # segment can be shorter than 5min, and that's fine — it's still
        # genuinely idle time, just a smaller amount of it.
        break_type = "long" if duration_seconds >= LONG_BREAK_THRESHOLD_SECONDS else "short"
        try:
            database.insert_break(idle_start, idle_end, break_type, self.user_id)
            logger.info("Break recorded: %s (%ds)", break_type, duration_seconds)
        except Exception:
            logger.exception("Failed to persist break")

        # 2.2 work day detector — work_end is the last input *before* a
        # qualifying long idle (>=15min), i.e. idle_start.
        if duration_seconds >= LONG_BREAK_THRESHOLD_SECONDS:
            try:
                database.set_work_end(idle_start.date(), idle_start, self.user_id)
            except Exception:
                logger.exception("Failed to persist work_end")

    # ── 2.4 focus score calculator ──

    def _maybe_roll_hourly_score(self, now: datetime) -> None:
        current_hour_key = (now.date(), now.hour)
        if self._last_processed_hour is None:
            self._last_processed_hour = current_hour_key
            return
        if current_hour_key != self._last_processed_hour:
            finished_date, finished_hour = self._last_processed_hour
            self.calculate_hourly_focus_score(finished_date, finished_hour)
            self.calculate_daily_focus_score(finished_date)
            self.detect_longest_focus_session(finished_date)
            self._last_processed_hour = current_hour_key

    def calculate_hourly_focus_score(self, day: date_cls, hour: int) -> Optional[float]:
        conn = database.get_connection()
        hour_start = datetime.combine(day, datetime.min.time()) + timedelta(hours=hour)
        hour_end = hour_start + timedelta(hours=1)

        rows = conn.execute(
            """
            SELECT app_name, category, duration_seconds FROM activity_logs
            WHERE user_id = ? AND end_time >= ? AND end_time < ?
            """,
            (self.user_id, hour_start.isoformat(sep=" "), hour_end.isoformat(sep=" ")),
        ).fetchall()

        # Ground truth for "how long was the user active" is activity_logs.
        # But for time spent inside a browser, its own category (typically
        # 'neutral'/'mixed' — a browser process alone says nothing about
        # productivity) is too coarse; the websites table's per-domain
        # category is the real signal, so browser rows are excluded from
        # the productive tally here and website rows are used instead.
        total_seconds = sum(r["duration_seconds"] or 0 for r in rows)
        productive_seconds = sum(
            r["duration_seconds"] or 0
            for r in rows
            if r["category"] == "productive" and r["app_name"] not in BROWSER_PROCESSES
        )
        switch_count = len(rows)

        website_rows = conn.execute(
            """
            SELECT category, duration_seconds FROM websites
            WHERE user_id = ? AND end_time >= ? AND end_time < ?
            """,
            (self.user_id, hour_start.isoformat(sep=" "), hour_end.isoformat(sep=" ")),
        ).fetchall()
        productive_seconds += sum(
            r["duration_seconds"] or 0 for r in website_rows if r["category"] == "productive"
        )

        focus_score = (productive_seconds / total_seconds * 100) if total_seconds > 0 else None

        try:
            database.upsert_hourly_score(
                day, hour, focus_score, productive_seconds, total_seconds, switch_count, self.user_id
            )
        except Exception:
            logger.exception("Failed to persist hourly focus score")

        return focus_score

    def calculate_daily_focus_score(self, day: date_cls) -> Optional[float]:
        conn = database.get_connection()
        row = conn.execute(
            """
            SELECT COALESCE(SUM(productive_seconds), 0) AS productive,
                   COALESCE(SUM(total_seconds), 0) AS total
            FROM hourly_scores WHERE user_id = ? AND date = ?
            """,
            (self.user_id, day.isoformat()),
        ).fetchone()

        productive_seconds = row["productive"]
        total_seconds = row["total"]
        focus_score = (productive_seconds / total_seconds * 100) if total_seconds > 0 else None

        try:
            # 2.5 productive hours counter — same underlying totals, persisted together.
            database.set_daily_focus_score(day, focus_score, productive_seconds, total_seconds, self.user_id)
        except Exception:
            logger.exception("Failed to persist daily focus score")

        return focus_score

    # ── 2.5 productive hours counter ──

    @staticmethod
    def format_hours_minutes(seconds: int) -> str:
        hours, remainder = divmod(max(0, seconds), 3600)
        minutes = remainder // 60
        return f"{hours}h {minutes}m"

    # ── 2.6 longest focus session detector ──

    def detect_longest_focus_session(self, day: date_cls) -> None:
        runs = compute_focus_runs(day, self.user_id)
        if not runs:
            return
        best = max(runs, key=lambda r: r["duration_seconds"])

        if best["duration_seconds"] > 0:
            try:
                database.set_longest_focus_session(
                    day,
                    best["start"],
                    best["end"],
                    best["duration_seconds"],
                    self.user_id,
                )
            except Exception:
                logger.exception("Failed to persist longest focus session")

    # ── 2.7 weekly trends calculator ──

    def calculate_weekly_trends(self) -> None:
        conn = database.get_connection()
        today = date_cls.today()
        week_start = today - timedelta(days=6)

        rows = conn.execute(
            """
            SELECT date, focus_score, total_active_seconds, productive_seconds
            FROM daily_stats
            WHERE user_id = ? AND date >= ? AND date <= ?
            ORDER BY date ASC
            """,
            (self.user_id, week_start.isoformat(), today.isoformat()),
        ).fetchall()

        scored_days = [r for r in rows if r["focus_score"] is not None]
        if not scored_days:
            logger.info("No scored days in the past 7 days; skipping weekly trend calculation")
            return

        avg_focus_score = sum(r["focus_score"] for r in scored_days) / len(scored_days)
        avg_total_hours = sum((r["total_active_seconds"] or 0) for r in rows) / (3600 * len(rows))
        avg_productive_hours = sum((r["productive_seconds"] or 0) for r in rows) / (3600 * len(rows))

        if len(scored_days) >= 2:
            first_half = scored_days[: len(scored_days) // 2]
            second_half = scored_days[len(scored_days) // 2:]
            first_avg = sum(r["focus_score"] for r in first_half) / len(first_half)
            second_avg = sum(r["focus_score"] for r in second_half) / len(second_half)
            if second_avg > first_avg + 1:
                trend_direction = "improving"
            elif second_avg < first_avg - 1:
                trend_direction = "declining"
            else:
                trend_direction = "stable"
        else:
            trend_direction = "stable"

        try:
            database.upsert_weekly_trend(
                week_start, avg_focus_score, avg_total_hours, avg_productive_hours,
                trend_direction, self.user_id,
            )
            logger.info(
                "Weekly trend updated: avg_focus=%.1f trend=%s", avg_focus_score, trend_direction
            )
        except Exception:
            logger.exception("Failed to persist weekly trend")


if __name__ == "__main__":
    import time
    from agent.logging_config import setup_logging

    setup_logging()
    engine = TimeIntelligenceEngine()
    engine.start()
    logger.info("Module 2 manual test running. Go idle for 5+ minutes to test breaks. Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        engine.stop()
