"""Pydantic response models for the FastAPI backend (module 5.1)."""
from datetime import date as date_type, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class ActivityLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    app_name: str
    window_title: Optional[str] = None
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    category: str
    date: date_type


class AppSummaryOut(BaseModel):
    app_name: str
    total_seconds: int
    category: str
    sessions: int


class ContextSwitchingHourOut(BaseModel):
    hour: int
    switch_count: int


class IdlePeriodOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    date: date_type


class WebsiteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    url: Optional[str] = None
    domain: Optional[str] = None
    page_title: Optional[str] = None
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    category: str
    date: date_type


class TopSiteOut(BaseModel):
    domain: str
    total_seconds: int
    visits: int


class ScreenshotOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    file_path: str
    thumbnail_path: Optional[str] = None
    original_path: Optional[str] = None
    timestamp: datetime
    date: date_type
    is_blurred: bool
    cloud_url: Optional[str] = None


class CaptureScreenshotOut(BaseModel):
    id: int
    file_path: str
    thumbnail_path: Optional[str] = None
    timestamp: datetime
    is_blurred: bool


class ProductivityScoreOut(BaseModel):
    date: date_type
    focus_score: Optional[float] = None
    productive_seconds: int = 0
    total_active_seconds: int = 0
    productive_hours_formatted: str = "0h 0m"
    work_start: Optional[datetime] = None
    work_end: Optional[datetime] = None
    longest_focus_seconds: int = 0


class WeeklyTrendOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    week_start: date_type
    avg_focus_score: Optional[float] = None
    total_hours: Optional[float] = None
    productive_hours: Optional[float] = None
    trend_direction: Optional[str] = None


class DailyScoreOut(BaseModel):
    date: date_type
    focus_score: Optional[float] = None


class FocusSessionOut(BaseModel):
    start: datetime
    end: datetime
    duration_seconds: int
    interrupted_by_distraction: bool


class FocusSessionsSummaryOut(BaseModel):
    session_count: int
    average_session_seconds: int
    longest_session_seconds: int
    interrupted_count: int
    sessions: list[FocusSessionOut]


class HeatmapCellOut(BaseModel):
    date: date_type
    hour: int
    focus_score: Optional[float] = None


class PeakHourOut(BaseModel):
    hour: int
    avg_focus_score: float


class ProductivityPatternsOut(BaseModel):
    peak_focus_hours: list[PeakHourOut]
    fragmented_hours: list[int]
    high_switching_windows_today: int


class DarReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    date: date_type
    content: str
    productivity_score: Optional[float] = None
    total_active_seconds: Optional[int] = None
    productive_seconds: Optional[int] = None
    generated_at: Optional[datetime] = None
    emailed_at: Optional[datetime] = None


class WeeklyReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    week_start: date_type
    content: str
    generated_at: Optional[datetime] = None
    emailed_at: Optional[datetime] = None


class StatusComponentOut(BaseModel):
    connected: bool
    detail: str


class SystemStatusOut(BaseModel):
    ollama: StatusComponentOut
    agent: StatusComponentOut
    database: StatusComponentOut
    gmail: StatusComponentOut
    playwright: StatusComponentOut


class AlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    alert_type: str
    message: str
    triggered_at: datetime
    dismissed_at: Optional[datetime] = None
    emailed: bool  # pydantic's lenient mode coerces SQLite's stored 0/1 automatically


class AlertPreferenceOut(BaseModel):
    enabled: bool
    threshold_value: Optional[float] = None


class AlertPreferenceUpdate(BaseModel):
    enabled: bool
    threshold_value: Optional[float] = None
