"""
MODULE — Grammar check & fix suggestions.

Runs the same local-LLM factory every other SEO content feature in this
codebase uses (ai/llm/factory.py) over a draft's plain text and asks it to
list concrete grammar/spelling/punctuation mistakes with a suggested fix
for each — a zero-external-API substitute for a dedicated grammar engine
(LanguageTool/Grammarly, neither of which this codebase integrates),
consistent with the project's local-first AI stance. Not a guarantee of
catching every mistake a dedicated grammar engine would, and the model can
occasionally flag something that isn't really wrong — this is surfaced to
a reviewer as suggestions to accept or ignore, never auto-applied to the
post's content.
"""
import json
import logging
import re
from dataclasses import dataclass, field
from typing import List, Optional

from ai.llm.factory import get_provider

logger = logging.getLogger(__name__)


def _strip_html(html: str) -> str:
    text = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", text).strip()


@dataclass
class GrammarIssue:
    original: str
    suggestion: str
    explanation: str


@dataclass
class GrammarReport:
    issues: List[GrammarIssue] = field(default_factory=list)
    checked_word_count: int = 0


def check_grammar(
    content_html: str, *, site_id: Optional[int] = None, max_issues: int = 15
) -> Optional[GrammarReport]:
    """Never raises — returns None on LLM failure or unparseable output,
    matching this codebase's graceful-degrade convention. Checks at most
    the first ~4000 words of plain text (a local model's response quality
    degrades over very long inputs) — enough to catch the kind of mistakes
    that recur across a whole draft without needing a chunk-and-merge
    multi-call review."""
    plain_text = _strip_html(content_html)
    if not plain_text:
        return GrammarReport(issues=[], checked_word_count=0)
    words = plain_text.split()
    checked_text = " ".join(words[:4000])

    prompt = (
        "Proofread the following article text for real grammar, spelling, and punctuation mistakes only — "
        "not style preferences, and don't suggest changes to sentences that are already correct. "
        f"List at most {max_issues} genuine mistakes.\n\n"
        'Return ONLY a JSON array: [{"original": "the exact mistaken phrase, verbatim from the text", '
        '"suggestion": "the corrected phrase", "explanation": "one short reason"}, ...]. If there are no '
        "mistakes, return []. No markdown, no explanation outside the array — the JSON array only.\n\n"
        f"TEXT:\n{checked_text}"
    )
    result = get_provider(task="grammar_check", site_id=site_id).generate(prompt, fast=True)
    if not result.ok:
        logger.warning("Grammar check failed: %s", result.error)
        return None

    text = result.text.strip()
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1 or end <= start:
        logger.warning("Grammar check returned unparseable output: %r", text)
        return None
    try:
        parsed = json.loads(text[start : end + 1])
        issues = [
            GrammarIssue(
                original=str(p.get("original", "")).strip(),
                suggestion=str(p.get("suggestion", "")).strip(),
                explanation=str(p.get("explanation", "")).strip(),
            )
            for p in parsed
            if isinstance(p, dict) and p.get("original") and p.get("suggestion")
        ]
    except (json.JSONDecodeError, TypeError, AttributeError):
        logger.warning("Grammar check JSON parse failed: %r", text)
        return None

    return GrammarReport(issues=issues[:max_issues], checked_word_count=len(words))
