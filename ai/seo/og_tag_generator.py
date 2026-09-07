"""
MODULE 27.3 — OpenGraph tag generation.

Uses the generic LLM provider factory (module 25) to write conversion-
optimised og:title/og:description for a page, given its title and a
content excerpt. Ollama by default; pointing the "og_tags" task at a
paid provider is one SEO_LLM_PROVIDER_OG_TAGS env var, same pattern as
every other LLM-backed SEO task.
"""
import json
import logging
from dataclasses import dataclass
from typing import Optional

from ai.llm.factory import get_provider

logger = logging.getLogger(__name__)

OG_TITLE_MAX_CHARS = 60
OG_DESCRIPTION_MAX_CHARS = 155


@dataclass
class OgTags:
    og_title: str
    og_description: str


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


def _truncate_at_word_boundary(text: str, max_chars: int) -> str:
    """A hard mid-word cut (e.g. "...Desktop Fo") reads as broken output,
    not a compact one — this is the safety net for when the model doesn't
    stay under the limit on its own, so it needs to look intentional."""
    if len(text) <= max_chars:
        return text
    truncated = text[:max_chars].rsplit(" ", 1)[0]
    return truncated.rstrip(",.;:-") if truncated else text[:max_chars]


def generate_og_tags(
    page_title: str, content_excerpt: str, *, site_id: Optional[int] = None
) -> Optional[OgTags]:
    """Never raises — returns None if the LLM call fails or its output
    can't be parsed, matching this codebase's graceful-degrade convention.
    Callers should skip updating OG tags on a page rather than push a
    bad/empty value on failure."""
    prompt = (
        "Write OpenGraph social-sharing tags for this page. Return ONLY a JSON "
        'object: {"og_title": "...", "og_description": "..."}\n'
        "Rules:\n"
        f"- og_title: click-optimised, under {OG_TITLE_MAX_CHARS} characters, includes the main keyword.\n"
        f"- og_description: a compelling hook, under {OG_DESCRIPTION_MAX_CHARS} characters, no truncated sentences.\n"
        "- No markdown, no quotes around the JSON, no explanation — the JSON object only.\n\n"
        f"PAGE TITLE: {page_title}\n\n"
        f"CONTENT EXCERPT:\n{content_excerpt[:1500]}"
    )

    result = get_provider(task="og_tags", site_id=site_id).generate(prompt, fast=True)
    if not result.ok:
        logger.warning("OG tag generation failed: %s", result.error)
        return None

    parsed = _parse_json_object(result.text)
    if parsed is None or "og_title" not in parsed or "og_description" not in parsed:
        logger.warning("OG tag generation returned unparseable output: %r", result.text)
        return None

    og_title = _truncate_at_word_boundary(str(parsed["og_title"]).strip(), OG_TITLE_MAX_CHARS)
    og_description = _truncate_at_word_boundary(
        str(parsed["og_description"]).strip(), OG_DESCRIPTION_MAX_CHARS
    )
    return OgTags(og_title=og_title, og_description=og_description)
