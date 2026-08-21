"""Pydantic response models for the FastAPI backend (module 5.1)."""
from datetime import date as date_type, datetime
from typing import Literal, Optional

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


class LeadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    company: Optional[str] = None
    role: Optional[str] = None
    interest: Optional[str] = None
    email: Optional[str] = None
    notes: Optional[str] = None
    last_contact: Optional[datetime] = None
    source: Optional[str] = None
    status: str
    created_at: Optional[datetime] = None


class LeadCreate(BaseModel):
    name: str
    company: Optional[str] = None
    role: Optional[str] = None
    interest: Optional[str] = None
    email: Optional[str] = None
    notes: Optional[str] = None
    source: Optional[str] = None
    status: str = "new"


class LeadUpdate(BaseModel):
    company: Optional[str] = None
    role: Optional[str] = None
    interest: Optional[str] = None
    email: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    email: Optional[str] = None
    role: str
    organisation_id: Optional[str] = None
    created_at: Optional[datetime] = None


class UserCreate(BaseModel):
    id: str
    name: str
    email: Optional[str] = None
    role: str = "employee"
    organisation_id: Optional[str] = None


class TeamMemberStatusOut(BaseModel):
    user: UserOut
    status: str  # active | idle | offline
    focus_score: Optional[float] = None
    active_hours_today: float = 0.0
    current_app: Optional[str] = None


class PostLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    date: date_type
    time: str
    topic: Optional[str] = None
    content: str
    post_id: Optional[str] = None
    platform: str
    status: str
    likes: int = 0
    comments: int = 0
    error: Optional[str] = None


class LinkedInStatusOut(BaseModel):
    can_post_now: bool
    last_post_at: Optional[datetime] = None
    minutes_until_next_allowed: int = 0
    posts_today: int = 0
    daily_limit: int


class CampaignLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    date: date_type
    time: str
    name: Optional[str] = None
    email: str
    company: Optional[str] = None
    subject: Optional[str] = None
    status: str
    error: Optional[str] = None
    follow_up_sent: bool


class CampaignStatsOut(BaseModel):
    total_sent: int
    total_failed: int
    sent_today: int
    daily_limit: int


class CommandRequest(BaseModel):
    command: str


class JobLogEntry(BaseModel):
    at: datetime
    message: str


class JobOut(BaseModel):
    id: str
    command: str
    action: str
    status: str  # queued | running | completed | failed | cancelled
    progress: int
    logs: list[JobLogEntry]
    result: Optional[str] = None
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


# ── Module 7 extension: department-custom DAR templates ──

FieldType = Literal["text", "textarea", "number", "date", "select", "url"]


class FieldDef(BaseModel):
    key: str
    label: str
    type: FieldType = "text"
    required: bool = False
    options: Optional[list[str]] = None  # only meaningful when type == "select"


class DepartmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    created_at: Optional[datetime] = None


class DepartmentCreate(BaseModel):
    name: str


class DarTemplateOut(BaseModel):
    department_id: Optional[int] = None
    fields: list[FieldDef]
    updated_at: Optional[datetime] = None


class DarTemplateUpdate(BaseModel):
    fields: list[FieldDef]


class DarEntryOut(BaseModel):
    id: int
    date: date_type
    department_id: Optional[int] = None
    task: str
    task_description: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    comment: Optional[str] = None
    remarks: Optional[str] = None
    link: Optional[str] = None
    custom_fields: dict
    source: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class DarEntryCreate(BaseModel):
    date: date_type
    department_id: Optional[int] = None
    task: str
    task_description: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    comment: Optional[str] = None
    remarks: Optional[str] = None
    link: Optional[str] = None
    custom_fields: dict = {}


class DarEntryUpdate(BaseModel):
    task: Optional[str] = None
    task_description: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    comment: Optional[str] = None
    remarks: Optional[str] = None
    link: Optional[str] = None
    custom_fields: Optional[dict] = None


class DarEntryDraftRequest(BaseModel):
    date: date_type
    department_id: int
