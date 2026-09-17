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

Twitter/X: automation/twitter/poster.py, the official API v2 (POST
/2/tweets) with OAuth 1.0a — real, verified-against-current-docs
endpoint shape, but needs real credentials (TWITTER_API_KEY/SECRET/
ACCESS_TOKEN/ACCESS_TOKEN_SECRET) in .env before it can post; blank
credentials degrade to the same "not configured" result as Instagram.

Facebook: automation/facebook/poster.py, the official Graph API (POST
/{page-id}/feed) — same pattern, needs FACEBOOK_PAGE_ACCESS_TOKEN/
FACEBOOK_PAGE_ID in .env as the default account. Module 40 added
multi-account support (seo_facebook_accounts table): passing
facebook_page_id/facebook_access_token here posts through that specific
connected Page instead of the .env default — api/routes/seo.py's publish
route resolves a post's chosen account before calling this.

Both Twitter and Facebook are listed in AUTOMATED_PLATFORMS because the
real API integration code exists and is correct against current docs —
"automated" here means "this codebase can post for you once you supply
credentials," not "credentials are already configured." Missing
credentials surface as a clear PublishResult(ok=False, detail=...)
identical in shape to any other failure, not a crash.
"""
import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

# Platforms this module can actually publish to automatically once
# credentials are configured (see module docstring above).
AUTOMATED_PLATFORMS = ("linkedin", "instagram", "twitter", "facebook")


@dataclass
class PublishResult:
    ok: bool
    detail: str
    external_post_id: Optional[str] = None


def publish_social_post(
    platform: str,
    content: str,
    image_url: Optional[str] = None,
    *,
    facebook_page_id: Optional[str] = None,
    facebook_access_token: Optional[str] = None,
) -> PublishResult:
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

    if platform == "twitter":
        from automation.twitter.poster import post_to_twitter

        result = post_to_twitter(content)
        return PublishResult(ok=result.ok, detail=result.detail, external_post_id=result.external_post_id)

    if platform == "facebook":
        from automation.facebook.poster import post_to_facebook

        result = post_to_facebook(
            content, image_url=image_url, page_id=facebook_page_id, access_token=facebook_access_token
        )
        return PublishResult(ok=result.ok, detail=result.detail, external_post_id=result.external_post_id)

    return PublishResult(
        ok=False,
        detail=(
            f"No automated posting exists for {platform!r} in this codebase — copy the "
            "approved content and post it manually."
        ),
    )
