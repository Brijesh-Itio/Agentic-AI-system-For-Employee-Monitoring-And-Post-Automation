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


@dataclass
class StructureIssue:
    rule: str
    severity: str  # "error" | "warning"
    message: str


@dataclass
class StructureReport:
    word_count: int
    h1_count: int
    h2_count: int
    h3_count: int
    issues: List[StructureIssue] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not any(i.severity == "error" for i in self.issues)


def analyze_structure(
    content_html: str,
    *,
    primary_keyword: Optional[str] = None,
    min_words: int = 600,
    max_words: int = 3000,
) -> StructureReport:
    """Pure, synchronous, no external calls — safe to run on every draft
    before it's ever pushed anywhere. Heading detection is a light regex
    over the CMS's own HTML output, not a full HTML parser — sufficient
    for well-formed content this pipeline generates itself, not meant to
    survive arbitrary hostile markup."""
    plain_text = _strip_html(content_html)
    word_count = len(plain_text.split())
    h1_count = _count_tag(content_html, "h1")
    h2_count = _count_tag(content_html, "h2")
    h3_count = _count_tag(content_html, "h3")

    issues: List[StructureIssue] = []

    if h1_count != 1:
        issues.append(StructureIssue("h1_count", "error", f"Expected exactly 1 H1, found {h1_count}"))
    if h2_count < 3:
        issues.append(
            StructureIssue("h2_count", "warning", f"Expected at least 3 H2 sections, found {h2_count}")
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

    return StructureReport(
        word_count=word_count, h1_count=h1_count, h2_count=h2_count, h3_count=h3_count, issues=issues
    )


@dataclass
class FaqPair:
    question: str
    answer: str


def generate_faq(
    page_title: str, seed_queries: List[str], *, site_id: Optional[int] = None, max_pairs: int = 5
) -> Optional[List[FaqPair]]:
    """Generates FAQ question/answer pairs seeded by real search queries
    (module 26's seo_gsc_queries is the intended source). Never raises —
    returns None on LLM failure or unparseable output, matching this
    codebase's graceful-degrade convention."""
    queries_block = "\n".join(f"- {q}" for q in seed_queries[:15]) or "(no seed queries provided)"
    prompt = (
        f"Write up to {max_pairs} FAQ question/answer pairs for a page titled "
        f'"{page_title}". Ground the questions in the real search queries below where '
        "relevant, rephrased as natural questions — don't invent unrelated questions.\n\n"
        f"REAL SEARCH QUERIES THAT LED TO THIS PAGE:\n{queries_block}\n\n"
        'Return ONLY a JSON array: [{"question": "...", "answer": "..."}, ...] — '
        "answers should be 1-3 sentences, factual, no marketing fluff. No markdown, no "
        "explanation, the JSON array only."
    )
    result = get_provider(task="faq", site_id=site_id).generate(prompt, fast=True)
    if not result.ok:
        logger.warning("FAQ generation failed: %s", result.error)
        return None

    text = result.text.strip()
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1 or end <= start:
        logger.warning("FAQ generation returned unparseable output: %r", text)
        return None
    try:
        parsed = json.loads(text[start : end + 1])
        return [
            FaqPair(question=str(p["question"]), answer=str(p["answer"]))
            for p in parsed
            if "question" in p and "answer" in p
        ]
    except (json.JSONDecodeError, KeyError, TypeError):
        logger.warning("FAQ generation JSON parse failed: %r", text)
        return None
