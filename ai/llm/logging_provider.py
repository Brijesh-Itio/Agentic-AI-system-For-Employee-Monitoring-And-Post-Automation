"""
MODULE 25.3 — Usage-logging decorator.

Wraps any LLMProvider so every generate()/embed() call writes one row to
llm_usage_log (agent/database.py), regardless of which underlying
provider actually ran. ai/llm/factory.get_provider() returns providers
wrapped in this — no per-caller boilerplate anywhere in the SEO
pipelines (module 26+) that call it.
"""
import logging
from typing import Optional

from agent import database
from ai.llm.base import LLMProvider, LLMResult

logger = logging.getLogger(__name__)


class LoggingProvider(LLMProvider):
    def __init__(self, inner: LLMProvider, task: str, site_id: Optional[int] = None):
        self._inner = inner
        self._task = task
        self._site_id = site_id
        self.name = inner.name

    def generate(
        self,
        prompt: str,
        *,
        system: Optional[str] = None,
        model: Optional[str] = None,
        fast: bool = False,
        max_tokens: Optional[int] = None,
    ) -> LLMResult:
        result = self._inner.generate(prompt, system=system, model=model, fast=fast, max_tokens=max_tokens)
        self._log_generate(result)
        return result

    def embed(self, text: str) -> Optional[list]:
        vector = self._inner.embed(text)
        self._log_embed(success=vector is not None)
        return vector

    def is_reachable(self) -> bool:
        return self._inner.is_reachable()

    def _log_generate(self, result: LLMResult) -> None:
        try:
            database.log_llm_usage(
                task=self._task,
                provider=result.provider,
                model=result.model,
                success=result.ok,
                site_id=self._site_id,
                tokens_in=result.tokens_in,
                tokens_out=result.tokens_out,
                cost_estimate=result.cost_estimate,
                latency_ms=result.latency_ms,
                error=result.error,
            )
        except Exception:
            # A logging failure must never mask the caller's real LLM
            # result — this is observability, not part of the request path.
            logger.exception(
                "Failed to write llm_usage_log row (task=%s, provider=%s)", self._task, result.provider
            )

    def _log_embed(self, success: bool) -> None:
        try:
            database.log_llm_usage(
                task=f"{self._task}:embed",
                provider=self._inner.name,
                model=None,
                success=success,
                site_id=self._site_id,
            )
        except Exception:
            logger.exception("Failed to write llm_usage_log row for embed (task=%s)", self._task)
