"""
MODULE 36 — Weekly/monthly digest roll-ups.

ai/seo/daily_digest.py only ever produced a daily narrative — the
blueprint's own "every Monday, full week summary with trend analysis"
and "monthly board report" were never built. Rather than re-querying
every underlying data source again, this reads back the daily digests
already saved for the period (ai/seo/daily_digest.py's own output) and
asks the LLM to synthesise a trend-aware summary across them — genuinely
different from a daily digest, not a re-run of it: it explicitly asks
for trend direction and week/month-over-period framing a single day's
narrative can't give.
"""
import logging
from dataclasses import dataclass
from datetime import date as date_cls, timedelta
from typing import Literal

from agent import database
from ai.llm.factory import get_provider

logger = logging.getLogger(__name__)

Period = Literal["weekly", "monthly"]


@dataclass
class RollupReport:
    site_id: int
    period: Period
    period_start: str
    period_end: str
    narrative: str
    stats_json: str


def _period_range(period: Period, today: date_cls) -> tuple[date_cls, date_cls]:
    if period == "weekly":
        start = today - timedelta(days=today.weekday())  # this week's Monday
        return start, today
    start = today.replace(day=1)  # this month's 1st
    return start, today


def _fallback_narrative(site_name: str, period: Period, digest_count: int) -> str:
    span = "week" if period == "weekly" else "month"
    return (
        f"{period.capitalize()} roll-up for {site_name}: {digest_count} daily digest(s) recorded "
        f"this {span}. (LLM unavailable — trend narrative skipped.)"
    )


def generate_rollup_digest(site_id: int, site_name: str, period: Period) -> RollupReport:
    """Never raises — falls back to a plain factual summary if the LLM
    call fails or if no daily digests exist yet for the period, same
    graceful-degrade convention as generate_daily_digest."""
    today = date_cls.today()
    start, end = _period_range(period, today)
    daily_rows = database.list_daily_digests_between(site_id, start, end)

    narratives = [row["narrative"] for row in daily_rows]
    stats_json = json_dumps_digest_list(daily_rows)

    if not narratives:
        narrative = _fallback_narrative(site_name, period, 0)
    else:
        joined = "\n".join(f"- {n}" for n in narratives)
        prompt = (
            f"You are an autonomous SEO operations agent writing a {period} roll-up for "
            f'"{site_name}", covering {start.isoformat()} to {end.isoformat()}. Below are that '
            f"period's daily digest notes, oldest first. Write a {'5-7' if period == 'monthly' else '3-5'} "
            "sentence summary: the overall trend direction (improving/declining/flat), the single "
            "biggest recurring issue, and one recommended priority for next period. Be direct and "
            "factual, no filler.\n\n"
            f"DAILY NOTES:\n{joined}"
        )
        result = get_provider(task=f"{period}_digest", site_id=site_id).generate(prompt, fast=True)
        narrative = result.text.strip() if result.ok else _fallback_narrative(site_name, period, len(narratives))

    return RollupReport(
        site_id=site_id, period=period, period_start=start.isoformat(), period_end=end.isoformat(),
        narrative=narrative, stats_json=stats_json,
    )


def json_dumps_digest_list(rows) -> str:
    import json

    return json.dumps([{"run_date": r["run_date"], "narrative": r["narrative"]} for r in rows])
