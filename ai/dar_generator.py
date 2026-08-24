"""
MODULE 7 — AI DAR Generator

Reads a full day's tracked data, formats it into a clean structured log,
and asks the local Ollama model (qwen3:1.7b — zero external API, per
DEVELOPMENT.md) to write a professional first-person Daily Activity Report
from it. Before building the log, it reuses Module 6's rescore_day() so the
report is generated from fully categorized, freshly scored data rather than
stale/uncategorised rows.

Sub-modules implemented (in order):
    7.1 Day log builder
    7.2 DAR prompt
    7.3 DAR saver
    7.4 Scheduler
"""
import logging
import threading
from datetime import date as date_cls, datetime
from typing import Optional

import schedule

from agent import database
from agent.browser_tracker import BROWSER_PROCESSES
from agent.config import DAR_GENERATION_TIME, USER_ID
from agent.time_intelligence import TimeIntelligenceEngine
from ai.ollama_client import generate
from ai.productivity_scorer import rescore_day

logger = logging.getLogger(__name__)

_format_hm = TimeIntelligenceEngine.format_hours_minutes


def _format_clock(dt_str: Optional[str]) -> str:
    if not dt_str:
        return "N/A"
    dt = datetime.fromisoformat(dt_str) if isinstance(dt_str, str) else dt_str
    return dt.strftime("%I:%M %p").lstrip("0")


def _switch_band(count: int) -> str: 
    if count < 20:
        return "low"
    if count <= 50:
        return "moderate"
    return "high"


# ── 7.1 Day log builder ──

def build_day_log(day: date_cls, user_id: str = USER_ID) -> str:
    conn = database.get_connection()

    stats = conn.execute(
        "SELECT * FROM daily_stats WHERE user_id = ? AND date = ?", (user_id, day.isoformat())
    ).fetchone()

    work_start = _format_clock(stats["work_start"]) if stats else "N/A"
    work_end = _format_clock(stats["work_end"]) if stats else "N/A"
    total_active = stats["total_active_seconds"] if stats else 0
    productive = stats["productive_seconds"] if stats else 0
    idle = stats["idle_seconds"] if stats else 0
    switch_count = stats["app_switch_count"] if stats else 0
    productive_pct = round(productive / total_active * 100) if total_active else 0

    breaks = conn.execute(
        "SELECT break_type, COUNT(*) AS c FROM breaks WHERE user_id = ? AND date = ? GROUP BY break_type",
        (user_id, day.isoformat()),
    ).fetchall()
    break_counts = {r["break_type"]: r["c"] for r in breaks}
    breaks_line = ", ".join(
        f"{break_counts.get(t, 0)} {t}" for t in ("short", "long") if break_counts.get(t, 0)
    ) or "none"

    top_apps = conn.execute(
        """
        SELECT app_name, category, SUM(duration_seconds) AS total
        FROM activity_logs WHERE user_id = ? AND date = ?
        GROUP BY app_name ORDER BY total DESC LIMIT 5
        """,
        (user_id, day.isoformat()),
    ).fetchall()
    top_apps_lines = "\n".join(
        f"- {r['app_name']} ({_format_hm(r['total'])}) — "
        f"{'mixed' if r['app_name'] in BROWSER_PROCESSES else r['category']}"
        for r in top_apps
    ) or "- none recorded"

    top_sites = conn.execute(
        """
        SELECT domain, category, SUM(duration_seconds) AS total
        FROM websites WHERE user_id = ? AND date = ? AND domain IS NOT NULL
        GROUP BY domain ORDER BY total DESC LIMIT 5
        """,
        (user_id, day.isoformat()),
    ).fetchall()
    top_sites_lines = "\n".join(
        f"- {r['domain']} ({_format_hm(r['total'])}) — {r['category']}" for r in top_sites
    ) or "- none recorded"

    longest_focus_line = "N/A"
    if stats and stats["longest_focus_seconds"]:
        longest_focus_line = (
            f"{_format_hm(stats['longest_focus_seconds'])} "
            f"({_format_clock(stats['longest_focus_start']).lower()} - "
            f"{_format_clock(stats['longest_focus_end']).lower()})"
        )

    screenshot_count = database.get_screenshot_count_for_date(day, user_id)

    return (
        f"DATE: {day.isoformat()}\n"
        f"WORK START: {work_start}\n"
        f"WORK END: {work_end}\n"
        f"TOTAL ACTIVE: {_format_hm(total_active)}\n"
        f"PRODUCTIVE: {_format_hm(productive)} ({productive_pct}%)\n"
        f"IDLE: {_format_hm(idle)}\n"
        f"BREAKS: {breaks_line}\n\n"
        f"TOP APPS:\n{top_apps_lines}\n\n"
        f"TOP WEBSITES:\n{top_sites_lines}\n\n"
        f"CONTEXT SWITCHING: {switch_count} switches ({_switch_band(switch_count)})\n"
        f"LONGEST FOCUS: {longest_focus_line}\n"
        f"SCREENSHOTS: {screenshot_count} captured"
    )


# ── 7.2 DAR prompt ──

def build_dar_prompt(day_log: str) -> str:
    return (
        "You are an employee writing your own Daily Activity Report at the end of the "
        "work day, based on the raw activity log below. Write in first person, as if you "
        "are honestly reporting your own day — not as an observer describing someone else.\n\n"
        "Write the report with exactly these section headers, in this order:\n"
        "Executive Summary (2-3 sentences)\n"
        "Work Accomplished (bullet points of what was actually done, based on the app/website usage)\n"
        "Time Analysis (an honest breakdown of productive vs lost time)\n"
        "Focus Insights (peak performance moments and distractions)\n"
        "Tomorrow's Recommendations (3 specific, actionable suggestions)\n\n"
        "Base every claim strictly on the data below — do not invent activity that isn't "
        "reflected in it.\n\n"
        f"RAW ACTIVITY LOG:\n{day_log}"
    ) 


# ── 7.3 DAR saver ──

def generate_and_save_dar(day: Optional[date_cls] = None, user_id: str = USER_ID) -> Optional[str]:
    day = day or date_cls.today()
    logger.info("Generating DAR for %s", day)

    rescore_day(day, user_id)
    day_log = build_day_log(day, user_id)
    prompt = build_dar_prompt(day_log)

    content = generate(prompt, fast=False) 
    if content is None:
        logger.error("DAR generation failed for %s: Ollama unreachable/timed out", day)
        return None

    conn = database.get_connection()
    stats = conn.execute(
        "SELECT focus_score, total_active_seconds, productive_seconds FROM daily_stats "
        "WHERE user_id = ? AND date = ?",
        (user_id, day.isoformat()),
    ).fetchone()

    try:
        database.upsert_dar_report(
            day=day,
            content=content,
            productivity_score=stats["focus_score"] if stats else None,
            total_active_seconds=stats["total_active_seconds"] if stats else 0,
            productive_seconds=stats["productive_seconds"] if stats else 0,
            user_id=user_id,
        )
        logger.info("DAR saved for %s", day)
    except Exception:
        logger.exception("Failed to save DAR for %s", day)
        return None

    return content


# ── 7.4 Scheduler ──

class DarScheduler:
    def __init__(self, user_id: str = USER_ID, run_time: str = DAR_GENERATION_TIME):
        self.user_id = user_id
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        # A private Scheduler(), not the bare `schedule` module — see
        # time_intelligence.py's TimeIntelligenceEngine for the full
        # explanation of why every scheduler class needs its own instance.
        self._scheduler = schedule.Scheduler()
        self._scheduler.every().day.at(run_time).do(self._safe_generate)

    def _safe_generate(self) -> None:
        try:
            generate_and_save_dar(user_id=self.user_id)
        except Exception:
            logger.exception("Scheduled DAR generation failed")

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run_loop, name="DarSchedulerThread", daemon=True)
        self._thread.start()
        logger.info("DarScheduler started (daily at %s)", DAR_GENERATION_TIME)

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
        logger.info("DarScheduler stopped")

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self._scheduler.run_pending()
            except Exception:
                logger.exception("DAR scheduler tick failed; continuing")
            self._stop_event.wait(30)


if __name__ == "__main__":
    from agent.logging_config import setup_logging

    setup_logging()
    logger.info("Module 7 manual test: generating today's DAR")
    result = generate_and_save_dar()
    print(result)
