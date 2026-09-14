"""
MODULE 29.1 — Daily SEO digest generator.

Pulls the latest data this site has across every module 26-28 source
(PageSpeed, GSC, GA4, technical issues, job run history) and synthesises
it into a short narrative via the module 25 LLM factory — "not a
spreadsheet, a narrative," per the blueprint's own framing for this
feature. Never raises; falls back to a plain factual summary (no LLM) if
the LLM call fails, so a digest is still produced and deliverable either
way.
"""
import logging
from dataclasses import dataclass, field
from datetime import date as date_cls
from typing import List, Optional

from agent import database
from ai.llm.factory import get_provider
from ai.seo.rank_alerts import compute_rank_changes, dropped_out_of_top_10, top_movers

logger = logging.getLogger(__name__)


@dataclass
class DigestStats:
    pending_issues: int
    critical_issues: int
    latest_performance_score: Optional[float]
    top_gsc_queries: List[dict] = field(default_factory=list)
    top_ga4_pages: List[dict] = field(default_factory=list)
    recent_job_failures: int = 0
    # Rank-change alerts (ai/seo/rank_alerts.py) — "keyword falls out of
    # top 10" is explicitly a daily-report flag, not an instant Slack
    # alert (unlike an index drop), so it's gathered here rather than
    # pushed separately.
    rank_drops: List[dict] = field(default_factory=list)
    rank_movers: List[dict] = field(default_factory=list)
    meta_opportunities_queued: int = 0


@dataclass
class DigestReport:
    site_id: int
    run_date: str
    narrative: str
    stats: DigestStats


def _gather_stats(site_id: int) -> DigestStats:
    issues = database.list_technical_issues(site_id, status="pending", limit=500)
    critical = sum(1 for i in issues if i["severity"] == "critical")

    pagespeed = database.list_pagespeed_results(site_id, limit=1)
    latest_score = pagespeed[0]["performance_score"] if pagespeed else None

    gsc_rows = database.list_gsc_queries(site_id, limit=5)
    top_queries = [{"query": r["query"], "clicks": r["clicks"]} for r in gsc_rows]

    ga4_rows = database.list_ga4_pages(site_id, limit=5)
    top_pages = [{"page": r["page_path"], "sessions": r["sessions"]} for r in ga4_rows]

    job_runs = database.list_job_runs(site_id=site_id, limit=20)
    failures = sum(1 for j in job_runs if j["status"] == "failed")

    rank_changes = compute_rank_changes(site_id)
    rank_drops = [
        {"query": c.query, "was": c.previous_position, "now": c.current_position}
        for c in dropped_out_of_top_10(rank_changes)
    ]
    rank_movers = [
        {"query": c.query, "was": c.previous_position, "now": c.current_position}
        for c in top_movers(rank_changes, limit=5)
    ]

    opportunities = database.list_meta_rewrite_queue(site_id, status="queued", limit=500)
    opportunities_today = sum(1 for o in opportunities if o["run_date"] == date_cls.today().isoformat())

    return DigestStats(
        pending_issues=len(issues),
        critical_issues=critical,
        latest_performance_score=latest_score,
        top_gsc_queries=top_queries,
        top_ga4_pages=top_pages,
        recent_job_failures=failures,
        rank_drops=rank_drops,
        rank_movers=rank_movers,
        meta_opportunities_queued=opportunities_today,
    )


def _fallback_narrative(site_name: str, stats: DigestStats) -> str:
    score = stats.latest_performance_score if stats.latest_performance_score is not None else "n/a"
    return (
        f"SEO digest for {site_name}: {stats.pending_issues} pending technical issue(s) "
        f"({stats.critical_issues} critical), latest PageSpeed score {score}, "
        f"{stats.recent_job_failures} recent job failure(s), "
        f"{len(stats.rank_drops)} keyword(s) fell out of the top 10, "
        f"{stats.meta_opportunities_queued} page(s) queued for a meta rewrite. "
        "(LLM unavailable — narrative skipped.)"
    )


def generate_daily_digest(site_id: int, site_name: str) -> DigestReport:
    """Never raises — a digest is always produced, LLM-written when
    possible, factually assembled when not."""
    stats = _gather_stats(site_id)

    prompt = (
        f"You are an autonomous SEO operations agent writing a short daily status digest "
        f'for "{site_name}". Write 3-5 sentences: notable facts, the biggest issue to act '
        "on, and one recommended next action. Be direct and factual, no filler.\n\n"
        f"PENDING TECHNICAL ISSUES: {stats.pending_issues} total, {stats.critical_issues} critical\n"
        f"LATEST PAGESPEED SCORE: {stats.latest_performance_score}\n"
        f"TOP SEARCH QUERIES: {stats.top_gsc_queries}\n"
        f"TOP TRAFFIC PAGES: {stats.top_ga4_pages}\n"
        f"RECENT JOB FAILURES: {stats.recent_job_failures}\n"
        f"KEYWORDS THAT FELL OUT OF THE TOP 10 SINCE THE LAST PULL: {stats.rank_drops}\n"
        f"BIGGEST RANK MOVERS (either direction): {stats.rank_movers}\n"
        f"PAGES CURRENTLY QUEUED FOR A META REWRITE (high impressions, low CTR): {stats.meta_opportunities_queued}"
    )
    result = get_provider(task="daily_digest", site_id=site_id).generate(prompt, fast=True)
    narrative = result.text.strip() if result.ok else _fallback_narrative(site_name, stats)

    return DigestReport(
        site_id=site_id, run_date=date_cls.today().isoformat(), narrative=narrative, stats=stats
    )
