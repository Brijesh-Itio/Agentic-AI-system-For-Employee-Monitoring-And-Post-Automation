"""
MODULE 29 — Slack delivery for SEO digests/alerts.

Posts to a Slack Incoming Webhook (free — api.slack.com/messaging/webhooks).
Blank SLACK_WEBHOOK_URL means "off," same convention as every other
optional integration in this codebase (Gmail, LinkedIn, Pexels) — a
digest still generates and gets stored even without Slack configured,
it just isn't also pushed there.
"""
import logging

import requests

from api.config import settings

logger = logging.getLogger(__name__)

TIMEOUT_SECONDS = 10


def send_slack_message(text: str) -> bool:
    """Never raises — returns False on any failure (unconfigured,
    network, Slack rejecting the payload), matching this codebase's
    graceful-degrade convention."""
    if not settings.SLACK_WEBHOOK_URL:
        logger.info("SLACK_WEBHOOK_URL not configured — skipping Slack delivery")
        return False
    try:
        response = requests.post(settings.SLACK_WEBHOOK_URL, json={"text": text}, timeout=TIMEOUT_SECONDS)
        response.raise_for_status()
        return True
    except Exception:
        logger.exception("Slack delivery failed")
        return False
