"""MODULE 5.5 — Productivity routes.

get_weekly_trend, get_patterns etc. are module 5.5. daily-scores,
focus-sessions/today, and heatmap were added for module 11 (Analytics),
which needs day-by-day and hour-by-day breakdowns the original route list
didn't cover — module 5's weekly_trends table only stores one aggregate
row per week, not the daily series module 11.4's chart needs.
"""
import logging
from datetime import date as date_type, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from agent.time_intelligence import TimeIntelligenceEngine, compute_focus_runs
from api.config import settings
from api.database import ContextSwitchFlag, DailyStats, HourlyScore, WeeklyTrend, get_db
from api.schemas import (
    DailyScoreOut,
    FocusSessionOut,
    FocusSessionsSummaryOut,
    HeatmapCellOut,
    PeakHourOut,
    ProductivityPatternsOut,
    ProductivityScoreOut,
    WeeklyTrendOut,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/productivity", tags=["productivity"])


def _score_for_date(db: Session, day: date_type) -> ProductivityScoreOut:
    row = (
        db.query(DailyStats)
        .filter(DailyStats.user_id == settings.DEFAULT_USER_ID, DailyStats.date == day)
        .first()
    )
    if row is None:
        return ProductivityScoreOut(date=day)

    return ProductivityScoreOut(
        date=row.date,
        focus_score=row.focus_score,
        productive_seconds=row.productive_seconds or 0,
        total_active_seconds=row.total_active_seconds or 0,
        productive_hours_formatted=TimeIntelligenceEngine.format_hours_minutes(row.productive_seconds or 0),
        work_start=row.work_start,
        work_end=row.work_end,
        longest_focus_seconds=row.longest_focus_seconds or 0,
    )


@router.get("/score/today", response_model=ProductivityScoreOut)
def get_today_score(db: Session = Depends(get_db)):
    return _score_for_date(db, date_type.today())


@router.get("/score/date/{target_date}", response_model=ProductivityScoreOut)
def get_score_by_date(target_date: date_type, db: Session = Depends(get_db)):
    return _score_for_date(db, target_date)


@router.get("/weekly", response_model=list[WeeklyTrendOut])
def get_weekly_trend(db: Session = Depends(get_db)):
    rows = (
        db.query(WeeklyTrend)
        .filter(WeeklyTrend.user_id == settings.DEFAULT_USER_ID)
        .order_by(WeeklyTrend.week_start.desc())
        .limit(12)
        .all()
    )
    return rows


@router.get("/patterns", response_model=ProductivityPatternsOut)
def get_patterns(db: Session = Depends(get_db)):
    """Best-effort patterns computed live from hourly_scores/context_switch_flags.
    Module 6 (AI pattern analyser) later enriches this with a dedicated,
    14-day-trained `user_patterns` table; this endpoint keeps working either way."""
    peak_rows = (
        db.query(HourlyScore.hour, func.avg(HourlyScore.focus_score).label("avg_score"))
        .filter(HourlyScore.user_id == settings.DEFAULT_USER_ID, HourlyScore.focus_score.isnot(None))
        .group_by(HourlyScore.hour)
        .order_by(func.avg(HourlyScore.focus_score).desc())
        .limit(3)
        .all()
    )
    peak_hours = [PeakHourOut(hour=r.hour, avg_focus_score=round(r.avg_score, 1)) for r in peak_rows]

    fragmented_rows = (
        db.query(HourlyScore.hour, func.avg(HourlyScore.switch_count).label("avg_switches"))
        .filter(HourlyScore.user_id == settings.DEFAULT_USER_ID)
        .group_by(HourlyScore.hour)
        .having(func.avg(HourlyScore.switch_count) > 10)
        .all()
    )
    fragmented_hours = [r.hour for r in fragmented_rows]

    high_switching_today = (
        db.query(func.count(ContextSwitchFlag.id))
        .filter(
            ContextSwitchFlag.user_id == settings.DEFAULT_USER_ID,
            ContextSwitchFlag.date == date_type.today(),
            ContextSwitchFlag.is_high_switching == 1,
        )
        .scalar()
    ) or 0

    return ProductivityPatternsOut(
        peak_focus_hours=peak_hours,
        fragmented_hours=fragmented_hours,
        high_switching_windows_today=high_switching_today,
    )


@router.get("/daily-scores", response_model=list[DailyScoreOut])
def get_daily_scores(days: int = 7, db: Session = Depends(get_db)):
    """11.4 — day-by-day focus scores (not week-aggregated) for a line chart."""
    since = date_type.today() - timedelta(days=days - 1)
    rows = (
        db.query(DailyStats.date, DailyStats.focus_score)
        .filter(
            DailyStats.user_id == settings.DEFAULT_USER_ID,
            DailyStats.date >= since,
            DailyStats.date <= date_type.today(),
        )
        .order_by(DailyStats.date.asc())
        .all()
    )
    by_date = {r.date: r.focus_score for r in rows}
    return [
        DailyScoreOut(date=since + timedelta(days=i), focus_score=by_date.get(since + timedelta(days=i)))
        for i in range(days)
    ]


@router.get("/focus-sessions/today", response_model=FocusSessionsSummaryOut)
def get_focus_sessions_today():
    """11.5 — every focus run today (reusing module 2.6/11's shared
    compute_focus_runs), plus the aggregate stats the summary cards need."""
    runs = compute_focus_runs(date_type.today(), settings.DEFAULT_USER_ID)
    if not runs:
        return FocusSessionsSummaryOut(
            session_count=0, average_session_seconds=0, longest_session_seconds=0,
            interrupted_count=0, sessions=[],
        )

    durations = [r["duration_seconds"] for r in runs]
    return FocusSessionsSummaryOut(
        session_count=len(runs),
        average_session_seconds=round(sum(durations) / len(durations)),
        longest_session_seconds=max(durations),
        interrupted_count=sum(1 for r in runs if r["interrupted_by_distraction"]),
        sessions=[
            FocusSessionOut(
                start=r["start"], end=r["end"], duration_seconds=r["duration_seconds"],
                interrupted_by_distraction=r["interrupted_by_distraction"],
            )
            for r in runs
        ],
    )


@router.get("/heatmap", response_model=list[HeatmapCellOut])
def get_peak_hours_heatmap(days: int = 7, db: Session = Depends(get_db)):
    """11.6 — hour x day focus-score grid for the past N days."""
    since = date_type.today() - timedelta(days=days - 1)
    rows = (
        db.query(HourlyScore.date, HourlyScore.hour, HourlyScore.focus_score)
        .filter(
            HourlyScore.user_id == settings.DEFAULT_USER_ID,
            HourlyScore.date >= since,
            HourlyScore.date <= date_type.today(),
        )
        .all()
    )
    return [HeatmapCellOut(date=r.date, hour=r.hour, focus_score=r.focus_score) for r in rows]
