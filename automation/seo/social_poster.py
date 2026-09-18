"""
MODULE 30.3 — Social post publishing dispatcher.

LinkedIn: real, tested automation already exists in this codebase
(automation/linkedin/poster.py, module 18 — a persistent Playwright
browser context, no LinkedIn API). This module reuses it directly rather
than building a second implementation. post_to_linkedin() takes a local
file Path (for Playwright's set_input_files), not a URL — but a
SeoSocialPost's image_url is a public URL already uploaded to the site's
own server (ai/seo/image_pipeline.py's upload path), so it has to be
downloaded to a temp file first (_download_image_to_temp below) before
handing it to post_to_linkedin. Fixed 2026-09-17: this download step was
previously missing entirely, so every LinkedIn post published through
this dispatcher went out text-only regardless of whether an image had
been generated for it.

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
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import requests

logger = logging.getLogger(__name__)


_DOWNLOAD_HEADERS = {
    # Sites with WAF/bot-protection plugins (Wordfence etc.) reject
    # requests' default "python-requests/x.x" User-Agent outright with a
    # 406 — verified live against a real generated image URL on
    # webpays.com. A plain browser-like UA is enough to pass.
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
}


def _download_image_to_temp(image_url: str) -> Optional[Path]:
    """Never raises — returns None on any failure, so a broken/unreachable
    image URL degrades to a text-only LinkedIn post instead of blocking
    publish entirely (same graceful-degrade convention as every other
    optional-image path in this codebase)."""
    try:
        response = requests.get(image_url, headers=_DOWNLOAD_HEADERS, timeout=30)
        response.raise_for_status()
        suffix = Path(image_url.split("?")[0]).suffix or ".jpg"
        fd, temp_path = tempfile.mkstemp(suffix=suffix, prefix="workpulse_social_")
        Path(temp_path).write_bytes(response.content)
        import os

        os.close(fd)
        return Path(temp_path)
    except Exception:
        logger.exception("Failed to download %s for LinkedIn post — posting text-only", image_url)
        return None

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

        image_path = _download_image_to_temp(image_url) if image_url else None
        result = post_to_linkedin(content=content, topic="seo-social-post", image_path=image_path)
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
