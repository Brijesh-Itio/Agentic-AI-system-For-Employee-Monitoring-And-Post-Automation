"""
MODULE 25.2 — Claude adapter.

Lazy-imports the `anthropic` SDK: only actually required when a task
resolves to "claude" (see ai/llm/factory.py's deferred import). Applies
ai/llm/retry.py around the network call since a paid, rate-limited API
can hit transient 429/5xx/timeout errors in ways the local-only Ollama
adapter never does. Returns the same LLMResult shape as every other
provider — callers never know or care which one actually ran.
"""
import logging
import time
from typing import Optional

from ai.llm.base import LLMProvider, LLMResult
from ai.llm.retry import with_retry
from api.config import settings

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "claude-sonnet-5"


class ClaudeProvider(LLMProvider):
    name = "claude"

    def __init__(self):
        if not settings.CLAUDE_API_KEY:
            logger.warning(
                "ClaudeProvider selected but CLAUDE_API_KEY is not set — "
                "every call will fail closed with a clear error instead of "
                "silently falling back to another provider."
            )
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                import anthropic
            except ImportError as exc:
                raise RuntimeError(
                    "The 'anthropic' package is required to use the Claude "
                    "provider. Install it with: pip install anthropic"
                ) from exc
            self._client = anthropic.Anthropic(api_key=settings.CLAUDE_API_KEY)
        return self._client

    def generate(
        self,
        prompt: str,
        *,
        system: Optional[str] = None,
        model: Optional[str] = None,
        fast: bool = False,
        max_tokens: Optional[int] = None,
    ) -> LLMResult:
        # `fast` is a no-op here today (reserved for future model tiering,
        # e.g. a cheaper Claude model) — Ollama's fast/slow split exists
        # because of CPU inference time, which doesn't apply to a paid API.
        chosen_model = model or settings.CLAUDE_MODEL or _DEFAULT_MODEL
        if not settings.CLAUDE_API_KEY:
            return LLMResult(
                text=None, provider=self.name, model=chosen_model,
                error="claude_api_key_not_configured",
            )

        start = time.monotonic()
        try:
            client = self._get_client()
            kwargs = {
                "model": chosen_model,
                "max_tokens": max_tokens or 4096,
                "messages": [{"role": "user", "content": prompt}],
            }
            if system:
                kwargs["system"] = system

            response = with_retry(lambda: client.messages.create(**kwargs), max_attempts=3)
            latency_ms = (time.monotonic() - start) * 1000
            text = "".join(
                block.text for block in response.content if getattr(block, "type", None) == "text"
            )
            return LLMResult(
                text=text.strip(),
                provider=self.name,
                model=chosen_model,
                tokens_in=response.usage.input_tokens,
                tokens_out=response.usage.output_tokens,
                latency_ms=latency_ms,
            )
        except Exception as exc:
            logger.exception("Claude generate() failed (model=%s)", chosen_model)
            return LLMResult(
                text=None, provider=self.name, model=chosen_model,
                latency_ms=(time.monotonic() - start) * 1000, error=str(exc),
            )

    def embed(self, text: str) -> Optional[list]:
        # Anthropic has no first-party embeddings endpoint. Embeddings for
        # SEO pipelines (interlink matching, etc.) stay on the local
        # nomic-embed-text model regardless of which provider is doing
        # text generation — a "claude" task for content writing can leave
        # an "embeddings" task on its "ollama" default (see factory.py's
        # per-task resolution), which is the expected configuration.
        logger.warning("ClaudeProvider.embed() called — Claude has no embeddings API, returning None")
        return None

    def is_reachable(self) -> bool:
        # Credentials-configured check, not a live network ping — matches
        # the codebase's existing _credentials_configured()-style guard
        # (automation/email/sender.py, automation/linkedin/poster.py)
        # rather than spending a paid API call just to check status.
        return bool(settings.CLAUDE_API_KEY)
