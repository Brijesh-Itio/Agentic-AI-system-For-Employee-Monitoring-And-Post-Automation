"""
MODULE 49 — Google Site Verification API.

A genuinely separate Google API from Search Console (base URL
www.googleapis.com/siteVerification/v1, its own OAuth scope) — it answers
"which web properties has THIS Google identity verified ownership of,"
not "which properties can this identity read Search Console data for."
Those are different permission systems: being added as a Search Console
user (what GSC_SITE_URL / seo_sites.gsc_site_url relies on for every
other GSC feature in this codebase) does not make the service account a
verified owner, and being a verified owner doesn't by itself grant
Search Console data access either — verified live this session as two
independently real, sometimes-empty result sets.

Honest expectation, not a guess: since this app's sites were connected by
adding the service account as a Search Console USER (not by having the
service account itself perform domain/HTML-file/meta-tag verification),
list_verified_sites() below can legitimately come back empty even though
Search Console data access works fine — that's a correct, expected
result for this account, not a bug in this client.
"""
import logging
from dataclasses import dataclass, field
from typing import List, Optional

import requests

from ai.llm.retry import with_retry
from automation.seo.google_auth import get_access_token

logger = logging.getLogger(__name__)

TIMEOUT_SECONDS = 30
BASE_URL = "https://www.googleapis.com/siteVerification/v1"
# verify_only is the read-capable half of this API's scope split — full
# "siteverification" additionally allows performing new verifications,
# which this codebase has no UI for (verification is normally a one-time
# manual step in Search Console itself, same as adding a GSC user).
SCOPE = ["https://www.googleapis.com/auth/siteverification.verify_only"]


@dataclass
class VerifiedSite:
    id: str
    type: Optional[str]  # "SITE" | "INET_DOMAIN"
    identifier: Optional[str]
    owners: List[str] = field(default_factory=list)


def _parse_site(raw: dict) -> VerifiedSite:
    site = raw.get("site", {})
    return VerifiedSite(
        id=raw.get("id", ""),
        type=site.get("type"),
        identifier=site.get("identifier"),
        owners=raw.get("owners", []),
    )


def list_verified_sites() -> Optional[List[VerifiedSite]]:
    """Lists every property this Google identity (the service account) is
    a verified owner of. Never raises — returns None on failure
    (unconfigured, auth, network), and a real empty list — not an error —
    when the identity owns nothing, which is the expected, correct result
    for a service account connected via the "add as Search Console user"
    path instead of performing its own site verification."""
    token = get_access_token(SCOPE)
    if token is None:
        return None

    def _do_request():
        response = requests.get(
            f"{BASE_URL}/webResource", headers={"Authorization": f"Bearer {token}"}, timeout=TIMEOUT_SECONDS
        )
        response.raise_for_status()
        return response

    try:
        response = with_retry(_do_request, max_attempts=3, retry_on=(requests.RequestException,))
        data = response.json()
    except Exception:
        logger.exception("list_verified_sites failed")
        return None

    return [_parse_site(r) for r in data.get("items", [])]


def get_verification_info(resource_id: str) -> Optional[VerifiedSite]:
    """Ownership detail for one already-verified property, addressed by
    its webResource id (the `id` field list_verified_sites returns —
    typically the site's own URL or "dns://domain" form, not a separate
    opaque id). Never raises — returns None on failure, including the
    honest case of a real 404 for an id this identity doesn't own."""
    token = get_access_token(SCOPE)
    if token is None:
        return None

    def _do_request():
        response = requests.get(
            f"{BASE_URL}/webResource/{resource_id}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return response

    try:
        response = with_retry(_do_request, max_attempts=3, retry_on=(requests.RequestException,))
        return _parse_site(response.json())
    except Exception:
        logger.exception("get_verification_info failed (resource_id=%s)", resource_id)
        return None
