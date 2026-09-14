"""
Meta title/description rewrite drafting for the CTR-opportunity queue
(ai/seo_master_agent.py's meta_opportunity_node) — a real page is ranking
(impressions prove real search demand) but its snippet isn't earning
clicks at the rate its position would predict. Deliberately a separate
module from ai/seo/og_tag_generator.py rather than reusing it: that one
writes social-share copy (og:title/og:description) with no notion of a
target query or a CTR problem to fix, while this prompt is built entirely
around "here is the underperforming query and its numbers, write a
snippet that earns the click" — different inputs, different job. Same
LLM provider factory (module 25) and JSON-parsing/truncation conventions
as og_tag_generator.py otherwise.
"""
import json
import logging
from dataclasses import dataclass
from typing import Optional

from ai.llm.factory import get_provider

logger = logging.getLogger(__name__)

META_TITLE_MAX_CHARS = 60
META_DESCRIPTION_MAX_CHARS = 155


@dataclass
class MetaRewrite:
    title: str
    description: str


def _parse_json_object(text: str) -> Optional[dict]:
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
    if len(text) <= max_chars:
        return text
    truncated = text[:max_chars].rsplit(" ", 1)[0]
    return truncated.rstrip(",.;:-") if truncated else text[:max_chars]


def generate_meta_rewrite(
    url: str,
    page_title: Optional[str],
    impressions: int,
    clicks: int,
    ctr: float,
    position: float,
    *,
    site_id: Optional[int] = None,
) -> Optional[MetaRewrite]:
    """Never raises — returns None if the LLM call fails or its output
    can't be parsed, matching this codebase's graceful-degrade convention.
    Callers should leave a candidate in the queue without AI-drafted copy
    rather than push a bad/empty value on failure (a human can still
    review and write it manually)."""
    prompt = (
        "You are an SEO copywriter. A page is getting real search "
        "impressions but a much lower click-through rate than its ranking "
        "position should earn — the search snippet (title + meta "
        "description) isn't convincing searchers to click. Rewrite it to "
        "earn more clicks without misleading searchers about the page's "
        "content.\n\n"
        f"PAGE URL: {url}\n"
        f"CURRENT PAGE TITLE: {page_title or '(unknown — infer from the URL)'}\n"
        f"LAST 28 DAYS: {impressions} impressions, {clicks} clicks, "
        f"{ctr:.2%} CTR, average position {position:.1f}\n\n"
        'Return ONLY a JSON object: {"title": "...", "description": "..."}\n'
        "Rules:\n"
        f"- title: under {META_TITLE_MAX_CHARS} characters, compelling, accurate to the page.\n"
        f"- description: under {META_DESCRIPTION_MAX_CHARS} characters, a clear reason to click, no truncated sentences.\n"
        "- No markdown, no quotes around the JSON, no explanation — the JSON object only."
    )

    result = get_provider(task="meta_rewrite", site_id=site_id).generate(prompt, fast=True)
    if not result.ok:
        logger.warning("Meta rewrite generation failed: %s", result.error)
        return None

    parsed = _parse_json_object(result.text)
    if parsed is None or "title" not in parsed or "description" not in parsed:
        logger.warning("Meta rewrite generation returned unparseable output: %r", result.text)
        return None

    title = _truncate_at_word_boundary(str(parsed["title"]).strip(), META_TITLE_MAX_CHARS)
    description = _truncate_at_word_boundary(str(parsed["description"]).strip(), META_DESCRIPTION_MAX_CHARS)
    return MetaRewrite(title=title, description=description)
