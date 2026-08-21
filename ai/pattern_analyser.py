"""
MODULE 6.4-6.6 — Pattern Analyser

Statistical pattern mining over already-tracked/scored data. Deliberately
does not call Ollama: "what were this user's best hours over 14 days" is a
GROUP BY/AVG query, not a reasoning task — using an LLM here would be
slower and less reliable than the deterministic aggregate it's standing in
for. (Contrast with productivity_scorer.py's 6.1/6.2, which classify
never-seen-before entities and genuinely need reasoning.)

Sub-modules implemented (in order):
    6.4 Peak focus hours detector
    6.5 Context switching analyser
    6.6 Break habit analyser
"""
import json
import logging
from datetime import date as date_cls, datetime, timedelta
from typing import Optional

from agent import database
from agent.config import CONTEXT_SWITCH_HIGH_THRESHOLD, USER_ID

logger = logging.getLogger(__name__)

LOOKBACK_DAYS = 14
PEAK_HOURS_COUNT = 3


# ── 6.4 Peak focus hours detector ──

def detect_peak_focus_hours(user_id: str = USER_ID, lookback_days: int = LOOKBACK_DAYS) -> list:
    conn = database.get_connection()
    since = (date_cls.today() - timedelta(days=lookback_days)).isoformat()

    rows = conn.execute(
        """
        SELECT hour, AVG(focus_score) AS avg_score
        FROM hourly_scores
        WHERE user_id = ? AND date >= ? AND focus_score IS NOT NULL
        GROUP BY hour
        ORDER BY avg_score DESC
        LIMIT ?
        """,
        (user_id, since, PEAK_HOURS_COUNT),
    ).fetchall()

    return [{"hour": r["hour"], "avg_focus_score": round(r["avg_score"], 1)} for r in rows]


# ── 6.5 Context switching analyser ──

def analyse_context_switching(user_id: str = USER_ID, lookback_days: int = LOOKBACK_DAYS) -> dict:
    conn = database.get_connection()
    since = (date_cls.today() - timedelta(days=lookback_days)).isoformat()

    rows = conn.execute(
        """
        SELECT hour, AVG(switch_count) AS avg_switches
        FROM hourly_scores
        WHERE user_id = ? AND date >= ?
        GROUP BY hour
        ORDER BY hour ASC
        """,
        (user_id, since),
    ).fetchall()

    fragmented_hours = [r["hour"] for r in rows if r["avg_switches"] > CONTEXT_SWITCH_HIGH_THRESHOLD]
    deep_work_hours = sorted(rows, key=lambda r: r["avg_switches"])[:PEAK_HOURS_COUNT]
    deep_work_hours = [r["hour"] for r in deep_work_hours]

    return {"fragmented_hours": fragmented_hours, "deep_work_hours": deep_work_hours}


# ── 6.6 Break habit analyser ──

def analyse_break_habits(user_id: str = USER_ID, lookback_days: int = LOOKBACK_DAYS) -> Optional[int]:
    """Correlates break duration with the focus score of the hour right
    after the break ends, and returns the duration bucket (in minutes)
    that precedes the best average follow-up focus score."""
    conn = database.get_connection()
    since = (date_cls.today() - timedelta(days=lookback_days)).isoformat()

    breaks = conn.execute(
        "SELECT start_time, end_time, duration_seconds FROM breaks WHERE user_id = ? AND date >= ?",
        (user_id, since),
    ).fetchall()

    if not breaks:
        return None

    short_scores, long_scores = [], []
    short_durations, long_durations = [], []

    for b in breaks:
        end_dt = datetime.fromisoformat(b["end_time"])
        follow_up_hour_row = conn.execute(
            "SELECT focus_score FROM hourly_scores WHERE user_id = ? AND date = ? AND hour = ?",
            (user_id, end_dt.date().isoformat(), end_dt.hour),
        ).fetchone()

        if follow_up_hour_row is None or follow_up_hour_row["focus_score"] is None:
            continue

        duration_minutes = (b["duration_seconds"] or 0) / 60
        score = follow_up_hour_row["focus_score"]

        if duration_minutes <= 15:
            short_scores.append(score)
            short_durations.append(duration_minutes)
        else:
            long_scores.append(score)
            long_durations.append(duration_minutes)

    short_avg = sum(short_scores) / len(short_scores) if short_scores else None
    long_avg = sum(long_scores) / len(long_scores) if long_scores else None

    if short_avg is None and long_avg is None:
        return None
    if long_avg is None or (short_avg is not None and short_avg >= long_avg):
        return round(sum(short_durations) / len(short_durations)) if short_durations else None
    return round(sum(long_durations) / len(long_durations)) if long_durations else None


# ── orchestrator ──

def analyse_patterns(user_id: str = USER_ID) -> dict:
    peak_hours = detect_peak_focus_hours(user_id)
    switching = analyse_context_switching(user_id)
    optimal_break_duration = analyse_break_habits(user_id)

    try:
        database.upsert_user_patterns(
            user_id=user_id,
            peak_focus_hours_json=json.dumps(peak_hours),
            optimal_break_duration=optimal_break_duration,
            fragmented_hours_json=json.dumps(switching["fragmented_hours"]),
        )
    except Exception:
        logger.exception("Failed to persist user_patterns")

    return {
        "peak_focus_hours": peak_hours,
        "fragmented_hours": switching["fragmented_hours"],
        "deep_work_hours": switching["deep_work_hours"],
        "optimal_break_duration": optimal_break_duration,
    }


if __name__ == "__main__":
    from agent.logging_config import setup_logging

    setup_logging()
    logger.info("Module 6 manual test: analysing patterns")
    result = analyse_patterns()
    logger.info("Result: %s", result)
