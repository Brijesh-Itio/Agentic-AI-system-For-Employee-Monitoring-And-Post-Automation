"""
Facebook Sub-Agent — same agentic pipeline shape as linkedin_agent.py:
plan -> write (automation/facebook/content_writer.py, an Ollama call) ->
source an image (reuses automation/linkedin/image_generator.py's FastSD
CPU pipeline and image_finder.py's Pexels fallback — image sourcing isn't
LinkedIn-specific, just historically homed in that package) -> post
(automation/facebook/poster.py, a real Graph API call, not browser
automation).

Same "never post text-only" rule as LinkedIn: if both local generation and
the Pexels fallback fail, that's a hard failure of the run.
"""
import logging
from typing import Callable, Optional, TypedDict

from agent.config import USER_ID

logger = logging.getLogger(__name__)


class FacebookResult(TypedDict):
    status: str  # "success" | "failure"
    detail: str
    post_id: Optional[str]


ProgressCallback = Callable[[str, int], None]


def _noop_progress(_label: str, _pct: int) -> None:
    pass


def run(
    topic: Optional[str] = None,
    user_id: str = USER_ID,
    on_progress: ProgressCallback = _noop_progress,
) -> FacebookResult:
    from automation.facebook.content_writer import write_post
    from automation.facebook.poster import post_to_facebook
    from automation.linkedin.image_finder import find_image
    from automation.linkedin.image_generator import generate_image

    on_progress("Generating post text (Ollama)", 10)
    written = write_post(topic)
    if written is None:
        detail = "Content writer failed (Ollama unreachable/timed out)"
        logger.error("Facebook sub-agent: %s", detail)
        return {"status": "failure", "detail": detail, "post_id": None}
    on_progress(f"Post text ready ({len(written['content'])} chars)", 30)

    on_progress("Generating matching image (Ollama + FastSD CPU)", 40)
    image_path = generate_image(written["content"]) or find_image(written["topic"])
    if image_path is None:
        detail = "No image available (FastSD CPU unreachable and no Pexels fallback) — refusing to post text-only"
        logger.error("Facebook sub-agent: %s", detail)
        return {"status": "failure", "detail": detail, "post_id": None}
    on_progress("Image ready", 75)

    on_progress("Posting to Facebook (Graph API)", 80)
    result = post_to_facebook(written["content"], image_path=image_path)

    status = "success" if result.ok else "failure"
    detail = f"Posted about {written['topic']!r}" if result.ok else result.detail
    logger.info("Facebook sub-agent: %s", detail)
    return {"status": status, "detail": detail, "post_id": result.external_post_id}


if __name__ == "__main__":
    from agent.logging_config import setup_logging

    setup_logging()
    logger.warning(
        "Manual test would post to a REAL Facebook Page. "
        "Refusing to run automatically — call run() explicitly if you mean it."
    )
