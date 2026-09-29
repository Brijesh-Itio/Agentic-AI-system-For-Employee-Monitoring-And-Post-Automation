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
import re
import time
import urllib.parse
from dataclasses import dataclass
from typing import Optional

from PIL import Image, ImageFilter

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
    "blog_post": (1200, 600),
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
        f" Compose as a single wide landscape image (roughly {target_w}:{target_h}). Every element — "
        "subject, text, icons, UI mockups — must be FULLY contained within the frame, with clear empty "
        "margin on all four sides; nothing may be cropped, cut off, or bleed past any edge, especially "
        "the top and bottom (those get cropped further for this format). If the scene involves multiple "
        "panels, labels, or data points, keep the count small (2-4 at most) and each one large and simple "
        "enough to fit with room to spare — do not pack many small panels or dense rows of text edge-to-edge; "
        "a crowded layout is what causes elements to run off the canvas or overlap."
    )


def _resize_to_standard(image_bytes: bytes, target_size: tuple[int, int]) -> bytes:
    """Fits the whole source image inside target_size with no cropping —
    scales it down (never up) so every pixel survives, then centers it on
    a blurred, filled-to-cover copy of the same image so the letterbox
    space reads as an intentional background rather than dead bars (the
    same technique Instagram/Spotify use for non-matching aspect ratios).

    This used to center-crop to the target ratio instead, which reliably
    threw away real content: no image provider here generates a native
    ~1.91:1 image (see generate_and_publish_image's own comment), so that
    crop always cut roughly the top+bottom 20% off, and _crop_safe_
    composition_guidance's prompt-level "leave that margin empty" request
    was confirmed live, twice, not to be reliably followed — a post title
    and a process-flow step both still got cut mid-element despite it. A
    prompt is advice the model can ignore; not cropping the image we
    already have is a hard guarantee, so that's what this does now."""
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    target_w, target_h = target_size
    src_w, src_h = image.size

    fit_scale = min(target_w / src_w, target_h / src_h)
    fit_w, fit_h = max(1, round(src_w * fit_scale)), max(1, round(src_h * fit_scale))
    fitted = image.resize((fit_w, fit_h), Image.LANCZOS)

    fill_scale = max(target_w / src_w, target_h / src_h)
    fill_w, fill_h = max(target_w, round(src_w * fill_scale)), max(target_h, round(src_h * fill_scale))
    background = image.resize((fill_w, fill_h), Image.LANCZOS)
    left = (fill_w - target_w) // 2
    top = (fill_h - target_h) // 2
    background = background.crop((left, top, left + target_w, top + target_h))
    background = background.filter(ImageFilter.GaussianBlur(radius=30))

    background.paste(fitted, ((target_w - fit_w) // 2, (target_h - fit_h) // 2))
    buffer = io.BytesIO()
    background.save(buffer, format="PNG")
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


def generate_and_publish_image(site, prompt: str, *, task: str = "seo_content") -> ImagePublishResult:
    provider = get_image_provider(task)
    standard_size = _standard_dimensions_for_task(task)
    request_width, request_height = standard_size or (1024, 1024)
    full_prompt = prompt + _crop_safe_composition_guidance(standard_size)
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
