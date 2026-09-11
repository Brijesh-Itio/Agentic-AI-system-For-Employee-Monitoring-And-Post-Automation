"""
MODULE 30.3 — Social post publishing dispatcher.

LinkedIn: real, tested automation already exists in this codebase
(automation/linkedin/poster.py, module 18 — a persistent Playwright
browser context, no LinkedIn API). This module reuses it directly rather
than building a second implementation.

Instagram: automation/instagram/poster.py, the official Graph API
(Content Publishing) rather than browser automation — Instagram polices
scripted posting more aggressively than LinkedIn does, and unlike
LinkedIn there was no real account here to verify browser-automation
selectors against without risking it getting flagged. Needs an image URL
(Instagram has no text-only post type) and real Meta app credentials in
.env; blank credentials degrade to the same "not configured" result as
every other optional integration in this codebase, not a crash.

Twitter/X, Facebook: no automation exists for these platforms anywhere
in this codebase, and building untested browser automation against two
more platforms — each with its own login flow, composer UI, and anti-
automation defenses, none of it verifiable without a real account to
test against — is out of scope here. publish_social_post() for these
platforms deliberately does not pretend to post; it returns a clear
"manual posting required" result so the approved content stays exactly
what it is: text a human copies into the platform themselves. This
matches the blueprint's own "human hits send" pattern for anything
relationship/account-sensitive.
"""
import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

# Platforms this module can actually publish to automatically.
AUTOMATED_PLATFORMS = ("linkedin", "instagram")


@dataclass
class PublishResult:
    ok: bool
    detail: str
    external_post_id: Optional[str] = None


def publish_social_post(platform: str, content: str, image_url: Optional[str] = None) -> PublishResult:
    if platform == "linkedin":
        from automation.linkedin.poster import post_to_linkedin

        result = post_to_linkedin(content=content, topic="seo-social-post")
        if result["status"] == "success":
            return PublishResult(ok=True, detail=result["detail"], external_post_id=result["post_id"])
        return PublishResult(ok=False, detail=result["detail"])

    if platform == "instagram":
        from automation.instagram.poster import post_to_instagram

        result = post_to_instagram(caption=content, image_url=image_url or "")
        return PublishResult(ok=result.ok, detail=result.detail, external_post_id=result.external_post_id)

    return PublishResult(
        ok=False,
        detail=(
            f"No automated posting exists for {platform!r} in this codebase — copy the "
            "approved content and post it manually."
        ),
    )
