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
from datetime import date as date_cls

from agent.config import WORK_HOURS_END, WORK_HOURS_START

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
