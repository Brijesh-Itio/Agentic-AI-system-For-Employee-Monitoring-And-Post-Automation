"""
MODULE 36 — Facebook Page posting (Graph API).

Real REST call against POST https://graph.facebook.com/{version}/{page-id}/feed,
no SDK — same plain-requests convention as automation/instagram/poster.py
(same Meta Graph API family). Endpoint shape, required `pages_manage_posts`
permission, and the message/access_token param names verified against
Meta's current Pages API docs this session, not guessed.

Simpler than Instagram's two-step container flow: Facebook's /feed
endpoint accepts a text post directly (Facebook has a genuine text-only
post type, unlike Instagram), and an optional image via the `link`
param when image_url is supplied.
"""
import logging
from dataclasses import dataclass
from typing import Optional

import requests

from ai.llm.retry import with_retry
from api.config import settings

logger = logging.getLogger(__name__)

API_VERSION = "v26.0"  # same version pin as automation/instagram/poster.py
GRAPH_BASE_URL = f"https://graph.facebook.com/{API_VERSION}"
TIMEOUT_SECONDS = 30


@dataclass
class PublishResult:
    ok: bool
    detail: str
    external_post_id: Optional[str] = None


def _credentials_configured() -> bool:
    return bool(settings.FACEBOOK_PAGE_ACCESS_TOKEN and settings.FACEBOOK_PAGE_ID)


def _api_error_detail(response: Optional[requests.Response]) -> str:
    if response is None:
        return "no response"
    try:
        message = response.json().get("error", {}).get("message")
        if message:
            return message
    except ValueError:
        pass
    return response.text[:300]


def post_to_facebook(content: str, image_url: Optional[str] = None) -> PublishResult:
    """Never raises — always returns a PublishResult, same graceful-
    degrade convention as every other dispatch target in
    automation/seo/social_poster.py."""
    if not _credentials_configured():
        return PublishResult(
            ok=False,
            detail="FACEBOOK_PAGE_ACCESS_TOKEN/FACEBOOK_PAGE_ID not set in .env — cannot post",
        )

    page_id = settings.FACEBOOK_PAGE_ID
    token = settings.FACEBOOK_PAGE_ACCESS_TOKEN
    data = {"message": content, "access_token": token}
    if image_url:
        data["link"] = image_url

    def _do_post():
        response = requests.post(f"{GRAPH_BASE_URL}/{page_id}/feed", data=data, timeout=TIMEOUT_SECONDS)
        response.raise_for_status()
        return response

    try:
        response = with_retry(_do_post, max_attempts=3, retry_on=(requests.RequestException,))
    except requests.RequestException as exc:
        detail = _api_error_detail(getattr(exc, "response", None))
        logger.error("Facebook post failed: %s", detail)
        return PublishResult(ok=False, detail=f"Couldn't post to Facebook Page: {detail}")

    post_id = response.json().get("id")
    logger.info("Posted to Facebook successfully (post_id=%s)", post_id)
    return PublishResult(ok=True, detail="Posted successfully", external_post_id=post_id)
