"""
MODULE 25.1 — Ollama adapter.

Wraps the existing ai/ollama_client.py (generate/embed/is_reachable)
behind the generic LLMProvider interface. No behaviour change versus
calling ai.ollama_client directly: same models, same two-timeout-budget
convention, same graceful-None-on-failure degrade. This is purely an
adapter so SEO pipelines go through ai.llm.factory instead of importing
Ollama specifically — every existing caller of ai/ollama_client.py
(DAR generator, team analysis, Master Agent) is untouched.
"""
import logging
import time
from typing import Optional

from ai import ollama_client
from ai.llm.base import LLMProvider, LLMResult
from api.config import settings

logger = logging.getLogger(__name__)


class OllamaProvider(LLMProvider):
    name = "ollama"

    def generate(
        self,
        prompt: str,
        *,
        system: Optional[str] = None,
        model: Optional[str] = None,
        fast: bool = False,
        max_tokens: Optional[int] = None,
    ) -> LLMResult:
        # ai.ollama_client.generate() has no system-prompt parameter (see
        # its own docstring — every module builds one prompt string) —
        # fold system in ahead of the task prompt, same as every existing
        # caller already constructs its prompts.
        full_prompt = f"{system}\n\n{prompt}" if system else prompt
        chosen_model = model or (settings.OLLAMA_FAST_MODEL if fast else settings.OLLAMA_MODEL)

        start = time.monotonic()
        text = ollama_client.generate(full_prompt, model=model, fast=fast, max_tokens=max_tokens)
        latency_ms = (time.monotonic() - start) * 1000

        if text is None:
            return LLMResult(
                text=None,
                provider=self.name,
                model=chosen_model,
                latency_ms=latency_ms,
                error="ollama_generate_failed",
            )
        return LLMResult(text=text, provider=self.name, model=chosen_model, latency_ms=latency_ms)

    def embed(self, text: str) -> Optional[list]:
        return ollama_client.embed(text)

    def is_reachable(self) -> bool:
        return ollama_client.is_reachable()
