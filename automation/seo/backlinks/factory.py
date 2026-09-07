"""
MODULE 31.1 — Backlink/mention provider factory.

Same pattern as ai/llm/factory.py and ai/images/factory.py: one place
resolves which provider a task uses. "google_alerts" (free) is the only
provider actually built and wired in — "ahrefs" is a deliberate,
documented extension point, not guessed at: unlike Stability AI (module
27.1, whose plain-REST v2beta shape is stable and well-documented) or
Claude/OpenAI (whose SDKs are authoritative), Ahrefs' current API surface
wasn't something this session could verify against real, current
documentation, and shipping a plausible-but-wrong integration would be
worse than being upfront that it isn't built yet — see module 31's
DEVELOPMENT.md entry. Requesting "ahrefs" raises a clear, actionable
error rather than silently falling back or pretending to work.
"""
import logging
import os

from automation.seo.backlinks.base import BacklinkProvider
from automation.seo.backlinks.google_alerts_provider import GoogleAlertsProvider
from api.config import settings

logger = logging.getLogger(__name__)

_provider_cache: dict = {}


def _build_provider(provider_name: str) -> BacklinkProvider:
    if provider_name == "google_alerts":
        return GoogleAlertsProvider()
    if provider_name == "ahrefs":
        raise NotImplementedError(
            "The Ahrefs backlink provider is a documented extension point, not yet built — "
            "its exact API request/response shape wasn't verified against current Ahrefs "
            "documentation this session, so a guessed implementation wasn't shipped. Add "
            "automation/seo/backlinks/ahrefs_provider.py following the GoogleAlertsProvider "
            "pattern once real Ahrefs API docs/credentials are available to build it against."
        )
    logger.warning("Unknown backlink provider %r requested, falling back to google_alerts", provider_name)
    return GoogleAlertsProvider()


def resolve_provider_name(task: str = "default") -> str:
    override = os.environ.get(f"BACKLINK_PROVIDER_{task.upper()}")
    if override:
        return override.strip().lower()
    return (settings.BACKLINK_PROVIDER_DEFAULT or "google_alerts").strip().lower()


def get_provider(task: str = "default") -> BacklinkProvider:
    provider_name = resolve_provider_name(task)
    if provider_name not in _provider_cache:
        _provider_cache[provider_name] = _build_provider(provider_name)
    return _provider_cache[provider_name]
