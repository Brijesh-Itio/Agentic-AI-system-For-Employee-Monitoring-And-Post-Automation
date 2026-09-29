"""
MODULE — Content Gap Analysis (Keyword Gap).

Compares this site's own domain against one or more competitor domains
using real organic-keyword data from the RapidAPI "Competitor Website
Keywords Analysis" wrapper (automation/seo/rapidapi_keyword_client.py's
fetch_keyword_analysis) — the standard meaning of "content gap analysis"
in SEO tooling (Semrush's own Keyword Gap tool does exactly this: diff
domains' ranking keywords into Missing/Weak/Strong/Shared/Untapped/
Unique categories, the same six this module reproduces, at the user's
explicit request after seeing that category list from Semrush's own
tool and asking for it "accordingly").

categorize_keyword_gap is pure set/rank comparison, no LLM — for every
keyword either this site or any competitor ranks for, it assigns exactly
one category:
  - unique   — only this site ranks
  - missing  — the ranking_condition is satisfied by the competitor(s)
               and this site doesn't rank (or ranks below
               your_position_threshold, if set)
  - untapped — only SOME (not all) competitors rank and this site
               doesn't — only distinguishable from "missing" when
               ranking_condition="all" and there are 2+ competitors;
               with one competitor or ranking_condition="at_least_one"
               it collapses into "missing" (an honest limitation of the
               single/loose-condition case, not a bug)
  - weak     — both this site and the competitor(s) rank, but the best
               competitor rank beats this site's
  - strong   — both rank, and this site's rank beats the best competitor
"shared" isn't a fifth bucket alongside these — it's weak + strong
together (everyone ranks), which the frontend derives rather than the
backend duplicating.

Honest limitation carried over from rapidapi_keyword_client.py: that
endpoint hard-caps at 5 keyword rows per domain with no working
pagination (tested live, not assumed) — every category here is computed
from at most 5 keywords per domain, not a full keyword profile, so most
categories will be sparse or empty on a real run. The UI says this
directly rather than implying a comprehensive report.

GPT-6 Sol's only job (suggest_topics_for_gap_rows) is turning each real
"missing"/"untapped" keyword into a concrete article topic + rationale —
it never invents the keyword, search volume, rank or URL. A second
function, suggest_broader_topics, reasons more broadly about content
themes/clusters/formats beyond single keywords, informed by this site's
own existing post topics and the competitors' real sampled keywords —
still grounded in real data, not invented from nothing.
"""
import json
import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from ai.llm.factory import get_provider

logger = logging.getLogger(__name__)


def normalize_keyword(k: str) -> str:
    return " ".join(k.strip().lower().split())


@dataclass
class CompetitorPresence:
    rank: Optional[int] = None
    url: str = ""


@dataclass
class KeywordGapRow:
    keyword: str
    search_volume: Optional[int]
    your_rank: Optional[int]
    category: str  # "missing" | "weak" | "strong" | "untapped" | "unique"
    competitors: Dict[str, CompetitorPresence] = field(default_factory=dict)
    topic: str = ""
    rationale: str = ""
    priority: str = ""


def _best_rank_map(rows: List, *, cutoff: Optional[int] = None) -> Dict[str, tuple]:
    """normalized keyword -> (rank, original keyword text, search_volume, url), keeping the best
    (lowest) rank when a domain's own data lists the same keyword more than once (verified live: a
    real domain returned the identical keyword in 4 of 5 rows, each a different ranking page)."""
    best: Dict[str, tuple] = {}
    for row in rows:
        if not row.keyword or row.rank is None:
            continue
        if cutoff is not None and row.rank > cutoff:
            continue
        norm = normalize_keyword(row.keyword)
        if norm not in best or row.rank < best[norm][0]:
            best[norm] = (row.rank, row.keyword, row.search_volume, row.top_ranked_url)
    return best


def categorize_keyword_gap(
    your_keywords: List,
    competitor_keyword_sets: Dict[str, List],
    *,
    ranking_condition: str = "at_least_one",  # "all" | "at_least_one"
    your_position_threshold: Optional[int] = None,
    competitor_position_cutoff: Optional[int] = None,
) -> List[KeywordGapRow]:
    """`your_keywords` / values of `competitor_keyword_sets` — DomainKeywordRow lists from
    fetch_keyword_analysis, keyed by competitor domain. See module docstring for category
    definitions and the ranking_condition/threshold/cutoff semantics."""
    your_best = _best_rank_map(your_keywords)
    competitor_bests = {domain: _best_rank_map(rows, cutoff=competitor_position_cutoff) for domain, rows in competitor_keyword_sets.items()}
    n_competitors = len(competitor_bests)

    all_norm_keywords: set = set(your_best)
    for cb in competitor_bests.values():
        all_norm_keywords.update(cb)

    rows_out: List[KeywordGapRow] = []
    for norm in all_norm_keywords:
        your_entry = your_best.get(norm)
        your_rank = your_entry[0] if your_entry else None
        you_effectively_rank = your_rank is not None and (your_position_threshold is None or your_rank <= your_position_threshold)

        competitors: Dict[str, CompetitorPresence] = {}
        for domain, cb in competitor_bests.items():
            entry = cb.get(norm)
            competitors[domain] = CompetitorPresence(rank=entry[0] if entry else None, url=entry[3] if entry else "")
        ranking_competitors = [d for d, p in competitors.items() if p.rank is not None]

        display_keyword = your_entry[1] if your_entry else None
        search_volume = your_entry[2] if your_entry and your_entry[2] else None
        if display_keyword is None or search_volume is None:
            for domain in ranking_competitors:
                entry = competitor_bests[domain].get(norm)
                if entry:
                    display_keyword = display_keyword or entry[1]
                    search_volume = search_volume or entry[2]

        if you_effectively_rank and not ranking_competitors:
            category = "unique"
        elif not you_effectively_rank and ranking_competitors:
            # At least one competitor ranks and this site doesn't. In "all" mode, whether every
            # competitor ranks for it decides missing (a full gap) vs. untapped (a partial one) — the
            # two are the same thing in "at_least_one" mode, since any single competitor is enough.
            if ranking_condition == "all" and len(ranking_competitors) < n_competitors:
                category = "untapped"
            else:
                category = "missing"
        elif you_effectively_rank and ranking_competitors:
            best_competitor_rank = min(p.rank for p in competitors.values() if p.rank is not None)
            category = "strong" if your_rank < best_competitor_rank else "weak"
        else:
            continue  # neither this site nor any competitor ranks for this keyword at all

        rows_out.append(KeywordGapRow(
            keyword=display_keyword or norm, search_volume=search_volume, your_rank=your_rank,
            category=category, competitors=competitors,
        ))

    rows_out.sort(key=lambda r: r.search_volume or 0, reverse=True)
    return rows_out


_EDGE_JUNK = re.compile(r'^[\s"\',:{}\[\]]+|[\s"\',:{}\[\]]+$')


def _parse_topic_suggestions(text: str) -> dict:
    """keyword (lowercased) -> {topic, rationale}. Tolerant JSON parse, same approach as content_structure.py's
    FAQ parser — a reasoning model can still slip on JSON syntax."""
    start, end = text.find("["), text.rfind("]")
    if start == -1 or end <= start:
        return {}
    try:
        parsed = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return {}

    out = {}
    for p in parsed:
        if not isinstance(p, dict) or "keyword" not in p or "topic" not in p:
            continue
        keyword = normalize_keyword(str(p["keyword"]))
        if keyword:
            out[keyword] = {"topic": str(p["topic"]).strip(), "rationale": str(p.get("rationale", "")).strip()}
    return out


def suggest_topics_for_gap_rows(
    rows: List[KeywordGapRow],
    *,
    site_id: Optional[int] = None,
    industry_context: Optional[str] = None,
    max_suggestions: int = 5,
) -> List[KeywordGapRow]:
    """Fills in .topic/.rationale/.priority on "missing"/"untapped" rows only — those are genuine
    "write something new" opportunities; weak/strong/unique/shared rows are about an existing page's
    performance, not a new article, so they're left as plain data with no LLM call. Priority is
    derived from the real search-volume ordering already applied by categorize_keyword_gap, never
    asked of the model. Never raises — rows without a successful LLM match keep the keyword itself as
    a fallback topic rather than losing real gap data over a generation hiccup."""
    candidates = [r for r in rows if r.category in ("missing", "untapped")][:max_suggestions]
    if not candidates:
        return rows

    priorities = ["high", "high", "medium", "medium", "medium"]
    for i, r in enumerate(candidates):
        r.priority = priorities[i] if i < len(priorities) else "low"
        r.topic = r.keyword.capitalize()  # fallback, overwritten below on a successful parse

    context_line = f"Site's industry/focus: {industry_context.strip()}\n\n" if industry_context and industry_context.strip() else ""
    kw_block = "\n".join(
        f'- "{r.keyword}"{f", ~{r.search_volume}/mo searches" if r.search_volume else ""} '
        f'(competitor best rank #{min((p.rank for p in r.competitors.values() if p.rank is not None), default="?")})'
        for r in candidates
    )
    prompt = (
        "Competitor website(s) rank for the real keywords below; this site currently has no content "
        "targeting any of them. For EACH keyword, suggest a specific article topic (a real, usable title, "
        "not a vague theme) this site could publish to compete for it, and a 1-2 sentence rationale for why "
        "it's worth covering. Work only from the real keyword given for that row — never invent an "
        "additional keyword, a search-volume number, or a competitor detail beyond what's given.\n\n"
        f"{context_line}KEYWORDS THIS SITE IS MISSING (from real competitor rankings):\n{kw_block}\n\n"
        'Return ONLY a JSON array, one entry per keyword above: [{"keyword": "...", "topic": "...", '
        '"rationale": "..."}, ...] — no markdown, no explanation, the JSON array only.'
    )

    result = get_provider(task="content_gap", site_id=site_id).generate(prompt, fast=False)
    if not result.ok:
        logger.warning("Content gap topic suggestion failed: %s", result.error)
        return rows

    parsed = _parse_topic_suggestions(result.text.strip())
    if not parsed:
        logger.warning("Content gap topic suggestion returned unusable output: %r", result.text[:300])
        return rows

    for r in candidates:
        match = parsed.get(normalize_keyword(r.keyword))
        if match:
            r.topic = match["topic"] or r.keyword.capitalize()
            r.rationale = match["rationale"]
    return rows


@dataclass
class TopicOpportunity:
    topic: str
    rationale: str
    priority: str  # "high" | "medium" | "low" — the model's own call here, not tied to one literal keyword's volume


def _parse_topic_opportunities(text: str) -> List[TopicOpportunity]:
    start, end = text.find("["), text.rfind("]")
    if start == -1 or end <= start:
        return []
    try:
        parsed = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return []

    out = []
    for p in parsed:
        if not isinstance(p, dict) or "topic" not in p:
            continue
        topic = str(p["topic"]).strip()
        if not topic:
            continue
        priority = str(p.get("priority", "medium")).strip().lower()
        if priority not in ("high", "medium", "low"):
            priority = "medium"
        out.append(TopicOpportunity(topic=topic, rationale=str(p.get("rationale", "")).strip(), priority=priority))
    return out


def suggest_broader_topics(
    existing_topics: List[str],
    competitor_keyword_sets: Dict[str, List],
    *,
    site_id: Optional[int] = None,
    industry_context: Optional[str] = None,
    max_suggestions: int = 6,
) -> Optional[List[TopicOpportunity]]:
    """Broader content-topic and strategic-opportunity suggestions, on top of the literal keyword-gap
    rows above — reasons about content themes, clusters, and formats (comparison pages, buyer's
    guides, FAQ hubs) this site is missing, informed by its own existing posts and by real signal
    about what the competitor(s) cover, not fabricated. Never raises — returns None on LLM failure or
    unusable output."""
    existing_block = "\n".join(f"- {t}" for t in existing_topics[:40]) or "(no existing content yet — this is a brand new site)"
    competitor_lines = []
    for domain, rows in competitor_keyword_sets.items():
        for k in rows[:10]:
            competitor_lines.append(f'- "{k.keyword}" (rank #{k.rank or "?"} on {domain}, {k.top_ranked_url or "a page"})')
    competitor_block = "\n".join(competitor_lines) or "(no competitor keyword data available)"
    context_line = f"Site's industry/focus: {industry_context.strip()}\n\n" if industry_context and industry_context.strip() else ""

    prompt = (
        "Compare this site's existing content against real signal about competitor content, and suggest "
        "broader content topics and strategic content opportunities this site is missing — not limited to a "
        "single literal keyword, think in terms of full article ideas, content clusters, or formats "
        "(comparison pages, buyer's guides, FAQ hubs) the existing list doesn't yet cover.\n\n"
        f"{context_line}"
        f"THIS SITE'S EXISTING CONTENT:\n{existing_block}\n\n"
        f"REAL SIGNAL FROM COMPETITORS' OWN RANKING KEYWORDS:\n{competitor_block}\n\n"
        f"Suggest up to {max_suggestions} genuine content opportunities. Each needs a specific topic (a real "
        "article title, not a vague theme) and a 1-2 sentence rationale grounded in the actual lists above. "
        "Never invent a specific statistic, search-volume number, or competitor detail beyond what's given.\n\n"
        'Return ONLY a JSON array: [{"topic": "...", "rationale": "...", "priority": "high|medium|low"}, ...] '
        "— no markdown, no explanation, the JSON array only."
    )

    result = get_provider(task="content_gap", site_id=site_id).generate(prompt, fast=False)
    if not result.ok:
        logger.warning("Broader content-topic suggestion failed: %s", result.error)
        return None

    parsed = _parse_topic_opportunities(result.text.strip())
    if not parsed:
        logger.warning("Broader content-topic suggestion returned unusable output: %r", result.text[:300])
        return None
    return parsed[:max_suggestions]
