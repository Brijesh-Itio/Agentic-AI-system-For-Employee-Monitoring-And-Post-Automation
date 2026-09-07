"""
MODULE 26.4 — PageSpeed Insights client.

Simplest of the three free Google data pulls this module adds: no OAuth,
just an optional API key (Google allows unauthenticated calls at a much
lower quota — PAGESPEED_API_KEY blank means "use that free anonymous
quota," not "off"). Pulls the Core Web Vitals / performance metrics the
SEO blueprint calls out (LCP, CLS, INP, TTFB, FCP, performance score)
plus the full raw response, so a later module can pull more detail out
without a schema change here.
"""
import logging
from dataclasses import dataclass
from typing import List, Optional

import requests

from ai.llm.retry import with_retry  # generic backoff helper, not LLM-specific
from api.config import settings

logger = logging.getLogger(__name__)

# Lighthouse runs server-side on Google's end and can genuinely take
# 20-40s for a real page — much longer than a typical REST call. A slow/
# heavy page (large LCP, lots of resources) can push a desktop audit past
# 60s, which was tripping this timeout before the real Lighthouse run
# even finished — 90s gives real audits enough room.
TIMEOUT_SECONDS = 90
API_URL = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"


@dataclass
class PageSpeedResult:
    url: str
    strategy: str
    performance_score: Optional[float]  # 0-100
    lcp_ms: Optional[float]
    cls: Optional[float]
    inp_ms: Optional[float]
    ttfb_ms: Optional[float]
    fcp_ms: Optional[float]
    raw: dict


def _audit_value(audits: dict, audit_id: str) -> Optional[float]:
    audit = audits.get(audit_id)
    if not audit:
        return None
    return audit.get("numericValue")


def fetch_page_speed(url: str, strategy: str = "mobile") -> Optional[PageSpeedResult]:
    """Never raises — returns None on failure, same graceful-degrade
    convention as every other external-call site in this codebase."""
    params = {"url": url, "strategy": strategy, "category": "performance"}
    if settings.PAGESPEED_API_KEY:
        params["key"] = settings.PAGESPEED_API_KEY

    def _do_request():
        response = requests.get(API_URL, params=params, timeout=TIMEOUT_SECONDS)
        response.raise_for_status()  # inside the retried call, so a 429/5xx retries too
        return response

    try:
        response = with_retry(_do_request, max_attempts=3, retry_on=(requests.RequestException,))
        data = response.json()
    except Exception:
        logger.exception("PageSpeed fetch failed (url=%s, strategy=%s)", url, strategy)
        return None

    lighthouse = data.get("lighthouseResult", {})
    categories = lighthouse.get("categories", {})
    audits = lighthouse.get("audits", {})
    performance_score = (categories.get("performance") or {}).get("score")

    return PageSpeedResult(
        url=url,
        strategy=strategy,
        performance_score=performance_score * 100 if performance_score is not None else None,
        lcp_ms=_audit_value(audits, "largest-contentful-paint"),
        cls=_audit_value(audits, "cumulative-layout-shift"),
        # INP is Lighthouse's newer replacement for FID; total-blocking-time
        # is the closest lab-data proxy on installs where INP isn't reported.
        inp_ms=_audit_value(audits, "interaction-to-next-paint")
        or _audit_value(audits, "total-blocking-time"),
        ttfb_ms=_audit_value(audits, "server-response-time"),
        fcp_ms=_audit_value(audits, "first-contentful-paint"),
        raw=data,
    )


@dataclass
class PageSpeedOpportunity:
    audit_id: str
    title: str
    description: str
    savings_ms: Optional[float]
    savings_bytes: Optional[float]


@dataclass
class ResourceAuditReport:
    total_requests: Optional[int]
    total_byte_weight_kb: Optional[float]
    unused_css_kb: Optional[float]
    unused_js_kb: Optional[float]
    render_blocking_requests: Optional[int]
    opportunities: List[PageSpeedOpportunity]


def extract_resource_report(raw: dict) -> ResourceAuditReport:
    """Pulls the blueprint's fuller resource audit (request counts, total
    page weight, unused CSS/JS, a prioritized fix list) out of a PageSpeed
    response that's already been fetched and stored — no second API call.
    Pure/offline: never touches the network, so it can run against any
    raw_json already sitting in seo_pagespeed_results.

    Two sources, both part of Lighthouse's stable, documented audit shape:
    - the "diagnostics" audit's single details.items[0] entry carries the
      page-level totals (request count, total byte weight) Lighthouse
      itself computes for its own report.
    - every audit whose details.type == "opportunity" is, by Lighthouse's
      own definition, a specific, actionable fix with an estimated saving
      — iterating all of them (rather than hardcoding specific audit IDs,
      which drift between Lighthouse versions) is what builds the
      prioritized fix list."""
    audits = (raw.get("lighthouseResult") or {}).get("audits") or {}

    diagnostics_items = ((audits.get("diagnostics") or {}).get("details") or {}).get("items") or []
    diag = diagnostics_items[0] if diagnostics_items else {}
    total_requests = diag.get("numRequests")
    total_byte_weight_kb = diag.get("totalByteWeight") / 1024 if diag.get("totalByteWeight") is not None else None

    render_blocking_items = ((audits.get("render-blocking-resources") or {}).get("details") or {}).get("items") or []

    def _savings_kb(audit_id: str) -> Optional[float]:
        details = (audits.get(audit_id) or {}).get("details") or {}
        savings_bytes = details.get("overallSavingsBytes")
        return savings_bytes / 1024 if savings_bytes is not None else None

    opportunities: List[PageSpeedOpportunity] = []
    for audit_id, audit in audits.items():
        details = audit.get("details") or {}
        if details.get("type") != "opportunity":
            continue
        opportunities.append(
            PageSpeedOpportunity(
                audit_id=audit_id,
                title=audit.get("title", audit_id),
                description=audit.get("description", ""),
                savings_ms=details.get("overallSavingsMs"),
                savings_bytes=details.get("overallSavingsBytes"),
            )
        )
    opportunities.sort(key=lambda o: (o.savings_ms or 0, o.savings_bytes or 0), reverse=True)

    return ResourceAuditReport(
        total_requests=total_requests,
        total_byte_weight_kb=total_byte_weight_kb,
        unused_css_kb=_savings_kb("unused-css-rules"),
        unused_js_kb=_savings_kb("unused-javascript"),
        render_blocking_requests=len(render_blocking_items) or None,
        opportunities=opportunities,
    )
