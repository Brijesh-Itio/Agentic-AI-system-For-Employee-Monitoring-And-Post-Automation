"""
MODULE 5.1 — FastAPI Backend entry point.

CORS is opened for the Vite dev server (localhost:5173). Schema creation
happens once, on startup, via a lifespan handler (agent/database.py's DDL
is the single source of truth — see api/database.py).
"""
import logging
import socket
from contextlib import asynccontextmanager

import urllib3.util.connection as urllib3_connection
from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from agent.logging_config import setup_logging
from api.config import settings
from api.database import init_db
from api.routes import (
    activity,
    alerts,
    attendance,
    auth,
    command,
    dar_entries,
    departments,
    email,
    email_templates,
    holidays,
    leads,
    linkedin,
    productivity,
    reports,
    seo,
    sso,
    status,
    team,
    websites,
)

# IPv6 to Google's APIs is broken on this machine's network — verified live
# that a plain `requests` call to searchconsole.googleapis.com took 80s
# (Python/urllib3 trying IPv6 addresses first and stalling before falling
# back to IPv4) versus 1.3s with IPv4 forced, while curl to the same host
# was fast throughout (it doesn't attempt IPv6 first here). This silent
# 80s+ stall was surfacing as a "URL Inspection failed" error in the SEO
# module's Indexing tab. Forcing IPv4 for every outbound `requests` call
# from this process fixes it for all of this module's Google API clients
# (GSC, GA4, PageSpeed, Indexing API), not just the one that reproduced it.
urllib3_connection.allowed_gai_family = lambda: socket.AF_INET

setup_logging()
logger = logging.getLogger(__name__)

# Module 33 — a real BackgroundScheduler thread (independent of FastAPI's
# asyncio loop; every function ai.seo_master_agent's daily cycle calls is
# synchronous requests-based, same as the rest of automation/seo) fires
# the SEO pipeline once a day per active site with no manual click
# needed. Built at import time, started/stopped in the lifespan below.
seo_scheduler = BackgroundScheduler()


def _run_server_file_backup_cleanup() -> None:
    from agent.database import purge_old_server_file_backups

    removed = purge_old_server_file_backups(retention_days=15)
    if removed:
        logger.info("Server file backup cleanup: removed %d backup row(s) older than 15 days", removed)


def _run_digest_rollup(period: str) -> None:
    """Module 36 — the scheduled half of the weekly/monthly roll-up
    feature; /api/seo/digest/rollup/{period} is the on-demand half. Runs
    for every active site, same graceful-degrade-per-site convention as
    run_daily_cycle_for_all_sites — one site's LLM/Slack failure doesn't
    stop the rest."""
    from datetime import date

    from agent.database import get_active_seo_sites, save_digest_rollup
    from ai.seo.rollup_digest import generate_rollup_digest
    from automation.seo.slack_notifier import send_slack_message

    sites = get_active_seo_sites()
    logger.info("SEO %s digest roll-up starting for %d active site(s)", period, len(sites))
    for site in sites:
        try:
            report = generate_rollup_digest(site["id"], site["name"], period)
            slack_delivered = send_slack_message(
                f"*SEO {period.capitalize()} Roll-Up — {site['name']}*\n{report.narrative}"
            )
            save_digest_rollup(
                site["id"], period, date.fromisoformat(report.period_start), date.fromisoformat(report.period_end),
                report.narrative, report.stats_json, slack_delivered,
            )
        except Exception:
            logger.exception("SEO %s digest roll-up failed for site %s — continuing to next site", period, site["id"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()

    # Housekeeping, not gated behind SEO_AUTOMATION_ENABLED — the Server
    # Files backup history (seo_server_file_backups) is a rolling
    # 15-day window regardless of whether the SEO pipeline itself runs.
    seo_scheduler.add_job(
        _run_server_file_backup_cleanup,
        trigger="cron",
        hour=3,
        minute=30,
        id="server_file_backup_cleanup",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    # Module 36 — weekly (every Monday) and monthly (1st of month) digest
    # roll-ups, same housekeeping tier as the backup cleanup above: not
    # gated behind SEO_AUTOMATION_ENABLED, since these summarise
    # whatever daily digests already exist rather than running the SEO
    # pipeline themselves.
    seo_scheduler.add_job(
        _run_digest_rollup,
        args=["weekly"],
        trigger="cron",
        day_of_week="mon",
        hour=7,
        minute=30,
        id="seo_weekly_rollup",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    seo_scheduler.add_job(
        _run_digest_rollup,
        args=["monthly"],
        trigger="cron",
        day=1,
        hour=7,
        minute=45,
        id="seo_monthly_rollup",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    if settings.SEO_AUTOMATION_ENABLED:
        from ai.seo_master_agent import run_daily_cycle_for_all_sites

        seo_scheduler.add_job(
            run_daily_cycle_for_all_sites,
            trigger="cron",
            hour=settings.SEO_AUTOMATION_HOUR,
            minute=0,
            id="seo_daily_cycle",
            replace_existing=True,
            misfire_grace_time=3600,
        )
        logger.info("SEO daily automation scheduled for %02d:00 local time", settings.SEO_AUTOMATION_HOUR)

    seo_scheduler.start()
    logger.info("Server file backup cleanup scheduled for 03:30 local time (15-day retention)")
    logger.info("WorkPulse AI API started")
    yield
    if seo_scheduler.running:
        seo_scheduler.shutdown(wait=False)
    logger.info("WorkPulse AI API shutting down")


app = FastAPI(title="WorkPulse AI API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(sso.router)
app.include_router(attendance.router)
app.include_router(activity.router)
app.include_router(websites.router)
app.include_router(productivity.router)
app.include_router(reports.router)
app.include_router(status.router)
app.include_router(alerts.router)
app.include_router(leads.router)
app.include_router(team.router)
app.include_router(linkedin.router)
app.include_router(email.router)
app.include_router(command.router)
app.include_router(departments.router)
app.include_router(holidays.router)
app.include_router(email_templates.router)
app.include_router(dar_entries.router)
app.include_router(seo.router)


@app.get("/")
def root():
    return {"service": "WorkPulse AI API", "status": "running"}
