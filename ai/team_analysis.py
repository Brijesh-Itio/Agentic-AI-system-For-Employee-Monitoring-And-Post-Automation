"""
MODULE 21.4 — AI Team Analysis

Weekly Ollama-powered analysis over every registered team member's real
tracked data: high performer identification, struggling member flags,
workload imbalance detection, bottleneck identification, rebalancing
suggestions, and burnout risk scoring. Computed on demand (like module
7's "Generate Now") rather than only on a schedule, so it's immediately
testable and usable without waiting for a weekly trigger.
"""
import json
import logging
from datetime import date as date_cls, timedelta
from typing import Optional, TypedDict

from agent import database
from ai.ollama_client import generate

logger = logging.getLogger(__name__)

DEFAULT_WINDOW_DAYS = 7


class MemberWeeklyStats(TypedDict):
    user_id: str
    name: str
    avg_focus_score: Optional[float]
    total_hours: float
    productive_hours: float
    avg_switch_count: float
    days_with_data: int


class TeamAnalysis(TypedDict):
    members: list[MemberWeeklyStats]
    high_performers: list[str]
    struggling_members: list[str]
    workload_imbalance: str
    bottlenecks: str
    rebalancing_suggestions: list[str]
    burnout_risk: list[dict]
    raw_summary: Optional[str]


def _member_weekly_stats(user_id: str, name: str, since: date_cls) -> MemberWeeklyStats:
    conn = database.get_connection()
    rows = conn.execute(
        """
        SELECT focus_score, total_active_seconds, productive_seconds, app_switch_count
        FROM daily_stats WHERE user_id = ? AND date >= ?
        """,
        (user_id, since.isoformat()),
    ).fetchall()

    scored = [r["focus_score"] for r in rows if r["focus_score"] is not None]
    total_seconds = sum(r["total_active_seconds"] or 0 for r in rows)
    productive_seconds = sum(r["productive_seconds"] or 0 for r in rows)
    switches = [r["app_switch_count"] or 0 for r in rows]

    return {
        "user_id": user_id,
        "name": name,
        "avg_focus_score": round(sum(scored) / len(scored), 1) if scored else None,
        "total_hours": round(total_seconds / 3600, 1),
        "productive_hours": round(productive_seconds / 3600, 1),
        "avg_switch_count": round(sum(switches) / len(switches), 1) if switches else 0.0,
        "days_with_data": len(rows),
    }


def _build_prompt(members: list[MemberWeeklyStats], window_days: int) -> str:
    lines = [
        f"{m['name']} ({m['user_id']}): avg focus {m['avg_focus_score']}%, "
        f"{m['total_hours']}h total ({m['productive_hours']}h productive), "
        f"avg {m['avg_switch_count']} app switches/day, {m['days_with_data']} day(s) of data"
        for m in members
    ]
    return (
        f"You are analysing a team's work data for the past {window_days} days. Based ONLY on the "
        "real metrics below, respond with a JSON object with exactly these keys:\n"
        '"high_performers": list of names with consistently high focus score and productive hours\n'
        '"struggling_members": list of names with low focus score, low hours, or very high context switching\n'
        '"workload_imbalance": one sentence on whether hours are distributed unevenly across the team\n'
        '"bottlenecks": one sentence identifying anyone whose low activity might be blocking others, or "None identified"\n'
        '"rebalancing_suggestions": list of 2-3 specific, actionable suggestions\n'
        '"burnout_risk": list of objects {"name": str, "risk": "low"|"medium"|"high", "reason": str} for each member\n\n'
        "Base every claim strictly on the metrics given — do not invent behaviour not reflected in them. "
        "Respond with ONLY the JSON object, no other text.\n\n"
        "TEAM METRICS:\n" + "\n".join(lines)
    )


def analyse_team(user_ids: Optional[list[str]] = None, window_days: int = DEFAULT_WINDOW_DAYS) -> TeamAnalysis:
    conn = database.get_connection()
    if user_ids:
        placeholders = ",".join("?" for _ in user_ids)
        users = conn.execute(f"SELECT id, name FROM users WHERE id IN ({placeholders})", user_ids).fetchall()
    else:
        users = conn.execute("SELECT id, name FROM users").fetchall()

    since = date_cls.today() - timedelta(days=window_days)
    members = [_member_weekly_stats(u["id"], u["name"], since) for u in users]

    empty: TeamAnalysis = {
        "members": members, "high_performers": [], "struggling_members": [], "workload_imbalance": "",
        "bottlenecks": "", "rebalancing_suggestions": [], "burnout_risk": [], "raw_summary": None,
    }

    if not members:
        logger.info("Team analysis: no registered team members to analyse")
        return empty

    raw = generate(_build_prompt(members, window_days), fast=False)
    if raw is None:
        logger.error("Team analysis: Ollama unreachable/timed out")
        return {**empty, "raw_summary": "Analysis unavailable — Ollama unreachable or timed out."}

    try:
        start = raw.index("{")
        end = raw.rindex("}") + 1
        parsed = json.loads(raw[start:end])
        result: TeamAnalysis = {
            "members": members,
            "high_performers": parsed.get("high_performers", []),
            "struggling_members": parsed.get("struggling_members", []),
            "workload_imbalance": parsed.get("workload_imbalance", ""),
            "bottlenecks": parsed.get("bottlenecks", ""),
            "rebalancing_suggestions": parsed.get("rebalancing_suggestions", []),
            "burnout_risk": parsed.get("burnout_risk", []),
            "raw_summary": None,
        }
        logger.info("Team analysis: produced structured result for %d member(s)", len(members))
        return result
    except (ValueError, json.JSONDecodeError):
        logger.warning("Team analysis: model response wasn't valid JSON — returning as raw narrative instead")
        return {**empty, "raw_summary": raw}


if __name__ == "__main__":
    from agent.logging_config import setup_logging

    setup_logging()
    logger.info("Module 21.4 manual test: running team analysis")
    print(analyse_team())
