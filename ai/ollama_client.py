"""
Shared local-Ollama client wrapper.

Centralises the "every Ollama call has a timeout and degrades to a safe
default instead of crashing" convention (DEVELOPMENT.md section 8) in one
place, so every AI module (classifier, DAR generator, Master Agent) gets
that behaviour for free instead of re-implementing it.
"""
import logging
from typing import Optional

import ollama

from api.config import settings

logger = logging.getLogger(__name__)

# A fresh client per call, not a shared module-level singleton: observed in
# practice that a long-lived FastAPI backend process reusing one persistent
# ollama.Client (and the keep-alive HTTP connection inside it) would hang on
# stale-connection reuse until its full timeout expired, even though a
# brand-new client to the same Ollama server responded in seconds — while
# short-lived manual test scripts (which always create a fresh client) never
# hit this. Two separate timeout budgets stay: single-word classification
# (fast=True) genuinely finishes in seconds, while a full multi-section DAR
# narrative from qwen3:1.7b on CPU can legitimately take a couple of
# minutes — sharing one timeout meant either classification calls waited
# too long to fail, or narrative generation timed out before it could ever
# finish (observed in practice at ~167s on this hardware).


def _fast_client() -> ollama.Client:
    return ollama.Client(host=settings.OLLAMA_BASE_URL, timeout=settings.OLLAMA_TIMEOUT_SECONDS)


def _client() -> ollama.Client:
    return ollama.Client(host=settings.OLLAMA_BASE_URL, timeout=settings.OLLAMA_GENERATE_TIMEOUT_SECONDS)


def _fix_mojibake(text: str) -> str:
    """Small quantized models occasionally mis-decode multi-byte UTF-8
    punctuation (em dashes, smart quotes) as if it were Windows-1252,
    producing garbage like 'dayâ€™s' instead of "day's".
    Reversing that specific mis-decode (encode as cp1252, decode as utf-8)
    recovers the original text; if the string was never mangled this way,
    the round-trip simply fails and the original text is kept untouched."""
    try:
        return text.encode("cp1252").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text


def generate(prompt: str, model: Optional[str] = None, fast: bool = False) -> Optional[str]:
    """Single-shot text generation. Returns None (never raises) on failure
    so callers can fall back to a safe default rather than crash a
    background thread."""
    chosen_model = model or (settings.OLLAMA_FAST_MODEL if fast else settings.OLLAMA_MODEL)
    client = _fast_client() if fast else _client()
    try:
        response = client.generate(model=chosen_model, prompt=prompt, stream=False)
        text = (response.get("response") or "").strip()
        return _fix_mojibake(text)
    except Exception:
        logger.exception("Ollama generate() failed (model=%s)", chosen_model)
        return None


def embed(text: str) -> Optional[list]:
    """Text embedding via the local nomic-embed-text model (used for
    ChromaDB semantic memory across the AI layer). Embeddings are cheap and
    fast, so this uses the short-timeout client."""
    try:
        response = _fast_client().embeddings(model="nomic-embed-text", prompt=text)
        return response.get("embedding")
    except Exception:
        logger.exception("Ollama embed() failed")
        return None


def is_reachable() -> bool:
    try:
        _fast_client().list()
        return True
    except Exception:
        return False
