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
import logging
import re
import time
import urllib.parse
from dataclasses import dataclass
from typing import Optional

from ai.images.factory import get_provider as get_image_provider
from automation.seo.server_access import client_for_site
from automation.seo.webp_converter import convert_to_webp

logger = logging.getLogger(__name__)

UPLOAD_SUBDIR = "wp-content/uploads/seo-agent"

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
    result = provider.generate(prompt)
    if not result.ok:
        return ImagePublishResult(
            ok=False,
            provider=provider.name,
            error=f"Image provider {provider.name!r} unavailable or failed: {result.error}. "
            "Configure PEXELS_API_KEY (free) or IMAGE_PROVIDER_DEFAULT=stability with "
            "STABILITY_API_KEY, or run a local FastSD server, then retry.",
        )

    webp = convert_to_webp(result.image_bytes)
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
