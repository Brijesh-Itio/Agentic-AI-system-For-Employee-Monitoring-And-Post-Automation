"""
MODULE 27.2 — PNG/JPG -> WebP conversion.

Uses Pillow (already a dependency — Module 3's screenshot system already
relies on it), not the blueprint's Node/Sharp suggestion, since this is a
Python backend. Pure in-memory bytes-in/bytes-out: callers (the CMS image
upload step, once module 27's later sub-modules wire it in) decide what
to do with the result — write to disk, upload to a CMS, etc.
"""
import io
import logging
from dataclasses import dataclass
from typing import Optional

from PIL import Image

logger = logging.getLogger(__name__)

DEFAULT_QUALITY = 80  # blueprint's own "optimal size-vs-quality ratio" figure


@dataclass
class WebpConversionResult:
    webp_bytes: bytes
    original_size: int
    webp_size: int

    @property
    def reduction_pct(self) -> float:
        if self.original_size == 0:
            return 0.0
        return round((1 - self.webp_size / self.original_size) * 100, 1)


def convert_to_webp(image_bytes: bytes, *, quality: int = DEFAULT_QUALITY) -> Optional[WebpConversionResult]:
    """Never raises — returns None on failure (corrupt input, an
    unsupported format Pillow can't decode), matching this codebase's
    graceful-degrade convention."""
    try:
        image = Image.open(io.BytesIO(image_bytes))
        # Preserve transparency when it exists, otherwise flatten to RGB —
        # WebP supports both, but saving a palette/"P" mode image without
        # this conversion first can produce incorrect colours.
        if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
            image = image.convert("RGBA")
        else:
            image = image.convert("RGB")

        output = io.BytesIO()
        image.save(output, format="WEBP", quality=quality)
        webp_bytes = output.getvalue()
        return WebpConversionResult(
            webp_bytes=webp_bytes, original_size=len(image_bytes), webp_size=len(webp_bytes)
        )
    except Exception:
        logger.exception("WebP conversion failed")
        return None
