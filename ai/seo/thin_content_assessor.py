"""
MODULE — Qualitative thin-content assessment.

automation/seo/technical_audit.py's detect_thin_content flags a page by
real body word count alone — a widely used practitioner proxy (Screaming
Frog, SEMrush and similar audit tools default to a similar figure), but
that is honestly NOT what Google's own guidance actually says: a short
page isn't automatically low-quality, and a long page isn't automatically
good. The actual standard is whether content is unclear, insufficient, or
fails to genuinely serve the reader — word count is only ever a signal
worth checking, never the rule itself. A page that fully and clearly
answers one narrow question in 250 words is not thin; a padded, vague
900-word page can be.

This module is the qualitative check applied to every page that already
tripped that word-count signal: it asks the LLM to judge the page's
actual relevance, clarity, usefulness, and completeness for its own
apparent topic, so a short-but-complete page isn't flagged alongside a
genuinely empty stub. Never raises — returns None on LLM failure or
unparseable output, matching this codebase's graceful-degrade convention;
the caller falls back to the word-count-only finding rather than losing
the signal entirely when this can't run (e.g. Ollama unreachable).
"""
import json
import logging
from dataclasses import dataclass, field
from typing import List, Optional

from ai.llm.factory import get_provider

logger = logging.getLogger(__name__)


@dataclass
class ThinContentAssessment:
    # False means: short, but relevant/clear/useful/complete for its own
    # apparent purpose — the word-count signal alone shouldn't flag it.
    is_thin: bool
    reason: str  # 1-2 sentences, specific to this page's own content
    missing_topics: List[str] = field(default_factory=list)


def _parse_json_object(text: str) -> Optional[dict]:
    """Small local models often wrap JSON in prose or code fences despite
    instructions not to — extract the first {...} block rather than
    require a perfectly clean response."""
    text = text.strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None


def assess_thin_content(
    text: str, url: str, word_count: int, *, site_id: Optional[int] = None
) -> Optional[ThinContentAssessment]:
    """text is the page's own real body text, boilerplate (nav/footer/
    scripts) already stripped by the caller. Never raises."""
    if not text.strip():
        return ThinContentAssessment(is_thin=True, reason="No real body content found on this page at all.")

    prompt = (
        "You are assessing whether a web page's content is genuinely \"thin\" by Google's own definition — "
        "content that is unclear, insufficient, or fails to meaningfully serve someone searching for this "
        "topic — NOT simply whether it's short. A short page that fully, clearly, and specifically answers "
        "one narrow question or purpose is NOT thin. A longer page that's vague, generic, or padded with "
        "filler CAN still be thin despite its length. Judge relevance, clarity, usefulness, and completeness "
        "for whatever this page's own apparent topic and purpose is — don't assume it should cover more "
        "than its own evident scope (e.g. a contact page or a narrow FAQ answer isn't incomplete for "
        "lacking unrelated detail).\n\n"
        f"PAGE URL: {url}\n"
        f"REAL BODY WORD COUNT (navigation/footer already excluded): {word_count}\n\n"
        f"PAGE TEXT:\n{text[:6000]}\n\n"
        "Return ONLY a JSON object with these exact keys: is_thin (true or false), reason (1-2 sentences "
        "specific to what this page actually says, not generic advice), missing_topics (a JSON array of "
        "specific sub-topics or questions this page plausibly should but doesn't cover — an empty array "
        "when there's nothing specific to add or the page isn't thin). "
        "No markdown, no explanation outside the JSON object."
    )
    result = get_provider(task="thin_content", site_id=site_id).generate(prompt, fast=True)
    if not result.ok:
        logger.warning("Thin-content assessment failed for %s: %s", url, result.error)
        return None

    parsed = _parse_json_object(result.text)
    if parsed is None or "is_thin" not in parsed:
        logger.warning("Thin-content assessment returned unparseable output for %s: %r", url, result.text[:300])
        return None

    return ThinContentAssessment(
        is_thin=bool(parsed["is_thin"]),
        reason=str(parsed.get("reason", "")).strip(),
        missing_topics=[str(t).strip() for t in (parsed.get("missing_topics") or []) if str(t).strip()],
    )
