"""
MODULE 30.3 — Social post publishing dispatcher.

LinkedIn: real, tested automation already exists in this codebase
(automation/linkedin/poster.py, module 18 — a persistent Playwright
browser context, no LinkedIn API). This module reuses it directly rather
than building a second implementation.

Twitter/X, Instagram, Facebook: no automation exists for these platforms
anywhere in this codebase, and building untested browser automation
against three more platforms — each with its own login flow, composer
UI, and anti-automation defenses, none of it verifiable without a real
account to test against — is out of scope here. publish_social_post()
for these platforms deliberately does not pretend to post; it returns a
clear "manual posting required" result so the approved content stays
exactly what it is: text a human copies into the platform themselves.
This matches the blueprint's own "human hits send" pattern for anything
relationship/account-sensitive.
"""
import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

# Platforms this module can actually publish to automatically.
AUTOMATED_PLATFORMS = ("linkedin",)


@dataclass
class PublishResult:
    ok: bool
    detail: str
    external_post_id: Optional[str] = None


def publish_social_post(platform: str, content: str) -> PublishResult:
    if platform == "linkedin":
        from automation.linkedin.poster import post_to_linkedin

        result = post_to_linkedin(content=content, topic="seo-social-post")
        if result["status"] == "success":
            return PublishResult(ok=True, detail=result["detail"], external_post_id=result["post_id"])
        return PublishResult(ok=False, detail=result["detail"])

    return PublishResult(
        ok=False,
        detail=(
            f"No automated posting exists for {platform!r} in this codebase — copy the "
            "approved content and post it manually."
        ),
    )
