"""
Business automation settings (module 18-20). Credentials load through
api.config.settings (.env-backed, same as Gmail's) — never hardcoded here.
Everything else is static configuration, not a secret, so it lives as
plain module constants matching DEVELOPMENT.md's section 7 reference.
"""
from pathlib import Path

from api.config import PROJECT_ROOT, settings

LINKEDIN_EMAIL: str = settings.LINKEDIN_EMAIL
LINKEDIN_PASSWORD: str = settings.LINKEDIN_PASSWORD
LINKEDIN_COOKIES_PATH: Path = PROJECT_ROOT / "linkedin_cookies.json"

# 18.2 — topics rotate through this list so none repeats until all have
# been used (last_topic.txt, alongside the cookies file, tracks position).
POST_TOPICS: list[str] = [
    "How local AI (Ollama) removes per-token cost from everyday agentic workflows",
    "Why an autonomous work-tracking agent should never need a button click",
    "What genuinely agentic AI looks like versus a chatbot wrapper",
    "Zero-API-cost automation: what's actually possible running entirely on-device",
    "How productivity scoring should work when it's built on real usage data",
]
LAST_TOPIC_PATH: Path = PROJECT_ROOT / "last_topic.txt"

DAILY_POST_LIMIT: int = 10  # temporarily raised for testing — restore to a low number (e.g. 3) before real unattended use
MIN_POST_INTERVAL_MINUTES: int = 0  # temporarily disabled for testing — restore to 30 before real unattended use

DAILY_EMAIL_LIMIT: int = 500
