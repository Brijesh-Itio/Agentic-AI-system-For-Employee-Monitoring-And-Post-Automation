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


class ProductivityScoreOut(BaseModel):
    date: date_type
    focus_score: Optional[float] = None
    productive_seconds: int = 0
    total_active_seconds: int = 0
    productive_hours_formatted: str = "0h 0m"
    active_seconds_live: int = 0
    active_hours_formatted: str = "0h 0m"
    idle_seconds: int = 0
    idle_formatted: str = "0h 0m"
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


class PeriodSummaryOut(BaseModel):
    """Analytics page's period-average stat row — averages only over days
    that actually have data, so a short history or a day the agent wasn't
    running doesn't drag the average toward zero."""
    days_requested: int
    days_tracked: int
    avg_focus_score: Optional[float] = None
    avg_active_seconds: int = 0
    avg_productive_seconds: int = 0
    avg_active_hours_formatted: str = "0h 0m"
    avg_productive_hours_formatted: str = "0h 0m"


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


class FeatureFlagUpdate(BaseModel):
    enabled: bool


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
    has_password: bool = False


class UserCreate(BaseModel):
    id: str
    name: str
    email: Optional[str] = None
    role: Literal["employee", "manager", "admin", "hr"] = "employee"
    organisation_id: Optional[str] = None
    password: Optional[str] = None


class UserRoleUpdate(BaseModel):
    role: Literal["employee", "manager", "admin", "hr"]


class UserProfileUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None


class SetPasswordRequest(BaseModel):
    password: str


class LoginRequest(BaseModel):
    user_id: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class TeamMemberStatusOut(BaseModel):
    user: UserOut
    status: str  # active | idle | offline
    focus_score: Optional[float] = None
    active_hours_today: float = 0.0
    current_app: Optional[str] = None


class MemberWeeklyStatsOut(BaseModel):
    user_id: str
    name: str
    avg_focus_score: Optional[float] = None
    total_hours: float
    productive_hours: float
    avg_switch_count: float
    days_with_data: int


class TeamAnalysisOut(BaseModel):
    members: list[MemberWeeklyStatsOut]
    high_performers: list[str]
    struggling_members: list[str]
    workload_imbalance: str
    bottlenecks: str
    rebalancing_suggestions: list[str]
    # AI-authored objects with an unpredictable exact shape (model may omit a
    # key) — kept loose rather than a strict sub-model so a slightly off
    # response still renders instead of failing response validation.
    burnout_risk: list[dict]
    raw_summary: Optional[str] = None


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


class AttendanceDayOut(BaseModel):
    date: date_type
    status: str  # week_off | full_day | half_day | absent | upcoming
    week_off_reason: Optional[str] = None
    check_in: Optional[datetime] = None
    check_out: Optional[datetime] = None
    active_seconds: int = 0
    active_hours_formatted: str = "0h 0m"
    focus_score: Optional[float] = None
    is_late: bool = False
    is_half_day_checkout: bool = False


class AttendanceSummaryOut(BaseModel):
    month: str  # YYYY-MM
    full_days: int
    half_days: int
    absents: int
    week_offs: int
    late_count: int = 0
    days: list[AttendanceDayOut]


class CompanyHolidayOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    date: date_type
    title: str
    holiday_type: Literal["holiday", "paid_holiday"]
    description: Optional[str] = None
    created_by: str
    created_at: Optional[datetime] = None


class CompanyHolidayCreate(BaseModel):
    date: date_type
    title: str
    holiday_type: Literal["holiday", "paid_holiday"] = "holiday"
    description: Optional[str] = None


class EmailTemplateOut(BaseModel):
    template_key: str
    label: str
    subject: str
    body: str
    variables: str
    is_custom: bool
    updated_by: Optional[str] = None
    updated_at: Optional[datetime] = None


class EmailTemplateUpdate(BaseModel):
    subject: str
    body: str


class EmailTemplatePreview(BaseModel):
    subject: str
    body: str


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


# Shared by DarEntry and Task — a DAR entry's status defaults to
# "in_progress" (it already represents work that happened), while a fresh
# Task defaults to "not_started" (nothing's been done on an assignment yet).
DarStatus = Literal["not_started", "in_progress", "blocked", "completed"]


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
    project: Optional[str] = None
    status: DarStatus = "in_progress"
    progress: int = 0
    task_id: Optional[int] = None
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
    project: Optional[str] = None
    status: DarStatus = "in_progress"
    progress: int = 0
    task_id: Optional[int] = None


class DarEntryUpdate(BaseModel):
    task: Optional[str] = None
    task_description: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    comment: Optional[str] = None
    remarks: Optional[str] = None
    link: Optional[str] = None
    custom_fields: Optional[dict] = None
    project: Optional[str] = None
    status: Optional[DarStatus] = None
    progress: Optional[int] = None
    task_id: Optional[int] = None


class DarEntryDraftRequest(BaseModel):
    date: date_type
    department_id: int


# ── Task assignment system (distinct from DAR entries' daily log) ──


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: str
    assigned_by: Optional[str] = None
    department_id: Optional[int] = None
    project: Optional[str] = None
    title: str
    description: Optional[str] = None
    status: DarStatus = "not_started"
    progress: int = 0
    priority: Literal["low", "medium", "high"] = "medium"
    due_date: Optional[date_type] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class TaskCreate(BaseModel):
    user_id: str
    department_id: Optional[int] = None
    project: Optional[str] = None
    title: str
    description: Optional[str] = None
    priority: Literal["low", "medium", "high"] = "medium"
    due_date: Optional[date_type] = None


class TaskUpdate(BaseModel):
    project: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[DarStatus] = None
    progress: Optional[int] = None
    priority: Optional[Literal["low", "medium", "high"]] = None
    due_date: Optional[date_type] = None


# ── Calendar (.ics) tracker ──


class CalendarEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    uid: Optional[str] = None
    subject: str
    organizer: Optional[str] = None
    attendees: list[str] = []
    meeting_type: Optional[str] = None
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    location: Optional[str] = None
    date: date_type


# ── File-activity watcher ──


class FileActivityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    file_path: str
    event_type: str
    timestamp: datetime
    date: date_type
    watched_root: Optional[str] = None
