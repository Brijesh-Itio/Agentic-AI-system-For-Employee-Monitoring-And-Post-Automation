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
    "- No text, letters, logos, or people's faces in the description.\n"
    "- Output ONLY the final image description, nothing else — no preamble, "
    "no quotes, no explanation of your reasoning.\n\n"
)


def derive_image_prompt(content: str, *, title: Optional[str] = None, site_id: Optional[int] = None) -> Optional[str]:
    """Never raises — returns None on LLM failure, so callers fall back to
    their previous title/excerpt behaviour, matching this codebase's
    graceful-degrade convention throughout."""
    excerpt = (content or title or "")[:1500]
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
