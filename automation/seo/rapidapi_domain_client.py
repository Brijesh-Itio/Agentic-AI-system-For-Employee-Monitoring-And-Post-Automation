"""
MODULE 47 — RapidAPI "SEMrush SEO" domain-analysis wrapper.

Same host as rapidapi_keyword_client.py's now-broken web-keyoword-tool.php
endpoint (semrush-seo3.p.rapidapi.com), but a DIFFERENT set of endpoints on
that host, live-verified this session against real domains (webpays.com,
rapidapi.com, thefinrate.com, google.com, youtube.com) using the same
RAPIDAPI_SEMRUSH_MAGIC_KEY already confirmed working for the Magic Tool /
semrush-seo10 products in rapidapi_keyword_client.py — RapidAPI keys are
per-account, not per-API, so one key authenticates across every product
the account is subscribed to; the host header is what selects the API.

Six endpoints under this host were tested live this session:
  - POST /backlink.php     (form: website)        -> real per-page backlinks         WORKING
  - POST /keyword-tool.php (form: country, keyword)-> real volume/cpc/competition     WORKING
  - POST /webtraffic.php   (form: website)         -> real organic traffic + samples  WORKING
  - POST /dapa.php         (form: website)         -> real Domain/Page Authority      WORKING
  - POST /bulk-dapa.php    (form: domains, csv)    -> same, for several domains       WORKING
  - POST /competitor.php   (any domain-like field) -> {"message":"Missing or invalid
    session credential","error":"Unauthorized","statusCode":401} EVERY time a real
    domain is supplied (tried as website=, domain=, with/without scheme, with/without
    a country field) — a provider-side auth bug, not a request-shape problem (the
    exact same request with no domain field at all gets past that check and instead
    returns "Website domain is required", proving the key/host auth itself is fine).
    Deliberately NOT implemented here: shipping a feature verified to never return
    real data would be worse than not having it.
"""
import logging
from dataclasses import dataclass, field
from typing import List, Optional

import requests

from ai.llm.retry import with_retry
from api.config import settings

logger = logging.getLogger(__name__)

TIMEOUT_SECONDS = 45
BASE_URL = "https://semrush-seo3.p.rapidapi.com"
HOST = "semrush-seo3.p.rapidapi.com"


def is_configured() -> bool:
    # Same RapidAPI application/key as the Magic Tool and semrush-seo10
    # endpoints in rapidapi_keyword_client.py.
    return bool(settings.RAPIDAPI_SEMRUSH_MAGIC_KEY)


def _headers() -> dict:
    return {"x-rapidapi-host": HOST, "x-rapidapi-key": settings.RAPIDAPI_SEMRUSH_MAGIC_KEY}


@dataclass
class BacklinkRow:
    url_from: str
    url_to: str
    title: str
    anchor: str
    nofollow: bool
    inlink_rank: Optional[float]
    domain_inlink_rank: Optional[float]
    first_seen: str
    last_visited: str
    date_lost: str
    spam_score: Optional[float]


def fetch_top_backlinks(website: str) -> Optional[List[BacklinkRow]]:
    """Never raises — returns None if unconfigured or on any request/
    parse failure, matching this codebase's graceful-degrade convention."""
    if not is_configured():
        logger.error("rapidapi_domain_client: RAPIDAPI_SEMRUSH_MAGIC_KEY not set")
        return None

    def _do_request():
        response = requests.post(
            f"{BASE_URL}/backlink.php", files={"website": (None, website)}, headers=_headers(), timeout=TIMEOUT_SECONDS
        )
        response.raise_for_status()
        return response

    try:
        response = with_retry(_do_request, max_attempts=2, retry_on=(requests.RequestException,))
        rows = response.json().get("backlinks", [])
        return [
            BacklinkRow(
                url_from=r.get("url_from", ""),
                url_to=r.get("url_to", ""),
                title=r.get("title", ""),
                anchor=r.get("anchor", ""),
                nofollow=bool(r.get("nofollow")),
                inlink_rank=r.get("inlink_rank"),
                domain_inlink_rank=r.get("domain_inlink_rank"),
                first_seen=r.get("first_seen", ""),
                last_visited=r.get("last_visited", ""),
                date_lost=r.get("date_lost", ""),
                spam_score=r.get("spam_score"),
            )
            for r in rows
        ]
    except Exception:
        logger.exception("Top backlinks request failed (website=%s)", website)
        return None


@dataclass
class DomainAuthorityResult:
    domain: str
    da: Optional[float]
    pa: Optional[float]
    spam_score: Optional[float]
    dr: Optional[float]
    org_traffic: Optional[float]


def fetch_domain_authority(website: str) -> Optional[DomainAuthorityResult]:
    if not is_configured():
        logger.error("rapidapi_domain_client: RAPIDAPI_SEMRUSH_MAGIC_KEY not set")
        return None

    def _do_request():
        response = requests.post(
            f"{BASE_URL}/dapa.php", files={"website": (None, website)}, headers=_headers(), timeout=TIMEOUT_SECONDS
        )
        response.raise_for_status()
        return response

    try:
        response = with_retry(_do_request, max_attempts=2, retry_on=(requests.RequestException,))
        data = response.json().get("data", {})
        return DomainAuthorityResult(
            domain=website,
            da=data.get("da"),
            pa=data.get("pa"),
            spam_score=data.get("spam_score"),
            dr=data.get("dr"),
            org_traffic=data.get("org_traffic"),
        )
    except Exception:
        logger.exception("Domain authority request failed (website=%s)", website)
        return None


def fetch_bulk_domain_authority(domains: List[str]) -> Optional[List[DomainAuthorityResult]]:
    if not is_configured():
        logger.error("rapidapi_domain_client: RAPIDAPI_SEMRUSH_MAGIC_KEY not set")
        return None

    def _do_request():
        response = requests.post(
            f"{BASE_URL}/bulk-dapa.php",
            files={"domains": (None, ",".join(domains))},
            headers=_headers(),
            timeout=TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return response

    try:
        response = with_retry(_do_request, max_attempts=2, retry_on=(requests.RequestException,))
        results = response.json().get("results", [])
        parsed = []
        for r in results:
            data = (r.get("response") or {}).get("data", {})
            parsed.append(
                DomainAuthorityResult(
                    domain=r.get("domain", ""),
                    da=data.get("da"),
                    pa=data.get("pa"),
                    spam_score=data.get("spam_score"),
                    dr=data.get("dr"),
                    org_traffic=data.get("org_traffic"),
                )
            )
        return parsed
    except Exception:
        logger.exception("Bulk domain authority request failed (domains=%s)", domains)
        return None


@dataclass
class KeywordInsightResult:
    keyword: str
    volume: Optional[float]
    competition: Optional[float]
    cpc_dollars: Optional[float]
    sd: Optional[float]  # provider's own field name — same meaning as "keyword_difficulty" elsewhere
    monthly_volumes: dict = field(default_factory=dict)
    search_intent: Optional[list] = None


def fetch_keyword_insights(keyword: str, country: str = "us") -> Optional[KeywordInsightResult]:
    if not is_configured():
        logger.error("rapidapi_domain_client: RAPIDAPI_SEMRUSH_MAGIC_KEY not set")
        return None

    def _do_request():
        response = requests.post(
            f"{BASE_URL}/keyword-tool.php",
            files={"country": (None, country), "keyword": (None, keyword)},
            headers=_headers(),
            timeout=TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return response

    try:
        response = with_retry(_do_request, max_attempts=2, retry_on=(requests.RequestException,))
        data = response.json()
        info = data.get("keywordInfo", {})
        return KeywordInsightResult(
            keyword=data.get("keyword", keyword),
            volume=info.get("volume"),
            competition=info.get("competition"),
            cpc_dollars=info.get("cpcDollars"),
            sd=info.get("sd"),
            monthly_volumes=info.get("ms", {}),
            search_intent=info.get("searchIntent"),
        )
    except Exception:
        logger.exception("Keyword insights request failed (keyword=%s)", keyword)
        return None


@dataclass
class SampleKeyword:
    keyword: str
    position: Optional[float]
    search_volume: Optional[float]
    etv: Optional[float]
    cpc: Optional[float]
    url: str


@dataclass
class WebsiteTrafficResult:
    domain: str
    organic_etv: Optional[float]
    organic_keywords: Optional[float]
    ranked_keywords_total: Optional[float]
    estimated_paid_traffic_cost: Optional[float]
    position_distribution: dict = field(default_factory=dict)
    sample_keywords: List[SampleKeyword] = field(default_factory=list)


def fetch_website_traffic(website: str) -> Optional[WebsiteTrafficResult]:
    if not is_configured():
        logger.error("rapidapi_domain_client: RAPIDAPI_SEMRUSH_MAGIC_KEY not set")
        return None

    def _do_request():
        response = requests.post(
            f"{BASE_URL}/webtraffic.php", files={"website": (None, website)}, headers=_headers(), timeout=TIMEOUT_SECONDS
        )
        response.raise_for_status()
        return response

    try:
        response = with_retry(_do_request, max_attempts=2, retry_on=(requests.RequestException,))
        data = response.json()
        organic = data.get("organic", {})
        position_distribution = {
            k: v for k, v in organic.items() if k.startswith("pos_")
        }
        return WebsiteTrafficResult(
            domain=data.get("domain", website),
            organic_etv=organic.get("etv"),
            organic_keywords=organic.get("keywords"),
            ranked_keywords_total=data.get("ranked_keywords_total"),
            estimated_paid_traffic_cost=organic.get("estimated_paid_traffic_cost"),
            position_distribution=position_distribution,
            sample_keywords=[
                SampleKeyword(
                    keyword=k.get("keyword", ""),
                    position=k.get("position"),
                    search_volume=k.get("search_volume"),
                    etv=k.get("etv"),
                    cpc=k.get("cpc"),
                    url=k.get("url", ""),
                )
                for k in data.get("sample_keywords", [])
            ],
        )
    except Exception:
        logger.exception("Website traffic request failed (website=%s)", website)
        return None
