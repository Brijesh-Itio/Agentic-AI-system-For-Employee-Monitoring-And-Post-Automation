"""
Local SQLite schema and data-access layer for the desktop agent.

Design notes (scalability / performance):
- WAL journal mode so the tracker thread can write while other threads
  (screenshot, sync) read/write concurrently without lock contention.
- A single module-level lock serialises writes from multiple threads on top
  of WAL, since sqlite3 connections are not safe to share across threads
  without care.
- Indexes are created on every column this module or the API will filter/
  sort by, since activity_logs grows unbounded over the life of the agent.
- Schema evolves via CREATE TABLE IF NOT EXISTS / ALTER TABLE ADD COLUMN so
  upgrading the agent never destroys existing tracked data.
"""
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

CREATE TABLE IF NOT EXISTS screenshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL DEFAULT 'local',
    file_path TEXT NOT NULL,
    thumbnail_path TEXT,
    timestamp DATETIME NOT NULL,
    date DATE NOT NULL,
    is_blurred INTEGER DEFAULT 0,
    cloud_url TEXT
);

CREATE INDEX IF NOT EXISTS idx_screenshots_user_date ON screenshots(user_id, date);

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
"""

# Columns added after the initial daily_stats design (module 2.6 — longest
# focus session). ALTER TABLE ADD COLUMN keeps existing rows/data intact.
_DAILY_STATS_EXTRA_COLUMNS = {
    "longest_focus_start": "DATETIME",
    "longest_focus_end": "DATETIME",
    "longest_focus_seconds": "INTEGER DEFAULT 0",
}

# module 3.3 — when blur is enabled we keep the original (unblurred) frame
# for audit purposes alongside the blurred one used for manager view.
_SCREENSHOTS_EXTRA_COLUMNS = {
    "original_path": "TEXT",
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
            _ensure_extra_columns(conn, "screenshots", _SCREENSHOTS_EXTRA_COLUMNS)
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
    """2.2 — record the first input of the day, once, without overwriting it."""
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


# ── screenshots ──

def insert_screenshot(
    file_path: str,
    thumbnail_path: Optional[str],
    timestamp: datetime,
    is_blurred: bool = False,
    original_path: Optional[str] = None,
    user_id: str = "local",
) -> int:
    with write_cursor() as cur:
        cur.execute(
            """
            INSERT INTO screenshots
                (user_id, file_path, thumbnail_path, timestamp, date, is_blurred, original_path)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                file_path,
                thumbnail_path,
                timestamp.isoformat(sep=" "),
                timestamp.date().isoformat(),
                1 if is_blurred else 0,
                original_path,
            ),
        )
        return cur.lastrowid


def get_screenshots_for_date(day: date_cls, user_id: str = "local"):
    conn = get_connection()
    return conn.execute(
        """
        SELECT * FROM screenshots WHERE user_id = ? AND date = ? ORDER BY timestamp ASC
        """,
        (user_id, day.isoformat()),
    ).fetchall()


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


def get_screenshot_count_for_date(day: date_cls, user_id: str = "local") -> int:
    conn = get_connection()
    row = conn.execute(
        "SELECT COUNT(*) AS c FROM screenshots WHERE user_id = ? AND date = ?",
        (user_id, day.isoformat()),
    ).fetchone()
    return row["c"] if row else 0


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

DEFAULT_ALERT_TYPES = ("focus", "distraction", "wellbeing", "manager")


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
