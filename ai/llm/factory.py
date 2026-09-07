"""
MODULE 25.1 — Provider factory.

The single place that decides which LLM backend a given SEO task actually
runs on. Resolution order per task:

    1. SEO_LLM_PROVIDER_<TASK> env var (per-task override, e.g.
       SEO_LLM_PROVIDER_CONTENT=claude) — read directly from the
       environment rather than a predeclared Settings field, so a brand
       new task name never requires a code change here.
    2. settings.SEO_LLM_PROVIDER_DEFAULT (api/config.py)
    3. "ollama" (hardcoded final fallback)

Everything downstream calls ai.llm.factory.get_provider(task) and treats
the result identically — adding a provider or repointing one task at a
different one is a config change, never a pipeline code change.
"""
import logging
import os
from typing import Dict

from ai.llm.base import LLMProvider
from ai.llm.providers.ollama_provider import OllamaProvider
from api.config import settings

logger = logging.getLogger(__name__)

# Provider adapters are stateless (they build a fresh underlying client
# per call, same as ai/ollama_client.py) — caching the adapter instance
# itself is safe and just avoids re-importing an SDK on every call.
_provider_cache: Dict[str, LLMProvider] = {}


def _build_provider(provider_name: str) -> LLMProvider:
    if provider_name == "ollama":
        return OllamaProvider()
    if provider_name == "claude":
        # Deferred import: module 25.2. Keeps `anthropic` an optional
        # dependency — the app boots fine without it as long as no task
        # actually resolves to "claude".
        from ai.llm.providers.claude_provider import ClaudeProvider

        return ClaudeProvider()
    if provider_name == "openai":
        # Deferred import: module 25.2. Same optional-dependency reasoning.
        from ai.llm.providers.openai_provider import OpenAIProvider

        return OpenAIProvider()

    logger.warning("Unknown SEO LLM provider %r requested, falling back to ollama", provider_name)
    return OllamaProvider()


def resolve_provider_name(task: str = "default") -> str:
    override = os.environ.get(f"SEO_LLM_PROVIDER_{task.upper()}")
    if override:
        return override.strip().lower()
    return (settings.SEO_LLM_PROVIDER_DEFAULT or "ollama").strip().lower()


def get_provider(task: str = "default", site_id=None) -> LLMProvider:
    """Returns a provider wrapped for automatic llm_usage_log logging
    (ai/llm/logging_provider.py). The underlying adapter instance is
    cached by provider name (SDK clients are worth reusing); the logging
    wrapper itself is cheap and built fresh per call so each call's
    task/site_id context is recorded correctly."""
    provider_name = resolve_provider_name(task)
    if provider_name not in _provider_cache:
        _provider_cache[provider_name] = _build_provider(provider_name)

    from ai.llm.logging_provider import LoggingProvider

    return LoggingProvider(_provider_cache[provider_name], task=task, site_id=site_id)
