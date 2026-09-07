"""
MODULE 26/28 hardening — public URL validation (SSRF protection).

seo_sites.base_url is user-supplied (any authenticated user can register
a site via POST /api/seo/sites) and flows directly into
automation/seo/crawler.py's crawl_site() and, from module 26, whatever
CMS/data-pull calls a future pipeline points at it. Without this check,
an authenticated user could register a "site" whose base_url points at
an internal service or the cloud metadata endpoint (169.254.169.254) and
trigger a technical audit to make this server fetch it on their behalf —
a textbook SSRF. Applied once at site-creation time (api/routes/seo.py's
create_site) so a bad URL is rejected before it's ever stored, and again
at crawl start (defense in depth against a hostname being repointed at
an internal IP after creation — "DNS rebinding") — not re-validated on
every single page fetch during a crawl, since this app's actual threat
model (single-tenant, operator-trusted CMS credentials) doesn't warrant
that cost; same-origin-only crawling (crawler.py's _normalize_url)
already bounds a crawl to whatever passed this check at its start.
"""
import ipaddress
import logging
import socket
import urllib.parse

logger = logging.getLogger(__name__)


class UnsafeUrlError(ValueError):
    pass


def _is_unsafe_ip(ip_str: str) -> bool:
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return True  # unparseable -> fail closed
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    )


def assert_public_url(url: str) -> None:
    """Raises UnsafeUrlError if `url` isn't a plausibly-public http(s)
    URL. Resolves the hostname and checks every returned address (a
    hostname can have multiple A/AAAA records) — rejects if any of them
    is private/internal/reserved, and fails closed on any resolution
    error rather than letting an unresolvable/ambiguous host through."""
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme not in ("http", "https"):
        raise UnsafeUrlError(f"URL must be http:// or https://, got {parsed.scheme!r}")
    if not parsed.hostname:
        raise UnsafeUrlError("URL has no hostname")
    if parsed.hostname.lower() == "localhost":
        raise UnsafeUrlError("localhost is not allowed")

    try:
        addr_infos = socket.getaddrinfo(parsed.hostname, None)
    except socket.gaierror as exc:
        raise UnsafeUrlError(f"Could not resolve hostname {parsed.hostname!r}: {exc}") from exc

    for _family, _type, _proto, _canonname, sockaddr in addr_infos:
        ip_str = sockaddr[0]
        if _is_unsafe_ip(ip_str):
            raise UnsafeUrlError(
                f"{parsed.hostname!r} resolves to {ip_str}, a private/internal/reserved address "
                "— refusing to register or crawl it"
            )
