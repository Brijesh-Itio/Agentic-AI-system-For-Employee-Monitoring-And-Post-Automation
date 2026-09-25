"""
Indexing Status & Crawl Monitoring — the blueprint feature that was
honestly left incomplete when module 26.5 shipped: only GSC's rank/query
data (searchAnalytics.query) was built, not index coverage. Two real,
documented Google APIs, both authenticated through the same
automation/seo/google_auth.py service-account flow already live-verified
for GSC/GA4:

1. Search Console's URL Inspection API (urlInspection.index:inspect) —
   the real, current replacement for the old Index Coverage report; tells
   you, per URL, whether Google has it indexed, why not if it doesn't,
   and what Google's own robots.txt/canonical reading of the page is.

2. The Indexing API (indexing.googleapis.com) — lets a site owner tell
   Google "this URL changed, please recrawl it soon" instead of waiting
   for the next scheduled crawl. Honest caveat, not glossed over: Google
   documents this API as intended only for pages marked up with
   JobPosting or BroadcastEvent structured data — using it for arbitrary
   content is outside its documented purpose and Google may not act on
   it. It's built here for real (a real, working REST call against a
   real, documented endpoint) rather than guessed at, but whether Google
   actually prioritizes a non-JobPosting/BroadcastEvent URL is between
   the site owner and Google, not something this codebase can promise.
"""
import logging
from dataclasses import dataclass
from typing import List, Optional

import requests

from ai.llm.retry import call_with_hard_timeout, with_retry
from automation.seo.google_auth import get_access_token, service_account_email

logger = logging.getLogger(__name__)

TIMEOUT_SECONDS = 30
INSPECT_URL = "https://searchconsole.googleapis.com/v1/urlInspection/index:inspect"
INDEXING_PUBLISH_URL = "https://indexing.googleapis.com/v3/urlNotifications:publish"

# Same scope gsc_client.py already uses and has live-verified — the URL
# Inspection API is part of the same Search Console API surface and
# Google's docs list webmasters.readonly as sufficient for a read-only
# inspection call.
INSPECT_SCOPE = ["https://www.googleapis.com/auth/webmasters.readonly"]
INDEXING_SCOPE = ["https://www.googleapis.com/auth/indexing"]

VALID_NOTIFICATION_TYPES = ("URL_UPDATED", "URL_DELETED")


@dataclass
class UrlInspectionResult:
    url: str
    verdict: Optional[str]
    coverage_state: Optional[str]
    indexing_state: Optional[str]
    robots_txt_state: Optional[str]
    page_fetch_state: Optional[str]
    last_crawl_time: Optional[str]
    google_canonical: Optional[str]
    user_canonical: Optional[str]
    sitemap: List[str]
    # Google's response carries this as a genuinely separate top-level
    # result object (mobileUsabilityResult), not part of indexStatusResult
    # — verified live this session that the real API response includes it
    # even though this field previously went unparsed. "VERDICT_UNSPECIFIED"
    # is Google's own value when it hasn't run a mobile-usability check for
    # this URL yet, not a failure of this call.
    mobile_usability_verdict: Optional[str] = None
    # Google's own real link to view this exact inspection result inside
    # Search Console — verified live this session that the API actually
    # returns this (inspectionResultLink), previously discarded.
    inspection_result_link: Optional[str] = None
    # "MOBILE" or "DESKTOP" — which user agent Google crawled the page
    # as. Also previously discarded despite being in the real response.
    crawled_as: Optional[str] = None


@dataclass
class IndexingSubmitResult:
    ok: bool
    url: str
    notification_type: str
    raw: Optional[dict] = None
    error: Optional[str] = None


def _explain_inspection_failure(exc: Exception, site_url: str) -> str:
    """Turns a failed inspection call into something a person can act on.
    The route used to say only "see server logs", which hid the one thing
    worth knowing — Google's own reason (e.g. "You do not own this site")."""
    response = getattr(exc, "response", None)
    if response is not None:
        try:
            google_message = (response.json().get("error") or {}).get("message") or ""
        except Exception:
            google_message = ""
        status = response.status_code
        if status in (401, 403):
            email = service_account_email() or "the service account"
            return (
                f"Google refused access to {site_url} — {google_message or 'permission denied'} "
                f"In Search Console (Settings → Users and permissions) make sure {email} is added "
                "to this exact property with Full or Owner access, and that the property is still verified."
            )
        if status == 404:
            return f"Google could not find the property {site_url} — check the Search Console property set for this site."
        return f"Google returned an error ({status}): {google_message or 'no details'}"
    if isinstance(exc, TimeoutError):
        return "Google did not answer in time — try again in a moment."
    return f"URL Inspection request failed: {exc}"


def fetch_url_inspection(url: str, site_url: Optional[str] = None) -> Optional[UrlInspectionResult]:
    """Same as fetch_url_inspection_with_reason, keeping only the result —
    the form every existing caller (the daily pipeline included) uses."""
    return fetch_url_inspection_with_reason(url, site_url)[0]


def fetch_url_inspection_with_reason(
    url: str, site_url: Optional[str] = None
) -> tuple[Optional[UrlInspectionResult], Optional[str]]:
    """Never raises — returns None on failure (unconfigured, auth,
    network, or the service account lacking Search Console access to this
    property), matching this codebase's graceful-degrade convention.
    site_url is the property to inspect against — callers decide whether
    falling back to the global GSC_SITE_URL .env default is safe (see
    gsc_client.py's matching note); inspecting against the wrong property
    is at least a real 403 from Google here (the property has to
    actually contain the URL), unlike gsc_pull/ga4_pull's plain data
    pulls, but this stays consistent with them rather than being the one
    exception to the "caller decides" rule."""
    if not site_url:
        logger.error("GSC not configured — set GSC_SITE_URL in .env")
        return None, "No Search Console property is set for this site — add one in the site's Google settings."

    token = get_access_token(INSPECT_SCOPE)
    if token is None:
        return None, "Google credentials aren't set up (GOOGLE_SERVICE_ACCOUNT_JSON_PATH) or the login to Google failed."

    body = {"inspectionUrl": url, "siteUrl": site_url}

    def _do_request():
        response = requests.post(
            INSPECT_URL, json=body, headers={"Authorization": f"Bearer {token}"}, timeout=TIMEOUT_SECONDS
        )
        response.raise_for_status()
        return response

    # Verified live: this specific call has hung indefinitely with the
    # process idle (0% CPU, thread stuck in Wait) well past
    # TIMEOUT_SECONDS, something curl against the same endpoint never
    # reproduced — requests'/urllib3's own timeout isn't reliably bounding
    # it on this host. call_with_hard_timeout is a second, independent
    # deadline so a single inspection call can't wedge a request forever.
    try:
        response = with_retry(
            lambda: call_with_hard_timeout(_do_request, TIMEOUT_SECONDS + 10),
            max_attempts=3,
            retry_on=(requests.RequestException, TimeoutError),
        )
        data = response.json()
    except Exception as exc:
        logger.exception("URL Inspection API failed (url=%s)", url)
        return None, _explain_inspection_failure(exc, site_url)

    inspection_result = data.get("inspectionResult") or {}
    index_result = inspection_result.get("indexStatusResult") or {}
    mobile_result = inspection_result.get("mobileUsabilityResult") or {}
    result = UrlInspectionResult(
        url=url,
        verdict=index_result.get("verdict"),
        coverage_state=index_result.get("coverageState"),
        indexing_state=index_result.get("indexingState"),
        robots_txt_state=index_result.get("robotsTxtState"),
        page_fetch_state=index_result.get("pageFetchState"),
        last_crawl_time=index_result.get("lastCrawlTime"),
        google_canonical=index_result.get("googleCanonical"),
        user_canonical=index_result.get("userCanonical"),
        sitemap=index_result.get("sitemap") or [],
        mobile_usability_verdict=mobile_result.get("verdict"),
        inspection_result_link=inspection_result.get("inspectionResultLink"),
        crawled_as=index_result.get("crawledAs"),
    )
    return result, None


def submit_url_for_indexing(url: str, notification_type: str = "URL_UPDATED") -> IndexingSubmitResult:
    """Never raises — always returns an IndexingSubmitResult, ok=False on
    any failure, so a caller can log/store the honest outcome (including
    a real permission error, e.g. the service account not yet added as an
    owner/user on this property in Search Console — that's a one-time
    manual step in the Search Console UI, not something this API call can
    do on its own) rather than crashing the request that triggered it."""
    if notification_type not in VALID_NOTIFICATION_TYPES:
        return IndexingSubmitResult(
            ok=False, url=url, notification_type=notification_type,
            error=f"notification_type must be one of {VALID_NOTIFICATION_TYPES}",
        )

    token = get_access_token(INDEXING_SCOPE)
    if token is None:
        return IndexingSubmitResult(
            ok=False, url=url, notification_type=notification_type,
            error="Could not obtain an OAuth2 token for the indexing scope — see server logs",
        )

    body = {"url": url, "type": notification_type}

    def _do_request():
        return requests.post(
            INDEXING_PUBLISH_URL, json=body, headers={"Authorization": f"Bearer {token}"}, timeout=TIMEOUT_SECONDS
        )

    try:
        response = with_retry(_do_request, max_attempts=3, retry_on=(requests.RequestException,))
    except requests.RequestException as exc:
        logger.exception("Indexing API request failed (url=%s)", url)
        return IndexingSubmitResult(ok=False, url=url, notification_type=notification_type, error=str(exc))

    try:
        data = response.json()
    except ValueError:
        data = {"raw_text": response.text}

    if response.status_code >= 400:
        error_detail = (data.get("error") or {}).get("message") or str(data)
        logger.warning("Indexing API rejected submission (url=%s, status=%s): %s", url, response.status_code, error_detail)
        return IndexingSubmitResult(ok=False, url=url, notification_type=notification_type, raw=data, error=error_detail)

    return IndexingSubmitResult(ok=True, url=url, notification_type=notification_type, raw=data)
