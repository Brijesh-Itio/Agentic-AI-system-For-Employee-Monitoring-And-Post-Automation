"""
MODULE 27 — Content-aware image prompt derivation for blog/social images.

Both blog post and social post image generation used to just hand the
image provider the post's raw title, or the first 200 characters of body
copy, directly as the "prompt". That isn't a visual scene description —
it's marketing/SEO copy — and a text-to-image model can't render
abstract phrases ("unlock possibilities", "streamline transactions") at
all; it renders literal objects. That mismatch, not a provider bug, is
what was producing images unrelated to the actual content.

This is the same reasoning step automation/linkedin/image_generator.py's
_build_image_prompt() already does for LinkedIn's own separate posting
pipeline, and the prompting strategy (and its hard-won constraints) is
deliberately copied from there rather than reinvented. It's a second,
independent implementation because that one calls Ollama directly
(automation/*'s zero-API-cost convention) while this one goes through
the generic LLM provider factory (ai/llm/factory.py), matching every
other ai/seo/* call (blog_content.py, social_content.py) — sharing the
exact function across those two conventions isn't a clean fit.
"""
import logging
import re
from typing import Optional

from ai.llm.factory import get_provider

logger = logging.getLogger(__name__)

# No literal example scene in the instruction, same reasoning as the
# LinkedIn version this is copied from: a concrete example gets echoed
# back near-verbatim across unrelated content instead of treated as a
# format hint, producing the same generic image regardless of what the
# content actually says. Naming the content's real subject explicitly
# (via the excerpt itself) forces grounding in this content, not a
# memorised example.
_INSTRUCTION = (
    "Below is a piece of content (a blog post or social media post). First "
    "identify the 2-3 most specific, concrete nouns or concepts it actually "
    "discusses (not generic words like 'business' or 'technology'). Then "
    "describe, in 12-20 words, a visual scene that depicts THOSE specific "
    "things — not a generic office scene, and not a restatement of the "
    "content's general topic.\n"
    "Rules:\n"
    "- Describe objects/scene/style only, grounded in the content's specific subject.\n"
    "- The scene must be made ONLY of physical, literal objects a camera could "
    "photograph (a laptop, a payment card, a server rack, hands typing, a phone "
    "screen, a warehouse, etc.) — the image model cannot render abstract ideas, "
    "so never describe concepts like 'growth', 'security', 'trust', 'streamlining', "
    "or symbolic/metaphorical imagery; if the content is abstract, pick a literal "
    "object plausibly related to it (e.g. a phone displaying a payment app for a "
    "'payment solutions' article) rather than trying to symbolise the idea itself.\n"
    "- Include 2-4 short labels or key terms from the content itself (for example "
    "'search intent', 'keywords', 'ranking'), written as they would appear on a screen or "
    "a notebook. No slogans, taglines, logos, brand names, or people's faces.\n"
    "- Prefer objects that show the topic itself: a screen with search results, "
    "keyword lists, ranking bars, or a content calendar; a notebook with a checklist; "
    "a desk setup with a laptop. Do NOT describe brochures, posters, banners, or "
    "magazine-style layouts, and do not invent slogans or taglines for them.\n"
    "- Output ONLY the final image description, nothing else — no preamble, "
    "no quotes, no explanation of your reasoning.\n\n"
)


def _post_excerpt(content: str, title: Optional[str]) -> str:
    """Plain text for the prompt, not raw HTML. Section headings come first:
    they name the post's real subject, and the start of a generated post is
    often a generic intro. Cutting the raw HTML at 1500 characters lost
    them, and the tags took up part of the budget."""
    source = content or title or ""
    if "<" not in source:
        return source[:1500]
    headings = re.findall(r"<h[2-4][^>]*>(.*?)</h[2-4]>", source, flags=re.IGNORECASE | re.DOTALL)
    heading_text = " | ".join(re.sub(r"<[^>]+>", "", h).strip() for h in headings if h.strip())
    body_text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", source)).strip()
    combined = f"Section headings: {heading_text}\n\n{body_text}" if heading_text else body_text
    return combined[:1500]


def derive_image_prompt(content: str, *, title: Optional[str] = None, site_id: Optional[int] = None) -> Optional[str]:
    """Never raises — returns None on LLM failure, so callers fall back to
    their previous title/excerpt behaviour, matching this codebase's
    graceful-degrade convention throughout."""
    excerpt = _post_excerpt(content, title)
    if not excerpt.strip():
        return None

    title_line = f"TITLE: {title}\n\n" if title else ""
    prompt = f"{_INSTRUCTION}{title_line}CONTENT:\n{excerpt}"

    result = get_provider(task="image_prompt", site_id=site_id).generate(prompt, fast=True)
    if not result.ok:
        logger.warning("Image prompt derivation failed: %s", result.error)
        return None

    text = (result.text or "").strip()
    if not text:
        return None
    # Small models sometimes keep going past the one description (an
    # "Alternative Description:" or a "-----" separator) despite the
    # single-output instruction — the first paragraph is always the
    # actual answer, so cut there rather than feed the image provider
    # the extra noise.
    first_paragraph = text.split("\n\n")[0].strip().strip('"')
    return first_paragraph or None
