"""
Pinterest Pin Publishing (API v5).

Real REST calls against Pinterest's official API v5, no SDK — same
plain-requests convention as automation/instagram/poster.py and
automation/twitter/poster.py. Endpoint/body shape (POST /v5/pins with
board_id, title, description, media_source.source_type="image_url")
verified against developers.pinterest.com's current API v5 docs this
session, not guessed.

Like Instagram, Pinterest has no text-only post type — every Pin needs
an image (a public URL, same as every other image this codebase already
generates and uploads to the site's own server) and a destination
board_id. This codebase's single "content" text field (shared across
every platform's post) is treated as the Pin's description; a title is
derived from its first sentence rather than requiring a second input
field, keeping the data model uniform across platforms rather than
adding a Pinterest-only "title" field just for this one platform.
"""
import logging
import re
from dataclasses import dataclass
from typing import Optional

import requests

from api.config import settings

logger = logging.getLogger(__name__)

API_BASE_URL = "https://api.pinterest.com/v5"
TIMEOUT_SECONDS = 30
_MAX_TITLE_LENGTH = 100  # Pinterest's own limit on a Pin's title
_MAX_DESCRIPTION_LENGTH = 500  # Pinterest's own limit on a Pin's description


@dataclass
class PublishResult:
    ok: bool
    detail: str
    external_post_id: Optional[str] = None


def _credentials_configured() -> bool:
    return bool(settings.PINTEREST_ACCESS_TOKEN and settings.PINTEREST_BOARD_ID)


def _api_error_detail(response: Optional[requests.Response]) -> str:
    if response is None:
        return "no response"
    try:
        payload = response.json()
        message = payload.get("message") or payload.get("error")
        if message:
            return message
    except ValueError:
        pass
    return response.text[:300]


def _title_from_description(description: str) -> str:
    """Pinterest wants a short title separate from the longer
    description — derived here from the first sentence rather than
    requiring a caller to supply one, since every other platform this
    codebase posts to only needs one text field."""
    first_line = description.strip().split("\n", 1)[0]
    first_sentence = re.split(r"(?<=[.!?])\s", first_line, 1)[0].strip()
    if len(first_sentence) > _MAX_TITLE_LENGTH:
        return first_sentence[: _MAX_TITLE_LENGTH - 1].rstrip() + "…"
    return first_sentence


def post_to_pinterest(
    description: str,
    image_url: Optional[str] = None,
    *,
    board_id: Optional[str] = None,
    link: Optional[str] = None,
) -> PublishResult:
    """Never raises — always returns a PublishResult, same graceful-
    degrade convention as every other dispatch target in
    automation/seo/social_poster.py. board_id defaults to
    settings.PINTEREST_BOARD_ID when not given explicitly."""
    if not settings.PINTEREST_ACCESS_TOKEN:
        return PublishResult(ok=False, detail="PINTEREST_ACCESS_TOKEN not set in .env — cannot post")

    resolved_board_id = board_id or settings.PINTEREST_BOARD_ID
    if not resolved_board_id:
        return PublishResult(ok=False, detail="No Pinterest board configured — set PINTEREST_BOARD_ID in .env")

    if not image_url:
        return PublishResult(
            ok=False,
            detail="Pinterest has no text-only Pin type — this post needs an image URL before it can publish",
        )

    body = {
        "board_id": resolved_board_id,
        "title": _title_from_description(description),
        "description": description[:_MAX_DESCRIPTION_LENGTH],
        "media_source": {"source_type": "image_url", "url": image_url},
    }
    if link:
        body["link"] = link

    try:
        response = requests.post(
            f"{API_BASE_URL}/pins",
            json=body,
            headers={"Authorization": f"Bearer {settings.PINTEREST_ACCESS_TOKEN}"},
            timeout=TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        logger.exception("Pinterest pin creation failed (network error)")
        return PublishResult(ok=False, detail=f"Network error: {exc}")

    if not response.ok:
        detail = _api_error_detail(response)
        logger.error("Pinterest pin creation failed: %s", detail)
        return PublishResult(ok=False, detail=detail)

    pin_id = response.json().get("id")
    logger.info("Posted to Pinterest successfully (pin_id=%s)", pin_id)
    return PublishResult(ok=True, detail="Pin created successfully", external_post_id=pin_id)


if __name__ == "__main__":
    from agent.logging_config import setup_logging

    setup_logging()
    logger.warning(
        "Manual test would post to a REAL Pinterest board. "
        "Refusing to run automatically — call post_to_pinterest() explicitly if you mean it."
    )
