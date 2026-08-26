"""
MODULE 14 — Smart Alerts System (alert-checking logic)

Deterministic threshold checks over already-tracked data — no AI reasoning
needed here, same rationale as pattern_analyser.py: "is idle time over 30
minutes during work hours" is a comparison, not a judgement call.

Sub-modules implemented (in order):
    14.1 Focus alert
    14.2 Distraction alert
    14.3 Wellbeing alert
    14.4 Manager alert (stub — Team Module 21 not built yet)
"""
import logging
import threading
from datetime import date as date_cls, datetime, time as time_cls, timedelta
from typing import Optional

from agent import database
from agent.browser_tracker import BROWSER_PROCESSES
from agent.config import USER_ID, WORK_HOURS_END, WORK_HOURS_START
from agent.idle_detector import get_idle_seconds

logger = logging.getLogger(__name__)

FOCUS_ALERT_IDLE_SECONDS = 30 * 60
FOCUS_ALERT_DEBOUNCE_SECONDS = 30 * 60  # don't refire mid-idle-episode

DISTRACTION_ALERT_THRESHOLD_PCT = 30.0

OVERWORK_THRESHOLD_SECONDS = 10 * 3600
BURNOUT_CONSECUTIVE_DAYS = 5

DASHBOARD_URL = "http://localhost:5173"


def _parse_hhmm(value: str) -> time_cls:
    hour, minute = value.split(":")
    return time_cls(int(hour), int(minute))


def is_within_work_hours(at: datetime) -> bool:
    start = _parse_hhmm(WORK_HOURS_START)
    end = _parse_hhmm(WORK_HOURS_END)
    return start <= at.time() <= end


def _send_desktop_notification(title: str, message: str) -> None:
    try:
        from plyer import notification

        notification.notify(title=title, message=message, app_name="WorkPulse AI", timeout=10)
    except Exception:
        logger.exception("Desktop notification failed")


def trigger_alert(alert_type: str, message: str, user_id: str = USER_ID, also_email: bool = True) -> Optional[int]:
    # Admin-controlled master switch (independent of the employee's own
    # per-type alert_preferences checked right below).
    if not database.is_feature_enabled("alerts_enabled", user_id):
        logger.debug("Alerts disabled by admin for %s; skipping", user_id)
        return None
    if not database.is_alert_enabled(alert_type, user_id):
        logger.debug("Alert type %s disabled for %s; skipping", alert_type, user_id)
        return None

    now = datetime.now()
    try:
        alert_id = database.insert_alert(alert_type, message, now, user_id)
    except Exception:
        logger.exception("Failed to persist alert")
        return None

    logger.warning("ALERT [%s]: %s", alert_type, message)
    _send_desktop_notification(f"WorkPulse: {alert_type.title()} Alert", message)

    if also_email:
        try:
            from automation.email.sender import send_alert_email

            if send_alert_email(alert_type, message, dashboard_url=DASHBOARD_URL):
                database.mark_alert_emailed(alert_id)
        except Exception:
            logger.exception("Failed to send alert email")

    return alert_id


# ── 14.1 Focus alert ──

def check_focus_alert(user_id: str = USER_ID) -> Optional[int]:
    now = datetime.now()
    if not is_within_work_hours(now):
        return None

    idle_seconds = get_idle_seconds()
    if idle_seconds < FOCUS_ALERT_IDLE_SECONDS:
        return None

    last = database.get_last_alert_of_type("focus", user_id)
    if last is not None:
        last_triggered = datetime.fromisoformat(last["triggered_at"])
        if (now - last_triggered).total_seconds() < FOCUS_ALERT_DEBOUNCE_SECONDS:
            return None  # already alerted for this idle episode

    message = f"You've been idle for {int(idle_seconds // 60)} minutes during work hours."
    return trigger_alert("focus", message, user_id)


# ── 14.2 Distraction alert ──

def check_distraction_alert(hour_start: Optional[datetime] = None, user_id: str = USER_ID) -> Optional[int]:
    now = datetime.now()
    hour_start = hour_start or now.replace(minute=0, second=0, microsecond=0)
    hour_end = hour_start + timedelta(hours=1)
    day = hour_start.date()

    conn = database.get_connection()
    activity_rows = conn.execute(
        """
        SELECT app_name, category, duration_seconds FROM activity_logs
        WHERE user_id = ? AND end_time >= ? AND end_time < ?
        """,
        (user_id, hour_start.isoformat(sep=" "), hour_end.isoformat(sep=" ")),
    ).fetchall()
    website_rows = conn.execute(
        """
        SELECT domain, category, duration_seconds FROM websites
        WHERE user_id = ? AND end_time >= ? AND end_time < ?
        """,
        (user_id, hour_start.isoformat(sep=" "), hour_end.isoformat(sep=" ")),
    ).fetchall()

    total_seconds = sum(r["duration_seconds"] or 0 for r in activity_rows)
    if total_seconds == 0:
        return None

    distraction_seconds = 0
    culprits: list[str] = []
    for r in activity_rows:
        if r["app_name"] in BROWSER_PROCESSES:
            continue
        if r["category"] == "distraction":
            distraction_seconds += r["duration_seconds"] or 0
            culprits.append(r["app_name"])
    for r in website_rows:
        if r["category"] == "distraction":
            distraction_seconds += r["duration_seconds"] or 0
            if r["domain"]:
                culprits.append(r["domain"])

    pct = (distraction_seconds / total_seconds) * 100
    if pct < DISTRACTION_ALERT_THRESHOLD_PCT:
        return None

    unique_culprits = sorted(set(culprits))
    message = f"{pct:.0f}% of the last hour was spent on distractions: {', '.join(unique_culprits)}."
    return trigger_alert("distraction", message, user_id)


# ── 14.3 Wellbeing alert ──

def check_wellbeing_alert(user_id: str = USER_ID) -> list:
    triggered = []
    conn = database.get_connection()
    today = date_cls.today()

    today_row = conn.execute(
        "SELECT total_active_seconds FROM daily_stats WHERE user_id = ? AND date = ?",
        (user_id, today.isoformat()),
    ).fetchone()

    if today_row and (today_row["total_active_seconds"] or 0) > OVERWORK_THRESHOLD_SECONDS:
        last = database.get_last_alert_of_type("wellbeing", user_id)
        already_today = last and datetime.fromisoformat(last["triggered_at"]).date() == today
        if not already_today:
            hours = (today_row["total_active_seconds"] or 0) / 3600
            alert_id = trigger_alert(
                "wellbeing", f"You've been active for {hours:.1f} hours today — consider taking a break.", user_id
            )
            if alert_id:
                triggered.append(alert_id)

    since = today - timedelta(days=BURNOUT_CONSECUTIVE_DAYS - 1)
    rows = conn.execute(
        "SELECT date, total_active_seconds FROM daily_stats WHERE user_id = ? AND date >= ? AND date <= ?",
        (user_id, since.isoformat(), today.isoformat()),
    ).fetchall()
    days_covered = {r["date"] for r in rows}
    all_days_present = all((since + timedelta(days=i)).isoformat() in days_covered for i in range(BURNOUT_CONSECUTIVE_DAYS))
    all_over_threshold = all((r["total_active_seconds"] or 0) > OVERWORK_THRESHOLD_SECONDS for r in rows)

    if all_days_present and all_over_threshold and rows:
        last = database.get_last_alert_of_type("wellbeing", user_id)
        # A distinct debounce from the overwork check above: only once,
        # not once per day, since burnout risk doesn't reset daily.
        recently_flagged = last and "burnout" in last["message"].lower() and \
            (datetime.now() - datetime.fromisoformat(last["triggered_at"])).days < BURNOUT_CONSECUTIVE_DAYS
        if not recently_flagged:
            alert_id = trigger_alert(
                "wellbeing",
                f"Burnout risk: you've exceeded 10 active hours for {BURNOUT_CONSECUTIVE_DAYS} consecutive days.",
                user_id,
            )
            if alert_id:
                triggered.append(alert_id)

    return triggered


# ── 14.4 Manager alert (stub) ──

def check_manager_alert(user_id: str = USER_ID) -> None:
    """Team mode (module 21 — Team Intelligence Dashboard) isn't built yet,
    so there's no multi-user roster to check "no activity for 2+ hours"
    against. Left as an explicit no-op rather than faking a check against
    data that doesn't exist."""
    return None


# ── scheduler ──

class AlertMonitor:
    """Runs all real-time/periodic alert checks on their own thread,
    alongside the other agent components (app tracker, screenshots, etc.)."""

    FOCUS_CHECK_INTERVAL_SECONDS = 60
    WELLBEING_CHECK_INTERVAL_SECONDS = 15 * 60

    def __init__(self, user_id: str = USER_ID):
        self.user_id = user_id
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._last_hour_checked: Optional[int] = None
        self._last_wellbeing_check: Optional[datetime] = None

    def start(self) -> None:
        database.init_db()
        self._thread = threading.Thread(target=self._run_loop, name="AlertMonitorThread", daemon=True)
        self._thread.start()
        logger.info("AlertMonitor started")

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
        logger.info("AlertMonitor stopped")

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self._tick()
            except Exception:
                logger.exception("AlertMonitor tick failed; continuing")
            self._stop_event.wait(self.FOCUS_CHECK_INTERVAL_SECONDS)

    def _tick(self) -> None:
        check_focus_alert(self.user_id)

        now = datetime.now()
        if self._last_hour_checked is not None and now.hour != self._last_hour_checked:
            finished_hour = now.replace(hour=self._last_hour_checked, minute=0, second=0, microsecond=0)
            check_distraction_alert(finished_hour, self.user_id)
        self._last_hour_checked = now.hour

        if (
            self._last_wellbeing_check is None
            or (now - self._last_wellbeing_check).total_seconds() >= self.WELLBEING_CHECK_INTERVAL_SECONDS
        ):
            check_wellbeing_alert(self.user_id)
            self._last_wellbeing_check = now
