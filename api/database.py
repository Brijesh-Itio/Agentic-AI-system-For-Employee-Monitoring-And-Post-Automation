"""
SQLAlchemy models and DB connection for the FastAPI backend.

Schema ownership: agent/database.py's raw-SQL DDL is the single source of
truth for table definitions (it's the process most likely to run first and
write most often). This module's `init_db()` simply invokes that same
function so the schema is guaranteed identical regardless of whether the
agent or the API starts first — no duplicate/drifting schema definitions.
SQLAlchemy here is purely for ergonomic querying from route handlers.
"""
import logging
from typing import Generator

from sqlalchemy import Column, Date, DateTime, Float, Integer, String, create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from agent import database as agent_db
from api.config import settings

logger = logging.getLogger(__name__)

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class ActivityLog(Base):
    __tablename__ = "activity_logs"
    id = Column(Integer, primary_key=True)
    user_id = Column(String, nullable=False, default="local")
    app_name = Column(String, nullable=False)
    window_title = Column(String)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime)
    duration_seconds = Column(Integer)
    category = Column(String, default="uncategorised")
    date = Column(Date, nullable=False)
    created_at = Column(DateTime)


class Website(Base):
    __tablename__ = "websites"
    id = Column(Integer, primary_key=True)
    user_id = Column(String, nullable=False, default="local")
    url = Column(String)
    domain = Column(String)
    page_title = Column(String)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime)
    duration_seconds = Column(Integer)
    category = Column(String, default="uncategorised")
    date = Column(Date, nullable=False)


class Screenshot(Base):
    __tablename__ = "screenshots"
    id = Column(Integer, primary_key=True)
    user_id = Column(String, nullable=False, default="local")
    file_path = Column(String, nullable=False)
    thumbnail_path = Column(String)
    timestamp = Column(DateTime, nullable=False)
    date = Column(Date, nullable=False)
    is_blurred = Column(Integer, default=0)
    cloud_url = Column(String)
    original_path = Column(String)


class DailyStats(Base):
    __tablename__ = "daily_stats"
    id = Column(Integer, primary_key=True)
    user_id = Column(String, nullable=False, default="local")
    date = Column(Date, nullable=False)
    work_start = Column(DateTime)
    work_end = Column(DateTime)
    total_active_seconds = Column(Integer, default=0)
    productive_seconds = Column(Integer, default=0)
    idle_seconds = Column(Integer, default=0)
    focus_score = Column(Float)
    app_switch_count = Column(Integer, default=0)
    top_apps_json = Column(String)
    top_sites_json = Column(String)
    longest_focus_start = Column(DateTime)
    longest_focus_end = Column(DateTime)
    longest_focus_seconds = Column(Integer, default=0)


class HourlyScore(Base):
    __tablename__ = "hourly_scores"
    id = Column(Integer, primary_key=True)
    user_id = Column(String, nullable=False, default="local")
    date = Column(Date, nullable=False)
    hour = Column(Integer, nullable=False)
    focus_score = Column(Float)
    productive_seconds = Column(Integer, default=0)
    total_seconds = Column(Integer, default=0)
    switch_count = Column(Integer, default=0)


class WeeklyTrend(Base):
    __tablename__ = "weekly_trends"
    id = Column(Integer, primary_key=True)
    user_id = Column(String, nullable=False, default="local")
    week_start = Column(Date, nullable=False)
    avg_focus_score = Column(Float)
    total_hours = Column(Float)
    productive_hours = Column(Float)
    trend_direction = Column(String)


class ContextSwitchFlag(Base):
    __tablename__ = "context_switch_flags"
    id = Column(Integer, primary_key=True)
    user_id = Column(String, nullable=False, default="local")
    date = Column(Date, nullable=False)
    window_start = Column(DateTime, nullable=False)
    window_end = Column(DateTime, nullable=False)
    switch_count = Column(Integer, nullable=False)
    is_high_switching = Column(Integer, default=0)
    created_at = Column(DateTime)


class Break(Base):
    __tablename__ = "breaks"
    id = Column(Integer, primary_key=True)
    user_id = Column(String, nullable=False, default="local")
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    duration_seconds = Column(Integer, nullable=False)
    break_type = Column(String, nullable=False)
    date = Column(Date, nullable=False)


class IdlePeriod(Base):
    __tablename__ = "idle_periods"
    id = Column(Integer, primary_key=True)
    user_id = Column(String, nullable=False, default="local")
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime)
    duration_seconds = Column(Integer)
    date = Column(Date, nullable=False)


class Alert(Base):
    __tablename__ = "alerts"
    id = Column(Integer, primary_key=True)
    user_id = Column(String, nullable=False, default="local")
    alert_type = Column(String, nullable=False)
    message = Column(String, nullable=False)
    triggered_at = Column(DateTime, nullable=False)
    dismissed_at = Column(DateTime)
    emailed = Column(Integer, default=0)


class AlertPreference(Base):
    __tablename__ = "alert_preferences"
    id = Column(Integer, primary_key=True)
    user_id = Column(String, nullable=False, default="local")
    alert_type = Column(String, nullable=False)
    enabled = Column(Integer, nullable=False, default=1)
    threshold_value = Column(Float)


class DarReport(Base):
    __tablename__ = "dar_reports"
    id = Column(Integer, primary_key=True)
    user_id = Column(String, nullable=False, default="local")
    date = Column(Date, nullable=False)
    content = Column(String, nullable=False)
    productivity_score = Column(Float)
    total_active_seconds = Column(Integer)
    productive_seconds = Column(Integer)
    generated_at = Column(DateTime)
    emailed_at = Column(DateTime)


class WeeklyReport(Base):
    __tablename__ = "weekly_reports"
    id = Column(Integer, primary_key=True)
    user_id = Column(String, nullable=False, default="local")
    week_start = Column(Date, nullable=False)
    content = Column(String, nullable=False)
    generated_at = Column(DateTime)
    emailed_at = Column(DateTime)


class Lead(Base):
    __tablename__ = "leads"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    company = Column(String)
    role = Column(String)
    interest = Column(String)
    email = Column(String)
    notes = Column(String)
    last_contact = Column(DateTime)
    source = Column(String)
    status = Column(String, nullable=False, default="new")
    created_at = Column(DateTime)


class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True)
    role = Column(String, nullable=False, default="employee")
    organisation_id = Column(String)
    created_at = Column(DateTime)


class PostLog(Base):
    __tablename__ = "post_log"
    id = Column(Integer, primary_key=True)
    date = Column(Date, nullable=False)
    time = Column(String, nullable=False)
    topic = Column(String)
    content = Column(String, nullable=False)
    post_id = Column(String)
    platform = Column(String, nullable=False, default="linkedin")
    status = Column(String, nullable=False)
    likes = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    error = Column(String)


class CampaignLog(Base):
    __tablename__ = "campaign_log"
    id = Column(Integer, primary_key=True)
    date = Column(Date, nullable=False)
    time = Column(String, nullable=False)
    name = Column(String)
    email = Column(String, nullable=False)
    company = Column(String)
    subject = Column(String)
    status = Column(String, nullable=False)
    error = Column(String)
    follow_up_sent = Column(Integer, default=0)


class Job(Base):
    __tablename__ = "jobs"
    id = Column(String, primary_key=True)
    command = Column(String, nullable=False)
    action = Column(String, nullable=False)
    status = Column(String, nullable=False, default="queued")
    progress = Column(Integer, nullable=False, default=0)
    logs_json = Column(String, nullable=False, default="[]")
    result = Column(String)
    created_at = Column(DateTime)
    completed_at = Column(DateTime)


def init_db() -> None:
    """Ensure schema exists before the API serves any requests."""
    agent_db.init_db()
    logger.info("API database ready at %s", settings.DATABASE_URL)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
