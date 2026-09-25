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
from typing import Literal, Optional

from agent import database
from ai.llm.factory import get_provider
from ai.seo.report_metrics import metric_labels

logger = logging.getLogger(__name__)

# Module 58 — "custom" is a genuinely arbitrary human-picked date range,
# not snapped to a week/month boundary the way weekly/monthly are.
Period = Literal["weekly", "monthly", "custom"]


@dataclass
class RollupReport:
    site_id: int
    period: Period
    period_start: str
    period_end: str
    narrative: str
    stats_json: str


def _period_range(period: Period, reference_date: date_cls) -> tuple[date_cls, date_cls]:
    """weekly/monthly are always anchored to reference_date (defaults to
    today at the call site below) rather than hardcoded to literal
    "today" — lets a human pull last week's, or any specific past week's/
    month's, report instead of only ever the current one. Not used for
    period == "custom", which takes its start/end directly from the
    caller instead of being derived from a single reference date."""
    if period == "weekly":
        start = reference_date - timedelta(days=reference_date.weekday())  # that week's Monday
        return start, reference_date
    start = reference_date.replace(day=1)  # that month's 1st
    return start, reference_date


# The roll-up prompt is the daily notes pasted end to end, so its size grows
# with the period: a month of ~1.3k-character notes is ~40k characters, far
# past the model's 4k-token window and minutes of CPU time. Keep it bounded.
MAX_NOTES_IN_PROMPT = 14
MAX_CHARS_PER_NOTE = 600
AI_UNAVAILABLE_MARKER = "AI summary unavailable"


def _fallback_narrative(
    site_name: str, period: Period, digest_count: int, start: date_cls, end: date_cls, notes: Optional[list[str]] = None
) -> str:
    span = "this week" if period == "weekly" else "this month" if period == "monthly" else f"{start.isoformat()} to {end.isoformat()}"
    head = f"{period.capitalize()} roll-up for {site_name}: {digest_count} daily digest(s) recorded {span}."
    if digest_count == 0:
        return f"{head} There are no daily digests in this period yet, so there is nothing to summarise."
    # The AI step failed (Ollama busy/slow) — show what the period's own notes
    # said rather than an empty placeholder, and say plainly that it's a retry
    # away.
    highlights = "\n".join(f"- {' '.join(n.split())[:220]}" for n in (notes or [])[-7:])
    return (
        f"{head} ({AI_UNAVAILABLE_MARKER} — the local AI did not answer in time; press Generate now to try again.)"
        + (f"\n\nHighlights from the daily notes:\n{highlights}" if highlights else "")
    )


def generate_rollup_digest(
    site_id: int,
    site_name: str,
    period: Period,
    reference_date: Optional[date_cls] = None,
    custom_start: Optional[date_cls] = None,
    custom_end: Optional[date_cls] = None,
    metrics: Optional[list[str]] = None,
) -> RollupReport:
    """Never raises — falls back to a plain factual summary if the LLM
    call fails or if no daily digests exist yet for the period, same
    graceful-degrade convention as generate_daily_digest.

    reference_date (weekly/monthly only) anchors "this week"/"this
    month" to a chosen day instead of always literal today — omit it to
    keep today's behavior exactly as before. custom_start/custom_end are
    required when period == "custom" (the route validates this before
    calling); ValueError otherwise, since there's no sensible default
    range for an explicitly custom period.

    metrics (keys of ai.seo.report_metrics.REPORT_METRICS) narrows what the
    roll-up talks about. The daily notes it reads are already-written
    prose, so this can only be done by instruction, not by filtering data:
    the prompt names the areas to cover and tells the model to ignore the
    rest. None means everything, as before."""
    if period == "custom":
        if custom_start is None or custom_end is None:
            raise ValueError("custom_start and custom_end are required when period == 'custom'")
        start, end = custom_start, custom_end
    else:
        start, end = _period_range(period, reference_date or date_cls.today())
    daily_rows = database.list_daily_digests_between(site_id, start, end)

    narratives = [row["narrative"] for row in daily_rows]
    stats_json = json_dumps_digest_list(daily_rows)

    if not narratives:
        narrative = _fallback_narrative(site_name, period, 0, start, end)
    else:
        prompt_notes = [" ".join(n.split())[:MAX_CHARS_PER_NOTE] for n in narratives[-MAX_NOTES_IN_PROMPT:]]
        omitted = len(narratives) - len(prompt_notes)
        joined = "\n".join(f"- {n}" for n in prompt_notes)
        if omitted > 0:
            joined = f"({omitted} earlier note(s) left out to keep this short)\n" + joined
        focus = (
            ""
            if metrics is None
            else f"Cover ONLY these areas: {', '.join(metric_labels(metrics))}. The daily notes may "
            "mention other topics — ignore them completely.\n"
        )
        prompt = (
            f"You are an autonomous SEO operations agent writing a {period} roll-up for "
            f'"{site_name}", covering {start.isoformat()} to {end.isoformat()}. Below are that '
            f"period's daily digest notes, oldest first. Write a {'5-7' if period == 'monthly' else '3-5'} "
            "sentence summary: the overall trend direction (improving/declining/flat), the single "
            "biggest recurring issue, and one recommended priority for next period. Be direct and "
            "factual, no filler.\n"
            f"{focus}\n"
            f"DAILY NOTES:\n{joined}"
        )
        # fast=False: the "fast" model (phi3:mini) could not finish even a
        # week's notes inside its 120 s limit on this hardware — measured, it
        # was still running at 500 s — while the main model (qwen3:1.7b)
        # answered the same prompt in ~50 s and has a 600 s allowance.
        result = get_provider(task=f"{period}_digest", site_id=site_id).generate(prompt, fast=False)
        narrative = (
            result.text.strip()
            if result.ok and result.text and result.text.strip()
            else _fallback_narrative(site_name, period, len(narratives), start, end, narratives)
        )

    return RollupReport(
        site_id=site_id, period=period, period_start=start.isoformat(), period_end=end.isoformat(),
        narrative=narrative, stats_json=stats_json,
    )


def json_dumps_digest_list(rows) -> str:
    import json

    return json.dumps([{"run_date": r["run_date"], "narrative": r["narrative"]} for r in rows])
