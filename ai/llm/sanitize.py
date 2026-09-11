"""
Strips a leaked/hallucinated prompt continuation from an LLM's response.

Some local models (especially in this codebase's "fast" mode — a smaller,
quicker model traded off against quality, see ai/llm/factory.py) don't
reliably stop after answering. Verified live: a "fast" LinkedIn post
generation continued past the real post and appended what read like a
continuation of its own instructions, PAGE TITLE:/PAGE CONTENT: markers
included — not even a verbatim echo of the actual prompt sent, but a
hallucinated embellishment of it (extra instructions that were never in
the real prompt at all: "include an analogy...", "incorporate
statistical evidence..." never appear in ai/seo/social_content.py's
_PLATFORM_PROMPTS). Only the prompt's opening sentence survived that
particular hallucination verbatim ("Write a LinkedIn post about this
page.") — nothing guarantees it's always the opening sentence specifically
for every prompt/model combination, so every sentence of the real prompt
is checked, not just the first, and whichever produces the earliest cut
point in the response wins.

Shared by every prompt in this codebase that follows the "PAGE TITLE: /
PAGE CONTENT:" convention (ai/seo/social_content.py, ai/seo/
issue_remediation.py) rather than each one re-implementing detection.
ai/seo/og_tag_generator.py doesn't need this: it already extracts just
the first {...} JSON block from the response, which discards a trailing
leaked continuation as a side effect of how it's parsed.
"""
import logging

logger = logging.getLogger(__name__)

_LEAK_MARKERS = ("PAGE TITLE:", "PAGE CONTENT:")
_MIN_SENTENCE_CHARS = 15  # skip anything too short/generic to safely match on


def strip_leaked_prompt_markers(text: str, prompt: str = "") -> str:
    """Never raises. Returns text unchanged if nothing leaked was found.
    Pass the actual prompt sent for this call in `prompt` — each of its
    sentences is checked in addition to the fixed structural markers."""
    candidates = list(_LEAK_MARKERS)
    if prompt:
        for sentence in prompt.replace("\n", " ").split(". "):
            sentence = sentence.strip()
            if len(sentence) >= _MIN_SENTENCE_CHARS:
                candidates.append(sentence)

    earliest = None
    for marker in candidates:
        idx = text.find(marker)
        if idx != -1 and (earliest is None or idx < earliest):
            earliest = idx
    if earliest is None:
        return text
    logger.warning("Stripped a leaked prompt continuation from an LLM response (cut at %d chars)", earliest)
    return text[:earliest].rstrip()
