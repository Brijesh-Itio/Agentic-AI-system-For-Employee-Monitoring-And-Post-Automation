"""
MODULE 48 — Google Search Console Sitemaps management.

The gap gsc_client.py's own docstring flagged as deliberately out of
scope when module 26.5 shipped: "index coverage and sitemap status are a
separate, later concern." This is that module — list/get/submit/delete
against the real Search Console Sitemaps resource
(webmasters/v3/sites/{siteUrl}/sitemaps), same service-account auth
already live-verified for search analytics.

List/get only need the read-only scope already used elsewhere in this
package; submit/delete need the broader read-write "webmasters" scope
(Google's Sitemaps API has no separate write-only scope) — a service
account whose Search Console access is read-only will get a real 403 on
those two calls, which this module surfaces honestly rather than masking.
"""
import logging
import urllib.parse
from dataclasses import dataclass, field
from typing import List, Optional

import requests

from ai.llm.retry import with_retry
from automation.seo.google_auth import get_access_token

logger = logging.getLogger(__name__)

TIMEOUT_SECONDS = 30
READONLY_SCOPE = ["https://www.googleapis.com/auth/webmasters.readonly"]
READWRITE_SCOPE = ["https://www.googleapis.com/auth/webmasters"]


@dataclass
class SitemapContentType:
    type: str
    submitted: Optional[int]
    indexed: Optional[int]


@dataclass
class SitemapInfo:
    path: str
    last_submitted: Optional[str]
    is_pending: Optional[bool]
    is_sitemaps_index: Optional[bool]
    type: Optional[str]
    last_downloaded: Optional[str]
    warnings: Optional[int]
    errors: Optional[int]
    contents: List[SitemapContentType] = field(default_factory=list)


def _parse_sitemap(raw: dict) -> SitemapInfo:
    return SitemapInfo(
        path=raw.get("path", ""),
        last_submitted=raw.get("lastSubmitted"),
        is_pending=raw.get("isPending"),
        is_sitemaps_index=raw.get("isSitemapsIndex"),
        type=raw.get("type"),
        last_downloaded=raw.get("lastDownloaded"),
        warnings=int(raw["warnings"]) if "warnings" in raw else None,
        errors=int(raw["errors"]) if "errors" in raw else None,
        contents=[
            SitemapContentType(
                type=c.get("type", ""),
                submitted=int(c["submitted"]) if "submitted" in c else None,
                indexed=int(c["indexed"]) if "indexed" in c else None,
            )
            for c in raw.get("contents", [])
        ],
    )


def _sitemaps_url(site_url: str, feedpath: Optional[str] = None) -> str:
    encoded_site = urllib.parse.quote(site_url, safe="")
    base = f"https://www.googleapis.com/webmasters/v3/sites/{encoded_site}/sitemaps"
    if feedpath is None:
        return base
    return f"{base}/{urllib.parse.quote(feedpath, safe='')}"


def list_sitemaps(site_url: str) -> Optional[List[SitemapInfo]]:
    """Never raises — returns None on failure (unconfigured, auth,
    network, or the service account lacking access to this property),
    matching this codebase's graceful-degrade convention. An empty list
    is a real, honest result (a property with no sitemaps submitted),
    not a failure."""
    token = get_access_token(READONLY_SCOPE)
    if token is None:
        return None

    def _do_request():
        response = requests.get(
            _sitemaps_url(site_url), headers={"Authorization": f"Bearer {token}"}, timeout=TIMEOUT_SECONDS
        )
        response.raise_for_status()
        return response

    try:
        response = with_retry(_do_request, max_attempts=3, retry_on=(requests.RequestException,))
        data = response.json()
    except Exception:
        logger.exception("list_sitemaps failed (site=%s)", site_url)
        return None

    return [_parse_sitemap(s) for s in data.get("sitemap", [])]


def get_sitemap_status(site_url: str, feedpath: str) -> Optional[SitemapInfo]:
    """Status/detail for ONE sitemap (indexed vs. submitted counts per
    content type, warnings/errors) — list_sitemaps above returns the same
    shape per row already, this exists for looking up a single one
    directly by its feed path without paging through the whole list."""
    token = get_access_token(READONLY_SCOPE)
    if token is None:
        return None

    def _do_request():
        response = requests.get(
            _sitemaps_url(site_url, feedpath), headers={"Authorization": f"Bearer {token}"}, timeout=TIMEOUT_SECONDS
        )
        response.raise_for_status()
        return response

    try:
        response = with_retry(_do_request, max_attempts=3, retry_on=(requests.RequestException,))
        return _parse_sitemap(response.json())
    except Exception:
        logger.exception("get_sitemap_status failed (site=%s, feedpath=%s)", site_url, feedpath)
        return None


@dataclass
class SitemapActionResult:
    ok: bool
    detail: str


def submit_sitemap(site_url: str, feedpath: str) -> SitemapActionResult:
    """Registers a sitemap URL with Search Console (PUT — idempotent,
    re-submitting an already-known sitemap is a no-op success, not an
    error). Never raises — always returns a SitemapActionResult; ok=False
    on any failure including a real permission error (the service account
    needs full read-write "webmasters" access to this property for this
    call to succeed, not just the read-only scope list/get use)."""
    token = get_access_token(READWRITE_SCOPE)
    if token is None:
        return SitemapActionResult(ok=False, detail="Could not obtain an OAuth2 token for the webmasters scope")

    def _do_request():
        return requests.put(
            _sitemaps_url(site_url, feedpath), headers={"Authorization": f"Bearer {token}"}, timeout=TIMEOUT_SECONDS
        )

    try:
        response = with_retry(_do_request, max_attempts=3, retry_on=(requests.RequestException,))
    except requests.RequestException as exc:
        logger.exception("submit_sitemap failed (site=%s, feedpath=%s)", site_url, feedpath)
        return SitemapActionResult(ok=False, detail=str(exc))

    if response.status_code >= 400:
        try:
            detail = (response.json().get("error") or {}).get("message") or response.text
        except Exception:
            detail = response.text
        logger.warning("submit_sitemap rejected (site=%s, feedpath=%s, status=%s): %s", site_url, feedpath, response.status_code, detail)
        return SitemapActionResult(ok=False, detail=detail)

    return SitemapActionResult(ok=True, detail=f"Sitemap {feedpath} submitted")


def delete_sitemap(site_url: str, feedpath: str) -> SitemapActionResult:
    """Removes a sitemap from Search Console's tracked list — does NOT
    delete the actual sitemap.xml file, only tells Google to stop
    tracking it as a submitted sitemap for this property."""
    token = get_access_token(READWRITE_SCOPE)
    if token is None:
        return SitemapActionResult(ok=False, detail="Could not obtain an OAuth2 token for the webmasters scope")

    def _do_request():
        return requests.delete(
            _sitemaps_url(site_url, feedpath), headers={"Authorization": f"Bearer {token}"}, timeout=TIMEOUT_SECONDS
        )

    try:
        response = with_retry(_do_request, max_attempts=3, retry_on=(requests.RequestException,))
    except requests.RequestException as exc:
        logger.exception("delete_sitemap failed (site=%s, feedpath=%s)", site_url, feedpath)
        return SitemapActionResult(ok=False, detail=str(exc))

    if response.status_code >= 400:
        try:
            detail = (response.json().get("error") or {}).get("message") or response.text
        except Exception:
            detail = response.text
        logger.warning("delete_sitemap rejected (site=%s, feedpath=%s, status=%s): %s", site_url, feedpath, response.status_code, detail)
        return SitemapActionResult(ok=False, detail=detail)

    return SitemapActionResult(ok=True, detail=f"Sitemap {feedpath} removed from Search Console's tracked list")
