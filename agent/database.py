"""
Local SQLite schema and data-access layer for the desktop agent.

Design notes (scalability / performance):
- WAL journal mode so the tracker thread can write while other threads
  (calendar sync, etc.) read/write concurrently without lock contention.
- A single module-level lock serialises writes from multiple threads on top
  of WAL, since sqlite3 connections are not safe to share across threads
  without care.
- Indexes are created on every column this module or the API will filter/
  sort by, since activity_logs grows unbounded over the life of the agent.
- Schema evolves via CREATE TABLE IF NOT EXISTS / ALTER TABLE ADD COLUMN so
  upgrading the agent never destroys existing tracked data.
"""
import json
import logging
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, date as date_cls
from typing import Optional

from agent.config import LOCAL_DB_PATH

logger = logging.getLogger(__name__)

_write_lock = threading.Lock()
_local = threading.local()


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(LOCAL_DB_PATH), timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def get_connection() -> sqlite3.Connection:
    """Return a thread-local SQLite connection (WAL mode allows concurrent readers)."""
    if not hasattr(_local, "conn"):
        _local.conn = _connect()
    return _local.conn


@contextmanager
def write_cursor():
    """Serialised write transaction. Commits on success, rolls back on error."""
    conn = get_connection()
    with _write_lock:
        cur = conn.cursor()
        try:
            yield cur
            conn.commit()
        except Exception:
            conn.rollback()
            logger.exception("SQLite write failed, transaction rolled back")
            raise
        finally:
            cur.close()


SCHEMA = """
CREATE TABLE IF NOT EXISTS activity_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL DEFAULT 'local',
    app_name TEXT NOT NULL,
    window_title TEXT,
    start_time DATETIME NOT NULL,
    end_time DATETIME,
    duration_seconds INTEGER,
    category TEXT DEFAULT 'uncategorised',
    date DATE NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_activity_logs_date ON activity_logs(date);
CREATE INDEX IF NOT EXISTS idx_activity_logs_user_date ON activity_logs(user_id, date);
CREATE INDEX IF NOT EXISTS idx_activity_logs_app_name ON activity_logs(app_name);

CREATE TABLE IF NOT EXISTS daily_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL DEFAULT 'local',
    date DATE NOT NULL,
    work_start DATETIME,
    work_end DATETIME,
    total_active_seconds INTEGER DEFAULT 0,
    productive_seconds INTEGER DEFAULT 0,
    idle_seconds INTEGER DEFAULT 0,
    focus_score REAL,
    app_switch_count INTEGER DEFAULT 0,
    top_apps_json TEXT,
    top_sites_json TEXT,
    UNIQUE(user_id, date)
);

CREATE INDEX IF NOT EXISTS idx_daily_stats_user_date ON daily_stats(user_id, date);

CREATE TABLE IF NOT EXISTS context_switch_flags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL DEFAULT 'local',
    date DATE NOT NULL,
    window_start DATETIME NOT NULL,
    window_end DATETIME NOT NULL,
    switch_count INTEGER NOT NULL,
    is_high_switching INTEGER NOT NULL DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_context_switch_flags_date ON context_switch_flags(date);

CREATE TABLE IF NOT EXISTS idle_periods (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL DEFAULT 'local',
    start_time DATETIME NOT NULL,
    end_time DATETIME,
    duration_seconds INTEGER,
    date DATE NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_idle_periods_user_date ON idle_periods(user_id, date);

CREATE TABLE IF NOT EXISTS breaks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL DEFAULT 'local',
    start_time DATETIME NOT NULL,
    end_time DATETIME NOT NULL,
    duration_seconds INTEGER NOT NULL,
    break_type TEXT NOT NULL,
    date DATE NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_breaks_user_date ON breaks(user_id, date);

CREATE TABLE IF NOT EXISTS hourly_scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL DEFAULT 'local',
    date DATE NOT NULL,
    hour INTEGER NOT NULL,
    focus_score REAL,
    productive_seconds INTEGER DEFAULT 0,
    total_seconds INTEGER DEFAULT 0,
    switch_count INTEGER DEFAULT 0,
    UNIQUE(user_id, date, hour)
);

CREATE INDEX IF NOT EXISTS idx_hourly_scores_user_date ON hourly_scores(user_id, date);

CREATE TABLE IF NOT EXISTS weekly_trends (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL DEFAULT 'local',
    week_start DATE NOT NULL,
    avg_focus_score REAL,
    total_hours REAL,
    productive_hours REAL,
    trend_direction TEXT,
    UNIQUE(user_id, week_start)
);

CREATE INDEX IF NOT EXISTS idx_weekly_trends_user_week ON weekly_trends(user_id, week_start);

CREATE TABLE IF NOT EXISTS websites (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL DEFAULT 'local',
    url TEXT,
    domain TEXT,
    page_title TEXT,
    start_time DATETIME NOT NULL,
    end_time DATETIME,
    duration_seconds INTEGER,
    category TEXT DEFAULT 'uncategorised',
    date DATE NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_websites_user_date ON websites(user_id, date);
CREATE INDEX IF NOT EXISTS idx_websites_domain ON websites(domain);

-- Report tables: schema owned here so module 5's read routes can exist and
-- respond correctly (empty results, not 500s) ahead of module 7 building
-- the actual Ollama-powered generation logic that populates them.
CREATE TABLE IF NOT EXISTS dar_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL DEFAULT 'local',
    date DATE NOT NULL,
    content TEXT NOT NULL,
    productivity_score REAL,
    total_active_seconds INTEGER,
    productive_seconds INTEGER,
    generated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    emailed_at DATETIME,
    UNIQUE(user_id, date)
);

CREATE INDEX IF NOT EXISTS idx_dar_reports_user_date ON dar_reports(user_id, date);

CREATE TABLE IF NOT EXISTS weekly_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL DEFAULT 'local',
    week_start DATE NOT NULL,
    content TEXT NOT NULL,
    generated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    emailed_at DATETIME,
    UNIQUE(user_id, week_start)
);

CREATE INDEX IF NOT EXISTS idx_weekly_reports_user_week ON weekly_reports(user_id, week_start);

CREATE TABLE IF NOT EXISTS user_patterns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL DEFAULT 'local',
    peak_focus_hours_json TEXT,
    optimal_break_duration INTEGER,
    fragmented_hours_json TEXT,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id)
);

-- Schema owned here (module 8's sender.py needs it to log sends); the
-- lead-loading/RAG-writing orchestration that populates it in bulk belongs
-- to module 19's campaign runner.
CREATE TABLE IF NOT EXISTS campaign_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE NOT NULL,
    time TEXT NOT NULL,
    name TEXT,
    email TEXT NOT NULL,
    company TEXT,
    subject TEXT,
    status TEXT NOT NULL,
    error TEXT,
    follow_up_sent INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_campaign_log_date ON campaign_log(date);
CREATE INDEX IF NOT EXISTS idx_campaign_log_email ON campaign_log(email);

CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL DEFAULT 'local',
    alert_type TEXT NOT NULL,
    message TEXT NOT NULL,
    triggered_at DATETIME NOT NULL,
    dismissed_at DATETIME,
    emailed INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_alerts_user_triggered ON alerts(user_id, triggered_at);

-- Not in DEVELOPMENT.md's section 6 schema reference, but module 14.6
-- ("enabling/disabling each alert type and configuring thresholds")
-- explicitly needs somewhere to persist those preferences.
CREATE TABLE IF NOT EXISTS alert_preferences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL DEFAULT 'local',
    alert_type TEXT NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1,
    threshold_value REAL,
    UNIQUE(user_id, alert_type)
);

-- Admin-controlled per-employee monitoring toggles (separate from
-- alert_preferences above, which an employee sets for themselves). An
-- admin disabling a feature here actually stops that component on the
-- employee's own desktop agent — see agent/app_tracker.py,
-- agent/browser_tracker.py and ai/dar_generator.py, which all check
-- is_feature_enabled() before doing their automatic work.
-- Feasible without any agent<->server network call because the packaged
-- agent and the FastAPI backend already read/write this same SQLite file
-- (see agent/config.py's LOCAL_DB_PATH vs api/config.py's DATABASE_PATH).
CREATE TABLE IF NOT EXISTS feature_flags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL DEFAULT 'local',
    feature TEXT NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1,
    UNIQUE(user_id, feature)
);

-- Schema owned here (module 5's leads route needs it to exist); the
-- Playwright-based discovery that populates it in bulk belongs to module 20.
CREATE TABLE IF NOT EXISTS leads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    company TEXT,
    role TEXT,
    interest TEXT,
    email TEXT,
    notes TEXT,
    last_contact DATETIME,
    source TEXT,
    status TEXT NOT NULL DEFAULT 'new',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_leads_email ON leads(email);
CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status);

-- Added after a real bug: /api/status's "is the agent running" check used
-- MAX(activity_logs.created_at) as its only liveness signal, but a session
-- only gets written to activity_logs once it *closes* (app_tracker.py's
-- session detector) — so staying on one app/window for a long stretch,
-- entirely normal behaviour, made a perfectly healthy agent falsely report
-- "offline" after ~30s. This table is touched on a fixed interval
-- independent of session boundaries, so liveness and "last completed
-- session" are no longer the same (flawed) signal.
CREATE TABLE IF NOT EXISTS agent_heartbeat (
    user_id TEXT PRIMARY KEY,
    last_seen DATETIME NOT NULL
);

-- Module 21.1's multi-user model. Schema owned here so module 5's team
-- routes can exist ahead of module 21's full team dashboard.
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT UNIQUE,
    role TEXT NOT NULL DEFAULT 'employee',
    organisation_id TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Schema owned here (module 5's linkedin route needs it to exist); module
-- 18's Playwright poster is the only thing that populates it.
CREATE TABLE IF NOT EXISTS post_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE NOT NULL,
    time TEXT NOT NULL,
    topic TEXT,
    content TEXT NOT NULL,
    post_id TEXT,
    platform TEXT NOT NULL DEFAULT 'linkedin',
    status TEXT NOT NULL,
    likes INTEGER DEFAULT 0,
    comments INTEGER DEFAULT 0,
    error TEXT
);

CREATE INDEX IF NOT EXISTS idx_post_log_date ON post_log(date);

-- Module 17.3's background job runner state. id is a UUID string, not an
-- autoincrement int, since job ids are handed to the client before any DB
-- row could exist to generate one from.
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    command TEXT NOT NULL,
    action TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'queued',
    progress INTEGER NOT NULL DEFAULT 0,
    logs_json TEXT NOT NULL DEFAULT '[]',
    result TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME
);

CREATE INDEX IF NOT EXISTS idx_jobs_created ON jobs(created_at);

-- Module 7 extension — department-custom DAR templates & structured entries
-- (see DEVELOPMENT.md, "Module 7 extension"). Purely additive: dar_reports/
-- the narrative generator above are untouched by any of this.
CREATE TABLE IF NOT EXISTS departments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- department_id is nullable and UNIQUE-when-present so each department has
-- at most one template; a NULL-department row is the default/base template.
CREATE TABLE IF NOT EXISTS dar_templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    department_id INTEGER UNIQUE REFERENCES departments(id) ON DELETE CASCADE,
    fields_json TEXT NOT NULL DEFAULT '[]',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS dar_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL DEFAULT 'local',
    date DATE NOT NULL,
    department_id INTEGER REFERENCES departments(id) ON DELETE SET NULL,
    task TEXT NOT NULL,
    task_description TEXT,
    start_time DATETIME,
    end_time DATETIME,
    comment TEXT,
    remarks TEXT,
    link TEXT,
    custom_fields_json TEXT NOT NULL DEFAULT '{}',
    source TEXT NOT NULL DEFAULT 'manual',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_dar_entries_user_date ON dar_entries(user_id, date);
CREATE INDEX IF NOT EXISTS idx_dar_entries_department ON dar_entries(department_id);

-- DAR system Layer 1/2 extension: manager-assigned tasks (distinct from
-- dar_entries, which is a per-day activity LOG, not an assignment-with-
-- deadline-and-progress system), plus two new automatic tracker sources.
-- Purely additive — nothing above this comment changes behaviour.
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    assigned_by TEXT,
    department_id INTEGER REFERENCES departments(id) ON DELETE SET NULL,
    project TEXT,
    title TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'not_started',
    progress INTEGER NOT NULL DEFAULT 0,
    priority TEXT NOT NULL DEFAULT 'medium',
    due_date DATE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    completed_at DATETIME
);

CREATE INDEX IF NOT EXISTS idx_tasks_user ON tasks(user_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_due_date ON tasks(due_date);

-- Parsed .ics meetings. UNIQUE(user_id, uid) makes re-parsing the same
-- calendar file idempotent — the tracker upserts, never duplicate-inserts.
CREATE TABLE IF NOT EXISTS calendar_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL DEFAULT 'local',
    uid TEXT,
    subject TEXT NOT NULL,
    organizer TEXT,
    attendees_json TEXT NOT NULL DEFAULT '[]',
    meeting_type TEXT,
    start_time DATETIME NOT NULL,
    end_time DATETIME,
    duration_seconds INTEGER,
    location TEXT,
    date DATE NOT NULL,
    source_file TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, uid)
);

CREATE INDEX IF NOT EXISTS idx_calendar_events_user_date ON calendar_events(user_id, date);

CREATE TABLE IF NOT EXISTS file_activity_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL DEFAULT 'local',
    file_path TEXT NOT NULL,
    event_type TEXT NOT NULL,
    timestamp DATETIME NOT NULL,
    date DATE NOT NULL,
    watched_root TEXT
);

-- Org-wide calendar entries HR/admin declare for everyone — distinct from
-- calendar_events above (that one is per-user, imported meetings). One
-- entry per date: holiday/paid_holiday override that date's attendance
-- status to week_off (see api/routes/attendance.py); event/announcement
-- is purely informational and doesn't affect attendance.
CREATE TABLE IF NOT EXISTS company_holidays (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE NOT NULL UNIQUE,
    title TEXT NOT NULL,
    holiday_type TEXT NOT NULL DEFAULT 'holiday',
    description TEXT,
    created_by TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_company_holidays_date ON company_holidays(date);

-- HR-customisable outbound email formats. One row per template_key
-- (dar_report, alert_focus, alert_distraction, ...) — absent means "use
-- the built-in default" (see automation/email/sender.py's DEFAULT_TEMPLATES),
-- present means HR has overridden it. subject/body use $variable
-- (string.Template) placeholders, substituted at send time.
CREATE TABLE IF NOT EXISTS email_templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    template_key TEXT NOT NULL UNIQUE,
    subject_template TEXT NOT NULL,
    body_template TEXT NOT NULL,
    updated_by TEXT,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_file_activity_logs_user_date ON file_activity_logs(user_id, date);
CREATE INDEX IF NOT EXISTS idx_file_activity_logs_path ON file_activity_logs(file_path);

-- Module 25 — SEO Agentic AI foundation. Purely additive; nothing above
-- this comment changes. seo_sites is the generic site registry (any
-- number of target websites, not hardcoded to one) that every other SEO
-- table below keys off via site_id.
CREATE TABLE IF NOT EXISTS seo_sites (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    base_url TEXT NOT NULL,
    cms_type TEXT NOT NULL DEFAULT 'wordpress',
    cms_base_url TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- One row per pipeline run. UNIQUE(site_id, job_type, run_date) is the
-- idempotency guarantee every SEO pipeline (module 26+) relies on: a
-- retried or overlapping trigger for a run that's already started is
-- rejected as a duplicate rather than double-executing against rate-
-- limited external APIs.
CREATE TABLE IF NOT EXISTS seo_job_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    site_id INTEGER NOT NULL REFERENCES seo_sites(id) ON DELETE CASCADE,
    job_type TEXT NOT NULL,
    run_date DATE NOT NULL,
    status TEXT NOT NULL DEFAULT 'running',
    started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    finished_at DATETIME,
    error TEXT,
    retry_count INTEGER NOT NULL DEFAULT 0,
    UNIQUE(site_id, job_type, run_date)
);

CREATE INDEX IF NOT EXISTS idx_seo_job_runs_site_status ON seo_job_runs(site_id, status);

-- Every ai/llm/factory.py provider call logs one row here regardless of
-- provider (ollama/claude/openai/...) — cost/usage visibility that
-- becomes necessary the moment a paid provider is switched on, which
-- nothing in this codebase tracked before module 25. site_id is nullable
-- since non-SEO LLM calls could in principle route through this layer
-- too in the future; only SEO tasks do today.
CREATE TABLE IF NOT EXISTS llm_usage_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    site_id INTEGER REFERENCES seo_sites(id) ON DELETE SET NULL,
    task TEXT NOT NULL,
    provider TEXT NOT NULL,
    model TEXT,
    tokens_in INTEGER,
    tokens_out INTEGER,
    cost_estimate REAL,
    latency_ms REAL,
    success INTEGER NOT NULL,
    error TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_llm_usage_log_created ON llm_usage_log(created_at);
CREATE INDEX IF NOT EXISTS idx_llm_usage_log_provider ON llm_usage_log(provider);

-- Module 26.4 — PageSpeed Insights pulls. UNIQUE(site_id, url, strategy,
-- run_date) makes re-running the same day's check for the same page
-- idempotent (upsert, not duplicate rows) independent of seo_job_runs'
-- one-row-per-job-per-day tracking, since one job run can check many URLs.
CREATE TABLE IF NOT EXISTS seo_pagespeed_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    site_id INTEGER NOT NULL REFERENCES seo_sites(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    strategy TEXT NOT NULL DEFAULT 'mobile',
    run_date DATE NOT NULL,
    performance_score REAL,
    lcp_ms REAL,
    cls REAL,
    inp_ms REAL,
    ttfb_ms REAL,
    fcp_ms REAL,
    raw_json TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(site_id, url, strategy, run_date)
);

CREATE INDEX IF NOT EXISTS idx_seo_pagespeed_site_date ON seo_pagespeed_results(site_id, run_date);

-- Module 26.5 — GSC Search Analytics pulls. UNIQUE(site_id, run_date,
-- query) makes re-running the same day's pull idempotent (upsert).
CREATE TABLE IF NOT EXISTS seo_gsc_queries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    site_id INTEGER NOT NULL REFERENCES seo_sites(id) ON DELETE CASCADE,
    run_date DATE NOT NULL,
    query TEXT NOT NULL,
    clicks INTEGER NOT NULL DEFAULT 0,
    impressions INTEGER NOT NULL DEFAULT 0,
    ctr REAL,
    position REAL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(site_id, run_date, query)
);

CREATE INDEX IF NOT EXISTS idx_seo_gsc_queries_site_date ON seo_gsc_queries(site_id, run_date);

-- Module 26.6 — GA4 per-page traffic pulls. Same idempotent-upsert shape.
CREATE TABLE IF NOT EXISTS seo_ga4_pages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    site_id INTEGER NOT NULL REFERENCES seo_sites(id) ON DELETE CASCADE,
    run_date DATE NOT NULL,
    page_path TEXT NOT NULL,
    sessions INTEGER NOT NULL DEFAULT 0,
    bounce_rate REAL,
    conversions REAL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(site_id, run_date, page_path)
);

CREATE INDEX IF NOT EXISTS idx_seo_ga4_pages_site_date ON seo_ga4_pages(site_id, run_date);

-- Module 27.3 — Generated OG tags. Stored here rather than pushed
-- straight into CMS meta fields: WordPress's base REST API has no
-- generic OG-tag field (that's normally an SEO plugin's custom meta —
-- Yoast/RankMath — whose exact field names vary per install and weren't
-- guessed at). UNIQUE(site_id, page_url) makes regenerating for the same
-- page idempotent (upsert, latest version wins).
CREATE TABLE IF NOT EXISTS seo_og_tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    site_id INTEGER NOT NULL REFERENCES seo_sites(id) ON DELETE CASCADE,
    page_url TEXT NOT NULL,
    page_title TEXT NOT NULL,
    og_title TEXT NOT NULL,
    og_description TEXT NOT NULL,
    generated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(site_id, page_url)
);

CREATE INDEX IF NOT EXISTS idx_seo_og_tags_site ON seo_og_tags(site_id);

-- Module 28 — Technical SEO detect+approve queue. UNIQUE(site_id, rule,
-- url) means re-running an audit upserts the same row (refreshed
-- message/severity/run_date) rather than piling up duplicates, and —
-- critically — the upsert (see upsert_technical_issues below) never
-- touches `status`, so a human's approve/reject decision on a
-- still-unresolved issue survives the next day's re-audit instead of
-- silently reverting to 'pending'.
CREATE TABLE IF NOT EXISTS seo_technical_issues (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    site_id INTEGER NOT NULL REFERENCES seo_sites(id) ON DELETE CASCADE,
    run_date DATE NOT NULL,
    rule TEXT NOT NULL,
    severity TEXT NOT NULL,
    url TEXT NOT NULL,
    message TEXT NOT NULL,
    suggested_fix TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    reviewed_at DATETIME,
    reviewed_by TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(site_id, rule, url)
);

CREATE INDEX IF NOT EXISTS idx_seo_technical_issues_site_status ON seo_technical_issues(site_id, status);

-- Module 29 — Daily digest archive. UNIQUE(site_id, run_date) makes
-- regenerating today's digest idempotent (upsert, latest version wins)
-- rather than piling up duplicates from a re-triggered run.
CREATE TABLE IF NOT EXISTS seo_daily_digests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    site_id INTEGER NOT NULL REFERENCES seo_sites(id) ON DELETE CASCADE,
    run_date DATE NOT NULL,
    narrative TEXT NOT NULL,
    stats_json TEXT NOT NULL,
    slack_delivered INTEGER NOT NULL DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(site_id, run_date)
);

CREATE INDEX IF NOT EXISTS idx_seo_daily_digests_site ON seo_daily_digests(site_id);

-- Module 30 — Social media content calendar + approval queue. Real
-- automated posting exists only for LinkedIn (reusing module 18's
-- Playwright automation, already tested against a real browser flow);
-- Twitter/Instagram/Facebook stay in 'draft'/'approved' status for a
-- human to post manually — no tested automation exists for those
-- platforms in this codebase, and this table deliberately doesn't
-- pretend otherwise.
CREATE TABLE IF NOT EXISTS seo_social_posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    site_id INTEGER NOT NULL REFERENCES seo_sites(id) ON DELETE CASCADE,
    platform TEXT NOT NULL,
    source_url TEXT,
    content TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft',
    external_post_id TEXT,
    error TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    posted_at DATETIME
);

CREATE INDEX IF NOT EXISTS idx_seo_social_posts_site_status ON seo_social_posts(site_id, status);

-- Module 31 — Backlink/brand-mention monitoring. UNIQUE(site_id,
-- source_url) makes re-polling the same feed idempotent (a mention seen
-- again on a later poll doesn't duplicate). outreach_subject/body are
-- filled in lazily (only once a human asks for a draft), not on ingest.
CREATE TABLE IF NOT EXISTS seo_backlink_mentions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    site_id INTEGER NOT NULL REFERENCES seo_sites(id) ON DELETE CASCADE,
    source_url TEXT NOT NULL,
    source_title TEXT,
    anchor_text TEXT,
    domain_rating REAL,
    discovered_at TEXT,
    outreach_subject TEXT,
    outreach_body TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(site_id, source_url)
);

CREATE INDEX IF NOT EXISTS idx_seo_backlink_mentions_site ON seo_backlink_mentions(site_id);

-- Indexing Status & Crawl Monitoring — the blueprint feature that was
-- honestly incomplete (only GSC's rank/query data existed, not index
-- coverage). UNIQUE(site_id, url) makes re-inspecting the same URL
-- idempotent (upsert, latest inspection wins) via GSC's real
-- urlInspection.index:inspect endpoint (automation/seo/indexing_client.py).
CREATE TABLE IF NOT EXISTS seo_index_status (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    site_id INTEGER NOT NULL REFERENCES seo_sites(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    coverage_state TEXT,
    indexing_state TEXT,
    robots_txt_state TEXT,
    page_fetch_state TEXT,
    last_crawl_time TEXT,
    google_canonical TEXT,
    user_canonical TEXT,
    sitemap_json TEXT,
    checked_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(site_id, url)
);

CREATE INDEX IF NOT EXISTS idx_seo_index_status_site ON seo_index_status(site_id);

-- Indexing API submission history — a call log, not upserted (each
-- submit attempt is its own real event worth keeping, e.g. to see how
-- often a URL is being re-submitted). Uses Google's real Indexing API
-- (indexing.googleapis.com), which is documented for JobPosting/
-- BroadcastEvent content — see indexing_client.py's module docstring for
-- the honest caveat about using it for general pages.
CREATE TABLE IF NOT EXISTS seo_indexing_submissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    site_id INTEGER NOT NULL REFERENCES seo_sites(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    notification_type TEXT NOT NULL,
    success INTEGER NOT NULL DEFAULT 0,
    response_json TEXT,
    error TEXT,
    submitted_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_seo_indexing_submissions_site ON seo_indexing_submissions(site_id);

-- Module 34 — Blog post generation + CMS draft publishing. Same
-- draft/approved/rejected review queue shape as seo_social_posts (module
-- 30), extended with the fields a full post needs (excerpt, primary
-- keyword) and structure_passed/structure_issues_json so a reviewer sees
-- content_structure.py's own H1/word-count/keyword checks (module 27.5)
-- right next to the draft, not as a separate manual step. status is
-- 'published' once pushed to the CMS as a real draft post there — that
-- word means two different things at two different layers on purpose:
-- 'published' here means "exists in the CMS", the CMS's own post status
-- stays 'draft' until a human publishes it for real (see automation/seo/
-- cms/base.py's create_post — publishing straight to a live site with no
-- second human checkpoint was deliberately ruled out for this module).
CREATE TABLE IF NOT EXISTS seo_blog_posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    site_id INTEGER NOT NULL REFERENCES seo_sites(id) ON DELETE CASCADE,
    topic TEXT NOT NULL,
    primary_keyword TEXT,
    title TEXT NOT NULL,
    excerpt TEXT,
    content TEXT NOT NULL,
    structure_passed INTEGER,
    structure_issues_json TEXT,
    status TEXT NOT NULL DEFAULT 'draft',
    cms_post_id TEXT,
    cms_post_link TEXT,
    error TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    published_at DATETIME
);

CREATE INDEX IF NOT EXISTS idx_seo_blog_posts_site_status ON seo_blog_posts(site_id, status);
"""

# Columns added after the initial daily_stats design (module 2.6 — longest
# focus session). ALTER TABLE ADD COLUMN keeps existing rows/data intact.
_DAILY_STATS_EXTRA_COLUMNS = {
    "longest_focus_start": "DATETIME",
    "longest_focus_end": "DATETIME",
    "longest_focus_seconds": "INTEGER DEFAULT 0",
}

# Login/logout + role-based access (added after module 21's users table —
# see DEVELOPMENT.md's "Login & Role-Based Access" section). NULL
# password_hash means the account can't log in yet (e.g. rows created by
# module 21's team-management UI before this feature existed).
_USERS_EXTRA_COLUMNS = {
    "password_hash": "TEXT",
}

# DAR system extension — Project/Status/Progress as first-class columns
# (previously only expressible per-department via custom_fields_json),
# plus an optional link back to an assigned tasks row. ALTER TABLE ADD
# COLUMN keeps every existing dar_entries row intact; status defaults to
# "in_progress" rather than "not_started" since an existing logged entry
# already represents work that happened, not an unstarted assignment.
_DAR_ENTRIES_EXTRA_COLUMNS = {
    "project": "TEXT",
    "status": "TEXT NOT NULL DEFAULT 'in_progress'",
    "progress": "INTEGER NOT NULL DEFAULT 0",
    "task_id": "INTEGER REFERENCES tasks(id) ON DELETE SET NULL",
}

# GSC/GA4 were originally one global .env value (GSC_SITE_URL,
# GA4_PROPERTY_ID) shared by every seo_sites row — fine for the single
# verified test property module 26.5/26.6 shipped with, but it meant
# switching to a second real site required editing .env and restarting
# the backend every time. Storing them per-site instead lets each site
# carry its own verified Search Console property / Analytics property.
# NULL here means "fall back to the .env value" (automation/seo/
# gsc_client.py, ga4_client.py, indexing_client.py all do this), so the
# existing test site keeps working with zero migration action needed.
_SEO_SITES_EXTRA_COLUMNS = {
    "gsc_site_url": "TEXT",
    "ga4_property_id": "TEXT",
    # CMS publishing credentials (module 34.2) — same "NULL means fall
    # back to .env, but only when unambiguous" story as gsc_site_url/
    # ga4_property_id above. cms_base_url already existed (module 26.1,
    # for a CMS admin URL that differs from the site's public base_url);
    # these four are new. WordPress uses username/app_password; Webflow
    # uses api_token/collection_id — each site only ever fills in the
    # pair matching its own cms_type.
    "cms_username": "TEXT",
    "cms_app_password": "TEXT",
    "cms_api_token": "TEXT",
    "cms_collection_id": "TEXT",
}


def _ensure_extra_columns(conn: sqlite3.Connection, table: str, columns: dict) -> None:
    existing = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
    for column, coltype in columns.items():
        if column not in existing:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {coltype}")


def init_db() -> None:
    """Create all tables/indexes this agent module needs. Safe to call repeatedly."""
    conn = get_connection()
    with _write_lock:
        try:
            conn.executescript(SCHEMA)
            _ensure_extra_columns(conn, "daily_stats", _DAILY_STATS_EXTRA_COLUMNS)
            _ensure_extra_columns(conn, "users", _USERS_EXTRA_COLUMNS)
            # tasks already exists by this point (created above in SCHEMA),
            # so the task_id column's FK reference resolves correctly.
            _ensure_extra_columns(conn, "dar_entries", _DAR_ENTRIES_EXTRA_COLUMNS)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_dar_entries_task ON dar_entries(task_id)")
            _ensure_extra_columns(conn, "seo_sites", _SEO_SITES_EXTRA_COLUMNS)
            conn.commit()
            logger.info("Local SQLite schema ready at %s", LOCAL_DB_PATH)
        except Exception:
            conn.rollback()
            logger.exception("Failed to initialise local SQLite schema")
            raise


# ── activity_logs ──

def insert_activity_session(
    app_name: str,
    window_title: Optional[str],
    start_time: datetime,
    end_time: datetime,
    user_id: str = "local",
) -> int:
    """Persist one completed app session. Returns the new row id."""
    duration_seconds = max(0, int((end_time - start_time).total_seconds()))
    session_date = start_time.date().isoformat()
    with write_cursor() as cur:
        cur.execute(
            """
            INSERT INTO activity_logs
                (user_id, app_name, window_title, start_time, end_time,
                 duration_seconds, date, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                app_name,
                window_title,
                start_time.isoformat(sep=" "),
                end_time.isoformat(sep=" "),
                duration_seconds,
                session_date,
                datetime.now().isoformat(sep=" "),
            ),
        )
        return cur.lastrowid


def touch_heartbeat(user_id: str = "local") -> None:
    """Called on a fixed interval by AppTracker's poll loop, independent of
    whether the active app/window has changed — see agent_heartbeat's
    schema comment for why this can't just reuse activity_logs."""
    now = datetime.now().isoformat(sep=" ")
    with write_cursor() as cur:
        cur.execute(
            """
            INSERT INTO agent_heartbeat (user_id, last_seen) VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET last_seen = excluded.last_seen
            """,
            (user_id, now),
        )


# ── daily_stats ──

def ensure_daily_stats_row(day: date_cls, user_id: str = "local") -> None:
    with write_cursor() as cur:
        cur.execute(
            """
            INSERT OR IGNORE INTO daily_stats (user_id, date, app_switch_count)
            VALUES (?, ?, 0)
            """,
            (user_id, day.isoformat()),
        )


def increment_app_switch_count(day: date_cls, user_id: str = "local") -> int:
    """Increment today's switch counter (module 1.4). Returns the new count."""
    ensure_daily_stats_row(day, user_id)
    with write_cursor() as cur:
        cur.execute(
            """
            UPDATE daily_stats
            SET app_switch_count = app_switch_count + 1
            WHERE user_id = ? AND date = ?
            """,
            (user_id, day.isoformat()),
        )
        cur.execute(
            "SELECT app_switch_count FROM daily_stats WHERE user_id = ? AND date = ?",
            (user_id, day.isoformat()),
        )
        row = cur.fetchone()
        return row["app_switch_count"] if row else 0


def get_daily_switch_count(day: date_cls, user_id: str = "local") -> int:
    conn = get_connection()
    row = conn.execute(
        "SELECT app_switch_count FROM daily_stats WHERE user_id = ? AND date = ?",
        (user_id, day.isoformat()),
    ).fetchone()
    return row["app_switch_count"] if row else 0


def set_work_start_if_unset(day: date_cls, at: datetime, user_id: str = "local") -> None:
    """2.2 — record check-in for the day, once, without overwriting it.
    Called by app_tracker.py's check-in trigger the first time the active
    window matches CHECK_IN_APP_KEYWORDS (e.g. opening Zoho), not on the
    day's first general keyboard/mouse input."""
    ensure_daily_stats_row(day, user_id)
    with write_cursor() as cur:
        cur.execute(
            """
            UPDATE daily_stats SET work_start = ?
            WHERE user_id = ? AND date = ? AND work_start IS NULL
            """,
            (at.isoformat(sep=" "), user_id, day.isoformat()),
        )


def set_work_end(day: date_cls, at: datetime, user_id: str = "local") -> None:
    """2.2 — record the last input before a qualifying (>=15min) idle period."""
    ensure_daily_stats_row(day, user_id)
    with write_cursor() as cur:
        cur.execute(
            "UPDATE daily_stats SET work_end = ? WHERE user_id = ? AND date = ?",
            (at.isoformat(sep=" "), user_id, day.isoformat()),
        )


def update_daily_idle_seconds(day: date_cls, added_seconds: int, user_id: str = "local") -> None:
    ensure_daily_stats_row(day, user_id)
    with write_cursor() as cur:
        cur.execute(
            """
            UPDATE daily_stats SET idle_seconds = idle_seconds + ?
            WHERE user_id = ? AND date = ?
            """,
            (added_seconds, user_id, day.isoformat()),
        )


def set_longest_focus_session(
    day: date_cls, start: datetime, end: datetime, duration_seconds: int, user_id: str = "local"
) -> None:
    ensure_daily_stats_row(day, user_id)
    with write_cursor() as cur:
        cur.execute(
            """
            UPDATE daily_stats
            SET longest_focus_start = ?, longest_focus_end = ?, longest_focus_seconds = ?
            WHERE user_id = ? AND date = ?
            """,
            (start.isoformat(sep=" "), end.isoformat(sep=" "), duration_seconds, user_id, day.isoformat()),
        )


def set_daily_focus_score(
    day: date_cls, focus_score: float, productive_seconds: int, total_active_seconds: int,
    user_id: str = "local",
) -> None:
    ensure_daily_stats_row(day, user_id)
    with write_cursor() as cur:
        cur.execute(
            """
            UPDATE daily_stats
            SET focus_score = ?, productive_seconds = ?, total_active_seconds = ?
            WHERE user_id = ? AND date = ?
            """,
            (focus_score, productive_seconds, total_active_seconds, user_id, day.isoformat()),
        )


# ── idle_periods ──

def insert_idle_period(
    start_time: datetime, end_time: datetime, user_id: str = "local"
) -> int:
    duration_seconds = max(0, int((end_time - start_time).total_seconds()))
    with write_cursor() as cur:
        cur.execute(
            """
            INSERT INTO idle_periods (user_id, start_time, end_time, duration_seconds, date)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                user_id,
                start_time.isoformat(sep=" "),
                end_time.isoformat(sep=" "),
                duration_seconds,
                start_time.date().isoformat(),
            ),
        )
        return cur.lastrowid


# ── breaks ──

def insert_break(
    start_time: datetime, end_time: datetime, break_type: str, user_id: str = "local"
) -> int:
    duration_seconds = max(0, int((end_time - start_time).total_seconds()))
    with write_cursor() as cur:
        cur.execute(
            """
            INSERT INTO breaks (user_id, start_time, end_time, duration_seconds, break_type, date)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                start_time.isoformat(sep=" "),
                end_time.isoformat(sep=" "),
                duration_seconds,
                break_type,
                start_time.date().isoformat(),
            ),
        )
        return cur.lastrowid


# ── hourly_scores ──

def upsert_hourly_score(
    day: date_cls,
    hour: int,
    focus_score: Optional[float],
    productive_seconds: int,
    total_seconds: int,
    switch_count: int,
    user_id: str = "local",
) -> None:
    with write_cursor() as cur:
        cur.execute(
            """
            INSERT INTO hourly_scores
                (user_id, date, hour, focus_score, productive_seconds, total_seconds, switch_count)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, date, hour) DO UPDATE SET
                focus_score = excluded.focus_score,
                productive_seconds = excluded.productive_seconds,
                total_seconds = excluded.total_seconds,
                switch_count = excluded.switch_count
            """,
            (user_id, day.isoformat(), hour, focus_score, productive_seconds, total_seconds, switch_count),
        )


# ── weekly_trends ──

def upsert_weekly_trend(
    week_start: date_cls,
    avg_focus_score: Optional[float],
    total_hours: float,
    productive_hours: float,
    trend_direction: str,
    user_id: str = "local",
) -> None:
    with write_cursor() as cur:
        cur.execute(
            """
            INSERT INTO weekly_trends
                (user_id, week_start, avg_focus_score, total_hours, productive_hours, trend_direction)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, week_start) DO UPDATE SET
                avg_focus_score = excluded.avg_focus_score,
                total_hours = excluded.total_hours,
                productive_hours = excluded.productive_hours,
                trend_direction = excluded.trend_direction
            """,
            (user_id, week_start.isoformat(), avg_focus_score, total_hours, productive_hours, trend_direction),
        )


# ── context_switch_flags ──

def insert_context_switch_flag(
    day: date_cls,
    window_start: datetime,
    window_end: datetime,
    switch_count: int,
    is_high_switching: bool,
    user_id: str = "local",
) -> int:
    with write_cursor() as cur:
        cur.execute(
            """
            INSERT INTO context_switch_flags
                (user_id, date, window_start, window_end, switch_count, is_high_switching, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                day.isoformat(),
                window_start.isoformat(sep=" "),
                window_end.isoformat(sep=" "),
                switch_count,
                1 if is_high_switching else 0,
                datetime.now().isoformat(sep=" "),
            ),
        )
        return cur.lastrowid


# ── websites ──

def insert_website_session(
    url: Optional[str],
    domain: Optional[str],
    page_title: Optional[str],
    start_time: datetime,
    end_time: datetime,
    user_id: str = "local",
) -> int:
    duration_seconds = max(0, int((end_time - start_time).total_seconds()))
    with write_cursor() as cur:
        cur.execute(
            """
            INSERT INTO websites
                (user_id, url, domain, page_title, start_time, end_time, duration_seconds, date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                url,
                domain,
                page_title,
                start_time.isoformat(sep=" "),
                end_time.isoformat(sep=" "),
                duration_seconds,
                start_time.date().isoformat(),
            ),
        )
        return cur.lastrowid


def get_top_sites_for_date(day: date_cls, user_id: str = "local", limit: int = 10):
    """4.5 — ranked list of domains by total time spent, for the given day."""
    conn = get_connection()
    return conn.execute(
        """
        SELECT domain, SUM(duration_seconds) AS total_seconds, COUNT(*) AS visits
        FROM websites
        WHERE user_id = ? AND date = ? AND domain IS NOT NULL
        GROUP BY domain
        ORDER BY total_seconds DESC
        LIMIT ?
        """,
        (user_id, day.isoformat(), limit),
    ).fetchall()


def set_daily_top_sites_json(day: date_cls, top_sites_json: str, user_id: str = "local") -> None:
    ensure_daily_stats_row(day, user_id)
    with write_cursor() as cur:
        cur.execute(
            "UPDATE daily_stats SET top_sites_json = ? WHERE user_id = ? AND date = ?",
            (top_sites_json, user_id, day.isoformat()),
        )


# ── user_patterns ──

def upsert_user_patterns(
    user_id: str = "local",
    peak_focus_hours_json: Optional[str] = None,
    optimal_break_duration: Optional[int] = None,
    fragmented_hours_json: Optional[str] = None,
) -> None:
    now = datetime.now().isoformat(sep=" ")
    with write_cursor() as cur:
        cur.execute(
            """
            INSERT INTO user_patterns
                (user_id, peak_focus_hours_json, optimal_break_duration, fragmented_hours_json, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                peak_focus_hours_json = COALESCE(excluded.peak_focus_hours_json, user_patterns.peak_focus_hours_json),
                optimal_break_duration = COALESCE(excluded.optimal_break_duration, user_patterns.optimal_break_duration),
                fragmented_hours_json = COALESCE(excluded.fragmented_hours_json, user_patterns.fragmented_hours_json),
                updated_at = excluded.updated_at
            """,
            (user_id, peak_focus_hours_json, optimal_break_duration, fragmented_hours_json, now),
        )


def get_user_patterns(user_id: str = "local"):
    conn = get_connection()
    return conn.execute(
        "SELECT * FROM user_patterns WHERE user_id = ?", (user_id,)
    ).fetchone()


# ── dar_reports ──

def upsert_dar_report(
    day: date_cls,
    content: str,
    productivity_score: Optional[float],
    total_active_seconds: int,
    productive_seconds: int,
    user_id: str = "local",
) -> int:
    now = datetime.now().isoformat(sep=" ")
    with write_cursor() as cur:
        cur.execute(
            """
            INSERT INTO dar_reports
                (user_id, date, content, productivity_score, total_active_seconds, productive_seconds, generated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, date) DO UPDATE SET
                content = excluded.content,
                productivity_score = excluded.productivity_score,
                total_active_seconds = excluded.total_active_seconds,
                productive_seconds = excluded.productive_seconds,
                generated_at = excluded.generated_at
            """,
            (user_id, day.isoformat(), content, productivity_score, total_active_seconds, productive_seconds, now),
        )
        row = cur.execute(
            "SELECT id FROM dar_reports WHERE user_id = ? AND date = ?", (user_id, day.isoformat())
        ).fetchone()
        return row["id"]


# ── tasks (manager-assigned work, distinct from dar_entries' daily log) ──

def insert_task(
    user_id: str,
    title: str,
    assigned_by: Optional[str] = None,
    department_id: Optional[int] = None,
    project: Optional[str] = None,
    description: Optional[str] = None,
    priority: str = "medium",
    due_date: Optional[date_cls] = None,
) -> int:
    with write_cursor() as cur:
        cur.execute(
            """
            INSERT INTO tasks
                (user_id, assigned_by, department_id, project, title, description, priority, due_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id, assigned_by, department_id, project, title, description,
                priority, due_date.isoformat() if due_date else None,
            ),
        )
        return cur.lastrowid


def get_task(task_id: int):
    conn = get_connection()
    return conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()


def get_tasks_for_user(user_id: str, status: Optional[str] = None):
    conn = get_connection()
    if status:
        return conn.execute(
            "SELECT * FROM tasks WHERE user_id = ? AND status = ? ORDER BY due_date IS NULL, due_date ASC",
            (user_id, status),
        ).fetchall()
    return conn.execute(
        "SELECT * FROM tasks WHERE user_id = ? ORDER BY due_date IS NULL, due_date ASC", (user_id,)
    ).fetchall()


def update_task(task_id: int, **fields) -> None:
    if not fields:
        return
    fields["updated_at"] = datetime.now().isoformat(sep=" ")
    if fields.get("status") == "completed" and "completed_at" not in fields:
        fields["completed_at"] = datetime.now().isoformat(sep=" ")
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    with write_cursor() as cur:
        cur.execute(f"UPDATE tasks SET {set_clause} WHERE id = ?", (*fields.values(), task_id))


def delete_task(task_id: int) -> None:
    with write_cursor() as cur:
        cur.execute("DELETE FROM tasks WHERE id = ?", (task_id,))


# ── calendar_events (Layer 1 — .ics tracker) ──

def upsert_calendar_event(
    user_id: str,
    uid: Optional[str],
    subject: str,
    start_time: datetime,
    end_time: Optional[datetime] = None,
    organizer: Optional[str] = None,
    attendees_json: str = "[]",
    location: Optional[str] = None,
    source_file: Optional[str] = None,
) -> None:
    duration_seconds = (
        max(0, int((end_time - start_time).total_seconds())) if end_time else None
    )
    with write_cursor() as cur:
        cur.execute(
            """
            INSERT INTO calendar_events
                (user_id, uid, subject, organizer, attendees_json, start_time, end_time,
                 duration_seconds, location, date, source_file)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, uid) DO UPDATE SET
                subject = excluded.subject,
                organizer = excluded.organizer,
                attendees_json = excluded.attendees_json,
                start_time = excluded.start_time,
                end_time = excluded.end_time,
                duration_seconds = excluded.duration_seconds,
                location = excluded.location,
                source_file = excluded.source_file
            """,
            (
                user_id, uid, subject, organizer, attendees_json,
                start_time.isoformat(sep=" "), end_time.isoformat(sep=" ") if end_time else None,
                duration_seconds, location, start_time.date().isoformat(), source_file,
            ),
        )


def get_calendar_events_for_date(day: date_cls, user_id: str = "local"):
    conn = get_connection()
    return conn.execute(
        "SELECT * FROM calendar_events WHERE user_id = ? AND date = ? ORDER BY start_time ASC",
        (user_id, day.isoformat()),
    ).fetchall()


def get_calendar_events_overlapping(start: datetime, end: datetime, user_id: str = "local"):
    """Meetings with a real end_time whose [start_time, end_time) window
    overlaps [start, end) at all — used to check whether an idle period
    happened during a scheduled meeting. Events are stored keyed by their
    own start date, so an idle window is only ever checked against that
    date's (and, for a rare midnight-spanning idle period, the next date's)
    rows rather than the whole table."""
    conn = get_connection()
    dates = {start.date().isoformat(), end.date().isoformat()}
    placeholders = ",".join("?" for _ in dates)
    rows = conn.execute(
        f"""
        SELECT * FROM calendar_events
        WHERE user_id = ? AND date IN ({placeholders}) AND end_time IS NOT NULL
        ORDER BY start_time ASC
        """,
        (user_id, *dates),
    ).fetchall()
    return [
        r for r in rows
        if datetime.fromisoformat(r["start_time"]) < end and datetime.fromisoformat(r["end_time"]) > start
    ]


# ── file_activity_logs (Layer 1 — file watcher) ──

def insert_file_activity(
    file_path: str,
    event_type: str,
    timestamp: datetime,
    watched_root: Optional[str] = None,
    user_id: str = "local",
) -> int:
    with write_cursor() as cur:
        cur.execute(
            """
            INSERT INTO file_activity_logs (user_id, file_path, event_type, timestamp, date, watched_root)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_id, file_path, event_type, timestamp.isoformat(sep=" "), timestamp.date().isoformat(), watched_root),
        )
        return cur.lastrowid


def get_file_activity_for_date(day: date_cls, user_id: str = "local"):
    conn = get_connection()
    return conn.execute(
        "SELECT * FROM file_activity_logs WHERE user_id = ? AND date = ? ORDER BY timestamp ASC",
        (user_id, day.isoformat()),
    ).fetchall()


# ── alerts ──

def insert_alert(alert_type: str, message: str, triggered_at: datetime, user_id: str = "local") -> int:
    with write_cursor() as cur:
        cur.execute(
            """
            INSERT INTO alerts (user_id, alert_type, message, triggered_at, emailed)
            VALUES (?, ?, ?, ?, 0)
            """,
            (user_id, alert_type, message, triggered_at.isoformat(sep=" ")),
        )
        return cur.lastrowid


def mark_alert_emailed(alert_id: int) -> None:
    with write_cursor() as cur:
        cur.execute("UPDATE alerts SET emailed = 1 WHERE id = ?", (alert_id,))


def dismiss_alert(alert_id: int) -> None:
    with write_cursor() as cur:
        cur.execute(
            "UPDATE alerts SET dismissed_at = ? WHERE id = ?",
            (datetime.now().isoformat(sep=" "), alert_id),
        )


def get_recent_alerts(user_id: str = "local", limit: int = 50):
    conn = get_connection()
    return conn.execute(
        "SELECT * FROM alerts WHERE user_id = ? ORDER BY triggered_at DESC LIMIT ?",
        (user_id, limit),
    ).fetchall()


def get_last_alert_of_type(alert_type: str, user_id: str = "local"):
    conn = get_connection()
    return conn.execute(
        """
        SELECT * FROM alerts WHERE user_id = ? AND alert_type = ?
        ORDER BY triggered_at DESC LIMIT 1
        """,
        (user_id, alert_type),
    ).fetchone()


# ── alert_preferences ──

DEFAULT_ALERT_TYPES = ("focus", "distraction", "wellbeing", "manager", "late_arrival", "holiday_announcement")


def get_alert_preferences(user_id: str = "local"):
    conn = get_connection()
    rows = {
        r["alert_type"]: r
        for r in conn.execute("SELECT * FROM alert_preferences WHERE user_id = ?", (user_id,)).fetchall()
    }
    # Any alert type without a stored row is enabled by default.
    return {
        alert_type: {
            "enabled": bool(rows[alert_type]["enabled"]) if alert_type in rows else True,
            "threshold_value": rows[alert_type]["threshold_value"] if alert_type in rows else None,
        }
        for alert_type in DEFAULT_ALERT_TYPES
    }


def is_alert_enabled(alert_type: str, user_id: str = "local") -> bool:
    conn = get_connection()
    row = conn.execute(
        "SELECT enabled FROM alert_preferences WHERE user_id = ? AND alert_type = ?",
        (user_id, alert_type),
    ).fetchone()
    return bool(row["enabled"]) if row else True


def set_alert_preference(alert_type: str, enabled: bool, threshold_value: Optional[float] = None, user_id: str = "local") -> None:
    with write_cursor() as cur:
        cur.execute(
            """
            INSERT INTO alert_preferences (user_id, alert_type, enabled, threshold_value)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, alert_type) DO UPDATE SET
                enabled = excluded.enabled,
                threshold_value = COALESCE(excluded.threshold_value, alert_preferences.threshold_value)
            """,
            (user_id, alert_type, 1 if enabled else 0, threshold_value),
        )


# ── company_holidays — HR/admin-declared org-wide calendar entries ──

def insert_company_holiday(
    day: date_cls, title: str, holiday_type: str, description: Optional[str], created_by: str
) -> int:
    with write_cursor() as cur:
        cur.execute(
            """
            INSERT INTO company_holidays (date, title, holiday_type, description, created_by)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(date) DO UPDATE SET
                title = excluded.title,
                holiday_type = excluded.holiday_type,
                description = excluded.description,
                created_by = excluded.created_by
            """,
            (day.isoformat(), title, holiday_type, description, created_by),
        )
        row = cur.execute("SELECT id FROM company_holidays WHERE date = ?", (day.isoformat(),)).fetchone()
        return row["id"]


def list_company_holidays(start: date_cls, end: date_cls):
    conn = get_connection()
    return conn.execute(
        "SELECT * FROM company_holidays WHERE date >= ? AND date <= ? ORDER BY date ASC",
        (start.isoformat(), end.isoformat()),
    ).fetchall()


def delete_company_holiday(holiday_id: int) -> None:
    with write_cursor() as cur:
        cur.execute("DELETE FROM company_holidays WHERE id = ?", (holiday_id,))


# ── email_templates — HR-customisable outbound email formats ──

def get_email_template(template_key: str):
    conn = get_connection()
    return conn.execute(
        "SELECT * FROM email_templates WHERE template_key = ?", (template_key,)
    ).fetchone()


def list_email_templates():
    conn = get_connection()
    return conn.execute("SELECT * FROM email_templates").fetchall()


def set_email_template(template_key: str, subject_template: str, body_template: str, updated_by: str) -> None:
    with write_cursor() as cur:
        cur.execute(
            """
            INSERT INTO email_templates (template_key, subject_template, body_template, updated_by, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(template_key) DO UPDATE SET
                subject_template = excluded.subject_template,
                body_template = excluded.body_template,
                updated_by = excluded.updated_by,
                updated_at = CURRENT_TIMESTAMP
            """,
            (template_key, subject_template, body_template, updated_by),
        )


def reset_email_template(template_key: str) -> None:
    with write_cursor() as cur:
        cur.execute("DELETE FROM email_templates WHERE template_key = ?", (template_key,))


# ── feature_flags — admin-controlled per-employee monitoring toggles ──

DEFAULT_FEATURE_TYPES = (
    "activity_tracking", "dar_generation", "alerts_enabled",
    "calendar_sync", "file_activity_tracking",
)


def get_feature_flags(user_id: str = "local") -> dict:
    conn = get_connection()
    rows = {
        r["feature"]: r
        for r in conn.execute("SELECT * FROM feature_flags WHERE user_id = ?", (user_id,)).fetchall()
    }
    # Any feature without a stored row is enabled by default.
    return {
        feature: bool(rows[feature]["enabled"]) if feature in rows else True
        for feature in DEFAULT_FEATURE_TYPES
    }


def is_feature_enabled(feature: str, user_id: str = "local") -> bool:
    conn = get_connection()
    row = conn.execute(
        "SELECT enabled FROM feature_flags WHERE user_id = ? AND feature = ?",
        (user_id, feature),
    ).fetchone()
    return bool(row["enabled"]) if row else True


def set_feature_flag(feature: str, enabled: bool, user_id: str = "local") -> None:
    with write_cursor() as cur:
        cur.execute(
            """
            INSERT INTO feature_flags (user_id, feature, enabled)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, feature) DO UPDATE SET enabled = excluded.enabled
            """,
            (user_id, feature, 1 if enabled else 0),
        )


# ── seo_sites — module 25 ──
# Creation/listing for the dashboard lives in api/routes/seo.py via
# SQLAlchemy (simple, request-driven CRUD — same pattern as
# departments.py). This one read helper exists for background/agent code
# (ai/seo_master_agent.py's planning node) that has no FastAPI request
# session to work with, mirroring how ai/master_agent.py's planning_node
# reads dar_reports straight off agent.database.get_connection().

def get_active_seo_sites():
    conn = get_connection()
    return conn.execute("SELECT * FROM seo_sites WHERE is_active = 1 ORDER BY id").fetchall()


def count_active_seo_sites() -> int:
    """Callers use this to decide whether falling back to the global
    GSC_SITE_URL/GA4_PROPERTY_ID .env values is safe: unambiguous when
    there's exactly one active site (that's who the .env value describes),
    unsafe the moment a second site exists — verified live that it isn't
    just a theoretical risk: with two active sites and no per-site
    override, gsc_pull/ga4_pull for the second site silently pulled and
    stored the FIRST site's real analytics under the second site's id,
    reporting "success" the whole time. See gsc_client.py/ga4_client.py's
    fetch_search_analytics/fetch_traffic_by_page callers."""
    conn = get_connection()
    row = conn.execute("SELECT COUNT(*) AS n FROM seo_sites WHERE is_active = 1").fetchone()
    return row["n"]


# ── seo_job_runs — module 25: pipeline idempotency + audit trail ──
# Job runs and LLM usage are written from background/pipeline code
# (module 26+ schedulers, ai/llm/factory.py), so they follow the
# raw-sqlite write_cursor() convention every other automation log
# (post_log, campaign_log) uses.

def start_job_run(site_id: int, job_type: str, run_date: date_cls) -> Optional[int]:
    """Begins tracking one pipeline run. Returns the new seo_job_runs row
    id, or None if a run for this (site_id, job_type, run_date) already
    exists. A duplicate trigger is routine (a scheduler tick landing
    twice, a manual re-trigger) rather than an error, so it's checked for
    up front to keep logs quiet in the common case; the UNIQUE constraint
    (caught below) remains the real correctness guarantee against a
    concurrent race between the check and the insert."""
    conn = get_connection()
    existing = conn.execute(
        "SELECT id FROM seo_job_runs WHERE site_id = ? AND job_type = ? AND run_date = ?",
        (site_id, job_type, run_date.isoformat()),
    ).fetchone()
    if existing is not None:
        logger.info(
            "seo_job_runs duplicate rejected: site_id=%s job_type=%s run_date=%s",
            site_id, job_type, run_date,
        )
        return None

    try:
        with write_cursor() as cur:
            cur.execute(
                "INSERT INTO seo_job_runs (site_id, job_type, run_date, status) VALUES (?, ?, ?, 'running')",
                (site_id, job_type, run_date.isoformat()),
            )
            return cur.lastrowid
    except sqlite3.IntegrityError:
        # Lost a race against a concurrent start_job_run() for the same
        # key between the SELECT above and this INSERT — rare, but the
        # UNIQUE constraint is what actually guarantees no double-run.
        logger.info(
            "seo_job_runs duplicate rejected (race): site_id=%s job_type=%s run_date=%s",
            site_id, job_type, run_date,
        )
        return None


def finish_job_run(run_id: int, status: str, error: Optional[str] = None) -> None:
    with write_cursor() as cur:
        cur.execute(
            "UPDATE seo_job_runs SET status = ?, error = ?, finished_at = ? WHERE id = ?",
            (status, error, datetime.now().isoformat(sep=" "), run_id),
        )


def increment_job_run_retry(run_id: int) -> None:
    with write_cursor() as cur:
        cur.execute(
            "UPDATE seo_job_runs SET retry_count = retry_count + 1, status = 'running', error = NULL WHERE id = ?",
            (run_id,),
        )


def get_job_run(run_id: int):
    conn = get_connection()
    return conn.execute("SELECT * FROM seo_job_runs WHERE id = ?", (run_id,)).fetchone()


def list_job_runs(site_id: Optional[int] = None, limit: int = 50):
    conn = get_connection()
    if site_id is not None:
        return conn.execute(
            "SELECT * FROM seo_job_runs WHERE site_id = ? ORDER BY started_at DESC LIMIT ?",
            (site_id, limit),
        ).fetchall()
    return conn.execute(
        "SELECT * FROM seo_job_runs ORDER BY started_at DESC LIMIT ?", (limit,)
    ).fetchall()


# ── llm_usage_log — module 25: cost/usage visibility across every LLM provider ──

def log_llm_usage(
    task: str,
    provider: str,
    model: Optional[str],
    success: bool,
    site_id: Optional[int] = None,
    tokens_in: Optional[int] = None,
    tokens_out: Optional[int] = None,
    cost_estimate: Optional[float] = None,
    latency_ms: Optional[float] = None,
    error: Optional[str] = None,
) -> None:
    with write_cursor() as cur:
        cur.execute(
            """
            INSERT INTO llm_usage_log
                (site_id, task, provider, model, tokens_in, tokens_out, cost_estimate, latency_ms, success, error)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                site_id, task, provider, model, tokens_in, tokens_out,
                cost_estimate, latency_ms, 1 if success else 0, error,
            ),
        )


def list_llm_usage(limit: int = 100):
    conn = get_connection()
    return conn.execute(
        "SELECT * FROM llm_usage_log ORDER BY created_at DESC LIMIT ?", (limit,)
    ).fetchall()


# ── seo_pagespeed_results — module 26.4 ──

def upsert_pagespeed_result(
    site_id: int,
    url: str,
    strategy: str,
    run_date: date_cls,
    performance_score: Optional[float],
    lcp_ms: Optional[float],
    cls: Optional[float],
    inp_ms: Optional[float],
    ttfb_ms: Optional[float],
    fcp_ms: Optional[float],
    raw_json: str,
) -> None:
    with write_cursor() as cur:
        cur.execute(
            """
            INSERT INTO seo_pagespeed_results
                (site_id, url, strategy, run_date, performance_score, lcp_ms, cls, inp_ms, ttfb_ms, fcp_ms, raw_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(site_id, url, strategy, run_date) DO UPDATE SET
                performance_score = excluded.performance_score,
                lcp_ms = excluded.lcp_ms,
                cls = excluded.cls,
                inp_ms = excluded.inp_ms,
                ttfb_ms = excluded.ttfb_ms,
                fcp_ms = excluded.fcp_ms,
                raw_json = excluded.raw_json
            """,
            (
                site_id, url, strategy, run_date.isoformat(), performance_score,
                lcp_ms, cls, inp_ms, ttfb_ms, fcp_ms, raw_json,
            ),
        )


def list_pagespeed_results(site_id: int, limit: int = 50):
    conn = get_connection()
    return conn.execute(
        "SELECT * FROM seo_pagespeed_results WHERE site_id = ? ORDER BY run_date DESC, created_at DESC LIMIT ?",
        (site_id, limit),
    ).fetchall()


# ── seo_gsc_queries — module 26.5 ──

def upsert_gsc_query_rows(site_id: int, run_date: date_cls, rows: list) -> None:
    """rows: list of automation.seo.gsc_client.GscQueryRow. A no-op on an
    empty list rather than an empty transaction."""
    if not rows:
        return
    with write_cursor() as cur:
        cur.executemany(
            """
            INSERT INTO seo_gsc_queries (site_id, run_date, query, clicks, impressions, ctr, position)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(site_id, run_date, query) DO UPDATE SET
                clicks = excluded.clicks,
                impressions = excluded.impressions,
                ctr = excluded.ctr,
                position = excluded.position
            """,
            [
                (site_id, run_date.isoformat(), r.query, r.clicks, r.impressions, r.ctr, r.position)
                for r in rows
            ],
        )


def list_gsc_queries(site_id: int, limit: int = 100):
    conn = get_connection()
    return conn.execute(
        "SELECT * FROM seo_gsc_queries WHERE site_id = ? ORDER BY run_date DESC, clicks DESC LIMIT ?",
        (site_id, limit),
    ).fetchall()


# ── seo_ga4_pages — module 26.6 ──

def upsert_ga4_page_rows(site_id: int, run_date: date_cls, rows: list) -> None:
    """rows: list of automation.seo.ga4_client.Ga4PageRow."""
    if not rows:
        return
    with write_cursor() as cur:
        cur.executemany(
            """
            INSERT INTO seo_ga4_pages (site_id, run_date, page_path, sessions, bounce_rate, conversions)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(site_id, run_date, page_path) DO UPDATE SET
                sessions = excluded.sessions,
                bounce_rate = excluded.bounce_rate,
                conversions = excluded.conversions
            """,
            [
                (site_id, run_date.isoformat(), r.page_path, r.sessions, r.bounce_rate, r.conversions)
                for r in rows
            ],
        )


def list_ga4_pages(site_id: int, limit: int = 100):
    conn = get_connection()
    return conn.execute(
        "SELECT * FROM seo_ga4_pages WHERE site_id = ? ORDER BY run_date DESC, sessions DESC LIMIT ?",
        (site_id, limit),
    ).fetchall()


# ── seo_og_tags — module 27.3 ──

def upsert_og_tags(site_id: int, page_url: str, page_title: str, og_title: str, og_description: str) -> None:
    with write_cursor() as cur:
        cur.execute(
            """
            INSERT INTO seo_og_tags (site_id, page_url, page_title, og_title, og_description, generated_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(site_id, page_url) DO UPDATE SET
                page_title = excluded.page_title,
                og_title = excluded.og_title,
                og_description = excluded.og_description,
                generated_at = CURRENT_TIMESTAMP
            """,
            (site_id, page_url, page_title, og_title, og_description),
        )


def list_og_tags(site_id: int, limit: int = 100):
    conn = get_connection()
    return conn.execute(
        "SELECT * FROM seo_og_tags WHERE site_id = ? ORDER BY generated_at DESC LIMIT ?",
        (site_id, limit),
    ).fetchall()


# ── seo_technical_issues — module 28 ──

def upsert_technical_issues(site_id: int, run_date: date_cls, issues: list) -> None:
    """issues: list of automation.seo.technical_audit.TechnicalIssue.
    Never overwrites `status` — see this table's schema comment."""
    if not issues:
        return
    with write_cursor() as cur:
        cur.executemany(
            """
            INSERT INTO seo_technical_issues
                (site_id, run_date, rule, severity, url, message, suggested_fix, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')
            ON CONFLICT(site_id, rule, url) DO UPDATE SET
                run_date = excluded.run_date,
                severity = excluded.severity,
                message = excluded.message,
                suggested_fix = excluded.suggested_fix
            """,
            [
                (site_id, run_date.isoformat(), i.rule, i.severity, i.url, i.message, i.suggested_fix)
                for i in issues
            ],
        )


def list_technical_issues(site_id: int, status: Optional[str] = None, limit: int = 200):
    conn = get_connection()
    if status is not None:
        return conn.execute(
            "SELECT * FROM seo_technical_issues WHERE site_id = ? AND status = ? "
            "ORDER BY severity, created_at DESC LIMIT ?",
            (site_id, status, limit),
        ).fetchall()
    return conn.execute(
        "SELECT * FROM seo_technical_issues WHERE site_id = ? ORDER BY severity, created_at DESC LIMIT ?",
        (site_id, limit),
    ).fetchall()


def set_technical_issue_status(issue_id: int, status: str, reviewed_by: Optional[str] = None) -> bool:
    with write_cursor() as cur:
        cur.execute(
            "UPDATE seo_technical_issues SET status = ?, reviewed_at = CURRENT_TIMESTAMP, reviewed_by = ? WHERE id = ?",
            (status, reviewed_by, issue_id),
        )
        return cur.rowcount > 0


# ── seo_daily_digests — module 29 ──

def save_daily_digest(
    site_id: int, run_date: date_cls, narrative: str, stats_json: str, slack_delivered: bool
) -> None:
    with write_cursor() as cur:
        cur.execute(
            """
            INSERT INTO seo_daily_digests (site_id, run_date, narrative, stats_json, slack_delivered)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(site_id, run_date) DO UPDATE SET
                narrative = excluded.narrative,
                stats_json = excluded.stats_json,
                slack_delivered = excluded.slack_delivered
            """,
            (site_id, run_date.isoformat(), narrative, stats_json, 1 if slack_delivered else 0),
        )


def list_daily_digests(site_id: int, limit: int = 30):
    conn = get_connection()
    return conn.execute(
        "SELECT * FROM seo_daily_digests WHERE site_id = ? ORDER BY run_date DESC LIMIT ?",
        (site_id, limit),
    ).fetchall()


# ── seo_social_posts — module 30 ──

def create_social_post(site_id: int, platform: str, content: str, source_url: Optional[str] = None) -> int:
    with write_cursor() as cur:
        cur.execute(
            "INSERT INTO seo_social_posts (site_id, platform, source_url, content, status) VALUES (?, ?, ?, ?, 'draft')",
            (site_id, platform, source_url, content),
        )
        return cur.lastrowid


def list_social_posts(site_id: int, status: Optional[str] = None, limit: int = 100):
    conn = get_connection()
    if status is not None:
        return conn.execute(
            "SELECT * FROM seo_social_posts WHERE site_id = ? AND status = ? ORDER BY created_at DESC LIMIT ?",
            (site_id, status, limit),
        ).fetchall()
    return conn.execute(
        "SELECT * FROM seo_social_posts WHERE site_id = ? ORDER BY created_at DESC LIMIT ?",
        (site_id, limit),
    ).fetchall()


def get_social_post(post_id: int):
    conn = get_connection()
    return conn.execute("SELECT * FROM seo_social_posts WHERE id = ?", (post_id,)).fetchone()


def set_social_post_status(post_id: int, status: str) -> bool:
    with write_cursor() as cur:
        cur.execute("UPDATE seo_social_posts SET status = ? WHERE id = ?", (status, post_id))
        return cur.rowcount > 0


def mark_social_post_posted(post_id: int, external_post_id: Optional[str]) -> None:
    with write_cursor() as cur:
        cur.execute(
            "UPDATE seo_social_posts SET status = 'posted', external_post_id = ?, posted_at = CURRENT_TIMESTAMP, error = NULL WHERE id = ?",
            (external_post_id, post_id),
        )


def mark_social_post_failed(post_id: int, error: str) -> None:
    with write_cursor() as cur:
        cur.execute(
            "UPDATE seo_social_posts SET status = 'failed', error = ? WHERE id = ?", (error, post_id)
        )


# ── seo_backlink_mentions — module 31 ──

def upsert_backlink_mentions(site_id: int, mentions: list) -> int:
    """mentions: list of automation.seo.backlinks.base.Mention. Returns
    the number of genuinely new mentions inserted (existing ones are
    left untouched, including any outreach draft already on them)."""
    if not mentions:
        return 0
    inserted = 0
    with write_cursor() as cur:
        for m in mentions:
            cur.execute(
                """
                INSERT INTO seo_backlink_mentions
                    (site_id, source_url, source_title, anchor_text, domain_rating, discovered_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(site_id, source_url) DO NOTHING
                """,
                (site_id, m.source_url, m.source_title, m.anchor_text, m.domain_rating, m.discovered_at),
            )
            inserted += cur.rowcount
    return inserted


def list_backlink_mentions(site_id: int, limit: int = 100):
    conn = get_connection()
    return conn.execute(
        "SELECT * FROM seo_backlink_mentions WHERE site_id = ? ORDER BY created_at DESC LIMIT ?",
        (site_id, limit),
    ).fetchall()


def save_outreach_draft(mention_id: int, subject: str, body: str) -> bool:
    with write_cursor() as cur:
        cur.execute(
            "UPDATE seo_backlink_mentions SET outreach_subject = ?, outreach_body = ? WHERE id = ?",
            (subject, body, mention_id),
        )
        return cur.rowcount > 0


# ── seo_index_status / seo_indexing_submissions — Indexing Status & Crawl Monitoring ──

def upsert_index_status(site_id: int, url: str, inspection) -> None:
    """inspection: automation.seo.indexing_client.UrlInspectionResult."""
    with write_cursor() as cur:
        cur.execute(
            """
            INSERT INTO seo_index_status
                (site_id, url, coverage_state, indexing_state, robots_txt_state, page_fetch_state,
                 last_crawl_time, google_canonical, user_canonical, sitemap_json, checked_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(site_id, url) DO UPDATE SET
                coverage_state = excluded.coverage_state,
                indexing_state = excluded.indexing_state,
                robots_txt_state = excluded.robots_txt_state,
                page_fetch_state = excluded.page_fetch_state,
                last_crawl_time = excluded.last_crawl_time,
                google_canonical = excluded.google_canonical,
                user_canonical = excluded.user_canonical,
                sitemap_json = excluded.sitemap_json,
                checked_at = CURRENT_TIMESTAMP
            """,
            (
                site_id,
                url,
                inspection.coverage_state,
                inspection.indexing_state,
                inspection.robots_txt_state,
                inspection.page_fetch_state,
                inspection.last_crawl_time,
                inspection.google_canonical,
                inspection.user_canonical,
                json.dumps(inspection.sitemap) if inspection.sitemap else None,
            ),
        )


def list_index_status(site_id: int, limit: int = 200):
    conn = get_connection()
    return conn.execute(
        "SELECT * FROM seo_index_status WHERE site_id = ? ORDER BY checked_at DESC LIMIT ?",
        (site_id, limit),
    ).fetchall()


def save_indexing_submission(
    site_id: int, url: str, notification_type: str, success: bool, response_json: Optional[str], error: Optional[str]
) -> int:
    with write_cursor() as cur:
        cur.execute(
            """
            INSERT INTO seo_indexing_submissions
                (site_id, url, notification_type, success, response_json, error)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (site_id, url, notification_type, 1 if success else 0, response_json, error),
        )
        return cur.lastrowid


def list_indexing_submissions(site_id: int, limit: int = 100):
    conn = get_connection()
    return conn.execute(
        "SELECT * FROM seo_indexing_submissions WHERE site_id = ? ORDER BY submitted_at DESC LIMIT ?",
        (site_id, limit),
    ).fetchall()


# ── seo_blog_posts — module 34 ──

def create_blog_post(
    site_id: int,
    topic: str,
    primary_keyword: Optional[str],
    title: str,
    excerpt: Optional[str],
    content: str,
    structure_passed: Optional[bool],
    structure_issues_json: Optional[str],
) -> int:
    with write_cursor() as cur:
        cur.execute(
            """
            INSERT INTO seo_blog_posts
                (site_id, topic, primary_keyword, title, excerpt, content,
                 structure_passed, structure_issues_json, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'draft')
            """,
            (
                site_id, topic, primary_keyword, title, excerpt, content,
                None if structure_passed is None else int(structure_passed), structure_issues_json,
            ),
        )
        return cur.lastrowid


def list_blog_posts(site_id: int, status: Optional[str] = None, limit: int = 100):
    conn = get_connection()
    if status is not None:
        return conn.execute(
            "SELECT * FROM seo_blog_posts WHERE site_id = ? AND status = ? ORDER BY created_at DESC LIMIT ?",
            (site_id, status, limit),
        ).fetchall()
    return conn.execute(
        "SELECT * FROM seo_blog_posts WHERE site_id = ? ORDER BY created_at DESC LIMIT ?",
        (site_id, limit),
    ).fetchall()


def get_blog_post(post_id: int):
    conn = get_connection()
    return conn.execute("SELECT * FROM seo_blog_posts WHERE id = ?", (post_id,)).fetchone()


def set_blog_post_status(post_id: int, status: str) -> bool:
    with write_cursor() as cur:
        cur.execute("UPDATE seo_blog_posts SET status = ? WHERE id = ?", (status, post_id))
        return cur.rowcount > 0


def mark_blog_post_published(post_id: int, cms_post_id: Optional[str], cms_post_link: Optional[str]) -> None:
    with write_cursor() as cur:
        cur.execute(
            """
            UPDATE seo_blog_posts
            SET status = 'published', cms_post_id = ?, cms_post_link = ?,
                published_at = CURRENT_TIMESTAMP, error = NULL
            WHERE id = ?
            """,
            (cms_post_id, cms_post_link, post_id),
        )


def mark_blog_post_failed(post_id: int, error: str) -> None:
    with write_cursor() as cur:
        cur.execute("UPDATE seo_blog_posts SET status = 'failed', error = ? WHERE id = ?", (error, post_id))
