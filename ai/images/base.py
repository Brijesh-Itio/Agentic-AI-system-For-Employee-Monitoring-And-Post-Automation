"""
MODULE 27.1 — Generic image provider interface.

Same shape as ai/llm/base.py: every adapter (FastSdProvider, PexelsProvider,
StabilityProvider) implements this and returns this same ImageResult, so
callers never branch on which provider actually ran.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class ImageResult:
    image_bytes: Optional[bytes]
    provider: str
    format: Optional[str] = None  # "jpg", "png", ...
    cost_estimate: Optional[float] = None
    latency_ms: Optional[float] = None
    error: Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.error is None and self.image_bytes is not None


class ImageProvider(ABC):
    """name identifies the provider in logs — must match the key used to
    select it in ai/images/factory.py's _build_provider()."""

    name: str

    @abstractmethod
    def generate(self, prompt: str, *, width: int = 1024, height: int = 1024) -> ImageResult:
        """For a generative provider (FastSD, Stability), prompt is a
        scene description to render. For a stock-photo provider
        (Pexels), prompt is treated as a search query instead — "generate"
        here means "produce a usable image for this prompt," not
        literally "diffusion-generate." Must never raise; failures come
        back as ImageResult(image_bytes=None, error=...)."""
        raise NotImplementedError

    @abstractmethod
    def is_reachable(self) -> bool:
        raise NotImplementedError
