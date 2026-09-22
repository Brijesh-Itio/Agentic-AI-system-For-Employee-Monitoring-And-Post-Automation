"""
MODULE 60 — Content plagiarism & humanization check.

Runs automatically right after a blog/social draft is generated (same
"surface it alongside the draft, not as a separate manual step" convention
module 27.5's structure checker established), so a reviewer sees originality
and how AI-sounding the writing reads before ever approving or publishing it.

Two honest scope notes, spelled out here because both are easy to oversell:

  - Plagiarism check: this compares a new draft against content already
    sitting in THIS install's own database (every other blog/social post,
    any site) — not the public internet. There is no web-crawling or
    paid plagiarism-API integration in this codebase (matching the
    project's zero-external-paid-API stance for the AI layer — see the
    README's "Zero-external-API architecture" section), so a true
    internet-wide scan isn't something this can honestly claim. What it
    IS genuinely useful for: catching the local LLM regenerating
    near-duplicate content across posts/sites, which is a real and common
    failure mode of prompt-based generation, and a real SEO risk
    (duplicate content) if two published pages end up saying the same
    thing in the same words.

  - Humanization check: there is no ML-based AI-content-detector (GPTZero,
    Originality.ai, etc.) wired up here either — again, no paid API, and
    those services' accuracy is itself contested. This is a deterministic,
    explainable heuristic over well-documented "reads like unedited AI
    output" signals (sentence-length uniformity, low lexical variety,
    stock AI-writing phrases, repetitive sentence openers). It's useful as
    a quick, consistent first read — a low score is a real signal worth a
    human edit pass — but it is not a certified detector and is labelled
    as an estimate everywhere it's surfaced.
"""
import re
from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple

# Common "this reads like unedited AI output" tells — collected from what
# AI-writing-detection writeups and style guides consistently flag, not
# from any one product's proprietary list. Deliberately phrases, not single
# words, to keep false positives (a human genuinely writing "furthermore")
# low relative to true tells (a paragraph opening with three of these).
_AI_CLICHES = [
    "in today's fast-paced world", "in today's digital age", "in today's digital landscape",
    "in the ever-evolving landscape", "in the ever-changing landscape", "in the realm of",
    "it's important to note that", "it is important to note that", "it's worth noting that",
    "in conclusion,", "in summary,", "to sum up,", "at the end of the day,",
    "moreover,", "furthermore,", "additionally,", "nonetheless,",
    "delve into", "dive into", "let's dive in", "navigate the complexities",
    "unlock the power of", "unleash the power of", "harness the power of",
    "game changer", "game-changer", "testament to", "boasts a", "boasts an",
    "seamless integration", "seamlessly integrate", "robust solution", "cutting-edge",
    "state-of-the-art", "whether you're a", "look no further", "elevate your",
    "embark on a journey", "embark on this journey", "the world of", "ever-changing landscape",
    "plays a crucial role", "plays a vital role", "underscores the importance",
    "when it comes to", "in a nutshell,", "without further ado", "a testament to",
]

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
_WORD_RE = re.compile(r"[A-Za-z0-9']+")


def _strip_html(html: str) -> str:
    text = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", text).strip()


def _sentences(text: str) -> List[str]:
    return [s.strip() for s in _SENTENCE_SPLIT_RE.split(text) if s.strip()]


def _words(text: str) -> List[str]:
    return _WORD_RE.findall(text.lower())


@dataclass
class FlaggedPhrase:
    phrase: str
    reason: str


@dataclass
class HumanizationReport:
    # 0-100 — higher reads more human/naturally varied, lower reads more
    # like unedited raw AI output. See the module docstring: an estimate,
    # not a certified AI-detector result.
    score: int
    band: str
    word_count: int
    avg_sentence_length: float
    sentence_length_variety: int  # 0-100, how varied sentence lengths are
    lexical_diversity: int  # 0-100, vocabulary variety (type-token ratio)
    flagged_phrases: List[FlaggedPhrase] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)


def assess_humanization(content_html: str) -> HumanizationReport:
    """Pure, synchronous, no external calls — safe to run on every draft.
    See the module docstring for exactly what this is (a heuristic
    estimate) and isn't (a certified AI-content detector)."""
    text = _strip_html(content_html)
    sentences = _sentences(text)
    words = _words(text)
    word_count = len(words)

    if word_count == 0 or not sentences:
        return HumanizationReport(
            score=0, band="Not enough text to assess", word_count=0,
            avg_sentence_length=0.0, sentence_length_variety=0, lexical_diversity=0,
            notes=["No text to analyze."],
        )

    # Burstiness: human writing mixes short and long sentences; very
    # uniform-length sentences are a common AI-writing tell. Coefficient
    # of variation (stdev/mean) of words-per-sentence, normalized to 0-100
    # by treating a CV of 0.6+ as "fully varied" — chosen from inspecting
    # real human-written vs. raw-LLM-output paragraphs, not a published
    # standard.
    sentence_lengths = [len(_WORD_RE.findall(s)) for s in sentences if _WORD_RE.findall(s)]
    avg_len = sum(sentence_lengths) / len(sentence_lengths)
    variance = sum((n - avg_len) ** 2 for n in sentence_lengths) / len(sentence_lengths)
    stdev = variance ** 0.5
    cv = (stdev / avg_len) if avg_len else 0.0
    sentence_variety_score = round(min(100, (cv / 0.6) * 100))

    # Lexical diversity: unique words / total words, over at most the
    # first 500 words so longer posts aren't unfairly marked "repetitive"
    # just for being long (TTR mechanically falls as text grows).
    sample = words[:500]
    lexical_diversity_raw = len(set(sample)) / len(sample)
    # A genuinely varied 500-word sample typically lands around 0.5-0.55
    # TTR; normalize so that range reads as "high" rather than capping at
    # a rarely-reached 1.0.
    lexical_diversity_score = round(min(100, (lexical_diversity_raw / 0.55) * 100))

    # Stock AI-writing phrases.
    lower_text = text.lower()
    flagged: List[FlaggedPhrase] = []
    cliche_hits = 0
    for phrase in _AI_CLICHES:
        count = lower_text.count(phrase)
        if count:
            cliche_hits += count
            flagged.append(
                FlaggedPhrase(phrase=phrase, reason=f"Common AI-writing phrase (found {count}x)")
            )
    cliche_density = cliche_hits / (word_count / 1000)  # occurrences per 1000 words

    # Repetitive sentence openers (same first two words starting >=25% of
    # sentences) — another common tell, e.g. every paragraph starting
    # "Additionally, ...".
    notes: List[str] = []
    if len(sentences) >= 4:
        openers = [" ".join(_WORD_RE.findall(s)[:2]).lower() for s in sentences if _WORD_RE.findall(s)]
        openers = [o for o in openers if o]
        if openers:
            most_common = max(set(openers), key=openers.count)
            share = openers.count(most_common) / len(openers)
            if share >= 0.25:
                notes.append(
                    f'{round(share * 100)}% of sentences open the same way ("{most_common}…") — vary sentence openings.'
                )

    score = 100
    score -= min(40, cliche_density * 8)  # heavy penalty for cliché-dense writing
    score -= (100 - sentence_variety_score) * 0.25
    score -= (100 - lexical_diversity_score) * 0.20
    if notes:
        score -= 10
    score = round(max(0, min(100, score)))

    if score >= 70:
        band = "Reads naturally"
    elif score >= 40:
        band = "Some AI patterns — light editing recommended"
    else:
        band = "Strong AI patterns — recommend a human edit pass before publishing"

    if cliche_density > 0:
        notes.append(f"~{round(cliche_density, 1)} stock AI-writing phrase(s) per 1,000 words.")

    return HumanizationReport(
        score=score,
        band=band,
        word_count=word_count,
        avg_sentence_length=round(avg_len, 1),
        sentence_length_variety=sentence_variety_score,
        lexical_diversity=lexical_diversity_score,
        flagged_phrases=flagged[:12],  # cap — a wall of hits isn't more actionable than the first dozen
        notes=notes,
    )


def _shingles(words: Sequence[str], n: int = 8) -> set:
    if len(words) < n:
        return {tuple(words)} if words else set()
    return {tuple(words[i : i + n]) for i in range(len(words) - n + 1)}


@dataclass
class PlagiarismMatch:
    source_type: str  # "blog" | "social"
    source_id: int
    source_title: str
    similarity: int  # 0-100
    matched_snippet: str


@dataclass
class PlagiarismReport:
    # Best (highest) match's similarity, 0-100. See the module docstring:
    # checked against this install's own stored content, not the internet.
    overall_similarity: int
    verdict: str
    matches: List[PlagiarismMatch] = field(default_factory=list)


def check_plagiarism(
    new_content_html: str,
    candidates: Sequence[Tuple[str, int, str, str]],
    *,
    shingle_size: int = 8,
    top_n: int = 3,
) -> PlagiarismReport:
    """Pure, synchronous, no external calls. `candidates` is
    (source_type, source_id, title, content_html) for every other post
    this new draft should be checked against — the route layer decides
    that scope (this codebase checks same-site blog+social posts; see
    the module docstring for why that's the honest scope) and loads it
    once per request rather than this function reaching into the DB
    itself, so a bulk/calendar generation call can reuse one loaded
    candidate pool across every post it creates instead of re-querying
    per post."""
    new_words = _words(_strip_html(new_content_html))
    new_shingles = _shingles(new_words, shingle_size)

    if not new_shingles:
        return PlagiarismReport(overall_similarity=0, verdict="Not enough text to compare", matches=[])

    scored: List[PlagiarismMatch] = []
    for source_type, source_id, title, content in candidates:
        candidate_words = _words(_strip_html(content))
        candidate_shingles = _shingles(candidate_words, shingle_size)
        if not candidate_shingles:
            continue
        overlap = new_shingles & candidate_shingles
        if not overlap:
            continue
        union = new_shingles | candidate_shingles
        similarity = round((len(overlap) / len(union)) * 100)
        if similarity <= 0:
            continue
        snippet = " ".join(next(iter(overlap)))
        scored.append(
            PlagiarismMatch(source_type=source_type, source_id=source_id, source_title=title,
                             similarity=similarity, matched_snippet=snippet)
        )

    scored.sort(key=lambda m: m.similarity, reverse=True)
    top_matches = scored[:top_n]
    overall = top_matches[0].similarity if top_matches else 0

    if overall < 10:
        verdict = "Original — no meaningful overlap with your existing content"
    elif overall < 30:
        best = top_matches[0]
        verdict = f'Some shared phrasing with your existing {best.source_type} post "{best.source_title}"'
    else:
        best = top_matches[0]
        verdict = f'High overlap with your existing {best.source_type} post "{best.source_title}" — review before publishing'

    return PlagiarismReport(overall_similarity=overall, verdict=verdict, matches=top_matches)
