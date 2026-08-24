"""
MODULE 18.3 — Image Finder

Finds an image matching the post topic via the Pexels API and downloads it
to a temp file for poster.py to attach.

Originally specced as Playwright scraping Pexels' search page directly
(matching DEVELOPMENT.md's "no image API" rule), but verified empirically
that both Pexels and Pixabay sit behind Cloudflare bot-detection that
blocks headless browsers with a "Verify you are human" challenge before
any content loads — not a fixable selector issue. The free, official
Pexels API (no cost, instant signup at pexels.com/api) is the reliable
alternative; this is a deliberate, user-approved exception to the
Playwright-only rule for this one component.
"""
import logging
import re
import tempfile
from pathlib import Path
from typing import Optional

import requests

from api.config import settings

logger = logging.getLogger(__name__)

PEXELS_SEARCH_ENDPOINT = "https://api.pexels.com/v1/search"
REQUEST_TIMEOUT_SECONDS = 15


def _search_keywords(topic: str) -> str:
    """Reduce a full post topic down to a short, image-searchable phrase —
    Pexels returns nothing useful for a long sentence."""
    words = re.findall(r"[A-Za-z]+", topic)
    stopwords = {"a", "an", "the", "of", "for", "and", "or", "is", "in", "on", "to", "what", "how"}
    keywords = [w for w in words if w.lower() not in stopwords][:4]
    return " ".join(keywords) or "technology"


def find_image(topic: str) -> Optional[Path]:
    """Returns a local temp file path to a downloaded image, or None
    (never raises) if no key is configured, Pexels is unreachable, or no
    result matches — poster.py treats a missing image as "post text-only",
    not a failure."""
    if not settings.PEXELS_API_KEY:
        logger.info("PEXELS_API_KEY not configured — skipping image, post will go out text-only")
        return None

    query = _search_keywords(topic)
    try:
        response = requests.get(
            PEXELS_SEARCH_ENDPOINT,
            headers={"Authorization": settings.PEXELS_API_KEY},
            params={"query": query, "per_page": 1, "orientation": "landscape"},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        photos = response.json().get("photos", [])
        if not photos:
            logger.info("No Pexels results for query %r — post will go out text-only", query)
            return None

        image_url = photos[0]["src"]["large"]
        image_response = requests.get(image_url, timeout=REQUEST_TIMEOUT_SECONDS)
        image_response.raise_for_status()

        fd, temp_path = tempfile.mkstemp(suffix=".jpg", prefix="workpulse_linkedin_")
        Path(temp_path).write_bytes(image_response.content)
        import os
        os.close(fd)

        logger.info("Downloaded LinkedIn post image for %r -> %s", query, temp_path)
        return Path(temp_path)

    except requests.RequestException:
        logger.exception("Pexels image search failed for topic %r (query=%r)", topic, query)
        return None


if __name__ == "__main__":
    from agent.logging_config import setup_logging

    setup_logging()
    logger.info("Module 18.3 manual test: finding an image")
    path = find_image("agentic AI automation")
    print("Downloaded to:", path)
