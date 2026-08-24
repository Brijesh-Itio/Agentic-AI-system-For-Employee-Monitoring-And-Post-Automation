"""Generates icon.ico at the project root if it doesn't already exist —
same simple mark as the tray icon (agent/tray_main.py's _make_icon_image),
just rendered as a multi-size .ico for the .exe's file icon.
"""
from pathlib import Path

from PIL import Image, ImageDraw

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ICON_PATH = PROJECT_ROOT / "icon.ico"


def make_icon(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    margin = max(1, size // 16)
    draw.ellipse((margin, margin, size - margin, size - margin), fill=(70, 95, 255, 255))
    inner = size // 3
    draw.ellipse((inner, inner, size - inner, size - inner), fill=(255, 255, 255, 255))
    return img


def main() -> None:
    if ICON_PATH.exists():
        print(f"{ICON_PATH} already exists, skipping")
        return
    sizes = [16, 32, 48, 64, 128, 256]
    images = [make_icon(s) for s in sizes]
    images[0].save(ICON_PATH, format="ICO", sizes=[(s, s) for s in sizes])
    print(f"Generated {ICON_PATH}")


if __name__ == "__main__":
    main()
