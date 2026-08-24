"""
MODULE 18.1 / 18.2 — LinkedIn Content Writer & Topic Rotation

Writes a LinkedIn post with Ollama and rotates through automation/config.py's
POST_TOPICS list so no topic repeats until every topic has been used once.
"""
import logging
from typing import Optional, TypedDict

from ai.ollama_client import generate
from automation.config import LAST_TOPIC_PATH, POST_TOPICS

logger = logging.getLogger(__name__)

MAX_POST_CHARACTERS = 1300


class GeneratedPost(TypedDict):
    content: str
    topic: str


# ── 18.2 Topic rotation ──

def next_topic() -> str:
    """Rotates through POST_TOPICS in order, persisting position in
    last_topic.txt so it survives process restarts. Wraps around once every
    topic has been used."""
    last_topic = LAST_TOPIC_PATH.read_text(encoding="utf-8").strip() if LAST_TOPIC_PATH.exists() else ""

    if last_topic in POST_TOPICS:
        next_index = (POST_TOPICS.index(last_topic) + 1) % len(POST_TOPICS)
    else:
        next_index = 0

    topic = POST_TOPICS[next_index]
    LAST_TOPIC_PATH.write_text(topic, encoding="utf-8")
    return topic


# ── 18.1 Content writer ──

def _build_prompt(topic: str) -> str:
    return (
        "Write a LinkedIn post for a founder/engineer audience about the topic below. "
        "Rules:\n"
        "- First-person, direct, no corporate fluff or emoji spam.\n"
        "- Short paragraphs separated by a blank line (LinkedIn has no markdown).\n"
        "- 3-5 relevant hashtags on the very last line only, nothing after them.\n"
        f"- Maximum {MAX_POST_CHARACTERS} characters total, including the hashtags.\n"
        "- No preamble like 'Here's a post about...' — output only the post itself.\n\n"
        f"TOPIC: {topic}"
    )


def _enforce_length(content: str) -> str:
    if len(content) <= MAX_POST_CHARACTERS:
        return content
    logger.warning("Generated post exceeded %d chars (%d) — truncating", MAX_POST_CHARACTERS, len(content))
    return content[: MAX_POST_CHARACTERS - 1].rstrip() + "…"


def write_post(topic: Optional[str] = None) -> Optional[GeneratedPost]:
    """Writes a post for `topic`, or rotates to the next one if omitted.
    Returns None (never raises) on Ollama failure, per the codebase's
    "degrade to a safe default" convention for every Ollama call."""
    chosen_topic = topic or next_topic()
    content = generate(_build_prompt(chosen_topic), fast=False)
    if content is None:
        logger.error("Content writer failed: Ollama unreachable/timed out for topic %r", chosen_topic)
        return None

    content = _enforce_length(content.strip())
    logger.info("LinkedIn post written for topic %r (%d chars)", chosen_topic, len(content))
    return {"content": content, "topic": chosen_topic}


if __name__ == "__main__":
    from agent.logging_config import setup_logging

    setup_logging()
    logger.info("Module 18.1/18.2 manual test: writing a LinkedIn post")
    result = write_post()
    print(result)
