"""
Manual smoke test for the Puter.js image provider (ai/images/providers/
puter_provider.py). Run after pasting a real PUTER_AUTH_TOKEN into .env:

    python scripts/test_puter_image.py
    python scripts/test_puter_image.py "a robot watering a plant"

Saves the generated image next to this script and prints latency/errors,
so a broken token or a Puter-side SDK change shows up here instead of
silently inside a real blog/LinkedIn post run.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ai.images.providers.puter_provider import PuterProvider  # noqa: E402
from api.config import settings  # noqa: E402

DEFAULT_PROMPT = "a cat playing piano, photorealistic"


def main() -> None:
    prompt = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PROMPT

    if not settings.PUTER_AUTH_TOKEN:
        print("PUTER_AUTH_TOKEN is not set in .env — paste your token there first.")
        print("Get one at https://puter.com/dashboard#account -> API token -> Create token.")
        sys.exit(1)

    provider = PuterProvider()
    print(f"is_reachable(): {provider.is_reachable()}")
    print(f"Generating image for prompt: {prompt!r} ...")

    result = provider.generate(prompt)

    if not result.ok:
        print(f"FAILED — provider={result.provider} error={result.error} latency_ms={result.latency_ms}")
        sys.exit(1)

    out_path = Path(__file__).parent / f"puter_test_output.{result.format or 'png'}"
    out_path.write_bytes(result.image_bytes)
    print(f"OK — saved {len(result.image_bytes)} bytes to {out_path} (latency_ms={result.latency_ms:.0f})")


if __name__ == "__main__":
    main()
