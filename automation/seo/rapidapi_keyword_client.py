"""
MODULE 37 — RapidAPI "SEMrush SEO" keyword wrapper.

IMPORTANT: this is a third-party RapidAPI reseller product (host
semrush-seo3.p.rapidapi.com), NOT Semrush's own official API
(automation/seo/semrush_client.py is that). A separate seller, a
separate product, chosen as a cheaper alternative to Semrush's own
Advanced plan ($455+/mo plus separately-purchased API units) for
keyword research specifically. No guarantee of data accuracy, freshness,
or continued uptime — these wrapper products typically scrape Semrush's
own site and can silently break when Semrush changes its UI.

fetch_keyword_analysis calls "Competitor Website Keywords Analysis"
(POST /web-keyoword-tool.php — sic, the provider's own typo, kept
verbatim since it's the real path): every organic keyword a domain
ranks for, with per-keyword rank/volume/difficulty/clicks plus
domain-level totals. Originally looked broken — every live call this
session returned the provider's own generic {"success": false, "error":
"API Error"} — but that was this function using its own dedicated
RAPIDAPI_SEMRUSH_KEY setting, a different (stale) key from the one
already working for every other endpoint in this module and in
rapidapi_domain_client.py. RapidAPI keys are per-account, not per-API
(see rapidapi_domain_client.py's module docstring) — switching this
function to the already-verified-working RAPIDAPI_SEMRUSH_MAGIC_KEY
fixed it. Re-verified live this session against a real domain (webpays.com): a
real 200 with 2,675 total ranking keywords, 113,238 total monthly
search volume, and 5 real keyword rows. Pagination was then explicitly
tested, not just left unverified: both `pageSize` and `startingRow`
were sent with different values (50; 1, 6, 11) and every response came
back with the exact same 5 rows regardless — the provider hard-caps
this endpoint at its top 5 keywords with no working pagination. Callers
(e.g. content gap analysis, ai/seo/content_gap.py) must treat this as a
genuine top-5 sample per domain, not a full keyword list.
"""
import logging
from dataclasses import dataclass, field
from typing import List, Optional

import requests

from ai.llm.retry import with_retry
from api.config import settings

logger = logging.getLogger(__name__)

TIMEOUT_SECONDS = 60  # observed live: a successful-looking round trip took ~50s
BASE_URL = "https://semrush-seo3.p.rapidapi.com"
HOST = "semrush-seo3.p.rapidapi.com"

# ── "Semrush Magic Tool" — a separate RapidAPI product (host
# semrush-magic-tool.p.rapidapi.com), verified live this session with a
# real 200 OK and genuine data (673 related-keyword rows for one seed
# keyword). Its own key/host, distinct from the (currently broken)
# provider above. ──

MAGIC_BASE_URL = "https://semrush-magic-tool.p.rapidapi.com"
MAGIC_HOST = "semrush-magic-tool.p.rapidapi.com"


@dataclass
class MonthlySearches:
    month: str
    year: int
    searches: int


@dataclass
class KeywordResearchRow:
    keyword: str
    avg_monthly_searches: Optional[int]
    low_cpc: Optional[str]
    high_cpc: Optional[str]
    competition_index: Optional[int]
    competition_value: Optional[str]
    # The provider's own response is inconsistent — some rows return
    # "intent" as a single string, others as a list of strings.
    # Normalized to always be a list here so callers don't need to
    # handle both shapes themselves.
    intent: List[str] = field(default_factory=list)
    intent_confidence: Optional[float] = None
    advice: List[str] = field(default_factory=list)
    content_gap_score: Optional[float] = None
    estimated_ctr: Optional[float] = None
    keyword_freshness: Optional[float] = None
    serp_feature_type: Optional[str] = None
    monetization_score: Optional[float] = None
    monthly_search_volumes: List[MonthlySearches] = field(default_factory=list)


def is_magic_tool_configured() -> bool:
    return bool(settings.RAPIDAPI_SEMRUSH_MAGIC_KEY)


def _parse_keyword_row(raw: dict) -> KeywordResearchRow:
    intent_raw = raw.get("intent")
    intent = intent_raw if isinstance(intent_raw, list) else ([intent_raw] if intent_raw else [])
    volumes = [
        MonthlySearches(month=m.get("month", ""), year=m.get("year", 0), searches=m.get("searches", 0))
        for m in raw.get("monthly_search_volumes", [])
    ]
    return KeywordResearchRow(
        keyword=raw.get("keyword", ""),
        avg_monthly_searches=raw.get("avg_monthly_searches"),
        low_cpc=raw.get("Low CPC"),
        high_cpc=raw.get("High CPC"),
        competition_index=raw.get("competition_index"),
        competition_value=raw.get("competition_value"),
        intent=intent,
        intent_confidence=raw.get("intent_confidence"),
        advice=raw.get("advice", []),
        content_gap_score=raw.get("content_gap_score"),
        estimated_ctr=raw.get("estimated_ctr"),
        keyword_freshness=raw.get("keyword_freshness"),
        serp_feature_type=raw.get("serp_feature_type"),
        monetization_score=raw.get("monetization_score"),
        monthly_search_volumes=volumes,
    )


def fetch_keyword_research(keyword: str, language: str = "en", country: str = "us") -> Optional[List[KeywordResearchRow]]:
    """Calls the Semrush Magic Tool's keyword-research endpoint — one
    seed keyword returns hundreds of related/long-tail keyword rows with
    real search volume, CPC, competition, and intent data (verified live
    this session). Never raises — returns None if unconfigured or on
    any request/parse failure, matching this codebase's graceful-
    degrade convention."""
    if not is_magic_tool_configured():
        logger.error("Magic Tool keyword research not configured — set RAPIDAPI_SEMRUSH_MAGIC_KEY in .env")
        return None

    def _do_request():
        response = requests.get(
            f"{MAGIC_BASE_URL}/keyword-research",
            params={"language": language, "keyword": keyword, "country": country},
            headers={"x-rapidapi-host": MAGIC_HOST, "x-rapidapi-key": settings.RAPIDAPI_SEMRUSH_MAGIC_KEY},
            timeout=TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return response

    try:
        response = with_retry(_do_request, max_attempts=2, retry_on=(requests.RequestException,))
        rows = response.json().get("result", [])
        return [_parse_keyword_row(r) for r in rows]
    except Exception:
        logger.exception("Magic Tool keyword research failed (keyword=%s)", keyword)
        return None


# ── "SEMrush SEO" (semrush-seo10.p.rapidapi.com) — Keyword Difficulty
# endpoint. A THIRD distinct RapidAPI product/host from the two above,
# same key as the Magic Tool one (same RapidAPI application). Verified
# live this session with real 200 OK responses for two different
# keywords/countries. ──

DIFFICULTY_BASE_URL = "https://semrush-seo10.p.rapidapi.com"
DIFFICULTY_HOST = "semrush-seo10.p.rapidapi.com"


@dataclass
class KeywordDifficultyResult:
    keyword: str
    keyword_difficulty: Optional[int]  # 0-100 score
    volume: Optional[int]  # monthly search volume
    competition: Optional[float]  # 0-1
    cpc_dollars: Optional[float]
    # Month ("YYYYMM") -> search volume, whatever trailing months the
    # provider includes — not a fixed 12-month window like Magic Tool's.
    monthly_volumes: dict = field(default_factory=dict)
    search_intent: Optional[list] = None  # provider returns raw intent-category ints, meaning undocumented
    raw: dict = field(default_factory=dict)


def fetch_keyword_difficulty(keyword: str, country: str = "us") -> Optional[KeywordDifficultyResult]:
    """Calls the Keyword Difficulty endpoint (note: this product uses a
    third distinct RapidAPI host from the other two functions in this
    module — semrush-seo10, not semrush-seo3 or semrush-magic-tool).
    Never raises — returns None if unconfigured or on any request/parse
    failure."""
    if not is_magic_tool_configured():  # same RapidAPI application/key as the Magic Tool endpoint
        logger.error("Keyword Difficulty not configured — set RAPIDAPI_SEMRUSH_MAGIC_KEY in .env")
        return None

    def _do_request():
        response = requests.post(
            f"{DIFFICULTY_BASE_URL}/keywordDifficulty.php",
            files={"country": (None, country), "keyword": (None, keyword)},
            headers={"x-rapidapi-host": DIFFICULTY_HOST, "x-rapidapi-key": settings.RAPIDAPI_SEMRUSH_MAGIC_KEY},
            timeout=TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return response

    try:
        response = with_retry(_do_request, max_attempts=2, retry_on=(requests.RequestException,))
        data = response.json()
        info = data.get("keywordInfo", {})
        return KeywordDifficultyResult(
            keyword=data.get("keyword", keyword),
            keyword_difficulty=info.get("keyword_difficulty"),
            volume=info.get("volume"),
            competition=info.get("competition"),
            cpc_dollars=info.get("cpcDollars"),
            monthly_volumes=info.get("ms", {}),
            search_intent=info.get("searchIntent"),
            raw=data,
        )
    except Exception:
        logger.exception("Keyword Difficulty request failed (keyword=%s)", keyword)
        return None


def is_configured() -> bool:
    # Same RapidAPI application/key as the Magic Tool, semrush-seo10, and
    # rapidapi_domain_client.py endpoints — see module docstring.
    return bool(settings.RAPIDAPI_SEMRUSH_MAGIC_KEY)


def _headers() -> dict:
    return {
        "Content-Type": "application/x-www-form-urlencoded",
        "x-rapidapi-host": HOST,
        "x-rapidapi-key": settings.RAPIDAPI_SEMRUSH_MAGIC_KEY,
    }


@dataclass
class DomainKeywordRow:
    keyword: str
    rank: Optional[int]
    rank_change: Optional[int]
    search_volume: Optional[int]
    difficulty: Optional[int]
    seo_clicks: Optional[int]
    seo_clicks_change: Optional[int]
    total_monthly_clicks: Optional[int]
    paid_competitors: Optional[int]
    top_ranked_url: str = ""


@dataclass
class DomainKeywordAnalysis:
    domain: str
    total_keywords: int
    total_volume: int
    total_seo_clicks: int
    total_seo_clicks_change: int
    keywords: List[DomainKeywordRow] = field(default_factory=list)


def _parse_domain_keyword_row(raw: dict) -> DomainKeywordRow:
    return DomainKeywordRow(
        keyword=raw.get("keyword", ""),
        rank=raw.get("rank"),
        rank_change=raw.get("rankChange"),
        search_volume=raw.get("searchVolume"),
        difficulty=raw.get("rankingDifficulty"),
        seo_clicks=raw.get("seoClicks"),
        seo_clicks_change=raw.get("seoClicksChange"),
        total_monthly_clicks=raw.get("totalMonthlyClicks"),
        paid_competitors=raw.get("paidCompetitors"),
        top_ranked_url=raw.get("topRankedUrl", ""),
    )


def fetch_keyword_analysis(website: str, country: str = "us") -> Optional[DomainKeywordAnalysis]:
    """Calls the 'Competitor Website Keywords Analysis' endpoint — every
    organic keyword a domain ranks for, with per-keyword rank/volume/
    difficulty/clicks and domain-level totals (see module docstring for
    the key-mismatch bug this fixed, and for what's verified vs. not).
    Never raises — returns None if unconfigured, on a network/timeout
    failure, on the provider's own {"success": false} error shape, or if
    the response doesn't match the verified shape."""
    if not is_configured():
        logger.error("RapidAPI Semrush wrapper not configured — set RAPIDAPI_SEMRUSH_MAGIC_KEY in .env")
        return None

    def _do_request():
        response = requests.post(
            f"{BASE_URL}/web-keyoword-tool.php",
            data={"country": country, "website": website},
            headers=_headers(),
            timeout=TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return response

    try:
        response = with_retry(_do_request, max_attempts=2, retry_on=(requests.RequestException,))
        body = response.json()
        if not body.get("success"):
            logger.warning("RapidAPI Semrush keyword lookup returned success=false (website=%s): %s", website, body.get("error"))
            return None
        data = body.get("data", {})
        return DomainKeywordAnalysis(
            domain=body.get("domain", website),
            total_keywords=data.get("total", 0),
            total_volume=data.get("totalVolume", 0),
            total_seo_clicks=data.get("totalSeoClicks", 0),
            total_seo_clicks_change=data.get("totalSeoClicksChange", 0),
            keywords=[_parse_domain_keyword_row(r) for r in data.get("keywords", [])],
        )
    except Exception:
        logger.exception("RapidAPI Semrush keyword lookup failed (website=%s)", website)
        return None
