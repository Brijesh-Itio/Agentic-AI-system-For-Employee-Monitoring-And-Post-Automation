"""
MODULE 27.1 follow-up — OpenAI image generation adapter (paid, real
pixels, not the prompt-writing step).

This is a genuinely different capability from ai/llm/providers/openai_
provider.py, which only ever writes TEXT (including the image *prompt*
handed to whichever provider draws the picture — see ai/seo/image_
prompt.py). This module is the one that actually draws it, via OpenAI's
Images API (client.images.generate), using the same OPENAI_API_KEY
already configured for text generation — no separate key needed.

Model and pricing verified live against the real account this was set up
on (a `models.list()` call, then a real test generation): the account had
access to gpt-image-1/1-mini/1.5/2, and the newest gpt-image-2.5 pair —
"sunburst" (OpenAI's own docs: "our most capable model for image
generation and editing") and "flare" ("fast, high-quality everyday image
generation"). Defaults to sunburst for quality — the user's explicit
complaint was that generated images weren't relevant/good enough, so the
fast/cheap tier isn't the right default here; flare is a documented,
cheaper fallback via OPENAI_IMAGE_MODEL for anyone who wants it. Priced
per token, not per image ($30/1M image-output-tokens for the 2.5 pair,
$8/1M for gpt-image-1-mini) — a real 1024x1024 test image here cost
about 439 output tokens (~$0.013), confirmed via the API's own real
usage response, not estimated.
"""
import base64
import logging
import time
from typing import Optional

from ai.images.base import ImageProvider, ImageResult
from ai.llm.retry import with_retry
from api.config import settings

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "gpt-image-2.5-sunburst"
# $ per 1M tokens, 2.5-generation pricing (verified against OpenAI's own pricing page)
# — used only to compute ImageResult.cost_estimate, an informational figure; billing
# itself is OpenAI's, not computed by this app.
_PRICE_PER_1M_INPUT_TOKENS = 5.00
_PRICE_PER_1M_OUTPUT_TOKENS = 30.00


def _size_for(width: int, height: int) -> str:
    """Maps the caller's requested pixel size to the nearest size this
    model family actually offers (square / landscape / portrait) —
    verified live that all three work. The image pipeline (ai/seo/
    image_pipeline.py's _resize_to_standard) already center-crops and
    exact-resizes whatever comes back to the real target size afterward,
    same as every other provider here, so an approximate aspect ratio in
    is all that's needed."""
    if width >= height * 1.15:
        return "1536x1024"
    if height >= width * 1.15:
        return "1024x1536"
    return "1024x1024"


class OpenAiImageProvider(ImageProvider):
    name = "openai"

    def __init__(self):
        self._client = None

    def _get_client(self):
        if self._client is None:
            import openai

            self._client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        return self._client

    def generate(self, prompt: str, *, width: int = 1024, height: int = 1024) -> ImageResult:
        if not settings.OPENAI_API_KEY:
            return ImageResult(image_bytes=None, provider=self.name, error="openai_api_key_not_configured")

        model = settings.OPENAI_IMAGE_MODEL or _DEFAULT_MODEL
        size = _size_for(width, height)
        start = time.monotonic()

        def _do_request():
            client = self._get_client()
            return client.images.generate(model=model, prompt=prompt, size=size)

        try:
            response = with_retry(_do_request, max_attempts=2)
            latency_ms = (time.monotonic() - start) * 1000
            b64 = response.data[0].b64_json if response.data else None
            if not b64:
                return ImageResult(image_bytes=None, provider=self.name, latency_ms=latency_ms, error="openai_returned_no_image_data")

            usage = getattr(response, "usage", None)
            cost_estimate: Optional[float] = None
            if usage is not None:
                cost_estimate = (
                    (usage.input_tokens or 0) / 1_000_000 * _PRICE_PER_1M_INPUT_TOKENS
                    + (usage.output_tokens or 0) / 1_000_000 * _PRICE_PER_1M_OUTPUT_TOKENS
                )

            return ImageResult(
                image_bytes=base64.b64decode(b64), provider=self.name, format="png",
                cost_estimate=cost_estimate, latency_ms=latency_ms,
            )
        except Exception as exc:
            logger.exception("OpenAI image generate() failed (model=%s, size=%s)", model, size)
            return ImageResult(
                image_bytes=None, provider=self.name, latency_ms=(time.monotonic() - start) * 1000, error=str(exc),
            )

    def is_reachable(self) -> bool:
        return bool(settings.OPENAI_API_KEY)
