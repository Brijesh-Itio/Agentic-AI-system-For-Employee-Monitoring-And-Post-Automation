"""
MODULE 36 — Image generation, WebP conversion, and publish-to-site.

Closes two gaps found in a verification audit against the SEO blueprint:
1. ai/images/factory.py (image generation) existed but was never called
   from anywhere in the codebase.
2. automation/seo/webp_converter.py's convert_to_webp() existed but had
   nowhere real to run, because no CMS client or upload path in this
   codebase accepts binary content — automation/seo/server_access.py's
   write_file only ever took text.

This module is the missing link: generate an image for a prompt, convert
it to WebP, and push the WebP bytes to the site's OWN server via the same
SFTP/FTP access already built and tested for Server Files (server_access.
py) — not a local media library, since this app has no public URL of its
own to serve images from. The uploaded file's public URL is derived from
the site's base_url, matching how a real CMS uploads folder is reachable.

Requires the site to have server-access credentials saved (Server Access
tab) — same requirement as every other server_access.py caller. Never
raises: every failure mode (no image provider configured, no server
access configured, upload failure) comes back as a clear ImagePublishResult
with ok=False and a specific reason, matching this codebase's
graceful-degrade convention throughout.
"""
import io
import logging
import os
import re
import time
import urllib.parse
from dataclasses import dataclass
from typing import Optional

from PIL import Image, ImageChops, ImageDraw, ImageFont

from ai.images.factory import get_provider as get_image_provider
from automation.seo.server_access import client_for_site
from automation.seo.webp_converter import convert_to_webp

logger = logging.getLogger(__name__)

UPLOAD_SUBDIR = "wp-content/uploads/seo-agent"

# AI Image Detection (provenance tracking) — ImagePublishResult.provider
# already tells us exactly which path produced an image; these are the
# provider names (see ai/images/providers/*.py's own `name` attributes)
# that are genuinely AI-generated, as opposed to "pexels" (real stock
# photography) or "manual-upload" (a human's own file). No ML image
# classifier is wired up anywhere in this codebase — this is provenance
# we already know for certain from having made the image ourselves, not a
# guess about an image's origin from its pixels.
AI_GENERATED_IMAGE_PROVIDERS = {"fastsd", "stability", "puter", "image_worker"}


def is_ai_generated_image_provider(provider: Optional[str]) -> bool:
    return provider in AI_GENERATED_IMAGE_PROVIDERS

# Facebook and LinkedIn both recommend a ~1.91:1 landscape crop for a
# feed post's image (1200x630 / 1200x627) — a real, specific requirement,
# not an arbitrary choice. A blog post's featured image follows a
# different, equally standard convention: a 2:1 landscape hero image
# (1200x600) — the common WordPress/blog-theme featured-image ratio,
# wide enough to crop cleanly into a 16:9 or square thumbnail downstream
# without losing the subject. None of this can be satisfied by asking
# the image provider for that size: verified live that the active
# provider (ai/images/providers/image_worker_provider.py) silently
# ignores width/height entirely and always returns a flat 1024x1024
# square regardless of what's requested, and FastSD/Stability/Puter
# offer no stronger guarantee either. Enforcing each task's real target
# resolution has to happen here, after generation, not by trusting the
# provider.
#
# Twitter/X, Instagram and Pinterest were missing from this dict entirely
# (found during a later audit of this feature) — every image for those
# three platforms was silently falling through to the generic 1024x1024
# square fallback in generate_and_publish_image below instead of each
# platform's own real recommended size: Twitter/X's documented in-timeline
# single-image size (1600x900, 16:9), Instagram's standard square feed
# post (1080x1080, 1:1 — Instagram also supports 4:5 portrait and 1.91:1
# landscape, but this app posts one image per post, and square is its
# universal safe default across placements), and Pinterest's own
# recommended "Standard Pin" size (1000x1500, 2:3 portrait — Pinterest
# is the one platform here where portrait, not landscape, is the native
# convention; _resize_to_standard below is orientation-agnostic so this
# needed no change there).
_STANDARD_IMAGE_DIMENSIONS = {
    "facebook": (1200, 630),
    "linkedin": (1200, 627),
    "blog_post": (1200, 800),
    "twitter": (1600, 900),
    "instagram": (1080, 1080),
    "pinterest": (1000, 1500),
}


def _standard_dimensions_for_task(task: str) -> Optional[tuple[int, int]]:
    for task_suffix, dims in _STANDARD_IMAGE_DIMENSIONS.items():
        if task.endswith(task_suffix):
            return dims
    return None


# Two distinct problems, both confirmed live from real generated images,
# both addressed by this same appended guidance:
#
# 1. The center-crop above is real and necessary (see
#    _STANDARD_IMAGE_DIMENSIONS' own comment), but no image provider here
#    offers a native ~1.91:1 generation size (OpenAI's Images API, the
#    current default, only offers 1024x1024/1536x1024/1024x1536 —
#    1536x1024 is the closest landscape option, at 1.5:1), so reaching
#    1200x627/1200x630 crops roughly the top and bottom 10% each off
#    whatever the provider actually drew. A dense infographic-style image
#    (packed rows of text/panels edge-to-edge) got that crop and lost
#    whole rows of content mid-sentence.
# 2. Separate from our own crop: the model itself can render text/UI
#    elements that bleed past its own canvas edges before we ever touch
#    the image — confirmed live on a "meeting room with dashboard screens"
#    image where a captions column ran off the right edge mid-word and a
#    process-step row was cut off at the bottom. This happens because a
#    prompt asking for a complex multi-panel dashboard/infographic mockup
#    pushes the model to cram more distinct elements than fit legibly in
#    frame — a rendering failure, not a crop artifact, so no amount of
#    crop-margin alone fixes it; the fix is asking for fewer, larger,
#    clearly-bounded elements in the first place.
#
# Applies regardless of which provider or which prompt (auto-derived or a
# human's own) generated the base text.
def _crop_safe_composition_guidance(standard_size: Optional[tuple[int, int]]) -> str:
    if not standard_size:
        return ""
    target_w, target_h = standard_size
    return (
        f" Compose as a single wide landscape image (roughly {target_w}:{target_h}), with every element "
        "fully inside the frame. If the scene involves multiple "
        "panels, labels, or data points, keep the count small (2-4 at most) and each one large and simple "
        "enough to fit with room to spare — do not pack many small panels or dense rows of text edge-to-edge; "
        "a crowded layout is what causes elements to run off the canvas or overlap."
    )


def _resize_to_standard(image_bytes: bytes, target_size: tuple[int, int]) -> bytes:
    """Fills target_size edge to edge: scales the source to cover the whole
    frame, then center-crops the overflow. No bars, no blur — the image
    looks like a full-bleed photo at the platform's standard size.

    Earlier this letterboxed the whole image onto a bar (to avoid cropping
    text out), which left unfilled side bars on wide images. That was
    reverted on user request. The composition guidance above asks the
    model to keep the subject in the central band, since the crop
    removes some of the top and bottom edges."""
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    target_w, target_h = target_size
    src_w, src_h = image.size

    fill_scale = max(target_w / src_w, target_h / src_h)
    fill_w, fill_h = max(target_w, round(src_w * fill_scale)), max(target_h, round(src_h * fill_scale))
    filled = image.resize((fill_w, fill_h), Image.LANCZOS)

    left = (fill_w - target_w) // 2
    top = (fill_h - target_h) // 2
    cropped = filled.crop((left, top, left + target_w, top + target_h))
    buffer = io.BytesIO()
    cropped.save(buffer, format="PNG")
    return buffer.getvalue()

# Verified live against a real cPanel host this session: the FTP
# account's root is NOT the web document root (files uploaded straight
# to "/wp-content/..." landed nowhere the live site could see — a 500
# on the resulting URL proved it), and the site's own cms_base_url
# ("https://host/demo") is a subdirectory of that document root, not
# the FTP root either. The real layout found: /public_html/demo/wp-
# content/... Candidates below are checked in order against whichever
# already contains a real "wp-content" folder at the site's own URL
# path, so this adapts to different hosts' conventions instead of
# guessing one.
_WEB_ROOT_CANDIDATES = ("", "public_html", "www", "htdocs", "public")


@dataclass
class ImagePublishResult:
    ok: bool
    url: Optional[str] = None
    provider: Optional[str] = None
    reduction_pct: Optional[float] = None
    error: Optional[str] = None


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:60] or "image"


def resolve_web_root_prefix(server_client, url_path: str) -> Optional[str]:
    """Finds which FTP-root-relative prefix actually reaches the site's
    real document root, by checking where "{prefix}{url_path}/wp-
    content" genuinely exists — see the module-level comment on
    _WEB_ROOT_CANDIDATES for how this was verified. Returns just the
    prefix (e.g. "/public_html", or "" if the FTP root already IS the
    document root) so a caller can apply it to any other path on the
    same site, not only url_path itself — see automation/seo/
    webp_bulk_converter.py, which resolves this once per site and reuses
    it for every individual image URL found across every post. None if
    none of the candidates panned out."""
    for candidate in _WEB_ROOT_CANDIDATES:
        prefix = f"/{candidate}".rstrip("/")
        base = f"{prefix}{url_path}".replace("//", "/").rstrip("/")
        try:
            server_client.list_dir(f"{base}/wp-content")
            return prefix
        except Exception:
            continue
    return None


def _resolve_upload_base(server_client, url_path: str) -> Optional[str]:
    prefix = resolve_web_root_prefix(server_client, url_path)
    if prefix is None:
        return None
    return f"{prefix}{url_path}".replace("//", "/").rstrip("/")


def _publish_webp_bytes(site, webp_bytes: bytes, name_hint: str, *, provider: Optional[str] = None) -> ImagePublishResult:
    """Shared upload step for both the AI-generated path
    (generate_and_publish_image) and the manual-upload path
    (upload_image_bytes below) — the only difference between them is
    where the WebP bytes come from."""
    server_client = client_for_site(site)
    if server_client is None:
        return ImagePublishResult(
            ok=False,
            provider=provider,
            error="No server access configured for this site — add SFTP/FTP credentials "
            "in the Server Access tab so images can be uploaded.",
        )

    # cms_base_url ("https://host/demo") reflects where the CMS
    # actually lives; base_url ("https://host/") is a separate,
    # sometimes-different field (e.g. one specific page used for
    # crawling/audits) — using base_url here was verified live to
    # produce a wrong, 500-erroring URL on a real subdirectory install.
    url_for_path = getattr(site, "cms_base_url", None) or site.base_url
    url_path = urllib.parse.urlsplit(url_for_path).path.rstrip("/")

    upload_base = _resolve_upload_base(server_client, url_path)
    if upload_base is None:
        return ImagePublishResult(
            ok=False,
            provider=provider,
            error=f"Could not find this site's actual web root on the server (tried {url_path!r} under "
            f"{', '.join(repr(c or '/') for c in _WEB_ROOT_CANDIDATES)}) — check Server Access points at "
            "the right account and that wp-content is reachable from it.",
        )

    upload_dir = f"{upload_base}/{UPLOAD_SUBDIR}"
    filename = f"{_slugify(name_hint)}-{int(time.time())}.webp"
    remote_path = f"{upload_dir}/{filename}"
    try:
        server_client.mkdir_p(upload_dir)
        server_client.write_binary_file(remote_path, webp_bytes)
    except Exception as exc:
        logger.exception("Image upload to %s failed for site %s", remote_path, getattr(site, "id", "?"))
        return ImagePublishResult(ok=False, provider=provider, error=f"Upload failed: {exc}")

    parsed = urllib.parse.urlsplit(site.base_url)
    domain_root = f"{parsed.scheme}://{parsed.netloc}"
    public_url = f"{domain_root}{url_path}/{UPLOAD_SUBDIR}/{filename}"
    return ImagePublishResult(ok=True, url=public_url, provider=provider)


# Brand block for blog images: a strip along the bottom of the image with
# the site's logo on the left and its email and phone on the right. The
# app draws it itself after generation, so the exact text and logo are
# always right; the image model is only asked to leave that strip empty.
_BRAND_STRIP_RATIO = 0.14
_BRAND_FONT_CANDIDATES = ("arialbd.ttf", "C:/Windows/Fonts/arialbd.ttf", "DejaVuSans-Bold.ttf")


def brand_for_site(site) -> Optional[dict]:
    """The site's brand block, or None when no brand is set. Only blog
    images get it (see generate_and_publish_image)."""
    if not getattr(site, "brand_enabled", None):
        return None
    logo_path = getattr(site, "brand_logo_path", None)
    email = (getattr(site, "brand_email", None) or "").strip()
    phone = (getattr(site, "brand_phone", None) or "").strip()
    website = (getattr(site, "brand_website", None) or "").strip()
    if not (logo_path or email or phone or website):
        return None
    return {
        "logo_path": logo_path if logo_path and os.path.exists(logo_path) else None,
        "email": email,
        "phone": phone,
        "website": _display_domain(website),
    }


def _display_domain(url: str) -> str:
    """Shows the website the way people write it on a card: no scheme, no
    trailing slash (https://webpays.com/ -> webpays.com)."""
    return re.sub(r"^https?://", "", url, flags=re.IGNORECASE).rstrip("/")


def _brand_font(size: int):
    for name in _BRAND_FONT_CANDIDATES:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)


_BRAND_SYMBOL_FONT_CANDIDATES = ("C:/Windows/Fonts/seguisym.ttf", "seguisym.ttf")
_BRAND_TEXT_COLOR = (30, 30, 30)


def _brand_symbol_font(size: int):
    """Segoe UI Symbol has the envelope and telephone glyphs. None when the
    font is missing, in which case the icon is left out and the text stands
    alone rather than drawing a wrong character."""
    for name in _BRAND_SYMBOL_FONT_CANDIDATES:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return None


def _draw_brand_icon(draw, kind: str, x: int, center_y: float, size: int, symbol_font) -> None:
    """Draws an icon whose vertical middle sits on center_y, the middle of
    the text beside it. Email and phone use the symbol font's glyphs, each
    centered by its own measured box; the globe is drawn with shapes so it
    never depends on a font."""
    line_w = max(1, size // 12)
    if kind == "globe":
        top = center_y - size / 2
        draw.ellipse([x, top, x + size, top + size], outline=_BRAND_TEXT_COLOR, width=line_w)
        draw.ellipse([x + size * 0.3, top, x + size * 0.7, top + size], outline=_BRAND_TEXT_COLOR, width=line_w)
        draw.line([(x, center_y), (x + size, center_y)], fill=_BRAND_TEXT_COLOR, width=line_w)
    elif symbol_font is not None:
        glyph = "\u2709" if kind == "email" else "\u260E"
        glyph_box = draw.textbbox((0, 0), glyph, font=symbol_font)
        glyph_mid = (glyph_box[1] + glyph_box[3]) / 2
        draw.text((x, center_y - glyph_mid), glyph, font=symbol_font, fill=_BRAND_TEXT_COLOR)


def _stamp_brand_strip(image_bytes: bytes, target_size: tuple[int, int], brand: dict) -> bytes:
    """Adds the brand footer BELOW the scene. The scene is never covered, so
    no part of the generated picture is hidden. Returns PNG bytes; the
    caller converts to WebP as usual."""
    scene_w, scene_h = target_size
    scene = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    if scene.size != target_size:
        scene = scene.resize(target_size, Image.LANCZOS)

    footer_h = round(scene_h * _BRAND_STRIP_RATIO)
    image = Image.new("RGB", (scene_w, scene_h + footer_h), (255, 255, 255))
    image.paste(scene, (0, 0))
    target_w, target_h = scene_w, scene_h + footer_h
    strip_h = footer_h
    strip_top = scene_h
    pad = max(6, strip_h // 6)
    draw = ImageDraw.Draw(image)
    draw.line([(0, strip_top), (target_w, strip_top)], fill=(225, 225, 225), width=2)

    logo_right_edge = 0
    if brand.get("logo_path"):
        logo = Image.open(brand["logo_path"]).convert("RGBA")
        max_logo_h = strip_h - 2 * pad
        max_logo_w = round(target_w * 0.28)
        scale = min(max_logo_h / logo.height, max_logo_w / logo.width)
        logo = logo.resize((max(1, round(logo.width * scale)), max(1, round(logo.height * scale))), Image.LANCZOS)
        image.paste(logo, (pad, strip_top + (strip_h - logo.height) // 2), mask=logo.split()[3])
        logo_right_edge = pad + logo.width

    # Layout: logo on the left, email and phone stacked on the right with an
    # icon before each, and the website centered along the bottom edge.
    font_size = max(12, round(strip_h * 0.26))
    font = _brand_font(font_size)
    symbol_font = _brand_symbol_font(font_size)
    icon_size = font_size
    icon_gap = max(4, font_size // 3)
    text_h = draw.textbbox((0, 0), "Ag", font=font)[3]
    # Middle of the capital letters, measured from the top of a text line.
    cap_box = draw.textbbox((0, 0), "H", font=font)
    cap_mid = (cap_box[1] + cap_box[3]) / 2

    contact_lines = []
    if brand.get("email"):
        contact_lines.append(("email", brand["email"]))
    if brand.get("phone"):
        contact_lines.append(("phone", brand["phone"]))
    line_gap = max(3, strip_h // 9)
    block_h = len(contact_lines) * text_h + max(0, len(contact_lines) - 1) * line_gap
    y = strip_top + (strip_h - block_h) // 2 - (text_h // 4)
    contact_left_edge = target_w - pad
    email_y = None
    for kind, text in contact_lines:
        if kind == "email":
            email_y = y
        text_w = draw.textbbox((0, 0), text, font=font)[2]
        x = target_w - pad - (icon_size + icon_gap + text_w)
        contact_left_edge = min(contact_left_edge, x)
        _draw_brand_icon(draw, kind, x, y + cap_mid, icon_size, symbol_font)
        draw.text((x + icon_size + icon_gap, y), text, font=font, fill=_BRAND_TEXT_COLOR)
        y += text_h + line_gap

    if brand.get("website"):
        text = brand["website"]
        text_w = draw.textbbox((0, 0), text, font=font)[2]
        total = icon_size + icon_gap + text_w
        # Centered on the empty space between the logo and the contact block,
        # not on the full canvas width — the logo and the contact text are
        # rarely the same width, so a canvas-center position looks off to
        # the eye even though it is mathematically centered.
        available_left = (logo_right_edge + pad) if logo_right_edge else pad
        available_right = contact_left_edge - pad if contact_lines else target_w - pad
        center = (available_left + available_right) / 2
        x = round(center - total / 2)
        x = max(available_left, min(x, available_right - total))
        # Same row as the email line — not pinned to the bottom edge — so the
        # website reads as part of the same line, not a separate one below it.
        y = email_y if email_y is not None else strip_top + (strip_h - text_h) // 2
        _draw_brand_icon(draw, "globe", x, y + cap_mid, icon_size, symbol_font)
        draw.text((x + icon_size + icon_gap, y), text, font=font, fill=_BRAND_TEXT_COLOR)

    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


# The post title drawn onto the blog image itself — in the upper-left, in a
# color sampled from the site's own logo (independent of whether the brand
# strip footer is switched on: the title is a separate feature). Added as
# its own step so the prompt, resize and brand-footer code above are
# untouched, apart from one added line asking the model to keep this corner
# plain (see generate_and_publish_image).
#
# A hard-edged, fully opaque rectangle read as a sticker pasted over the
# photo (user report, with a screenshot of a lab photo mostly hidden behind
# one). Replaced with a soft, partly translucent tint that fades out at its
# own right and bottom edges, sized to the text itself rather than a fixed
# block — so it blends into the picture instead of sitting on top of it.
_TITLE_FONT_CANDIDATES = ("arialbd.ttf", "C:/Windows/Fonts/arialbd.ttf", "seguisb.ttf", "C:/Windows/Fonts/segoeuib.ttf")
_TITLE_FALLBACK_COLOR = (25, 30, 45)
_TITLE_TINT_MAX_ALPHA = 190
_TITLE_MAX_LINES = 3


def _title_font(size: int):
    for name in _TITLE_FONT_CANDIDATES:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)


def _dominant_logo_color(logo_path: Optional[str]) -> Optional[tuple[int, int, int]]:
    """The logo's own most common vivid color (skipping near-white,
    near-black and near-gray pixels, which are backgrounds/outlines, not
    the brand color). None when there is no logo or it has no vivid color
    — the caller falls back to a plain dark color in that case."""
    if not logo_path or not os.path.exists(logo_path):
        return None
    try:
        logo = Image.open(logo_path).convert("RGBA")
    except Exception:
        return None
    small = logo.copy()
    small.thumbnail((120, 120))
    buckets: dict[tuple[int, int, int], int] = {}
    for r, g, b, a in small.getdata():
        if a < 128:
            continue
        hi, lo = max(r, g, b), min(r, g, b)
        saturation = 0 if hi == 0 else (hi - lo) / hi
        value = hi / 255
        if saturation < 0.35 or value < 0.25:
            continue
        key = (r // 24 * 24, g // 24 * 24, b // 24 * 24)
        buckets[key] = buckets.get(key, 0) + 1
    if not buckets:
        return None
    return max(buckets.items(), key=lambda kv: kv[1])[0]


def _wrap_title(draw, text: str, font, max_width: int, max_lines: int = _TITLE_MAX_LINES) -> list[str]:
    words = text.split()
    lines: list[str] = []
    i = 0
    while i < len(words) and len(lines) < max_lines:
        current = words[i]
        i += 1
        while i < len(words):
            trial = f"{current} {words[i]}"
            if draw.textlength(trial, font=font) <= max_width:
                current = trial
                i += 1
            else:
                break
        lines.append(current)
    if i < len(words) and lines:
        last = lines[-1]
        while " " in last and draw.textlength(last + "…", font=font) > max_width:
            last = last.rsplit(" ", 1)[0]
        lines[-1] = last + "…"
    return lines


def _fade_mask(size: tuple[int, int], solid_w: int, fade_w: int, fade_h: int, max_alpha: int) -> Image.Image:
    """An alpha mask at max_alpha for the first solid_w columns, fading
    linearly to 0 over the next fade_w columns (a soft right edge), and
    separately fading the bottom fade_h rows to 0 (a soft bottom edge). The
    left and top edges are left hard because they already sit on the
    image's own corner, not a visible edge of the tint."""
    w, h = size
    row = [max_alpha] * min(solid_w, w)
    for i in range(fade_w):
        if len(row) >= w:
            break
        row.append(round(max_alpha * (1 - (i + 1) / fade_w)))
    row += [0] * max(0, w - len(row))
    h_mask = Image.new("L", (w, 1))
    h_mask.putdata(row[:w])
    h_mask = h_mask.resize((w, h))

    col = [max_alpha] * max(0, h - fade_h)
    for i in range(fade_h):
        col.append(round(max_alpha * (1 - (i + 1) / fade_h)))
    col = (col[:h] + [0] * max(0, h - len(col)))[:h]
    v_mask = Image.new("L", (1, h))
    v_mask.putdata(col)
    v_mask = v_mask.resize((w, h))

    return ImageChops.multiply(h_mask, v_mask)


def _stamp_title_card(image_bytes: bytes, title: str, logo_path: Optional[str]) -> bytes:
    """Draws the post title in the upper-left of the scene, on a soft tint
    sized to the text and faded at its own edges — not a hard panel."""
    base = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    w, h = base.size
    measure = ImageDraw.Draw(Image.new("RGBA", (1, 1)))

    pad = round(w * 0.03)
    font = _title_font(max(16, round(h * 0.05)))
    max_text_w = round(w * 0.56) - 2 * pad
    lines = _wrap_title(measure, title.strip(), font, max_text_w)
    if not lines:
        return image_bytes

    line_h = measure.textbbox((0, 0), "Ag", font=font)[3]
    line_gap = max(2, round(line_h * 0.35))
    zone_h = 2 * pad + len(lines) * line_h + (len(lines) - 1) * line_gap
    longest_line_w = max(measure.textlength(line, font=font) for line in lines)
    solid_w = round(2 * pad + longest_line_w)
    # Generous fade margins — a softer, longer blend so the tint reads as a
    # light wash over the photo rather than any kind of edge at all.
    fade_w = round(pad * 4)
    fade_h = round(pad * 2)

    mask = _fade_mask((w, zone_h), solid_w, fade_w, fade_h, _TITLE_TINT_MAX_ALPHA)
    tint = Image.new("RGBA", (w, zone_h), (255, 255, 255, 255))
    tint.putalpha(mask)
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    overlay.paste(tint, (0, 0), tint)

    draw = ImageDraw.Draw(overlay)
    color = _dominant_logo_color(logo_path) or _TITLE_FALLBACK_COLOR
    y = pad
    for line in lines:
        draw.text((pad, y), line, font=font, fill=color)
        y += line_h + line_gap

    composited = Image.alpha_composite(base, overlay).convert("RGB")
    buffer = io.BytesIO()
    composited.save(buffer, format="PNG")
    return buffer.getvalue()


def generate_and_publish_image(site, prompt: str, *, task: str = "seo_content", title: Optional[str] = None) -> ImagePublishResult:
    provider = get_image_provider(task)
    standard_size = _standard_dimensions_for_task(task)
    request_width, request_height = standard_size or (1024, 1024)
    # Brand block: blog images only, and only when the site has one set.
    brand = brand_for_site(site) if task == "blog_post" and standard_size else None
    # Text inside the image should be a few short, correctly spelled labels
    # taken from the post itself (its key terms), not invented slogans.
    # Image models make up slogans and brochure copy when a prompt leaves
    # text open-ended, so the wording below is explicit about what is allowed.
    full_prompt = (
        prompt
        + _crop_safe_composition_guidance(standard_size)
        + " Include 2-4 short, correctly spelled labels that name the post's key terms "
        "(for example the topic words in the prompt above). No slogans, taglines, lorem ipsum, "
        "logos or brand names."
    )
    if task == "blog_post" and title:
        # The post title is drawn onto the upper-left corner afterward (see
        # _stamp_title_card) — asking for a plain area there up front means
        # there is less underneath for that tint to cover.
        full_prompt += (
            " The upper-left third of the image (from the top-left corner to roughly the middle) must be "
            "visually empty: a plain, softly blurred background only — no people, faces, objects, screens, "
            "charts, icons or UI elements there at all. Keep every subject and every detail of the scene in "
            "the remaining two-thirds of the frame instead. A title will be placed over that empty corner."
        )
    result = provider.generate(full_prompt, width=request_width, height=request_height)
    if not result.ok:
        return ImagePublishResult(
            ok=False,
            provider=provider.name,
            error=f"Image provider {provider.name!r} unavailable or failed: {result.error}. "
            "Configure PEXELS_API_KEY (free) or IMAGE_PROVIDER_DEFAULT=stability with "
            "STABILITY_API_KEY, or run a local FastSD server, then retry.",
        )

    image_bytes = result.image_bytes
    if standard_size:
        try:
            image_bytes = _resize_to_standard(image_bytes, standard_size)
        except Exception:
            logger.exception(
                "Failed to resize image to standard %s dimensions for task %r — using provider's original size",
                standard_size,
                task,
            )
            image_bytes = result.image_bytes

    if task == "blog_post" and title and standard_size:
        try:
            image_bytes = _stamp_title_card(image_bytes, title, getattr(site, "brand_logo_path", None))
        except Exception:
            # Never blocks the image itself — same graceful-degrade
            # convention as the resize and brand-strip steps above.
            logger.exception("Title card failed for site %s — publishing the image without it", getattr(site, "id", None))

    if brand and standard_size:
        try:
            image_bytes = _stamp_brand_strip(image_bytes, standard_size, brand)
        except Exception:
            # Never blocks the image itself: an unbranded image is still a
            # usable blog image, same graceful-degrade convention as resize.
            logger.exception("Brand strip failed for site %s — publishing the image without it", getattr(site, "id", None))

    webp = convert_to_webp(image_bytes)
    if webp is None:
        return ImagePublishResult(ok=False, provider=provider.name, error="WebP conversion failed — see server logs")

    publish_result = _publish_webp_bytes(site, webp.webp_bytes, prompt, provider=provider.name)
    if publish_result.ok:
        publish_result.reduction_pct = webp.reduction_pct
    return publish_result


def upload_image_bytes(site, image_bytes: bytes, name_hint: str) -> ImagePublishResult:
    """Module 38 — manual image upload: a human picks a file from their
    own computer instead of the AI generating one. Same WebP-conversion-
    then-upload-to-the-site's-own-server pipeline as generate_and_
    publish_image, just skipping the generation step — the file the
    caller already has takes the place of an ImageProvider's output."""
    webp = convert_to_webp(image_bytes)
    if webp is None:
        return ImagePublishResult(ok=False, provider="manual-upload", error="WebP conversion failed — is this a valid image file?")

    publish_result = _publish_webp_bytes(site, webp.webp_bytes, name_hint, provider="manual-upload")
    if publish_result.ok:
        publish_result.reduction_pct = webp.reduction_pct
    return publish_result
