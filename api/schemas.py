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


# ── SEO Agentic AI (module 25) ──

SeoCmsType = Literal["wordpress", "webflow"]


class SeoSiteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    base_url: str
    cms_type: str
    cms_base_url: Optional[str] = None
    is_active: bool
    created_at: Optional[datetime] = None
    gsc_site_url: Optional[str] = None
    ga4_property_id: Optional[str] = None
    # cms_username/cms_collection_id aren't secrets, returned as-is; the
    # app password/API token never come back over the API once saved —
    # only whether one is set (see api/database.py's SeoSite properties).
    cms_username: Optional[str] = None
    cms_collection_id: Optional[str] = None
    cms_app_password_set: bool = False
    cms_api_token_set: bool = False
    # Direct SFTP server access — host/port/username aren't secrets,
    # returned as-is; the password never comes back over the API once
    # saved, only whether one is set (see api/database.py's SeoSite
    # properties).
    ssh_host: Optional[str] = None
    ssh_port: Optional[str] = None
    ssh_username: Optional[str] = None
    ssh_protocol: Optional[str] = None
    ssh_password_set: bool = False


class SeoSiteCreate(BaseModel):
    name: str
    base_url: str
    cms_type: SeoCmsType = "wordpress"
    cms_base_url: Optional[str] = None
    gsc_site_url: Optional[str] = None
    ga4_property_id: Optional[str] = None


class SeoSiteGoogleConfigUpdate(BaseModel):
    """Blank string clears the override back to the .env fallback."""

    gsc_site_url: Optional[str] = None
    ga4_property_id: Optional[str] = None


class SeoSiteCmsConfigUpdate(BaseModel):
    """Blank string clears an override back to the .env fallback. Only
    the pair matching this site's own cms_type matters — WordPress reads
    username/app_password, Webflow reads api_token/collection_id."""

    cms_base_url: Optional[str] = None
    cms_username: Optional[str] = None
    cms_app_password: Optional[str] = None
    cms_api_token: Optional[str] = None
    cms_collection_id: Optional[str] = None


class SeoSiteSshConfigUpdate(BaseModel):
    """Same blank-clears/blank-keeps split as SeoSiteCmsConfigUpdate:
    host/port/username are plain overrides (blank clears them), password
    is a secret (blank leaves whatever's already saved untouched)."""

    ssh_host: Optional[str] = None
    ssh_port: Optional[str] = None
    ssh_username: Optional[str] = None
    ssh_protocol: Optional[str] = None
    ssh_password: Optional[str] = None


class SshStatusOut(BaseModel):
    site_id: int
    reachable: bool
    error: Optional[str] = None


class ServerFileWriteRequest(BaseModel):
    site_id: int
    path: str
    content: str


class ServerFileRenameRequest(BaseModel):
    site_id: int
    path: str
    new_path: str


class ServerFileContentOut(BaseModel):
    path: str
    content: str


class ServerFileBackupCreate(BaseModel):
    site_id: int
    path: str
    content: str


class ServerFileBackupSummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    path: str
    action: str
    new_path: Optional[str] = None
    created_at: Optional[datetime] = None


class ServerFileBackupOut(ServerFileBackupSummaryOut):
    content: Optional[str] = None


class ServerDirEntryOut(BaseModel):
    name: str
    is_dir: bool
    size: Optional[int] = None


class ServerDirListingOut(BaseModel):
    path: str
    entries: list[ServerDirEntryOut]


class SeoJobRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    site_id: int
    job_type: str
    run_date: date_type
    status: str
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    error: Optional[str] = None
    retry_count: int


class SeoJobRunTrigger(BaseModel):
    site_id: int
    job_type: str


class CmsPostOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    slug: str
    status: str
    link: Optional[str] = None
    excerpt: Optional[str] = None
    content: Optional[str] = None
    modified_at: Optional[str] = None


class CmsStatusOut(BaseModel):
    site_id: int
    cms_type: str
    reachable: bool


class SemrushMetricsCheckRequest(BaseModel):
    site_id: int


class RapidApiKeywordCheckRequest(BaseModel):
    site_id: int
    country: str = "us"


class KeywordResearchRequest(BaseModel):
    keyword: str
    language: str = "en"
    country: str = "us"


class MonthlySearchesOut(BaseModel):
    month: str
    year: int
    searches: int


class KeywordResearchRowOut(BaseModel):
    keyword: str
    avg_monthly_searches: Optional[int] = None
    low_cpc: Optional[str] = None
    high_cpc: Optional[str] = None
    competition_index: Optional[int] = None
    competition_value: Optional[str] = None
    intent: list[str] = []
    intent_confidence: Optional[float] = None
    advice: list[str] = []
    content_gap_score: Optional[float] = None
    estimated_ctr: Optional[float] = None
    keyword_freshness: Optional[float] = None
    serp_feature_type: Optional[str] = None
    monetization_score: Optional[float] = None
    monthly_search_volumes: list[MonthlySearchesOut] = []


class KeywordDifficultyRequest(BaseModel):
    keyword: str
    country: str = "us"


class KeywordDifficultyOut(BaseModel):
    keyword: str
    keyword_difficulty: Optional[int] = None
    volume: Optional[int] = None
    competition: Optional[float] = None
    cpc_dollars: Optional[float] = None
    monthly_volumes: dict = {}
    search_intent: Optional[list] = None


# Module 47 — RapidAPI "SEMrush SEO" domain-analysis wrapper
# (automation/seo/rapidapi_domain_client.py). site_id is required on the
# domain/website-lookup requests purely for site-existence validation
# consistency with the rest of this API, not because the lookup itself is
# scoped to that site — checking a competitor's domain is the whole point.

class TopBacklinksRequest(BaseModel):
    site_id: int
    website: str


class BacklinkRowOut(BaseModel):
    url_from: str
    url_to: str
    title: str
    anchor: str
    nofollow: bool
    # This provider's numeric fields aren't reliably integers — verified
    # live that "dr" on DomainAuthorityOut below came back as 0.3 for a
    # real domain (inquid.com), breaking response validation under a
    # strict int type. Every numeric field sourced from this same
    # provider (automation/seo/rapidapi_domain_client.py) is float here
    # defensively, not just the one field that happened to break first.
    inlink_rank: Optional[float] = None
    domain_inlink_rank: Optional[float] = None
    first_seen: str
    last_visited: str
    date_lost: str
    spam_score: Optional[float] = None


class DomainAuthorityRequest(BaseModel):
    site_id: int
    website: str


class BulkDomainAuthorityRequest(BaseModel):
    site_id: int
    domains: list[str]


class DomainAuthorityOut(BaseModel):
    domain: str
    da: Optional[float] = None
    pa: Optional[float] = None
    spam_score: Optional[float] = None
    dr: Optional[float] = None
    org_traffic: Optional[float] = None


class KeywordInsightRequest(BaseModel):
    keyword: str
    country: str = "us"


class KeywordInsightOut(BaseModel):
    keyword: str
    volume: Optional[float] = None
    competition: Optional[float] = None
    cpc_dollars: Optional[float] = None
    sd: Optional[float] = None
    monthly_volumes: dict = {}
    search_intent: Optional[list] = None


class WebsiteTrafficRequest(BaseModel):
    site_id: int
    website: str


class SampleKeywordOut(BaseModel):
    keyword: str
    position: Optional[float] = None
    search_volume: Optional[float] = None
    etv: Optional[float] = None
    cpc: Optional[float] = None
    url: str


class WebsiteTrafficOut(BaseModel):
    domain: str
    organic_etv: Optional[float] = None
    organic_keywords: Optional[float] = None
    ranked_keywords_total: Optional[float] = None
    estimated_paid_traffic_cost: Optional[float] = None
    position_distribution: dict = {}
    sample_keywords: list[SampleKeywordOut] = []


class SemrushMetricsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    site_id: int
    run_date: date_type
    authority_score: Optional[float] = None
    organic_traffic: Optional[int] = None
    organic_keywords: Optional[int] = None
    paid_keywords: Optional[int] = None
    referring_domains: Optional[int] = None
    backlinks_total: Optional[int] = None
    semrush_rank: Optional[int] = None
    created_at: Optional[datetime] = None


class SemrushBacklinkListRequest(BaseModel):
    site_id: int
    limit: int = 50


class SemrushBacklinkRowOut(BaseModel):
    source_url: str
    target_url: str
    anchor: str
    nofollow: bool
    first_seen: str
    last_seen: str
    page_authority_score: Optional[float] = None


class SemrushReferringDomainOut(BaseModel):
    domain: str
    authority_score: Optional[float] = None
    backlinks_num: Optional[int] = None
    country: str
    first_seen: str
    last_seen: str


class SemrushBacklinkGapRequest(BaseModel):
    site_id: int
    competitor_domains: list[str]


class SemrushGapRowOut(BaseModel):
    target: str
    authority_score: Optional[float] = None
    backlinks_num: Optional[int] = None
    referring_domains_num: Optional[int] = None


class PageSpeedCheckRequest(BaseModel):
    site_id: int
    url: str
    strategy: Literal["mobile", "desktop"] = "mobile"


class PageSpeedResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    site_id: int
    url: str
    strategy: str
    run_date: date_type
    performance_score: Optional[float] = None
    lcp_ms: Optional[float] = None
    cls: Optional[float] = None
    inp_ms: Optional[float] = None
    ttfb_ms: Optional[float] = None
    fcp_ms: Optional[float] = None
    created_at: Optional[datetime] = None


class PageSpeedOpportunityItemOut(BaseModel):
    url: Optional[str] = None
    wasted_bytes: Optional[float] = None
    wasted_ms: Optional[float] = None
    total_bytes: Optional[float] = None


class PageSpeedOpportunityOut(BaseModel):
    audit_id: str
    title: str
    description: str
    savings_ms: Optional[float] = None
    savings_bytes: Optional[float] = None
    items: list[PageSpeedOpportunityItemOut] = []


class ResourceAuditReportOut(BaseModel):
    total_requests: Optional[int] = None
    total_byte_weight_kb: Optional[float] = None
    unused_css_kb: Optional[float] = None
    unused_js_kb: Optional[float] = None
    render_blocking_requests: Optional[int] = None
    opportunities: list[PageSpeedOpportunityOut]


class GscPullRequest(BaseModel):
    site_id: int
    days_back: int = 7


class GscQueryRowOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    site_id: int
    run_date: date_type
    query: str
    clicks: int
    impressions: int
    ctr: Optional[float] = None
    position: Optional[float] = None
    created_at: Optional[datetime] = None


class GscPageRowOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    site_id: int
    run_date: date_type
    page: str
    clicks: int
    impressions: int
    ctr: Optional[float] = None
    position: Optional[float] = None
    created_at: Optional[datetime] = None


class RankChangeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    query: str
    previous_position: float
    current_position: float
    delta: float


class MetaRewriteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    site_id: int
    url: str
    run_date: date_type
    impressions: int
    clicks: int
    ctr: Optional[float] = None
    position: Optional[float] = None
    suggested_title: Optional[str] = None
    suggested_description: Optional[str] = None
    status: str
    created_at: Optional[datetime] = None
    reviewed_at: Optional[datetime] = None


class Ga4PullRequest(BaseModel):
    site_id: int
    start_date: str = "7daysAgo"
    end_date: str = "today"


class Ga4PageRowOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    site_id: int
    run_date: date_type
    page_path: str
    sessions: int
    bounce_rate: Optional[float] = None
    conversions: Optional[float] = None
    created_at: Optional[datetime] = None


class OgTagsGenerateRequest(BaseModel):
    site_id: int
    page_url: str
    page_title: str
    content_excerpt: str


class OgTagsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    site_id: int
    page_url: str
    page_title: str
    og_title: str
    og_description: str
    generated_at: Optional[datetime] = None


class InterlinkPage(BaseModel):
    site_id: int
    url: str
    title: str
    content: str


class InterlinkSuggestRequest(InterlinkPage):
    n_results: int = 8


class RelatedPageOut(BaseModel):
    url: str
    title: str
    distance: float


class ContentAnalyzeRequest(BaseModel):
    content_html: str
    primary_keyword: Optional[str] = None
    min_words: int = 600
    max_words: int = 3000


class StructureIssueOut(BaseModel):
    rule: str
    severity: str
    message: str


class StructureReportOut(BaseModel):
    word_count: int
    h1_count: int
    h2_count: int
    h3_count: int
    passed: bool
    issues: list[StructureIssueOut]


class FaqRequest(BaseModel):
    site_id: int
    page_title: str
    max_pairs: int = 5


class FaqPairOut(BaseModel):
    question: str
    answer: str


class TechnicalAuditRequest(BaseModel):
    site_id: int
    max_pages: int = 100


class TechnicalIssueOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    site_id: int
    run_date: date_type
    rule: str
    severity: str
    url: str
    message: str
    suggested_fix: str
    status: str
    reviewed_at: Optional[datetime] = None
    reviewed_by: Optional[str] = None
    created_at: Optional[datetime] = None
    fix_value: Optional[str] = None
    fix_applied: bool = False
    fix_error: Optional[str] = None
    ai_suggestion: Optional[str] = None


class TechnicalIssueReview(BaseModel):
    reviewed_by: Optional[str] = None


class TechnicalIssueEditTargetOut(BaseModel):
    kind: str  # "cms" | "static_file" | "unavailable"
    edit_url: Optional[str] = None
    file_path: Optional[str] = None
    detail: str


class PageTagAuditRequest(BaseModel):
    site_id: int
    url: str


class PageTagFindingOut(BaseModel):
    tag: str
    detail: str
    values: list[str] = []


class PageTagAuditOut(BaseModel):
    url: str
    missing_tags: list[PageTagFindingOut]
    existing_tags: list[PageTagFindingOut]
    duplicate_tags: list[PageTagFindingOut]
    invalid_tags: list[PageTagFindingOut]


class DigestGenerateRequest(BaseModel):
    site_id: int
    send_to_slack: bool = True


class DigestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    site_id: int
    run_date: date_type
    narrative: str
    stats_json: str
    slack_delivered: bool
    created_at: Optional[datetime] = None


class DigestRollupOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    site_id: int
    period: str
    period_start: date_type
    period_end: date_type
    narrative: str
    stats_json: str
    slack_delivered: bool
    created_at: Optional[datetime] = None


SocialPlatform = Literal["linkedin", "twitter", "instagram", "facebook"]


class SocialGenerateRequest(BaseModel):
    site_id: int
    page_title: str
    content_excerpt: str
    source_url: Optional[str] = None
    # Required for Instagram to actually publish (its API has no
    # text-only post type) — optional for every other platform.
    image_url: Optional[str] = None
    platforms: list[SocialPlatform] = ["linkedin"]
    # Module 40 — which seo_facebook_accounts row a facebook-platform post
    # should publish through; ignored for every other platform. None =
    # use the single default account from .env.
    facebook_account_id: Optional[int] = None


class SocialPostOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    site_id: int
    platform: str
    source_url: Optional[str] = None
    content: str
    image_url: Optional[str] = None
    status: str
    external_post_id: Optional[str] = None
    error: Optional[str] = None
    created_at: Optional[datetime] = None
    posted_at: Optional[datetime] = None
    facebook_account_id: Optional[int] = None


class FacebookAccountCreate(BaseModel):
    label: str
    page_id: str
    page_access_token: str


class FacebookAccountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    label: str
    page_id: str
    # page_access_token deliberately omitted — this is a real, live
    # credential (see api/config.py's comment on FACEBOOK_PAGE_ACCESS_TOKEN
    # for how sensitive one of these is); the frontend never needs it back
    # after creation, only enough to identify/delete the right account.
    created_at: Optional[datetime] = None


class BacklinkPullRequest(BaseModel):
    site_id: int


class BacklinkMentionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    site_id: int
    source_url: str
    source_title: Optional[str] = None
    anchor_text: Optional[str] = None
    domain_rating: Optional[float] = None
    discovered_at: Optional[str] = None
    outreach_subject: Optional[str] = None
    outreach_body: Optional[str] = None
    created_at: Optional[datetime] = None


class OutreachDraftRequest(BaseModel):
    site_name: str
    site_url: str


class UrlInspectRequest(BaseModel):
    site_id: int
    url: str


class IndexStatusOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    site_id: int
    url: str
    coverage_state: Optional[str] = None
    indexing_state: Optional[str] = None
    robots_txt_state: Optional[str] = None
    page_fetch_state: Optional[str] = None
    last_crawl_time: Optional[str] = None
    google_canonical: Optional[str] = None
    user_canonical: Optional[str] = None
    mobile_usability_verdict: Optional[str] = None
    inspection_result_link: Optional[str] = None
    crawled_as: Optional[str] = None
    # Raw JSON string (a list of sitemap URLs) — matches the DB column
    # as-is rather than parsing server-side; the frontend JSON.parses it,
    # same convention as this codebase's other *_json fields.
    sitemap_json: Optional[str] = None
    checked_at: Optional[datetime] = None


# Module 48/49 — GSC dimension filtering, Sitemaps management, Site
# Verification. Stateless (no local persistence) — this data lives in
# Google's own system and is cheap enough to re-fetch live each time.

class GscDimensionRequest(BaseModel):
    site_id: int
    days_back: int = 7
    row_limit: int = 100
    # ISO 3166-1 alpha-3 code — the same "click a country row to drill
    # into it" filter the real Search Console UI applies; matches the row
    # values automation/seo/gsc_client.py's country dimension returns.
    country: Optional[str] = None
    # Exact page URL — the same "click a page row to drill into it"
    # filter. Given as its own field (not folded into `country`) since a
    # human/UI caller may combine both, matching the real UI's filter chips.
    page: Optional[str] = None
    # Explicit range, overriding days_back when both are given — the
    # "Custom" date-range option in the real Search Console UI. Plain
    # ISO date strings ("YYYY-MM-DD"), not datetimes — GSC's own API is
    # date-granular, not time-of-day granular.
    start_date: Optional[date_type] = None
    end_date: Optional[date_type] = None


class GscDimensionRowOut(BaseModel):
    key: str
    clicks: int
    impressions: int
    ctr: float
    position: float


class GscDateRowOut(BaseModel):
    date: str
    clicks: int
    impressions: int
    ctr: float
    position: float


class GscExportRow(BaseModel):
    label: str
    clicks: int
    impressions: int
    ctr: float
    position: float


class GscExportRequest(BaseModel):
    site_id: int
    view: str
    date_range: str
    rows: list[GscExportRow]


class GscExportResult(BaseModel):
    ok: bool
    detail: str
    sheet_url: Optional[str] = None


class GscExportAllRequest(BaseModel):
    """Module 50 follow-up — one export call for every dimension at
    once (Queries/Pages/Countries/Devices/Search Appearance), each
    written to its own clean tab, instead of only whichever single tab
    a human currently has open on screen."""

    site_id: int
    date_range: str
    focus_view: str = "Queries"
    queries: list[GscExportRow] = []
    pages: list[GscExportRow] = []
    countries: list[GscExportRow] = []
    devices: list[GscExportRow] = []
    search_appearance: list[GscExportRow] = []
    # Per-day clicks/impressions — the same data behind the in-app trend
    # chart — used to (re)embed a real Google Sheets line chart on its
    # own "GSC Chart" tab, matching the real Search Console UI's own
    # "Export > Google Sheets" layout (Chart tab first, then one tab per
    # dimension).
    timeseries: list[GscDateRowOut] = []


class GscLiveQueryRowOut(BaseModel):
    query: str
    clicks: int
    impressions: int
    ctr: float
    position: float


class GscLivePageRowOut(BaseModel):
    page: str
    clicks: int
    impressions: int
    ctr: float
    position: float


# Module 51 — GA4 dimension/timeseries live views and Sheets export,
# mirroring the GscDimensionRequest/GscDateRowOut/GscExport* family
# above (see those classes' comments for the shared reasoning); GA4 has
# no country/page drill-down filter here since automation/seo/
# ga4_client.py's dimension pulls don't support combining filters the
# way gsc_client.py's dimensionFilterGroups do.
class Ga4DimensionRequest(BaseModel):
    site_id: int
    days_back: int = 28
    row_limit: int = 100
    start_date: Optional[date_type] = None
    end_date: Optional[date_type] = None


class Ga4DimensionRowOut(BaseModel):
    key: str
    sessions: int
    bounce_rate: float
    conversions: float
    active_users: int = 0
    new_users: int = 0
    total_users: int = 0
    event_count: int = 0
    engagement_rate: float = 0.0
    engaged_sessions: int = 0
    avg_session_duration: float = 0.0


class Ga4LivePageRowOut(BaseModel):
    page_path: str
    sessions: int
    bounce_rate: float
    conversions: float
    active_users: int = 0
    new_users: int = 0
    total_users: int = 0
    event_count: int = 0
    engagement_rate: float = 0.0
    engaged_sessions: int = 0
    avg_session_duration: float = 0.0


class Ga4DateRowOut(BaseModel):
    date: str
    sessions: int
    bounce_rate: float
    conversions: float
    active_users: int = 0
    new_users: int = 0
    total_users: int = 0
    event_count: int = 0
    engagement_rate: float = 0.0
    engaged_sessions: int = 0
    avg_session_duration: float = 0.0


class Ga4ExportRow(BaseModel):
    label: str
    sessions: int
    bounce_rate: float
    conversions: float


class Ga4EventExportRow(BaseModel):
    event_name: str
    event_count: int
    total_users: int
    event_count_per_active_user: float
    total_revenue: float


class Ga4ExportAllRequest(BaseModel):
    """One export call for every GA4 dimension at once (Pages/Sources/
    Countries/Devices/Events), each written to its own clean tab — see
    GscExportAllRequest above for the identical pattern this mirrors."""

    site_id: int
    date_range: str
    focus_view: str = "Pages"
    pages: list[Ga4ExportRow] = []
    sources: list[Ga4ExportRow] = []
    countries: list[Ga4ExportRow] = []
    devices: list[Ga4ExportRow] = []
    events: list[Ga4EventExportRow] = []
    timeseries: list[Ga4DateRowOut] = []


class Ga4ExportResult(BaseModel):
    ok: bool
    detail: str
    sheet_url: Optional[str] = None


# Module 57 — the site Overview dashboard's own "download this report in
# Google Sheets" button (Top Search Queries / Top Traffic Pages / CTR by
# Page / Rank Alerts — the 4-panel grid right under the Latest Digest
# card). Reuses each panel's own already-defined row shape rather than
# introducing a parallel one, since the export is just "whatever's
# already on screen," not a re-fetch.
class OverviewExportRequest(BaseModel):
    site_id: int
    top_queries: list[GscQueryRowOut] = []
    top_pages: list[Ga4PageRowOut] = []
    ctr_by_page: list[GscPageRowOut] = []
    rank_alerts: list[RankChangeOut] = []


class OverviewExportResult(BaseModel):
    ok: bool
    detail: str
    sheet_url: Optional[str] = None


# Module 52 — GA4's "Active users in last 30 minutes" realtime tile plus
# its country breakdown, matching the real GA4 UI's own Home/Realtime
# report.
class Ga4RealtimeRowOut(BaseModel):
    country: str
    active_users: int


# Module 55 — GA4's own "Events: Event name" report.
class Ga4EventRowOut(BaseModel):
    event_name: str
    event_count: int
    total_users: int
    active_users: int
    total_revenue: float
    event_count_per_active_user: float


# Module 52 follow-up — the fuller "Realtime overview" report (active
# users per minute, plus by device/page/audience), matching the real
# GA4 UI's dedicated Realtime page rather than just its Home tile.
class Ga4RealtimeMinuteRowOut(BaseModel):
    minutes_ago: int
    active_users: int


class Ga4RealtimeDimensionRowOut(BaseModel):
    key: str
    value: int


class SitemapListRequest(BaseModel):
    site_id: int


class SitemapContentTypeOut(BaseModel):
    type: str
    submitted: Optional[int] = None
    indexed: Optional[int] = None


class SitemapInfoOut(BaseModel):
    path: str
    last_submitted: Optional[str] = None
    is_pending: Optional[bool] = None
    is_sitemaps_index: Optional[bool] = None
    type: Optional[str] = None
    last_downloaded: Optional[str] = None
    warnings: Optional[int] = None
    errors: Optional[int] = None
    contents: list[SitemapContentTypeOut] = []


class SitemapActionRequest(BaseModel):
    site_id: int
    feedpath: str


class SitemapActionOut(BaseModel):
    ok: bool
    detail: str


class VerifiedSiteOut(BaseModel):
    id: str
    type: Optional[str] = None
    identifier: Optional[str] = None
    owners: list[str] = []


class IndexingSubmitRequest(BaseModel):
    site_id: int
    url: str
    notification_type: Literal["URL_UPDATED", "URL_DELETED"] = "URL_UPDATED"


class IndexingSubmissionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    site_id: int
    url: str
    notification_type: str
    success: bool
    error: Optional[str] = None
    submitted_at: Optional[datetime] = None


class LlmUsageLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    site_id: Optional[int] = None
    task: str
    provider: str
    model: Optional[str] = None
    tokens_in: Optional[int] = None
    tokens_out: Optional[int] = None
    cost_estimate: Optional[float] = None
    latency_ms: Optional[float] = None
    success: bool
    error: Optional[str] = None
    created_at: Optional[datetime] = None


class BlogGenerateRequest(BaseModel):
    site_id: int
    topic: str
    primary_keyword: Optional[str] = None
    min_words: int = 600


class ImageGenerateRequest(BaseModel):
    # If omitted, the route derives a prompt from the post's own
    # title/topic — an explicit prompt lets a human steer the image
    # (e.g. "a hand holding a phone" instead of the raw post title).
    prompt: Optional[str] = None


class SheetsShareRequest(BaseModel):
    email: str
    # Module 56 — which of the three spreadsheets (main/gsc/ga4) to
    # share; defaults to "main" so a pre-Module-56 client omitting this
    # field keeps behaving exactly as before.
    kind: str = "main"


class SheetsAdoptRequest(BaseModel):
    # Accepts either the bare spreadsheet id or a full Google Sheets URL
    # containing it — the route extracts the id either way.
    spreadsheet_id_or_url: str
    kind: str = "main"


class SheetsStatusOut(BaseModel):
    configured: bool
    spreadsheet_id: Optional[str] = None
    url: Optional[str] = None
    error: Optional[str] = None


class BlogPostUpdate(BaseModel):
    title: str
    excerpt: Optional[str] = None
    content: str


class BlogTaxonomyUpdate(BaseModel):
    # None = leave that field untouched; [] clears tags/categories.
    slug: Optional[str] = None
    tags: Optional[list[str]] = None
    categories: Optional[list[str]] = None


class BlogPostOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    site_id: int
    topic: str
    primary_keyword: Optional[str] = None
    title: str
    excerpt: Optional[str] = None
    content: str
    structure_passed: Optional[bool] = None
    structure_issues_json: Optional[str] = None
    status: str
    image_url: Optional[str] = None
    slug: Optional[str] = None
    # JSON-encoded arrays of plain names, same convention as
    # structure_issues_json above — the frontend JSON.parses these.
    tags: Optional[str] = None
    categories: Optional[str] = None
    cms_post_id: Optional[str] = None
    cms_post_link: Optional[str] = None
    error: Optional[str] = None
    created_at: Optional[datetime] = None
    published_at: Optional[datetime] = None


class WebpConvertRequest(BaseModel):
    site_id: int
    dry_run: bool = True


class WebpConvertUrlRequest(BaseModel):
    site_id: int
    url: str
    dry_run: bool = True


class PostConversionDetailOut(BaseModel):
    post_id: str
    kind: str
    title: str
    image_urls_found: list[str] = []
    images_converted: int = 0
    images_cached: int = 0
    images_failed: int = 0
    content_changed: bool = False
    updated: bool = False
    backup_id: Optional[int] = None
    error: Optional[str] = None


class BulkConvertReportOut(BaseModel):
    dry_run: bool
    posts_scanned: int = 0
    posts_with_images: int = 0
    posts_updated: int = 0
    images_found: int = 0
    images_converted: int = 0
    images_cached: int = 0
    images_failed: int = 0
    error: Optional[str] = None
    details: list[PostConversionDetailOut] = []


class ContentBackupSummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    site_id: int
    cms_post_id: str
    kind: str
    reason: str
    created_at: Optional[datetime] = None


class ContentBackupOut(ContentBackupSummaryOut):
    original_content: str
