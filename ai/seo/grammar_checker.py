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
import time
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


# Why the article is checked in pieces: one request carrying a whole ~1,000-word
# post cannot finish on this hardware with either local model — measured on a
# real post, qwen3:1.7b needed 314 s and returned an unusable reply, and
# phi3:mini was still going after 600 s (the fast client gives up at 120 s, so
# the check "timed out" on nearly every longer post and the post was saved with
# no grammar review at all).
#
# What decides the time here is how much the model WRITES back (~5 words/s on
# this CPU), not how much it reads: a 85-word piece took 92 s when the model
# was free to list every mistake it saw (1,820 characters back), but a 137-word
# piece took 39 s when asked for at most 3 mistakes with a short reason. So each
# piece is small AND the reply is kept short. A piece that still fails costs
# only that piece, not the whole check.
CHUNK_WORDS = 150
MAX_CHUNKS = 8             # ~1,200 words — covers a normal 1,200-word post
ISSUES_PER_PIECE = 3
# ~5 words/s on this CPU: 350 tokens keeps one piece comfortably inside the
# fast model's 120 s limit even when it ignores "at most 3" (seen live: it
# returned 7 findings and took 109 s).
MAX_REPLY_TOKENS = 350
TIME_BUDGET_SECONDS = 420  # stop starting new pieces after this; keep what's found


def _split_into_chunks(plain_text: str, chunk_words: int = CHUNK_WORDS) -> List[str]:
    """Splits on sentence boundaries so a mistake is never cut in half across
    two pieces (a sentence longer than a whole chunk is split by words)."""
    sentences = re.split(r"(?<=[.!?])\s+", plain_text)
    chunks: List[str] = []
    current: List[str] = []
    count = 0
    for sentence in sentences:
        n = len(sentence.split())
        if n == 0:
            continue
        if n > chunk_words:
            if current:
                chunks.append(" ".join(current))
                current, count = [], 0
            words = sentence.split()
            chunks.extend(" ".join(words[i : i + chunk_words]) for i in range(0, len(words), chunk_words))
            continue
        if count + n > chunk_words and current:
            chunks.append(" ".join(current))
            current, count = [], 0
        current.append(sentence)
        count += n
    if current:
        chunks.append(" ".join(current))
    return chunks


def _is_real_finding(item: dict) -> bool:
    """The small model sometimes "reports" a mistake whose suggested fix is the
    very same text, or says in its own reason that it found nothing wrong
    (seen live: 'Correction needed, no mistake found.'). Those are noise."""
    original = " ".join(str(item.get("original", "")).split()).lower()
    suggestion = " ".join(str(item.get("suggestion", "")).split()).lower()
    explanation = str(item.get("explanation", "")).lower()
    return original != suggestion and "no mistake" not in explanation and "no error" not in explanation


def _parse_grammar_issues(text: str) -> Optional[List[GrammarIssue]]:
    """None when nothing can be read from the reply at all. A reply cut off
    by MAX_REPLY_TOKENS ends mid-array, so when the whole array won't parse
    the complete {...} objects before the cut are still used."""
    start, end = text.find("["), text.rfind("]")
    parsed = None
    if start != -1 and end > start:
        try:
            parsed = json.loads(text[start : end + 1])
        except (json.JSONDecodeError, TypeError):
            parsed = None
    if parsed is None:
        salvaged = []
        for match in re.finditer(r"\{[^{}]*\}", text):
            try:
                obj = json.loads(match.group(0))
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict) and "original" in obj:
                salvaged.append(obj)
        if not salvaged:
            return None
        parsed = salvaged
    try:
        return [
            GrammarIssue(
                original=str(p.get("original", "")).strip(),
                suggestion=str(p.get("suggestion", "")).strip(),
                explanation=str(p.get("explanation", "")).strip(),
            )
            for p in parsed
            if isinstance(p, dict) and p.get("original") and p.get("suggestion") and _is_real_finding(p)
        ]
    except AttributeError:
        return None


def _check_chunk(chunk: str, site_id: Optional[int], max_issues: int) -> Optional[List[GrammarIssue]]:
    prompt = (
        "Proofread the following article text for real grammar, spelling, and punctuation mistakes only — "
        "not style preferences, and don't suggest changes to sentences that are already correct. "
        f"List at most {max_issues} genuine mistakes.\n\n"
        'Return ONLY a JSON array: [{"original": "the exact mistaken phrase, verbatim from the text", '
        '"suggestion": "the corrected phrase", "explanation": "max 8 words"}, ...]. If there are no '
        "mistakes, return []. No markdown, no explanation outside the array — the JSON array only.\n\n"
        f"TEXT:\n{chunk}"
    )
    result = get_provider(task="grammar_check", site_id=site_id).generate(prompt, fast=True, max_tokens=MAX_REPLY_TOKENS)
    if not result.ok:
        logger.warning("Grammar check piece failed: %s", result.error)
        return None
    issues = _parse_grammar_issues(result.text.strip())
    if issues is None:
        logger.warning("Grammar check piece returned unparseable output: %r", result.text[:300])
    return issues


def check_grammar(
    content_html: str, *, site_id: Optional[int] = None, max_issues: int = 15
) -> Optional[GrammarReport]:
    """Never raises — returns None only when NOTHING could be checked (every
    piece failed), matching this codebase's graceful-degrade convention.
    The text is checked in ~200-word pieces (see the note above CHUNK_WORDS)
    and the findings merged; if some pieces fail or the time budget runs out
    the report still carries what was found, and checked_word_count says how
    much of the article that actually covers."""
    plain_text = _strip_html(content_html)
    if not plain_text:
        return GrammarReport(issues=[], checked_word_count=0)

    chunks = _split_into_chunks(plain_text)[:MAX_CHUNKS]
    issues: List[GrammarIssue] = []
    seen = set()
    checked_words = 0
    started = time.monotonic()
    for i, chunk in enumerate(chunks):
        if i > 0 and time.monotonic() - started > TIME_BUDGET_SECONDS:
            logger.warning("Grammar check stopped after %d of %d pieces (time budget)", i, len(chunks))
            break
        found = _check_chunk(chunk, site_id, min(ISSUES_PER_PIECE, max_issues))
        if found is None:
            continue
        checked_words += len(chunk.split())
        for issue in found:
            key = issue.original.lower()
            if key not in seen:
                seen.add(key)
                issues.append(issue)

    if checked_words == 0:
        return None
    return GrammarReport(issues=issues[:max_issues], checked_word_count=checked_words)
