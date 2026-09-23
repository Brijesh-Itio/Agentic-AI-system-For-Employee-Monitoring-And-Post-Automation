"""
MODULE 30.1 — Social media content generation.

Uses the module 25 LLM factory to write platform-specific copy for a
published page — LinkedIn, Twitter/X, Instagram, Facebook — matching the
blueprint's own per-platform tone/format spec. Content generation only;
see automation/seo/social_poster.py for what happens to it afterward
(real posting for LinkedIn, reusing module 18's existing Playwright
automation; a human-review queue for the other three, since no tested
automation exists for them in this codebase — see that module's
docstring for why that's a deliberate scope boundary, not a gap).
"""
import logging
from dataclasses import dataclass
from typing import Optional

from ai.llm.factory import get_provider
from ai.llm.sanitize import strip_leaked_prompt_markers

logger = logging.getLogger(__name__)

SUPPORTED_PLATFORMS = ("linkedin", "twitter", "instagram", "facebook")

_PLATFORM_PROMPTS = {
    "linkedin": (
        "Write a LinkedIn post about this page. Professional, insight-led tone, "
        "150-200 words, end with 3-5 relevant hashtags. No preamble, no quotes "
        "around the output — just the post text."
    ),
    "twitter": (
        "Write a Twitter/X thread about this page: a hook tweet, then 4-5 short "
        "follow-up tweets with the key points, ending with a call to action. "
        "Separate tweets with a blank line. No preamble, no quotes."
    ),
    "instagram": (
        "Write an Instagram caption about this page: conversational tone, "
        "emoji-appropriate, ending with relevant hashtags. No preamble, no quotes."
    ),
    "facebook": (
        "Write a Facebook post about this page: casual but informative tone, "
        "shorter than LinkedIn, inviting comments/discussion. No preamble, no quotes."
    ),
}


@dataclass
class SocialPostDraft:
    platform: str
    content: str


# A "fast" local model sometimes answers a "write X" request by writing
# *about* writing X instead of writing it — e.g. asked for a LinkedIn post,
# it instead produces something like "Write an in-depth LinkedIn article
# with the following constraints: 1. Include a comprehensive analysis...
# 2. Integrate personal anecdotes..." — a restated/expanded version of a
# content brief, not an actual post. This is especially likely when
# content_excerpt is itself a detailed multi-point brief (bulk-generate and
# the content calendar both send a freeform pasted topic as content_excerpt
# — see api/routes/seo.py's bulk_generate_social_posts_route/calendar
# route), which nudges the model toward echoing that same instructional
# shape back rather than following it. This doesn't verbatim-match the real
# prompt sent (so strip_leaked_prompt_markers's sentence-matching against
# it doesn't catch it — verified live it was silently passing this
# straight through to a saved, publishable post), but it reliably opens the
# same way any "write a ..." instruction does, which real post copy never
# does. Deliberately narrow (just the two openers every _PLATFORM_PROMPTS
# entry above actually starts with) rather than also matching "create a"/
# "draft a" — those double as completely ordinary ways for real post copy
# to open ("Create a morning routine that actually sticks..."), so adding
# them would trade this false negative for real false positives.
_INSTRUCTION_OPENERS = ("write a ", "write an ")


def _looks_like_leaked_instructions(text: str) -> bool:
    return text.strip()[:40].lower().startswith(_INSTRUCTION_OPENERS)


def generate_social_post(
    platform: str, page_title: str, content_excerpt: str, *, site_id: Optional[int] = None
) -> Optional[SocialPostDraft]:
    """Never raises — returns None on LLM failure, matching this
    codebase's graceful-degrade convention."""
    if platform not in SUPPORTED_PLATFORMS:
        logger.error("generate_social_post: unsupported platform %r", platform)
        return None

    prompt = (
        f"{_PLATFORM_PROMPTS[platform]}\n\n"
        f"PAGE TITLE: {page_title}\n\n"
        f"PAGE CONTENT:\n{content_excerpt[:1500]}"
    )
    provider = get_provider(task=f"social_{platform}", site_id=site_id)
    result = provider.generate(prompt, fast=True)
    if not result.ok:
        logger.warning("Social content generation failed for %s: %s", platform, result.error)
        return None

    content = strip_leaked_prompt_markers(result.text.strip(), prompt=prompt)

    if content and _looks_like_leaked_instructions(content):
        logger.warning(
            "Social content generation for %s produced instructions instead of an actual post — retrying once",
            platform,
        )
        retry_prompt = (
            f"{prompt}\n\nOutput ONLY the finished post text itself — no preamble, no restating or "
            "expanding on these instructions, no meta-commentary about what the post should contain. "
            "Write the actual post now."
        )
        result = provider.generate(retry_prompt, fast=True)
        content = strip_leaked_prompt_markers(result.text.strip(), prompt=retry_prompt) if result.ok else ""
        if not content or _looks_like_leaked_instructions(content):
            logger.warning(
                "Social content generation for %s still produced only instructions after retry, no real content",
                platform,
            )
            return None

    if not content:
        logger.warning("Social content generation for %s produced only a leaked prompt, no real content", platform)
        return None
    return SocialPostDraft(platform=platform, content=content)
