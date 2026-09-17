"""
Facebook Page Posting (Graph API).

Real REST calls against Meta's Graph API — POST /{page-id}/feed for a
text-only post, POST /{page-id}/photos for an image (+ optional caption)
— same plain-requests convention as automation/twitter/poster.py and
automation/instagram/poster.py, not browser automation. This is the
implementation automation/seo/social_poster.py (module 30.3) already
documented and dispatches to; it just didn't exist as a file yet.

Unlike Instagram, Facebook has a genuine text-only post type, so both
image_url and image_path are optional. image_path (a local file — e.g.
a FastSD-CPU-generated temp image with no public URL yet, as used by
ai/sub_agents/facebook_agent.py) takes priority over image_url when both
are given, since it's uploaded directly rather than needing to already be
hosted somewhere reachable.

FACEBOOK_PAGE_ACCESS_TOKEN must be the long-lived/permanent kind — see
api/config.py's comment on that field for why and how to get one; a
token straight from Graph API Explorer's "Generate Access Token" button
expires in ~2 hours and will make this look like it works only briefly.

Module 40 — page_id/access_token are optional overrides so a caller with
a specific seo_facebook_accounts row (multiple connected Pages) can post
through that one instead of the single default account in .env; omitting
both keeps every pre-module-40 caller (ai/sub_agents/facebook_agent.py
included) working exactly as before.
"""
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union

import requests

from api.config import settings

logger = logging.getLogger(__name__)

GRAPH_API_BASE = "https://graph.facebook.com/v21.0"
TIMEOUT_SECONDS = 60


@dataclass
class PublishResult:
    ok: bool
    detail: str
    external_post_id: Optional[str] = None


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


def post_to_facebook(
    content: str,
    image_url: Optional[str] = None,
    image_path: Optional[Union[str, Path]] = None,
    *,
    page_id: Optional[str] = None,
    access_token: Optional[str] = None,
) -> PublishResult:
    """Never raises — always returns a PublishResult, same graceful-
    degrade convention as every other dispatch target in
    automation/seo/social_poster.py. page_id/access_token override the
    single default .env account (module 40's multi-account support) —
    both must be given together to take effect; omit both to keep using
    the default."""
    page_id = page_id or settings.FACEBOOK_PAGE_ID
    token = access_token or settings.FACEBOOK_PAGE_ACCESS_TOKEN
    if not (page_id and token):
        return PublishResult(
            ok=False, detail="FACEBOOK_PAGE_ID/FACEBOOK_PAGE_ACCESS_TOKEN not set in .env — cannot post"
        )

    try:
        if image_path:
            with open(image_path, "rb") as image_file:
                response = requests.post(
                    f"{GRAPH_API_BASE}/{page_id}/photos",
                    data={"caption": content, "access_token": token},
                    files={"source": image_file},
                    timeout=TIMEOUT_SECONDS,
                )
        elif image_url:
            response = requests.post(
                f"{GRAPH_API_BASE}/{page_id}/photos",
                data={"url": image_url, "caption": content, "access_token": token},
                timeout=TIMEOUT_SECONDS,
            )
        else:
            response = requests.post(
                f"{GRAPH_API_BASE}/{page_id}/feed",
                data={"message": content, "access_token": token},
                timeout=TIMEOUT_SECONDS,
            )
    except requests.RequestException as exc:
        logger.exception("Facebook post failed (network error)")
        return PublishResult(ok=False, detail=f"Network error: {exc}")
    except OSError as exc:
        logger.exception("Facebook post failed (couldn't read image_path)")
        return PublishResult(ok=False, detail=f"Couldn't read image file: {exc}")

    if not response.ok:
        detail = _api_error_detail(response)
        logger.error("Facebook post failed: %s", detail)
        return PublishResult(ok=False, detail=detail)

    payload = response.json()
    # A photo upload returns {"id": <photo_id>, "post_id": <page_post_id>};
    # a plain /feed post returns just {"id": <page_post_id>} — post_id
    # (the actual feed entry) is what matters when present.
    post_id = payload.get("post_id") or payload.get("id")
    logger.info("Posted to Facebook successfully (post_id=%s)", post_id)
    return PublishResult(ok=True, detail="Posted successfully", external_post_id=post_id)


if __name__ == "__main__":
    from agent.logging_config import setup_logging

    setup_logging()
    logger.warning(
        "Manual test would post to a REAL Facebook Page. "
        "Refusing to run automatically — call post_to_facebook() explicitly if you mean it."
    )
