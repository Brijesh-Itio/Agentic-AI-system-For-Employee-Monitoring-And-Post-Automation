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

from sqlalchemy import Column, Date, DateTime, Float, ForeignKey, Integer, String, create_engine
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


class CompanyHoliday(Base):
    __tablename__ = "company_holidays"
    id = Column(Integer, primary_key=True)
    date = Column(Date, nullable=False, unique=True)
    title = Column(String, nullable=False)
    holiday_type = Column(String, nullable=False, default="holiday")
    description = Column(String)
    created_by = Column(String, nullable=False)
    created_at = Column(DateTime)


class EmailTemplate(Base):
    __tablename__ = "email_templates"
    id = Column(Integer, primary_key=True)
    template_key = Column(String, nullable=False, unique=True)
    subject_template = Column(String, nullable=False)
    body_template = Column(String, nullable=False)
    updated_by = Column(String)
    updated_at = Column(DateTime)


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
    # Login/logout + RBAC. NULL means the account was created before this
    # feature existed (or by an admin who hasn't set a password yet) and
    # can't log in until one is set.
    password_hash = Column(String)


class AgentHeartbeat(Base):
    """Liveness signal independent of activity_logs — see the table's
    schema comment in agent/database.py for why activity_logs alone (which
    only gets a row when a session *closes*) was the wrong liveness check."""
    __tablename__ = "agent_heartbeat"
    user_id = Column(String, primary_key=True)
    last_seen = Column(DateTime, nullable=False)


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


class Department(Base):
    __tablename__ = "departments"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    created_at = Column(DateTime)


class UrlRedirect(Base):
    __tablename__ = "url_redirects"
    id = Column(Integer, primary_key=True)
    source_url = Column(String, nullable=False)
    source_host = Column(String)
    source_path = Column(String, nullable=False)
    target_url = Column(String, nullable=False)
    status_code = Column(Integer, nullable=False)
    hit_count = Column(Integer, nullable=False, default=0)
    last_hit_at = Column(DateTime)
    created_by = Column(String)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    sync_status = Column(String)
    sync_message = Column(String)
    synced_at = Column(DateTime)


class DarTemplate(Base):
    __tablename__ = "dar_templates"
    id = Column(Integer, primary_key=True)
    department_id = Column(Integer, ForeignKey("departments.id", ondelete="CASCADE"), unique=True)
    fields_json = Column(String, nullable=False, default="[]")
    updated_at = Column(DateTime)


class DarEntry(Base):
    __tablename__ = "dar_entries"
    id = Column(Integer, primary_key=True)
    user_id = Column(String, nullable=False, default="local")
    date = Column(Date, nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id", ondelete="SET NULL"))
    task = Column(String, nullable=False)
    task_description = Column(String)
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    comment = Column(String)
    remarks = Column(String)
    link = Column(String)
    custom_fields_json = Column(String, nullable=False, default="{}")
    source = Column(String, nullable=False, default="manual")
    project = Column(String)
    status = Column(String, nullable=False, default="in_progress")
    progress = Column(Integer, nullable=False, default=0)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="SET NULL"))
    created_at = Column(DateTime)
    updated_at = Column(DateTime)


class Task(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True)
    user_id = Column(String, nullable=False)
    assigned_by = Column(String)
    department_id = Column(Integer, ForeignKey("departments.id", ondelete="SET NULL"))
    project = Column(String)
    title = Column(String, nullable=False)
    description = Column(String)
    status = Column(String, nullable=False, default="not_started")
    progress = Column(Integer, nullable=False, default=0)
    priority = Column(String, nullable=False, default="medium")
    due_date = Column(Date)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    completed_at = Column(DateTime)


class CalendarEvent(Base):
    __tablename__ = "calendar_events"
    id = Column(Integer, primary_key=True)
    user_id = Column(String, nullable=False, default="local")
    uid = Column(String)
    subject = Column(String, nullable=False)
    organizer = Column(String)
    attendees_json = Column(String, nullable=False, default="[]")
    meeting_type = Column(String)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime)
    duration_seconds = Column(Integer)
    location = Column(String)
    date = Column(Date, nullable=False)
    source_file = Column(String)
    created_at = Column(DateTime)


class FileActivityLog(Base):
    __tablename__ = "file_activity_logs"
    id = Column(Integer, primary_key=True)
    user_id = Column(String, nullable=False, default="local")
    file_path = Column(String, nullable=False)
    event_type = Column(String, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    date = Column(Date, nullable=False)
    watched_root = Column(String)


class SeoSite(Base):
    __tablename__ = "seo_sites"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    base_url = Column(String, nullable=False)
    cms_type = Column(String, nullable=False, default="wordpress")
    cms_base_url = Column(String)
    is_active = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime)
    # NULL means "fall back to the .env value" — see agent/database.py's
    # _SEO_SITES_EXTRA_COLUMNS comment for why these are per-site.
    gsc_site_url = Column(String)
    ga4_property_id = Column(String)
    cms_username = Column(String)
    cms_app_password = Column(String)
    cms_api_token = Column(String)
    cms_collection_id = Column(String)
    # Direct SFTP server access — see agent/database.py's
    # _SEO_SITES_EXTRA_COLUMNS comment for why these exist alongside CMS.
    ssh_host = Column(String)
    ssh_port = Column(String)
    ssh_username = Column(String)
    ssh_password = Column(String)
    ssh_protocol = Column(String)  # NULL/blank means "sftp" — see agent/database.py

    # Plain Python properties (not Columns) — SeoSiteOut's from_attributes
    # reads these via getattr same as any Column, but the API never
    # echoes the actual secret back once saved, only whether one is set.
    @property
    def cms_app_password_set(self) -> bool:
        return bool(self.cms_app_password)

    @property
    def cms_api_token_set(self) -> bool:
        return bool(self.cms_api_token)

    @property
    def ssh_password_set(self) -> bool:
        return bool(self.ssh_password)


class SeoJobRun(Base):
    __tablename__ = "seo_job_runs"
    id = Column(Integer, primary_key=True)
    site_id = Column(Integer, ForeignKey("seo_sites.id", ondelete="CASCADE"), nullable=False)
    job_type = Column(String, nullable=False)
    run_date = Column(Date, nullable=False)
    status = Column(String, nullable=False, default="running")
    started_at = Column(DateTime)
    finished_at = Column(DateTime)
    error = Column(String)
    retry_count = Column(Integer, nullable=False, default=0)


class LlmUsageLog(Base):
    __tablename__ = "llm_usage_log"
    id = Column(Integer, primary_key=True)
    site_id = Column(Integer, ForeignKey("seo_sites.id", ondelete="SET NULL"))
    task = Column(String, nullable=False)
    provider = Column(String, nullable=False)
    model = Column(String)
    tokens_in = Column(Integer)
    tokens_out = Column(Integer)
    cost_estimate = Column(Float)
    latency_ms = Column(Float)
    success = Column(Integer, nullable=False)
    error = Column(String)
    created_at = Column(DateTime)


class SeoPagespeedResult(Base):
    __tablename__ = "seo_pagespeed_results"
    id = Column(Integer, primary_key=True)
    site_id = Column(Integer, ForeignKey("seo_sites.id", ondelete="CASCADE"), nullable=False)
    url = Column(String, nullable=False)
    strategy = Column(String, nullable=False, default="mobile")
    run_date = Column(Date, nullable=False)
    performance_score = Column(Float)
    lcp_ms = Column(Float)
    cls = Column(Float)
    inp_ms = Column(Float)
    ttfb_ms = Column(Float)
    fcp_ms = Column(Float)
    raw_json = Column(String)
    created_at = Column(DateTime)


class SeoSemrushMetric(Base):
    __tablename__ = "seo_semrush_metrics"
    id = Column(Integer, primary_key=True)
    site_id = Column(Integer, ForeignKey("seo_sites.id", ondelete="CASCADE"), nullable=False)
    run_date = Column(Date, nullable=False)
    authority_score = Column(Float)
    organic_traffic = Column(Integer)
    organic_keywords = Column(Integer)
    paid_keywords = Column(Integer)
    referring_domains = Column(Integer)
    backlinks_total = Column(Integer)
    raw_json = Column(String)
    semrush_rank = Column(Integer)
    created_at = Column(DateTime)


class SeoServerFileBackup(Base):
    __tablename__ = "seo_server_file_backups"
    id = Column(Integer, primary_key=True)
    site_id = Column(Integer, ForeignKey("seo_sites.id", ondelete="CASCADE"), nullable=False)
    path = Column(String, nullable=False)
    action = Column(String, nullable=False)
    new_path = Column(String)
    content = Column(String)
    created_at = Column(DateTime)


class SeoGscQuery(Base):
    __tablename__ = "seo_gsc_queries"
    id = Column(Integer, primary_key=True)
    site_id = Column(Integer, ForeignKey("seo_sites.id", ondelete="CASCADE"), nullable=False)
    run_date = Column(Date, nullable=False)
    query = Column(String, nullable=False)
    clicks = Column(Integer, nullable=False, default=0)
    impressions = Column(Integer, nullable=False, default=0)
    ctr = Column(Float)
    position = Column(Float)
    created_at = Column(DateTime)


class SeoGscPage(Base):
    __tablename__ = "seo_gsc_pages"
    id = Column(Integer, primary_key=True)
    site_id = Column(Integer, ForeignKey("seo_sites.id", ondelete="CASCADE"), nullable=False)
    run_date = Column(Date, nullable=False)
    page = Column(String, nullable=False)
    clicks = Column(Integer, nullable=False, default=0)
    impressions = Column(Integer, nullable=False, default=0)
    ctr = Column(Float)
    position = Column(Float)
    created_at = Column(DateTime)


class SeoMetaRewrite(Base):
    __tablename__ = "seo_meta_rewrite_queue"
    id = Column(Integer, primary_key=True)
    site_id = Column(Integer, ForeignKey("seo_sites.id", ondelete="CASCADE"), nullable=False)
    url = Column(String, nullable=False)
    run_date = Column(Date, nullable=False)
    impressions = Column(Integer, nullable=False, default=0)
    clicks = Column(Integer, nullable=False, default=0)
    ctr = Column(Float)
    position = Column(Float)
    suggested_title = Column(String)
    suggested_description = Column(String)
    status = Column(String, nullable=False, default="queued")
    created_at = Column(DateTime)
    reviewed_at = Column(DateTime)


class SeoGa4Page(Base):
    __tablename__ = "seo_ga4_pages"
    id = Column(Integer, primary_key=True)
    site_id = Column(Integer, ForeignKey("seo_sites.id", ondelete="CASCADE"), nullable=False)
    run_date = Column(Date, nullable=False)
    page_path = Column(String, nullable=False)
    sessions = Column(Integer, nullable=False, default=0)
    bounce_rate = Column(Float)
    conversions = Column(Float)
    created_at = Column(DateTime)


class SeoOgTags(Base):
    __tablename__ = "seo_og_tags"
    id = Column(Integer, primary_key=True)
    site_id = Column(Integer, ForeignKey("seo_sites.id", ondelete="CASCADE"), nullable=False)
    page_url = Column(String, nullable=False)
    page_title = Column(String, nullable=False)
    og_title = Column(String, nullable=False)
    og_description = Column(String, nullable=False)
    generated_at = Column(DateTime)


class SeoTechnicalIssue(Base):
    __tablename__ = "seo_technical_issues"
    id = Column(Integer, primary_key=True)
    site_id = Column(Integer, ForeignKey("seo_sites.id", ondelete="CASCADE"), nullable=False)
    run_date = Column(Date, nullable=False)
    rule = Column(String, nullable=False)
    severity = Column(String, nullable=False)
    url = Column(String, nullable=False)
    message = Column(String, nullable=False)
    suggested_fix = Column(String, nullable=False)
    status = Column(String, nullable=False, default="pending")
    reviewed_at = Column(DateTime)
    reviewed_by = Column(String)
    created_at = Column(DateTime)
    fix_value = Column(String)
    fix_applied = Column(Integer, nullable=False, default=0)
    fix_error = Column(String)
    ai_suggestion = Column(String)


class SeoDailyDigest(Base):
    __tablename__ = "seo_daily_digests"
    id = Column(Integer, primary_key=True)
    site_id = Column(Integer, ForeignKey("seo_sites.id", ondelete="CASCADE"), nullable=False)
    run_date = Column(Date, nullable=False)
    narrative = Column(String, nullable=False)
    stats_json = Column(String, nullable=False)
    slack_delivered = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime)
    emailed_at = Column(DateTime)


class SeoDigestRollup(Base):
    __tablename__ = "seo_digest_rollups"
    id = Column(Integer, primary_key=True)
    site_id = Column(Integer, ForeignKey("seo_sites.id", ondelete="CASCADE"), nullable=False)
    period = Column(String, nullable=False)
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    narrative = Column(String, nullable=False)
    stats_json = Column(String, nullable=False)
    slack_delivered = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime)
    emailed_at = Column(DateTime)


class SeoSocialPost(Base):
    __tablename__ = "seo_social_posts"
    id = Column(Integer, primary_key=True)
    site_id = Column(Integer, ForeignKey("seo_sites.id", ondelete="CASCADE"), nullable=False)
    platform = Column(String, nullable=False)
    source_url = Column(String)
    content = Column(String, nullable=False)
    image_url = Column(String)  # required for Instagram (no text-only post type); optional elsewhere
    status = Column(String, nullable=False, default="draft")
    external_post_id = Column(String)
    error = Column(String)
    created_at = Column(DateTime)
    posted_at = Column(DateTime)
    # Module 40 — which seo_facebook_accounts row this post publishes
    # through when more than one Facebook Page is configured; NULL means
    # "use the single default account from .env".
    facebook_account_id = Column(Integer, ForeignKey("seo_facebook_accounts.id"))
    # Module 41 — when set and status='approved', the scheduler
    # (ai/seo/social_scheduler.py) auto-publishes this post once this
    # time arrives; NULL means manual-publish-only, unchanged behaviour.
    scheduled_for = Column(DateTime)
    # Module 60 — plagiarism/humanization check result, JSON-encoded
    # ContentQualityReportOut. NULL means not checked yet.
    quality_report_json = Column(String)
    quality_checked_at = Column(DateTime)


class SeoFacebookAccount(Base):
    __tablename__ = "seo_facebook_accounts"
    id = Column(Integer, primary_key=True)
    label = Column(String, nullable=False)
    page_id = Column(String, nullable=False)
    page_access_token = Column(String, nullable=False)
    created_at = Column(DateTime)


class SeoBacklinkMention(Base):
    __tablename__ = "seo_backlink_mentions"
    id = Column(Integer, primary_key=True)
    site_id = Column(Integer, ForeignKey("seo_sites.id", ondelete="CASCADE"), nullable=False)
    source_url = Column(String, nullable=False)
    source_title = Column(String)
    anchor_text = Column(String)
    domain_rating = Column(Float)
    discovered_at = Column(String)
    outreach_subject = Column(String)
    outreach_body = Column(String)
    created_at = Column(DateTime)


class SeoIndexStatus(Base):
    __tablename__ = "seo_index_status"
    id = Column(Integer, primary_key=True)
    site_id = Column(Integer, ForeignKey("seo_sites.id", ondelete="CASCADE"), nullable=False)
    url = Column(String, nullable=False)
    coverage_state = Column(String)
    indexing_state = Column(String)
    robots_txt_state = Column(String)
    page_fetch_state = Column(String)
    last_crawl_time = Column(String)
    google_canonical = Column(String)
    user_canonical = Column(String)
    sitemap_json = Column(String)
    mobile_usability_verdict = Column(String)
    inspection_result_link = Column(String)
    crawled_as = Column(String)
    checked_at = Column(DateTime)


class SeoIndexingSubmission(Base):
    __tablename__ = "seo_indexing_submissions"
    id = Column(Integer, primary_key=True)
    site_id = Column(Integer, ForeignKey("seo_sites.id", ondelete="CASCADE"), nullable=False)
    url = Column(String, nullable=False)
    notification_type = Column(String, nullable=False)
    success = Column(Integer, nullable=False, default=0)
    response_json = Column(String)
    error = Column(String)
    submitted_at = Column(DateTime)


class SeoBlogPost(Base):
    __tablename__ = "seo_blog_posts"
    id = Column(Integer, primary_key=True)
    site_id = Column(Integer, ForeignKey("seo_sites.id", ondelete="CASCADE"), nullable=False)
    topic = Column(String, nullable=False)
    primary_keyword = Column(String)
    title = Column(String, nullable=False)
    excerpt = Column(String)
    content = Column(String, nullable=False)
    structure_passed = Column(Integer)
    structure_issues_json = Column(String)
    status = Column(String, nullable=False, default="draft")
    image_url = Column(String)
    slug = Column(String)
    tags = Column(String)
    categories = Column(String)
    cms_post_id = Column(String)
    cms_post_link = Column(String)
    error = Column(String)
    created_at = Column(DateTime)
    published_at = Column(DateTime)
    scheduled_at = Column(DateTime)
    # Module 60 — same convention as seo_social_posts' own columns above.
    quality_report_json = Column(String)
    quality_checked_at = Column(DateTime)


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
