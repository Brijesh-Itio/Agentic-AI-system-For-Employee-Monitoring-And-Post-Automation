"""
MODULE 34.1 — Blog post generation.

Writes a full, structured blog post (title, excerpt, HTML body) from a
topic via the module 25 LLM factory — fast=False, same as ai/dar_
generator.py and ai/master_agent.py's report compilation, since a real
post is long-form content worth the slower/better model, not the
short-copy fast=True path module 30's social posts use. The body is
generated WITH its own single H1 matching the title (not left to the
CMS theme to render one) specifically so content_structure.analyze_
structure (module 27.5) — run automatically right after generation, see
api/routes/seo.py's /blog/generate — checks a real, complete document
instead of one that would always fail its own H1-count rule.
"""
import logging
from dataclasses import dataclass
from typing import Optional

from ai.llm.factory import get_provider

logger = logging.getLogger(__name__)


@dataclass
class BlogPostDraft:
    title: str
    excerpt: str
    content_html: str


def generate_blog_post(
    topic: str, primary_keyword: Optional[str] = None, *, site_id: Optional[int] = None, min_words: int = 600
) -> Optional[BlogPostDraft]:
    """Never raises — returns None on LLM failure or unparseable output,
    matching this codebase's graceful-degrade convention."""
    keyword_line = f'Primary SEO keyword to work naturally into the first paragraph: "{primary_keyword}".\n' if primary_keyword else ""
    prompt = (
        f'Write a complete, well-structured blog post about: "{topic}".\n'
        f"{keyword_line}"
        f"At least {min_words} words. Direct, factual, no marketing fluff or filler.\n\n"
        "Output ONLY these three sections, each on its own line, in this exact format "
        "(no markdown code fences, no extra commentary):\n"
        "TITLE: <the post title, no HTML>\n"
        "EXCERPT: <a 1-2 sentence summary, no HTML>\n"
        "CONTENT: <the full post body as HTML — exactly one <h1> matching the title, "
        "3 or more <h2> sections, <p> paragraphs, no <html>/<body> wrapper tags>"
    )
    result = get_provider(task="blog_post", site_id=site_id).generate(prompt, fast=False)
    if not result.ok:
        logger.warning("Blog post generation failed for topic %r: %s", topic, result.error)
        return None

    parsed = _parse_sections(result.text)
    if parsed is None:
        logger.warning("Blog post generation returned unparseable output for topic %r: %r", topic, result.text[:300])
        return None

    return parsed


def _parse_sections(text: str) -> Optional[BlogPostDraft]:
    title_idx = text.find("TITLE:")
    excerpt_idx = text.find("EXCERPT:")
    content_idx = text.find("CONTENT:")
    if title_idx == -1 or excerpt_idx == -1 or content_idx == -1:
        return None
    if not (title_idx < excerpt_idx < content_idx):
        return None

    title = text[title_idx + len("TITLE:") : excerpt_idx].strip()
    excerpt = text[excerpt_idx + len("EXCERPT:") : content_idx].strip()
    content_html = text[content_idx + len("CONTENT:") :].strip()
    if not title or not content_html:
        return None

    return BlogPostDraft(title=title, excerpt=excerpt, content_html=content_html)
