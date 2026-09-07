"""
MODULE 25.1 — Generic LLM provider interface.

Every provider adapter (OllamaProvider today, ClaudeProvider/OpenAIProvider
from module 25.2 onward) implements this ABC and returns this same
LLMResult shape, so callers (SEO pipelines, ai/seo_master_agent.py) never
branch on which provider is actually running underneath — they call
ai.llm.factory.get_provider(task) once and treat the result identically
regardless of provider.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class LLMResult:
    text: Optional[str]
    provider: str
    model: str
    tokens_in: Optional[int] = None
    tokens_out: Optional[int] = None
    cost_estimate: Optional[float] = None
    latency_ms: Optional[float] = None
    error: Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.error is None and self.text is not None


class LLMProvider(ABC):
    """name identifies the provider in logs and in llm_usage_log rows
    (module 25.3) — must match the key used to select it in
    ai/llm/factory.py's _build_provider()."""

    name: str

    @abstractmethod
    def generate(
        self,
        prompt: str,
        *,
        system: Optional[str] = None,
        model: Optional[str] = None,
        fast: bool = False,
        max_tokens: Optional[int] = None,
    ) -> LLMResult:
        """Single-shot text generation. Must never raise — failures come
        back as an LLMResult with text=None and error set, matching the
        existing ai/ollama_client.py convention of degrading to a safe
        default instead of crashing a caller (often a background thread)."""
        raise NotImplementedError

    @abstractmethod
    def embed(self, text: str) -> Optional[list]:
        """Returns an embedding vector, or None on failure. Never raises."""
        raise NotImplementedError

    @abstractmethod
    def is_reachable(self) -> bool:
        """Cheap liveness check, used by health/status endpoints."""
        raise NotImplementedError
