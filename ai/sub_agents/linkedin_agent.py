"""
MODULE 16.3 — LinkedIn Sub-Agent

The agentic pipeline: plan -> write (18.1's content_writer, an Ollama call)
-> reason about what image the post needs and generate it (18.3's
image_generator, a second Ollama call feeding a FastSD CPU tool call) ->
fall back to a Pexels stock photo (image_finder) only if local generation
is unavailable -> combine and post (18.4's poster). Each step is a real,
independently-inspectable call, not a fixed script.

Every real post must carry a real, content-matched image — a post is never
allowed to go out text-only. If FastSD CPU's agentic generation fails AND
the Pexels fallback also fails (or isn't configured), that's a hard
failure of the whole run, not a silent downgrade to text-only.
Rate limiting and credential/session handling all live in poster.py
(18.5/18.6); this module's job is just orchestrating the pipeline.
"""
import logging
from typing import Callable, Optional, TypedDict

from agent.config import USER_ID

logger = logging.getLogger(__name__)


class LinkedInResult(TypedDict):
    status: str  # "success" | "failure"
    detail: str
    post_id: Optional[str]


# (stage_label, progress_percent) after each real step completes — callers
# (the job-tracked API route) use this to show live progress instead of one
# opaque multi-minute wait, without this module knowing anything about jobs.
ProgressCallback = Callable[[str, int], None]


def _noop_progress(_label: str, _pct: int) -> None:
    pass


def run(
    topic: Optional[str] = None,
    user_id: str = USER_ID,
    on_progress: ProgressCallback = _noop_progress,
) -> LinkedInResult:
    from automation.linkedin.content_writer import write_post
    from automation.linkedin.image_finder import find_image
    from automation.linkedin.image_generator import generate_image
    from automation.linkedin.poster import post_to_linkedin

    on_progress("Generating post text (Ollama)", 10)
    written = write_post(topic)
    if written is None:
        detail = "Content writer failed (Ollama unreachable/timed out)"
        logger.error("LinkedIn sub-agent: %s", detail)
        return {"status": "failure", "detail": detail, "post_id": None}
    on_progress(f"Post text ready ({len(written['content'])} chars)", 30)

    # Agentic image sourcing: reason from the actual post text and generate
    # locally first; a Pexels stock photo is only a fallback for when the
    # local FastSD CPU server isn't running. Unlike before, a missing image
    # here is a hard failure — every real post must carry one.
    on_progress("Generating matching image (Ollama + FastSD CPU)", 40)
    image_path = generate_image(written["content"]) or find_image(written["topic"])
    if image_path is None:
        detail = "No image available (FastSD CPU unreachable and no Pexels fallback) — refusing to post text-only"
        logger.error("LinkedIn sub-agent: %s", detail)
        return {"status": "failure", "detail": detail, "post_id": None}
    on_progress("Image ready", 75)

    on_progress("Posting to LinkedIn (Playwright)", 80)
    result = post_to_linkedin(written["content"], written["topic"], image_path)

    detail = result["detail"] if result["status"] == "failure" else f"Posted about {written['topic']!r}"
    logger.info("LinkedIn sub-agent: %s", detail)
    return {"status": result["status"], "detail": detail, "post_id": result["post_id"]}


if __name__ == "__main__":
    from agent.logging_config import setup_logging

    setup_logging()
    logger.info("Module 16.3 manual test: running LinkedIn sub-agent")
    print(run(topic="Agentic AI"))
