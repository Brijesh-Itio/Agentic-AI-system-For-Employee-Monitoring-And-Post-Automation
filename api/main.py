"""
MODULE 5.1 — FastAPI Backend entry point.

CORS is opened for the Vite dev server (localhost:5173). Schema creation
happens once, on startup, via a lifespan handler (agent/database.py's DDL
is the single source of truth — see api/database.py).
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from agent.logging_config import setup_logging
from api.config import settings
from api.database import init_db
from api.routes import (
    activity,
    alerts,
    command,
    email,
    leads,
    linkedin,
    productivity,
    reports,
    screenshots,
    status,
    team,
    websites,
)

setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    logger.info("WorkPulse AI API started")
    yield
    logger.info("WorkPulse AI API shutting down")


app = FastAPI(title="WorkPulse AI API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(activity.router)
app.include_router(screenshots.router)
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


@app.get("/")
def root():
    return {"service": "WorkPulse AI API", "status": "running"}
