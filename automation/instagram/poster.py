"""
Instagram Content Publishing (Graph API).

Real REST calls against Meta's Instagram Graph API, no SDK — same
plain-requests convention as automation/seo/google_auth.py and
pagespeed_client.py. Two-step flow, verified against Meta's current
docs this session rather than guessed: create a media container (POST
.../media with image_url + caption), then publish it (POST
.../media_publish with the container's id). Unlike LinkedIn/Twitter/
Facebook, Instagram has no text-only post type at all — image_url is
mandatory here, not optional, a real platform constraint this module
can't work around, not an oversight.

Chosen over browser automation (LinkedIn's approach, automation/
linkedin/poster.py) deliberately: Instagram polices automated/scripted
posting far more aggressively than LinkedIn, and unlike LinkedIn this
session had no real account to verify browser-automation selectors
against without risking it getting flagged or banned. The official API
needs more setup up front (a Business/Creator account + a Meta developer
app + App Review for publish permissions) but carries no such risk.
"""
import logging
from dataclasses import dataclass
from typing import Optional

import requests

from ai.llm.retry import with_retry
from api.config import settings

logger = logging.getLogger(__name__)

API_VERSION = "v26.0"
GRAPH_BASE_URL = f"https://graph.instagram.com/{API_VERSION}"
TIMEOUT_SECONDS = 30


@dataclass
class PublishResult:
    ok: bool
    detail: str
    external_post_id: Optional[str] = None


def _credentials_configured() -> bool:
    return bool(settings.INSTAGRAM_ACCESS_TOKEN and settings.INSTAGRAM_BUSINESS_ACCOUNT_ID)


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


def post_to_instagram(caption: str, image_url: str) -> PublishResult:
    """Never raises — always returns a PublishResult, same graceful-
    degrade convention as every other dispatch target in
    automation/seo/social_poster.py."""
    if not _credentials_configured():
        return PublishResult(
            ok=False,
            detail="INSTAGRAM_ACCESS_TOKEN/INSTAGRAM_BUSINESS_ACCOUNT_ID not set in .env — cannot post",
        )
    if not image_url:
        return PublishResult(
            ok=False,
            detail="Instagram has no text-only post type — this post needs an image URL before it can publish",
        )

    ig_id = settings.INSTAGRAM_BUSINESS_ACCOUNT_ID
    token = settings.INSTAGRAM_ACCESS_TOKEN

    try:
        container_response = requests.post(
            f"{GRAPH_BASE_URL}/{ig_id}/media",
            data={"image_url": image_url, "caption": caption, "access_token": token},
            timeout=TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        logger.exception("Instagram media container creation failed (network error)")
        return PublishResult(ok=False, detail=f"Network error creating media container: {exc}")

    if not container_response.ok:
        detail = _api_error_detail(container_response)
        logger.error("Instagram media container creation failed: %s", detail)
        return PublishResult(ok=False, detail=f"Couldn't create media container: {detail}")

    container_id = container_response.json().get("id")
    if not container_id:
        return PublishResult(ok=False, detail="Instagram didn't return a container id")

    def _do_publish():
        response = requests.post(
            f"{GRAPH_BASE_URL}/{ig_id}/media_publish",
            data={"creation_id": container_id, "access_token": token},
            timeout=TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return response

    try:
        # A freshly created container isn't always immediately ready to
        # publish (Meta's own docs: a container can sit IN_PROGRESS
        # briefly) — a short bounded retry covers this without the
        # caller waiting the full 5 minutes Meta's troubleshooting guide
        # allows for.
        publish_response = with_retry(
            _do_publish,
            max_attempts=4,
            base_delay_seconds=3,
            max_delay_seconds=15,
            retry_on=(requests.RequestException,),
        )
    except requests.RequestException as exc:
        detail = _api_error_detail(getattr(exc, "response", None))
        logger.error("Instagram media publish failed: %s", detail)
        return PublishResult(ok=False, detail=f"Couldn't publish media container: {detail}")

    media_id = publish_response.json().get("id")
    logger.info("Posted to Instagram successfully (media_id=%s)", media_id)
    return PublishResult(ok=True, detail="Posted successfully", external_post_id=media_id)
