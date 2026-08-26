"""
MODULE 18.3 — Agentic Image Generation (FastSD CPU, primary path)

This is the "agent" half of image sourcing: rather than a fixed keyword
extraction from the topic, an Ollama reasoning step reads the *actual
generated post text* and decides what image concretely represents it,
then that decision is handed to a tool call (FastSD CPU's local
/api/generate) to produce the image. Two real steps, each independently
inspectable — not one opaque prompt template.

FastSD CPU (https://github.com/rupeshs/fastsdcpu) runs as a second local
inference server next to Ollama — same zero-API-cost, same-machine
architecture, just for images instead of text. Configured here for its
LCM-LoRA mode (dreamshaper-8 + latent-consistency/lcm-lora-sdv1-5):
CPU-only, no OpenVINO IR conversion needed, ~2GB of weights, matches the
"fast, good-enough, dev/testing" tier the user chose over SDXL-Turbo's
higher-quality/slower tier for now.

Never raises: any failure (server not running, model not yet downloaded,
timeout) returns None so linkedin_agent.py can fall back to image_finder.py
(Pexels) or post text-only, exactly like every other Ollama-adjacent call
in this codebase.
"""
import base64
import logging
import tempfile
from pathlib import Path
from typing import Optional

import requests

from ai.ollama_client import generate
from api.config import settings

logger = logging.getLogger(__name__)

GENERATE_ENDPOINT = f"{settings.FASTSD_API_URL}/api/generate"
INFO_ENDPOINT = f"{settings.FASTSD_API_URL}/api/info"
HEALTH_TIMEOUT_SECONDS = 3

# LCM-LoRA mode: a real SD1.5 checkpoint + a LoRA adapter that collapses
# denoising to a handful of steps, all running through the plain diffusers
# CPU pipeline (no OpenVINO IR conversion step needed first).
LCM_LORA_BASE_MODEL = "Lykon/dreamshaper-8"
LCM_LORA_ADAPTER = "latent-consistency/lcm-lora-sdv1-5"
INFERENCE_STEPS = 6
GUIDANCE_SCALE = 1.5
IMAGE_SIZE = 512


def is_available() -> bool:
    """Cheap health check so callers can skip straight to the Pexels
    fallback instead of waiting out a full generation timeout when the
    FastSD CPU server just isn't running."""
    try:
        response = requests.get(INFO_ENDPOINT, timeout=HEALTH_TIMEOUT_SECONDS)
        return response.ok
    except requests.RequestException:
        return False


def _build_image_prompt(post_content: str) -> Optional[str]:
    """The reasoning step: the LLM reads the finished post and decides what
    image concretely represents it — a short, literal, visual description
    a diffusion model can render, not a restatement of the post's topic."""
    # No literal example scene in the instruction: verified live that a
    # single concrete example ("a minimalist workspace with a laptop...")
    # got copied back near-verbatim across unrelated posts by the small
    # model instead of treated as a format hint — every generated image
    # ended up the same generic desk scene regardless of what the post
    # actually said. Naming the post's real subject/keywords explicitly
    # forces the model to ground the scene in this post, not a memorised one.
    instruction = (
        "Below is a LinkedIn post. First identify the 2-3 most specific, concrete "
        "nouns or concepts it actually discusses (not generic words like "
        "'workspace' or 'technology'). Then describe, in 12-20 words, a visual "
        "scene that depicts THOSE specific things — not a generic office or "
        "desk scene, and not a restatement of the post's general topic.\n"
        "Rules:\n"
        "- Describe objects/scene/style only, grounded in the post's specific content.\n"
        "- The scene must be made ONLY of physical, literal objects a camera could "
        "photograph (a laptop, a server rack, a whiteboard, hands typing, a robot "
        "arm, a phone screen, etc.) — the small local image model cannot render "
        "abstract ideas, so never describe concepts like 'ethics', 'responsibility', "
        "'innovation', 'trust', or symbolic/metaphorical imagery; if the post is "
        "abstract, pick a literal object plausibly nearby (e.g. a person coding at "
        "a desk) rather than trying to symbolise the idea itself.\n"
        "- No text, letters, logos, or people's faces in the description.\n"
        "- Output ONLY the final image description, nothing else — no preamble, "
        "no quotes, no explanation of your reasoning.\n\n"
        f"POST:\n{post_content}"
    )
    # fast=False (the same model write_post() just used), not fast=True:
    # verified live that immediately switching to the fast model here made
    # Ollama swap qwen3 out for phi3:mini in memory, and that swap alone
    # exceeded the fast client's 120s timeout on this CPU-only machine —
    # reusing the model that's already loaded avoids the swap entirely.
    prompt = generate(instruction, fast=False)
    if not prompt:
        logger.warning("Image generator: Ollama couldn't derive an image prompt from the post")
        return None
    # Small models sometimes keep going past the one description (an
    # "Alternative Description:" or a "-----" separator) despite the
    # single-output instruction — the first paragraph is always the actual
    # answer, so cut there rather than feed FastSD the extra noise.
    first_paragraph = prompt.strip().split("\n\n")[0]
    return first_paragraph.strip().strip('"')


def _call_fastsd(prompt: str) -> Optional[bytes]:
    payload = {
        "prompt": prompt,
        "use_lcm_lora": True,
        "lcm_lora": {"base_model_id": LCM_LORA_BASE_MODEL, "lcm_lora_id": LCM_LORA_ADAPTER},
        "use_openvino": False,
        "use_safety_checker": False,
        "image_height": IMAGE_SIZE,
        "image_width": IMAGE_SIZE,
        "inference_steps": INFERENCE_STEPS,
        "guidance_scale": GUIDANCE_SCALE,
        "number_of_images": 1,
    }
    try:
        response = requests.post(GENERATE_ENDPOINT, json=payload, timeout=settings.FASTSD_TIMEOUT_SECONDS)
        response.raise_for_status()
        images = response.json().get("images") or []
        if not images:
            logger.warning("FastSD CPU returned no images for prompt %r", prompt)
            return None
        return base64.b64decode(images[0])
    except requests.RequestException:
        logger.exception("FastSD CPU generate() failed for prompt %r", prompt)
        return None


def generate_image(post_content: str) -> Optional[Path]:
    """Full agentic pipeline: plan (derive an image prompt from the actual
    post text) -> tool call (FastSD CPU) -> local file. Returns None on any
    failure at any step; callers treat that as "no image", not an error."""
    if not is_available():
        logger.info("FastSD CPU not reachable at %s — skipping local image generation", settings.FASTSD_API_URL)
        return None

    image_prompt = _build_image_prompt(post_content)
    if image_prompt is None:
        return None

    image_bytes = _call_fastsd(image_prompt)
    if image_bytes is None:
        return None

    # FastSD CPU's /api/generate returns JPEG-encoded bytes despite what its
    # own docs might suggest — verified directly (`file` on a real output:
    # "JPEG image data, JFIF standard"), so the suffix here must match, not
    # just look plausible.
    fd, temp_path = tempfile.mkstemp(suffix=".jpg", prefix="workpulse_fastsd_")
    Path(temp_path).write_bytes(image_bytes)
    import os

    os.close(fd)
    logger.info("Generated LinkedIn post image locally via FastSD CPU (prompt=%r) -> %s", image_prompt, temp_path)
    return Path(temp_path)


if __name__ == "__main__":
    from agent.logging_config import setup_logging

    setup_logging()
    logger.info("Module 18.3 manual test: agentic FastSD CPU image generation")
    sample_post = (
        "Most 'AI agents' are just a chatbot with extra steps. A real agentic system "
        "plans, calls tools, and acts without a human in the loop for every step."
    )
    result = generate_image(sample_post)
    print("Generated:", result)
