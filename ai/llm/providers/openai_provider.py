"""
MODULE 25.2 — OpenAI adapter.

Lazy-imports the `openai` SDK: only actually required when a task
resolves to "openai" (see ai/llm/factory.py's deferred import). Same
retry/logging/LLMResult shape as ai/llm/providers/claude_provider.py.
Unlike Claude, OpenAI does expose an embeddings endpoint, so this
provider can genuinely serve an "embeddings" task if ever configured to,
though the default stays local (nomic-embed-text via Ollama) — see
ai/llm/factory.py's per-task resolution.
"""
import logging
import time
from typing import Optional

from ai.llm.base import LLMProvider, LLMResult
from ai.llm.retry import with_retry
from api.config import settings

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "gpt-6-sol"
_DEFAULT_EMBED_MODEL = "text-embedding-3-small"


class OpenAIProvider(LLMProvider):
    name = "openai"

    def __init__(self):
        if not settings.OPENAI_API_KEY:
            logger.warning(
                "OpenAIProvider selected but OPENAI_API_KEY is not set — "
                "every call will fail closed with a clear error instead of "
                "silently falling back to another provider."
            )
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                import openai
            except ImportError as exc:
                raise RuntimeError(
                    "The 'openai' package is required to use the OpenAI "
                    "provider. Install it with: pip install openai"
                ) from exc
            self._client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
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
        # `fast` is a no-op here today, same reasoning as ClaudeProvider.
        chosen_model = model or settings.OPENAI_MODEL or _DEFAULT_MODEL
        if not settings.OPENAI_API_KEY:
            return LLMResult(
                text=None, provider=self.name, model=chosen_model,
                error="openai_api_key_not_configured",
            )

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        # Verified live: newer models (gpt-5 and other reasoning-capable models) reject the classic
        # `max_tokens` param outright ("Unsupported parameter... Use 'max_completion_tokens' instead").
        budget = max_tokens or 4096

        def _call(token_budget: int):
            return client.chat.completions.create(
                model=chosen_model, max_completion_tokens=token_budget, messages=messages,
            )

        start = time.monotonic()
        try:
            client = self._get_client()
            response = with_retry(lambda: _call(budget), max_attempts=3)
            text = (response.choices[0].message.content or "").strip()

            # Verified live: on a reasoning-capable model, invisible "reasoning tokens" are drawn from
            # the SAME completion budget as the visible answer — a caller-supplied `max_tokens` sized
            # for a non-reasoning model (Ollama, gpt-4-class) can be entirely consumed by reasoning,
            # leaving finish_reason="length" and an EMPTY message with no error raised. Detected here
            # (rather than masked by silently padding every call's budget) and retried once with a much
            # larger budget so a caller never gets a false-empty result without at least one real attempt
            # at a visible answer; a caller wanting to avoid the extra cost/latency this retry can add
            # should pass a generous max_tokens for reasoning models in the first place.
            if not text and response.choices[0].finish_reason == "length":
                bigger = max(budget * 6, 2048)
                logger.warning(
                    "OpenAI %s returned an empty message after using its whole %d-token budget on internal "
                    "reasoning — retrying once with max_completion_tokens=%d", chosen_model, budget, bigger,
                )
                response = with_retry(lambda: _call(bigger), max_attempts=2)
                text = (response.choices[0].message.content or "").strip()

            latency_ms = (time.monotonic() - start) * 1000
            return LLMResult(
                text=text,
                provider=self.name,
                model=chosen_model,
                tokens_in=response.usage.prompt_tokens,
                tokens_out=response.usage.completion_tokens,
                latency_ms=latency_ms,
            )
        except Exception as exc:
            logger.exception("OpenAI generate() failed (model=%s)", chosen_model)
            return LLMResult(
                text=None, provider=self.name, model=chosen_model,
                latency_ms=(time.monotonic() - start) * 1000, error=str(exc),
            )

    def embed(self, text: str) -> Optional[list]:
        if not settings.OPENAI_API_KEY:
            logger.warning("OpenAIProvider.embed() called without OPENAI_API_KEY configured")
            return None
        try:
            client = self._get_client()
            embed_model = settings.OPENAI_EMBED_MODEL or _DEFAULT_EMBED_MODEL
            response = with_retry(
                lambda: client.embeddings.create(model=embed_model, input=text), max_attempts=3
            )
            return response.data[0].embedding
        except Exception:
            logger.exception("OpenAI embed() failed")
            return None

    def is_reachable(self) -> bool:
        return bool(settings.OPENAI_API_KEY)
