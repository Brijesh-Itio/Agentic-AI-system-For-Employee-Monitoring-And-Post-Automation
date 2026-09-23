"""
MODULE — Blog post SEO meta title/description generation.

Generates the search-snippet meta title/description for a generated blog
post. Separate from ai/seo/og_tag_generator.py's OG (social-share) tags,
which target a different surface (Facebook/LinkedIn link previews) with
different length limits — this targets the actual Google search-result
snippet. Same LLM-factory + truncate-at-word-boundary enforcement pattern
as og_tag_generator.py, so a model that ignores the character budget still
produces a clean, intentional-looking result rather than a raw overrun.
"""
import json
import logging
from dataclasses import dataclass
from typing import Optional

from ai.llm.factory import get_provider

logger = logging.getLogger(__name__)

META_TITLE_MIN_CHARS = 50
META_TITLE_MAX_CHARS = 60
META_DESCRIPTION_MIN_CHARS = 150
META_DESCRIPTION_MAX_CHARS = 160


@dataclass
class BlogMetaTags:
    meta_title: str
    meta_description: str


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


def generate_blog_meta_tags(
    title: str, excerpt: str, primary_keyword: Optional[str] = None, *, site_id: Optional[int] = None
) -> Optional[BlogMetaTags]:
    """Never raises — returns None on LLM failure or unparseable output,
    matching this codebase's graceful-degrade convention. Callers should
    leave meta_title/meta_description unset on failure rather than push a
    bad/empty value.

    Only enforces the upper bound deterministically (truncate-at-word-
    boundary, like og_tag_generator.py) — there's no honest way to pad a
    too-short title/description up to the minimum without fabricating
    content, so a result under the minimum is left as-is and simply shows
    as such via the character counter wherever it's displayed."""
    keyword_line = f'Work the keyword "{primary_keyword}" naturally into both.\n' if primary_keyword else ""
    prompt = (
        "Write SEO meta tags for this blog post's Google search-result snippet. Return ONLY a JSON "
        'object: {"meta_title": "...", "meta_description": "..."}\n'
        "Rules:\n"
        f"- meta_title: {META_TITLE_MIN_CHARS}-{META_TITLE_MAX_CHARS} characters, compelling, includes the main keyword.\n"
        f"- meta_description: {META_DESCRIPTION_MIN_CHARS}-{META_DESCRIPTION_MAX_CHARS} characters, a genuine "
        "summary that earns the click, no truncated sentences.\n"
        f"{keyword_line}"
        "- No markdown, no quotes around the JSON, no explanation — the JSON object only.\n\n"
        f"POST TITLE: {title}\n\n"
        f"POST SUMMARY:\n{excerpt[:1500]}"
    )

    result = get_provider(task="blog_meta", site_id=site_id).generate(prompt, fast=True)
    if not result.ok:
        logger.warning("Blog meta tag generation failed: %s", result.error)
        return None

    parsed = _parse_json_object(result.text)
    if parsed is None or "meta_title" not in parsed or "meta_description" not in parsed:
        logger.warning("Blog meta tag generation returned unparseable output: %r", result.text)
        return None

    meta_title = _truncate_at_word_boundary(str(parsed["meta_title"]).strip(), META_TITLE_MAX_CHARS)
    meta_description = _truncate_at_word_boundary(str(parsed["meta_description"]).strip(), META_DESCRIPTION_MAX_CHARS)
    return BlogMetaTags(meta_title=meta_title, meta_description=meta_description)
