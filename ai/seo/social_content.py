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
    result = get_provider(task=f"social_{platform}", site_id=site_id).generate(prompt, fast=True)
    if not result.ok:
        logger.warning("Social content generation failed for %s: %s", platform, result.error)
        return None

    content = strip_leaked_prompt_markers(result.text.strip(), prompt=prompt)
    if not content:
        logger.warning("Social content generation for %s produced only a leaked prompt, no real content", platform)
        return None
    return SocialPostDraft(platform=platform, content=content)
