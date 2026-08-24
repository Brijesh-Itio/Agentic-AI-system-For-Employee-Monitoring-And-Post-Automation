"""
MODULE 16.1 — Tracker Sub-Agent

Reads real-time activity data, checks alert thresholds, triggers alerts,
and refreshes daily_stats/user_patterns. Reuses module 6's scorer and
module 14's alert checks rather than duplicating their logic — this
module's job is orchestrating them into one callable unit the Master
Agent (module 15) can dispatch to, not reimplementing them.
"""
import logging
from datetime import date as date_cls
from typing import TypedDict

from agent.config import USER_ID
from ai.pattern_analyser import analyse_patterns
from ai.productivity_scorer import rescore_day
from ai.tools.activity_tools import (
    check_distraction_alert,
    check_focus_alert,
    check_manager_alert,
    check_wellbeing_alert,
)

logger = logging.getLogger(__name__)


class TrackerResult(TypedDict):
    status: str  # "success" | "failure"
    detail: str
    alerts_triggered: list[str]


def run(user_id: str = USER_ID) -> TrackerResult:
    today = date_cls.today()
    alerts_triggered: list[str] = []

    try:
        rescore_day(today, user_id)
        analyse_patterns(user_id)

        if check_focus_alert(user_id) is not None:
            alerts_triggered.append("focus")
        if check_distraction_alert(user_id=user_id) is not None:
            alerts_triggered.append("distraction")
        if check_wellbeing_alert(user_id):
            alerts_triggered.append("wellbeing")
        check_manager_alert(user_id)  # 14.4 — only fires anything when team mode has other members

        detail = (
            f"Rescored {today.isoformat()}, refreshed patterns, "
            f"{len(alerts_triggered)} alert(s) triggered"
            + (f" ({', '.join(alerts_triggered)})" if alerts_triggered else "")
        )
        logger.info("Tracker sub-agent: %s", detail)
        return {"status": "success", "detail": detail, "alerts_triggered": alerts_triggered}

    except Exception:
        logger.exception("Tracker sub-agent failed")
        return {"status": "failure", "detail": "rescore/pattern-analysis/alert-check raised an exception", "alerts_triggered": alerts_triggered}


if __name__ == "__main__":
    from agent.logging_config import setup_logging

    setup_logging()
    logger.info("Module 16.1 manual test: running tracker sub-agent")
    print(run())
