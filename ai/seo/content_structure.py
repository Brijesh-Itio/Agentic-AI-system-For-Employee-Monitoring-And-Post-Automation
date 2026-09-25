"""
MODULE 27.5 — Content structure & word-count enforcement.

Checks a piece of content against the SEO blueprint's structural rules
(H1/H2/H3 usage, intro keyword placement, word count) before it's pushed
to a CMS as a draft. One rule from the original blueprint is honestly
NOT implemented as specified: "word count calibrated to 110% of the
top-10 ranking pages' average" needs live SERP scraping, which this
codebase's own module 20 already proved Google blocks outright
(DEVELOPMENT.md's module 20 status: real scraping code, honestly returns
0 results today). Word count here is checked against a caller-supplied
target range instead of a scraped competitor average. FAQ generation is
seeded by real search queries (module 26's GSC pull) rather than a
People-Also-Ask-scraping capability this stack doesn't have either —
the blueprint's "auto-generated from People Also Ask + GSC query data"
is genuinely deliverable as the GSC half, not the PAA half.
"""
import json
import logging
import re
from dataclasses import dataclass, field
from typing import List, Optional

from ai.llm.factory import get_provider

logger = logging.getLogger(__name__)


def _strip_html(html: str) -> str:
    text = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", text).strip()


def _count_tag(html: str, tag: str) -> int:
    return len(re.findall(rf"<{tag}[\s>]", html, re.IGNORECASE))


def _tag_inner_texts(html: str, tag: str) -> List[str]:
    """Plain-text content of every <tag>...</tag> occurrence, in document
    order — used for heading-length checks (h1_count/h2_count above only
    count tags, not what's inside them)."""
    return [_strip_html(m) for m in re.findall(rf"<{tag}[^>]*>(.*?)</{tag}>", html, re.IGNORECASE | re.DOTALL)]


@dataclass
class StructureIssue:
    rule: str
    severity: str  # "error" | "warning"
    message: str


@dataclass
class KeywordDensity:
    keyword: str
    role: str  # "primary" | "secondary"
    count: int
    density: float  # percent of total word count, e.g. 1.2 == 1.2%
    target_min: float
    target_max: float

    @property
    def in_range(self) -> bool:
        return self.target_min <= self.density <= self.target_max


@dataclass
class StructureReport:
    word_count: int
    h1_count: int
    h2_count: int
    h3_count: int
    issues: List[StructureIssue] = field(default_factory=list)
    keyword_density: List[KeywordDensity] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not any(i.severity == "error" for i in self.issues)


# Keyword-stuffing avoidance targets: dense enough to signal relevance to
# search engines, sparse enough not to read as spam. Secondary keywords get
# a lower target since an article naturally mentions its primary term more.
PRIMARY_KEYWORD_DENSITY_TARGET = (1.0, 1.5)
SECONDARY_KEYWORD_DENSITY_TARGET = (0.5, 1.0)


def _keyword_density(plain_text_lower: str, word_count: int, keyword: str) -> float:
    if not keyword or word_count == 0:
        return 0.0
    count = plain_text_lower.count(keyword.lower())
    return round((count / word_count) * 100, 2)


def analyze_structure(
    content_html: str,
    *,
    primary_keyword: Optional[str] = None,
    secondary_keywords: Optional[List[str]] = None,
    min_words: int = 1200,
    max_words: int = 1500,
) -> StructureReport:
    """Pure, synchronous, no external calls — safe to run on every draft
    before it's ever pushed anywhere. Heading detection is a light regex
    over the CMS's own HTML output, not a full HTML parser — sufficient
    for well-formed content this pipeline generates itself, not meant to
    survive arbitrary hostile markup."""
    plain_text = _strip_html(content_html)
    plain_text_lower = plain_text.lower()
    word_count = len(plain_text.split())
    h1_count = _count_tag(content_html, "h1")
    h2_count = _count_tag(content_html, "h2")
    h3_count = _count_tag(content_html, "h3")

    issues: List[StructureIssue] = []

    if h1_count != 1:
        issues.append(StructureIssue("h1_count", "error", f"Expected exactly 1 H1, found {h1_count}"))
    else:
        h1_text = _tag_inner_texts(content_html, "h1")[0]
        h1_len, h1_words = len(h1_text), len(h1_text.split())
        if not (20 <= h1_len <= 70 and 5 <= h1_words <= 8):
            issues.append(
                StructureIssue(
                    "h1_length", "warning",
                    f"H1 is {h1_len} characters / {h1_words} words — aim for 20-70 characters and 5-8 words",
                )
            )
    if h2_count < 4:
        issues.append(
            StructureIssue("h2_count", "warning", f"Expected at least 4 H2 sections, found {h2_count}")
        )
    h2_texts = _tag_inner_texts(content_html, "h2")
    out_of_range_h2 = [t for t in h2_texts if not (45 <= len(t) <= 60)]
    if out_of_range_h2:
        issues.append(
            StructureIssue(
                "h2_length", "warning",
                f"{len(out_of_range_h2)} of {len(h2_texts)} H2 headings are outside the 45-60 character guideline",
            )
        )
    if h3_count < 2:
        issues.append(
            StructureIssue("h3_count", "warning", f"Expected at least 2 H3 subheadings, found {h3_count}")
        )
    if word_count < min_words:
        issues.append(
            StructureIssue("word_count", "error", f"{word_count} words is below the {min_words}-word minimum")
        )
    elif word_count > max_words:
        issues.append(
            StructureIssue(
                "word_count", "warning", f"{word_count} words exceeds the {max_words}-word soft maximum"
            )
        )

    if primary_keyword:
        first_100_words = " ".join(plain_text.split()[:100]).lower()
        if primary_keyword.lower() not in first_100_words:
            issues.append(
                StructureIssue(
                    "intro_keyword",
                    "warning",
                    f"Primary keyword {primary_keyword!r} not found in the first 100 words",
                )
            )

    keyword_density: List[KeywordDensity] = []
    if primary_keyword:
        count = plain_text_lower.count(primary_keyword.lower())
        density = _keyword_density(plain_text_lower, word_count, primary_keyword)
        lo, hi = PRIMARY_KEYWORD_DENSITY_TARGET
        keyword_density.append(KeywordDensity(primary_keyword, "primary", count, density, lo, hi))
        if not (lo <= density <= hi):
            issues.append(
                StructureIssue(
                    "keyword_density_primary", "warning",
                    f"Primary keyword {primary_keyword!r} density is {density}% — target {lo}-{hi}% "
                    "to avoid under-optimizing or keyword stuffing",
                )
            )
    for kw in secondary_keywords or []:
        kw = kw.strip()
        if not kw:
            continue
        count = plain_text_lower.count(kw.lower())
        density = _keyword_density(plain_text_lower, word_count, kw)
        lo, hi = SECONDARY_KEYWORD_DENSITY_TARGET
        keyword_density.append(KeywordDensity(kw, "secondary", count, density, lo, hi))
        if not (lo <= density <= hi):
            issues.append(
                StructureIssue(
                    "keyword_density_secondary", "warning",
                    f"Secondary keyword {kw!r} density is {density}% — target {lo}-{hi}%",
                )
            )

    return StructureReport(
        word_count=word_count, h1_count=h1_count, h2_count=h2_count, h3_count=h3_count,
        issues=issues, keyword_density=keyword_density,
    )


@dataclass
class FaqPair:
    question: str
    answer: str


# Characters that mean nothing once a JSON-ish fragment has been cut out of
# the model's reply: quotes, commas, braces and brackets left on either end.
_FAQ_EDGE_JUNK = re.compile(r'^[\s"\',:{}\[\]]+|[\s"\',:{}\[\]]+$')


def _parse_faq_pairs(text: str) -> List[FaqPair]:
    """Reads FAQ pairs out of an LLM reply. Strict JSON first; if that
    fails, a tolerant read of the "question"/"answer" pairs.

    The tolerant read exists because of a real, recurring failure (seen in
    the server log, posts silently saved with NO FAQs): the small local
    model writes the FAQs correctly but slips on the JSON syntax — most
    often dropping the closing quote of a question, e.g.
    `"question": "How can AI help?\n "answer": "..."` — and json.loads
    rejects the whole reply, discarding five good answers over one
    missing quote."""
    start, end = text.find("["), text.rfind("]")
    if start != -1 and end > start:
        try:
            parsed = json.loads(text[start : end + 1])
            pairs = [
                FaqPair(question=str(p["question"]).strip(), answer=str(p["answer"]).strip())
                for p in parsed
                if isinstance(p, dict) and "question" in p and "answer" in p
            ]
            if pairs:
                return pairs
        except (json.JSONDecodeError, KeyError, TypeError):
            pass

    pairs: List[FaqPair] = []
    for chunk in re.split(r'"question"\s*:', text)[1:]:
        question_part, _, answer_part = chunk.partition('"answer"')
        if not answer_part:
            continue
        # Answer text runs to the next pair's "question" (already split off) or the end of the reply.
        question = _FAQ_EDGE_JUNK.sub("", question_part).replace('\\"', '"')
        answer = _FAQ_EDGE_JUNK.sub("", answer_part).replace('\\"', '"')
        question, answer = " ".join(question.split()), " ".join(answer.split())
        if question and answer:
            pairs.append(FaqPair(question=question, answer=answer))
    return pairs


def generate_faq(
    page_title: str, seed_queries: List[str], *, site_id: Optional[int] = None, max_pairs: int = 5
) -> Optional[List[FaqPair]]:
    """Generates FAQ question/answer pairs seeded by real search queries
    (module 26's seo_gsc_queries is the intended source). Never raises —
    returns None on LLM failure or unusable output, matching this
    codebase's graceful-degrade convention.

    Asks for exactly max_pairs (the auto-FAQ feature promises 5 per post)
    and tries once more if the first reply yields fewer, keeping whichever
    attempt produced more."""
    queries_block = "\n".join(f"- {q}" for q in seed_queries[:15]) or "(no seed queries provided)"
    prompt = (
        f"Write exactly {max_pairs} FAQ question/answer pairs for a page titled "
        f'"{page_title}". Ground the questions in the real search queries below where '
        "relevant, rephrased as natural questions — don't invent unrelated questions.\n\n"
        f"REAL SEARCH QUERIES THAT LED TO THIS PAGE:\n{queries_block}\n\n"
        'Return ONLY a JSON array: [{"question": "...", "answer": "..."}, ...] — '
        "answers should be 1-3 sentences, factual, no marketing fluff. Every question and "
        "every answer must be wrapped in double quotes. No markdown, no explanation, the "
        "JSON array only."
    )

    best: List[FaqPair] = []
    for attempt in (1, 2):
        result = get_provider(task="faq", site_id=site_id).generate(prompt, fast=True)
        if not result.ok:
            logger.warning("FAQ generation failed (attempt %d): %s", attempt, result.error)
            break
        pairs = _parse_faq_pairs(result.text.strip())
        if len(pairs) > len(best):
            best = pairs
        if len(best) >= max_pairs:
            break
        logger.warning(
            "FAQ generation gave %d of %d pairs (attempt %d)%s",
            len(pairs), max_pairs, attempt, "" if pairs else f" — unusable reply: {result.text[:200]!r}",
        )

    return best[:max_pairs] or None
