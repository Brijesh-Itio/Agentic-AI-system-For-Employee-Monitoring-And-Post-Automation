"""
Attendance policy — pure date/threshold logic, no I/O.

Two independent questions per calendar day:
1. Is this a working day at all? (`week_off_reason`) — every Sunday, plus
   the 1st and 3rd Saturday of each month, are permanent paid week-offs,
   per standing policy. Every other day is a working day.
2. For a working day, how much of it did the already-tracked
   `daily_stats.total_active_seconds` cover? (`classify_attendance`) —
   reuses real tracked data (the same numbers the Dashboard/DAR already
   show), never a separate manual entry, so attendance is automatically
   derived rather than something anyone has to fill in.
"""
from datetime import date as date_cls, datetime, time as time_cls
from typing import Optional

from agent.config import (
    AFTERNOON_PUNCH_IN_WINDOW,
    HALF_DAY_PUNCH_OUT_WINDOW,
    MORNING_PUNCH_IN_WINDOW,
    WORK_HOURS_END,
    WORK_HOURS_START,
)

# A full working day is WORK_HOURS_START-WORK_HOURS_END (10h by default);
# thresholds are fractions of that shift rather than fixed hour counts, so
# they stay correct if the shift length in agent/config.py ever changes.
_shift_hours = (
    int(WORK_HOURS_END.split(":")[0]) + int(WORK_HOURS_END.split(":")[1]) / 60
    - int(WORK_HOURS_START.split(":")[0]) - int(WORK_HOURS_START.split(":")[1]) / 60
)
FULL_DAY_THRESHOLD_SECONDS = int(_shift_hours * 3600 * 0.6)  # 60% of the shift
HALF_DAY_THRESHOLD_SECONDS = int(_shift_hours * 3600 * 0.3)  # 30% of the shift


def week_off_reason(day: date_cls) -> str | None:
    """None for a working day; otherwise the reason it's a paid week-off."""
    if day.weekday() == 6:  # Monday=0 ... Sunday=6
        return "Sunday"
    if day.weekday() == 5:  # Saturday
        nth_saturday = (day.day - 1) // 7 + 1
        if nth_saturday in (1, 3):
            return "1st/3rd Saturday"
    return None


def classify_attendance(day: date_cls, total_active_seconds: int, today: date_cls) -> str:
    """One of: week_off | full_day | half_day | absent | upcoming."""
    if week_off_reason(day) is not None:
        return "week_off"
    if day > today:
        return "upcoming"
    if total_active_seconds >= FULL_DAY_THRESHOLD_SECONDS:
        return "full_day"
    if total_active_seconds >= HALF_DAY_THRESHOLD_SECONDS:
        return "half_day"
    return "absent"


def _parse_hhmm(value: str) -> time_cls:
    hour, minute = value.split(":")
    return time_cls(int(hour), int(minute))


def _within_window(t: time_cls, window: tuple[str, str]) -> bool:
    start, end = window
    return _parse_hhmm(start) <= t <= _parse_hhmm(end)


def is_late_arrival(check_in: Optional[datetime]) -> bool:
    """A late arrival is orthogonal to the full/half/absent classification
    above — someone who checks in late can still put in a full day, so this
    is reported alongside `classify_attendance`, never instead of it.

    On-time means the check-in falls inside one of two sanctioned punch-in
    windows: the normal morning shift, or an afternoon shift for someone
    starting their day after lunch. Anything outside both windows — too
    early, in the gap between them, or after the afternoon window — is
    late, regardless of how much was worked afterwards."""
    if check_in is None:
        return False
    t = check_in.time()
    return not (_within_window(t, MORNING_PUNCH_IN_WINDOW) or _within_window(t, AFTERNOON_PUNCH_IN_WINDOW))


def is_sanctioned_half_day_checkout(check_out: Optional[datetime]) -> bool:
    """True when a check-out falls inside the sanctioned half-day early
    departure window — paired with a morning check-in, this marks a
    legitimate "worked the morning, left at lunch" day. Purely
    informational for attendance display; classify_attendance()'s
    hours-based full/half/absent split is unaffected."""
    if check_out is None:
        return False
    return _within_window(check_out.time(), HALF_DAY_PUNCH_OUT_WINDOW)
