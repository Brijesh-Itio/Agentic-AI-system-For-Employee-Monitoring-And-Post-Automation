"""
MODULE 27.1 — Pexels stock-photo adapter (free fallback provider).

Reuses automation/linkedin/image_finder.py's Pexels search/download logic
directly (module 18.3) rather than reimplementing it — find_image(topic)
is already generic (keyword search -> download), not LinkedIn-post-specific.
"""
import logging

from ai.images.base import ImageProvider, ImageResult
from api.config import settings
from automation.linkedin.image_finder import find_image

logger = logging.getLogger(__name__)


class PexelsProvider(ImageProvider):
    name = "pexels"

    def generate(self, prompt: str, *, width: int = 1024, height: int = 1024) -> ImageResult:
        # Pexels searches rather than generates — prompt is treated as a
        # search query (see ai/images/base.py's docstring on this).
        path = find_image(prompt)
        if path is None:
            return ImageResult(
                image_bytes=None, provider=self.name, error="pexels_no_result_or_not_configured"
            )
        try:
            image_bytes = path.read_bytes()
        finally:
            path.unlink(missing_ok=True)
        return ImageResult(image_bytes=image_bytes, provider=self.name, format="jpg")

    def is_reachable(self) -> bool:
        return bool(settings.PEXELS_API_KEY)
