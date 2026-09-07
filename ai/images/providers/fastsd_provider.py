"""
MODULE 27.1 — FastSD CPU adapter (local, zero-cost — the default provider).

Reuses automation/linkedin/image_generator.py's low-level FastSD CPU call
(module 18.3's call_fastsd()/is_available()) rather than reimplementing
the HTTP request, but skips that module's LinkedIn-post-specific prompt
derivation step — SEO pipelines build and pass their own image prompt
directly.
"""
import logging
import time
from typing import Optional

from ai.images.base import ImageProvider, ImageResult
from automation.linkedin.image_generator import call_fastsd, is_available

logger = logging.getLogger(__name__)


class FastSdProvider(ImageProvider):
    name = "fastsd"

    def generate(self, prompt: str, *, width: int = 1024, height: int = 1024) -> ImageResult:
        # width/height accepted for interface consistency with other
        # providers but not honoured — module 18.3's LCM-LoRA config is
        # deliberately fixed at 512x512 for CPU-inference speed; changing
        # it would undo that tradeoff. Note this in the roadmap, not force
        # a config a local CPU model can't actually deliver in time.
        start = time.monotonic()
        if not is_available():
            return ImageResult(image_bytes=None, provider=self.name, error="fastsd_not_reachable")

        image_bytes = call_fastsd(prompt)
        latency_ms = (time.monotonic() - start) * 1000
        if image_bytes is None:
            return ImageResult(
                image_bytes=None, provider=self.name, latency_ms=latency_ms, error="fastsd_generate_failed"
            )
        return ImageResult(image_bytes=image_bytes, provider=self.name, format="jpg", latency_ms=latency_ms)

    def is_reachable(self) -> bool:
        return is_available()
