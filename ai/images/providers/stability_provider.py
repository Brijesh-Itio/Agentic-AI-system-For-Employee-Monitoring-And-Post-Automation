"""
MODULE 27.1 — Stability AI adapter (paid image generation).

Plain REST via `requests` (Stability's API needs no SDK), same
fail-closed-when-unconfigured convention as ai/llm/providers/
claude_provider.py: off by default, and pointing an image task at this
provider is a config change (api/config.py's STABILITY_API_KEY +
ai/images/factory.py's resolution), never a pipeline code change.

Flux isn't wired in yet — there's no single canonical "Flux API" (it's
offered through several different hosts: Replicate, fal.ai, Black Forest
Labs directly, each with a different request shape), so it wasn't guessed
at. Adding it later means one more file in this providers/ package
following this exact pattern, once a specific host is chosen.
"""
import logging
import time
from typing import Optional

import requests

from ai.images.base import ImageProvider, ImageResult
from ai.llm.retry import with_retry
from api.config import settings

logger = logging.getLogger(__name__)

API_URL = "https://api.stability.ai/v2beta/stable-image/generate/core"
TIMEOUT_SECONDS = 60


class StabilityProvider(ImageProvider):
    name = "stability"

    def generate(self, prompt: str, *, width: int = 1024, height: int = 1024) -> ImageResult:
        if not settings.STABILITY_API_KEY:
            return ImageResult(
                image_bytes=None, provider=self.name, error="stability_api_key_not_configured"
            )

        start = time.monotonic()

        def _do_request():
            response = requests.post(
                API_URL,
                headers={
                    "Authorization": f"Bearer {settings.STABILITY_API_KEY}",
                    "Accept": "image/*",
                },
                # Stability's v2beta endpoints require multipart/form-data
                # even with no actual file input — an empty "none" file
                # field is their documented workaround, not a mistake here.
                files={"none": ""},
                data={"prompt": prompt, "output_format": "jpeg"},
                timeout=TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            return response

        try:
            response = with_retry(_do_request, max_attempts=3, retry_on=(requests.RequestException,))
            latency_ms = (time.monotonic() - start) * 1000
            return ImageResult(
                image_bytes=response.content, provider=self.name, format="jpeg", latency_ms=latency_ms
            )
        except Exception as exc:
            logger.exception("Stability AI generate() failed")
            return ImageResult(
                image_bytes=None,
                provider=self.name,
                latency_ms=(time.monotonic() - start) * 1000,
                error=str(exc),
            )

    def is_reachable(self) -> bool:
        return bool(settings.STABILITY_API_KEY)
