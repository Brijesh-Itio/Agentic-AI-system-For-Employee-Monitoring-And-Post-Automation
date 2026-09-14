"""
MODULE 27 — Puter.js image generation adapter (current default, per user request).

Puter offers free, "user-pays-with-their-own-account" image generation
through an OpenAI-compatible REST endpoint (api.puter.com/puterai/openai/
v1/images/generations) — no Node.js SDK or browser needed, just a bearer
token (settings.PUTER_AUTH_TOKEN, from https://puter.com/dashboard#account
-> API token -> Create token). Plain `requests`, same as
stability_provider.py, not the `openai` pip package, to avoid adding a
dependency for what's a single POST.

FastSD CPU (fastsd_provider.py) is unaffected by this and stays available
as a zero-cost local fallback — switch back with
IMAGE_PROVIDER_DEFAULT=fastsd (api/config.py) or a per-task
IMAGE_PROVIDER_<TASK> override, no code change needed.
"""
import base64
import logging
import time

import requests

from ai.images.base import ImageProvider, ImageResult
from ai.llm.retry import with_retry
from api.config import settings

logger = logging.getLogger(__name__)

API_URL = "https://api.puter.com/puterai/openai/v1/images/generations"
MODEL = "gpt-image-2"
TIMEOUT_SECONDS = 90


class PuterProvider(ImageProvider):
    name = "puter"

    def generate(self, prompt: str, *, width: int = 1024, height: int = 1024) -> ImageResult:
        if not settings.PUTER_AUTH_TOKEN:
            return ImageResult(image_bytes=None, provider=self.name, error="puter_auth_token_not_configured")

        start = time.monotonic()

        def _do_request():
            response = requests.post(
                API_URL,
                headers={"Authorization": f"Bearer {settings.PUTER_AUTH_TOKEN}"},
                json={"model": MODEL, "prompt": prompt, "size": f"{width}x{height}"},
                timeout=TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            return response

        try:
            response = with_retry(_do_request, max_attempts=3, retry_on=(requests.RequestException,))
            entries = response.json().get("data") or []
            if not entries:
                return ImageResult(
                    image_bytes=None,
                    provider=self.name,
                    latency_ms=(time.monotonic() - start) * 1000,
                    error="puter_returned_no_images",
                )

            entry = entries[0]
            if "b64_json" in entry:
                image_bytes = base64.b64decode(entry["b64_json"])
            elif "url" in entry:
                image_response = requests.get(entry["url"], timeout=TIMEOUT_SECONDS)
                image_response.raise_for_status()
                image_bytes = image_response.content
            else:
                return ImageResult(
                    image_bytes=None,
                    provider=self.name,
                    latency_ms=(time.monotonic() - start) * 1000,
                    error=f"unrecognised_response_shape: {list(entry.keys())}",
                )

            return ImageResult(
                image_bytes=image_bytes,
                provider=self.name,
                format="png",
                latency_ms=(time.monotonic() - start) * 1000,
            )
        except Exception as exc:
            logger.exception("Puter image generate() failed for prompt %r", prompt)
            return ImageResult(
                image_bytes=None,
                provider=self.name,
                latency_ms=(time.monotonic() - start) * 1000,
                error=str(exc),
            )

    def is_reachable(self) -> bool:
        return bool(settings.PUTER_AUTH_TOKEN)
