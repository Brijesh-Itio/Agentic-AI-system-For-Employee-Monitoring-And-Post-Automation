"""
MODULE 27 — Personal image-generation worker adapter (current default,
per user request — Puter's free tier doesn't support image generation
via API token, see puter_provider.py's comment for why that one is
parked).

A single Cloudflare Worker endpoint the user runs themselves (proxying
to whatever image model is configured there) — POST {"prompt": ...} with
a bearer token, get raw image bytes back. No JSON envelope, no polling,
one request in and one image out. Verified live this session: a real
~1MB image returned for a test prompt, rendering correctly.

Note: the worker's Content-Type header claims "image/jpeg" but the
actual bytes are PNG (verified via magic-byte sniffing, not the header)
— format is detected from the real bytes, never trusted from that header.
"""
import logging
import time
from typing import Optional

import requests

from ai.images.base import ImageProvider, ImageResult
from api.config import settings

logger = logging.getLogger(__name__)

TIMEOUT_SECONDS = 90

_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
_JPEG_MAGIC = b"\xff\xd8\xff"


def _sniff_format(data: bytes) -> str:
    if data[:8] == _PNG_MAGIC:
        return "png"
    if data[:3] == _JPEG_MAGIC:
        return "jpeg"
    return "png"  # the worker has only ever been observed returning PNG bytes


class ImageWorkerProvider(ImageProvider):
    name = "image_worker"

    def generate(self, prompt: str, *, width: int = 1024, height: int = 1024) -> ImageResult:
        if not (settings.IMAGE_WORKER_URL and settings.IMAGE_WORKER_API_KEY):
            return ImageResult(image_bytes=None, provider=self.name, error="image_worker_not_configured")

        start = time.monotonic()
        try:
            response = requests.post(
                settings.IMAGE_WORKER_URL,
                headers={
                    "Authorization": f"Bearer {settings.IMAGE_WORKER_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={"prompt": prompt},
                timeout=TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            image_bytes = response.content
            latency_ms = (time.monotonic() - start) * 1000

            if not image_bytes:
                return ImageResult(image_bytes=None, provider=self.name, error="empty_response", latency_ms=latency_ms)

            return ImageResult(
                image_bytes=image_bytes,
                provider=self.name,
                format=_sniff_format(image_bytes),
                latency_ms=latency_ms,
            )
        except Exception as exc:
            logger.exception("Image worker generate() failed for prompt %r", prompt)
            return ImageResult(
                image_bytes=None,
                provider=self.name,
                latency_ms=(time.monotonic() - start) * 1000,
                error=str(exc),
            )

    def is_reachable(self) -> bool:
        return bool(settings.IMAGE_WORKER_URL and settings.IMAGE_WORKER_API_KEY)
