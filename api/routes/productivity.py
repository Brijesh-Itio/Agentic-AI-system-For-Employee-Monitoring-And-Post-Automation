"""MODULE 5.5 — Productivity routes. Scoped to the logged-in user.

get_weekly_trend, get_patterns etc. are module 5.5. daily-scores,
focus-sessions/today, and heatmap were added for module 11 (Analytics),
which needs day-by-day and hour-by-day breakdowns the original route list
didn't cover — module 5's weekly_trends table only stores one aggregate
row per week, not the daily series module 11.4's chart needs.
"""
import logging
from datetime import date as date_type, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from agent.time_intelligence import TimeIntelligenceEngine, compute_focus_runs
from api.auth import get_current_user
from api.database import ContextSwitchFlag, DailyStats, HourlyScore, User, WeeklyTrend, get_db
from api.schemas import (
    DailyScoreOut,
    FocusSessionOut,
    FocusSessionsSummaryOut,
    HeatmapCellOut,
    PeakHourOut,
    PeriodSummaryOut,
    ProductivityPatternsOut,
    ProductivityScoreOut,
    WeeklyTrendOut,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/productivity", tags=["productivity"])


def _score_for_date(db: Session, day: date_type, user_id: str) -> ProductivityScoreOut:
    row = db.query(DailyStats).filter(DailyStats.user_id == user_id, DailyStats.date == day).first()
    if row is None:
        return ProductivityScoreOut(date=day)

    idle_seconds = row.idle_seconds or 0

    # "Active hours" is a live, moment-by-moment stat for today (system
    # on/attended time since work_start, minus completed idle periods) —
    # unlike total_active_seconds/productive_seconds/focus_score, which are
    # snapshots only refreshed once an hour rolls over (see
    # TimeIntelligenceEngine._maybe_roll_hourly_score) and would otherwise
    # look frozen/zero for most of the day. Past days are already final, so
    # they just use the stored total.
    if day == date_type.today() and row.work_start is not None:
        elapsed_seconds = int((datetime.now() - row.work_start).total_seconds())
        active_seconds = max(0, elapsed_seconds - idle_seconds)
    else:
        active_seconds = row.total_active_seconds or 0

    return ProductivityScoreOut(
        date=row.date,
        focus_score=row.focus_score,
        productive_seconds=row.productive_seconds or 0,
        total_active_seconds=row.total_active_seconds or 0,
        productive_hours_formatted=TimeIntelligenceEngine.format_hours_minutes(row.productive_seconds or 0),
        active_seconds_live=active_seconds,
        active_hours_formatted=TimeIntelligenceEngine.format_hours_minutes(active_seconds),
        idle_seconds=idle_seconds,
        idle_formatted=TimeIntelligenceEngine.format_hours_minutes(idle_seconds),
        work_start=row.work_start,
        work_end=row.work_end,
        longest_focus_seconds=row.longest_focus_seconds or 0,
    )


@router.get("/score/today", response_model=ProductivityScoreOut)
def get_today_score(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return _score_for_date(db, date_type.today(), current_user.id)


@router.get("/score/date/{target_date}", response_model=ProductivityScoreOut)
def get_score_by_date(
    target_date: date_type, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    return _score_for_date(db, target_date, current_user.id)


@router.get("/weekly", response_model=list[WeeklyTrendOut])
def get_weekly_trend(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    rows = (
        db.query(WeeklyTrend)
        .filter(WeeklyTrend.user_id == current_user.id)
        .order_by(WeeklyTrend.week_start.desc())
        .limit(12)
        .all()
    )
    return rows


@router.get("/patterns", response_model=ProductivityPatternsOut)
def get_patterns(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Best-effort patterns computed live from hourly_scores/context_switch_flags.
    Module 6 (AI pattern analyser) later enriches this with a dedicated,
    14-day-trained `user_patterns` table; this endpoint keeps working either way."""
    peak_rows = (
        db.query(HourlyScore.hour, func.avg(HourlyScore.focus_score).label("avg_score"))
        .filter(HourlyScore.user_id == current_user.id, HourlyScore.focus_score.isnot(None))
        .group_by(HourlyScore.hour)
        .order_by(func.avg(HourlyScore.focus_score).desc())
        .limit(3)
        .all()
    )
    peak_hours = [PeakHourOut(hour=r.hour, avg_focus_score=round(r.avg_score, 1)) for r in peak_rows]

    fragmented_rows = (
        db.query(HourlyScore.hour, func.avg(HourlyScore.switch_count).label("avg_switches"))
        .filter(HourlyScore.user_id == current_user.id)
        .group_by(HourlyScore.hour)
        .having(func.avg(HourlyScore.switch_count) > 10)
        .all()
    )
    fragmented_hours = [r.hour for r in fragmented_rows]

    high_switching_today = (
        db.query(func.count(ContextSwitchFlag.id))
        .filter(
            ContextSwitchFlag.user_id == current_user.id,
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
def get_daily_scores(days: int = 7, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """11.4 — day-by-day focus scores (not week-aggregated) for a line chart."""
    since = date_type.today() - timedelta(days=days - 1)
    rows = (
        db.query(DailyStats.date, DailyStats.focus_score)
        .filter(
            DailyStats.user_id == current_user.id,
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


@router.get("/summary", response_model=PeriodSummaryOut)
def get_period_summary(days: int = 7, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Analytics page's 'Last N Days Average' stat row — same DailyStats
    rows daily-scores already reads, aggregated instead of listed day by
    day. Days with no row at all (agent wasn't running) are excluded from
    the average rather than counted as zero."""
    since = date_type.today() - timedelta(days=days - 1)
    rows = (
        db.query(DailyStats.focus_score, DailyStats.total_active_seconds, DailyStats.productive_seconds)
        .filter(
            DailyStats.user_id == current_user.id,
            DailyStats.date >= since,
            DailyStats.date <= date_type.today(),
        )
        .all()
    )

    if not rows:
        return PeriodSummaryOut(days_requested=days, days_tracked=0)

    scored = [r.focus_score for r in rows if r.focus_score is not None]
    avg_focus = round(sum(scored) / len(scored), 1) if scored else None
    avg_active = round(sum(r.total_active_seconds or 0 for r in rows) / len(rows))
    avg_productive = round(sum(r.productive_seconds or 0 for r in rows) / len(rows))

    return PeriodSummaryOut(
        days_requested=days,
        days_tracked=len(rows),
        avg_focus_score=avg_focus,
        avg_active_seconds=avg_active,
        avg_productive_seconds=avg_productive,
        avg_active_hours_formatted=TimeIntelligenceEngine.format_hours_minutes(avg_active),
        avg_productive_hours_formatted=TimeIntelligenceEngine.format_hours_minutes(avg_productive),
    )


@router.get("/focus-sessions/today", response_model=FocusSessionsSummaryOut)
def get_focus_sessions_today(current_user: User = Depends(get_current_user)):
    """11.5 — every focus run today (reusing module 2.6/11's shared
    compute_focus_runs), plus the aggregate stats the summary cards need."""
    runs = compute_focus_runs(date_type.today(), current_user.id)
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
def get_peak_hours_heatmap(
    days: int = 7, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """11.6 — hour x day focus-score grid for the past N days."""
    since = date_type.today() - timedelta(days=days - 1)
    rows = (
        db.query(HourlyScore.date, HourlyScore.hour, HourlyScore.focus_score)
        .filter(
            HourlyScore.user_id == current_user.id,
            HourlyScore.date >= since,
            HourlyScore.date <= date_type.today(),
        )
        .all()
    )
    return [HeatmapCellOut(date=r.date, hour=r.hour, focus_score=r.focus_score) for r in rows]
