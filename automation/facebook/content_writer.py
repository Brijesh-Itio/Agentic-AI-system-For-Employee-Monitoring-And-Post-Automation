"""
Facebook Page content writer & topic rotation — same pattern as
automation/linkedin/content_writer.py, just a Facebook-flavoured prompt
(shorter, more conversational, hashtags optional rather than required)
and its own topic-rotation pointer (FACEBOOK_LAST_TOPIC_PATH) so this
doesn't advance/consume LinkedIn's position in the shared POST_TOPICS
list, or vice versa.
"""
import logging
from typing import Optional, TypedDict

from ai.ollama_client import generate
from automation.config import FACEBOOK_LAST_TOPIC_PATH, POST_TOPICS

logger = logging.getLogger(__name__)

MAX_POST_CHARACTERS = 500


class GeneratedPost(TypedDict):
    content: str
    topic: str


def next_topic() -> str:
    last_topic = FACEBOOK_LAST_TOPIC_PATH.read_text(encoding="utf-8").strip() if FACEBOOK_LAST_TOPIC_PATH.exists() else ""

    if last_topic in POST_TOPICS:
        next_index = (POST_TOPICS.index(last_topic) + 1) % len(POST_TOPICS)
    else:
        next_index = 0

    topic = POST_TOPICS[next_index]
    FACEBOOK_LAST_TOPIC_PATH.write_text(topic, encoding="utf-8")
    return topic


def _build_prompt(topic: str) -> str:
    return (
        "Write a Facebook Page post for a general business/tech-curious audience about "
        "the topic below. Rules:\n"
        "- Conversational and direct, short sentences — this is a Facebook Page, not "
        "LinkedIn, so skip corporate tone entirely.\n"
        "- Short paragraphs separated by a blank line.\n"
        "- At most 2-3 hashtags at the very end, only if they add discoverability — "
        "they're optional here, not required.\n"
        f"- Maximum {MAX_POST_CHARACTERS} characters total, including any hashtags.\n"
        "- No preamble like 'Here's a post about...' — output only the post itself.\n\n"
        f"TOPIC: {topic}"
    )


def _enforce_length(content: str) -> str:
    if len(content) <= MAX_POST_CHARACTERS:
        return content
    logger.warning("Generated Facebook post exceeded %d chars (%d) — truncating", MAX_POST_CHARACTERS, len(content))
    return content[: MAX_POST_CHARACTERS - 1].rstrip() + "…"


def write_post(topic: Optional[str] = None) -> Optional[GeneratedPost]:
    """Returns None (never raises) on Ollama failure, same convention as
    every other Ollama call in this codebase."""
    chosen_topic = topic or next_topic()
    content = generate(_build_prompt(chosen_topic), fast=False)
    if content is None:
        logger.error("Facebook content writer failed: Ollama unreachable/timed out for topic %r", chosen_topic)
        return None

    content = _enforce_length(content.strip())
    logger.info("Facebook post written for topic %r (%d chars)", chosen_topic, len(content))
    return {"content": content, "topic": chosen_topic}


if __name__ == "__main__":
    from agent.logging_config import setup_logging

    setup_logging()
    logger.info("Manual test: writing a Facebook post")
    print(write_post())
