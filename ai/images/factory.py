"""
MODULE 27.1 — Image provider factory.

Same pattern as ai/llm/factory.py: resolves which provider a given task
uses via IMAGE_PROVIDER_<TASK> env override -> settings.IMAGE_PROVIDER_DEFAULT
-> "fastsd". Local FastSD CPU is the zero-cost default; pointing a task
at Pexels (free stock) or Stability (paid) is a config change, not a
pipeline code change.
"""
import logging
import os
from typing import Dict

from ai.images.base import ImageProvider
from ai.images.providers.fastsd_provider import FastSdProvider
from ai.images.providers.pexels_provider import PexelsProvider
from api.config import settings

logger = logging.getLogger(__name__)

_provider_cache: Dict[str, ImageProvider] = {}


def _build_provider(provider_name: str) -> ImageProvider:
    if provider_name == "fastsd":
        return FastSdProvider()
    if provider_name == "pexels":
        return PexelsProvider()
    if provider_name == "stability":
        # Deferred import: keeps this factory from needing anything
        # stability-specific until a task actually resolves to it.
        from ai.images.providers.stability_provider import StabilityProvider

        return StabilityProvider()

    logger.warning("Unknown image provider %r requested, falling back to fastsd", provider_name)
    return FastSdProvider()


def resolve_provider_name(task: str = "default") -> str:
    override = os.environ.get(f"IMAGE_PROVIDER_{task.upper()}")
    if override:
        return override.strip().lower()
    return (settings.IMAGE_PROVIDER_DEFAULT or "fastsd").strip().lower()


def get_provider(task: str = "default") -> ImageProvider:
    provider_name = resolve_provider_name(task)
    if provider_name not in _provider_cache:
        _provider_cache[provider_name] = _build_provider(provider_name)
    return _provider_cache[provider_name]
