"""
Rank-change detection for the daily GSC pull — diffs today's query
positions against the last pull before it (agent/database.py's
seo_gsc_queries, query dimension) and flags two things the raw pull alone
never surfaces: which queries moved and by how much, and which queries
fell out of the top 10. Pure computation over already-stored data, no
external calls — runs as part of ai/seo/daily_digest.py's stats gathering
so both land in the same daily report the digest already produces.
"""
import logging
from dataclasses import dataclass
from typing import List

from agent import database

logger = logging.getLogger(__name__)

TOP_10_THRESHOLD = 10.0


@dataclass
class RankChange:
    query: str
    previous_position: float
    current_position: float
    delta: float  # positive = worse (moved further from #1)


def compute_rank_changes(site_id: int) -> List[RankChange]:
    """Never raises — returns an empty list if there's no prior pull to
    diff against yet (first-ever run, or yesterday's pull failed/was
    skipped), same graceful-degrade convention as every other SEO data
    source in this codebase."""
    run_dates = database.list_gsc_query_run_dates(site_id, limit=2)
    if len(run_dates) < 2:
        return []

    current_date, previous_date = run_dates[0], run_dates[1]
    current_rows = database.list_gsc_queries_for_date(site_id, current_date)
    previous_rows = database.list_gsc_queries_for_date(site_id, previous_date)
    previous_by_query = {row["query"]: row["position"] for row in previous_rows}

    changes = []
    for row in current_rows:
        prev_position = previous_by_query.get(row["query"])
        if prev_position is None or row["position"] is None:
            continue
        changes.append(
            RankChange(
                query=row["query"],
                previous_position=prev_position,
                current_position=row["position"],
                delta=row["position"] - prev_position,
            )
        )
    return changes


def top_movers(changes: List[RankChange], limit: int = 5) -> List[RankChange]:
    """Biggest swings either direction, worst first."""
    return sorted(changes, key=lambda c: abs(c.delta), reverse=True)[:limit]


def dropped_out_of_top_10(changes: List[RankChange]) -> List[RankChange]:
    """Queries that were ranking in the top 10 yesterday and aren't
    today — the specific alert the SEO blueprint calls out by name."""
    return [
        c for c in changes
        if c.previous_position <= TOP_10_THRESHOLD < c.current_position
    ]
