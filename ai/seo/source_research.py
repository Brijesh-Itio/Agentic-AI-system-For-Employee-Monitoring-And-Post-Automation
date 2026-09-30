"""
MODULE — Trusted URL Sources for content research (user instruction).

Real, web-search-grounded research via OpenAI's Responses API
(client.responses.create with the built-in `web_search` tool) — NOT the
Chat Completions API every other LLM task in this codebase uses
(ai/llm/providers/openai_provider.py, routed through ai/llm/factory.py's
shared LLMProvider interface). That interface has no way to return real
citations because a plain Chat Completions call has no web access at
all — confirmed live this session: it's pure text generation from
training data, so asking it for "trusted source URLs" would just be
asking it to invent them, exactly the fabrication risk blog_content.py's
content_brief already guards against for statistics/studies. The
Responses API is a genuinely different capability: verified live that
GPT-6 Sol actually calls a real web_search tool (multiple
`web_search_call` output items per request) and returns real
`url_citation` annotations — an exact URL, page title, and the precise
span of generated text that citation backs — for claims it looked up
live, not recalled from memory.

research_trusted_sources is deliberately its own function calling
`openai.OpenAI(...).responses.create` directly, the same "call the SDK
directly for an OpenAI-specific capability" pattern already used by
ai/images/providers/openai_image_provider.py — NOT wired into
ai/llm/factory.py, so this can never affect Ollama/Claude or any other
existing LLM task (blog writing, social writing, grammar checking, image
prompts, content gap analysis) that shares that factory's interface.

Second correction (user instruction): citations should appear inline in
the published article itself, automatically on every generation, not as
a separate manual panel. match_sources_to_paragraphs + insert_citation_
links implement that WITHOUT letting an LLM rewrite the article's actual
sentences — real sources are researched independently of the article
(above), worded in the model's own summary, not verbatim from the
article's prose, so they can't be reliably string-matched into the
existing text. Instead, a narrowly-scoped LLM call (the shared
ai/llm/factory.py provider — this part has no need for web access, it's
pure classification) is asked ONLY to say which paragraph (by number) a
source best supports, never to rewrite anything; insert_citation_links
then does the actual insertion itself, deterministically, appending a
small citation link just before a matched paragraph's closing </p> —
the article's own sentences are never touched by an LLM, only appended
to, eliminating the content-drift risk a "rewrite with citations woven
in" approach would carry.
"""
import html as html_lib
import logging
import re
from dataclasses import dataclass
from typing import Dict, List, Optional
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

from ai.llm.factory import get_provider
from api.config import settings

logger = logging.getLogger(__name__)

_MODEL = "gpt-6-sol"
# The web_search tool appends its own tracking param to every URL
# (verified live: "?utm_source=openai" on every citation) — stripped here
# so what's shown/stored is the real canonical URL, not an OpenAI-specific
# tracking link.
_STRIP_QUERY_PARAMS = {"utm_source"}


@dataclass
class TrustedSource:
    url: str
    title: str
    # The exact sentence/claim this source backs, taken from the model's
    # own cited output text (not written separately) — so a reviewer can
    # see what the source is actually being used to support.
    quoted_text: str


def _claim_before(text: str, citation_start: int) -> str:
    """The real claim a citation backs — NOT text[start:end], which is the
    citation marker itself ("([domain.com](url))"), confirmed live: the
    Responses API's annotation span covers that inline marker, sitting
    right after the sentence it supports, not the sentence itself (and
    right after that sentence's own closing period, verified live against
    a real numbered-list response — a naive "text after the last sentence
    boundary" search finds that same closing period and returns nothing).
    Walks back from just before the cited sentence's own terminator to the
    PREVIOUS sentence boundary (or start of text/line), so the returned
    span is the complete cited sentence, then strips a leading markdown
    list marker ("1. ", "- ") and bold markers."""
    preceding = text[:citation_start].rstrip()
    if not preceding:
        return ""
    search_end = len(preceding) - 1  # before the cited sentence's own trailing punctuation
    boundary = max(
        preceding.rfind(". ", 0, search_end),
        preceding.rfind("! ", 0, search_end),
        preceding.rfind("? ", 0, search_end),
        preceding.rfind("\n", 0, search_end),
    )
    claim = preceding[boundary + 1 :] if boundary != -1 else preceding
    claim = re.sub(r"^\s*(?:\d+\.\s+|-\s+)", "", claim)  # leading "1. " / "- " list marker
    claim = re.sub(r"\*\*(.+?)\*\*", r"\1", claim)  # **bold** -> bold
    return re.sub(r"\s+", " ", claim).strip()


def _clean_url(url: str) -> str:
    parts = urlsplit(url)
    kept_params = [(k, v) for k, v in parse_qsl(parts.query) if k not in _STRIP_QUERY_PARAMS]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(kept_params), ""))


def research_trusted_sources(
    topic: str, primary_keyword: Optional[str] = None, *, max_sources: int = 6
) -> Optional[List[TrustedSource]]:
    """Never raises — returns None if unconfigured, the call fails, or no
    real citations came back (never fabricates a substitute)."""
    if not settings.OPENAI_API_KEY:
        logger.error("Trusted source research not configured — set OPENAI_API_KEY in .env")
        return None

    keyword_line = f' The article\'s primary keyword is "{primary_keyword}".' if primary_keyword else ""
    prompt = (
        f'Research real, current, authoritative sources for an article about: "{topic}".{keyword_line} '
        "Look up specific facts, figures, standards, or requirements a reader would want backed by a real "
        "source — actually search for them, don't rely on memory. Prefer official/authoritative sources "
        "(standards bodies, regulators, the primary organization a claim is about) over blogs or secondary "
        f"summaries. Write {max_sources} short factual statements, each backed by a real citation."
    )

    try:
        import openai

        client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        response = client.responses.create(model=_MODEL, input=prompt, tools=[{"type": "web_search"}])
    except Exception:
        logger.exception("Trusted source research failed (topic=%r)", topic)
        return None

    sources: List[TrustedSource] = []
    seen_urls: set = set()
    for item in getattr(response, "output", []) or []:
        if getattr(item, "type", None) != "message":
            continue
        for content in getattr(item, "content", []) or []:
            text = getattr(content, "text", "") or ""
            for ann in getattr(content, "annotations", []) or []:
                if getattr(ann, "type", None) != "url_citation":
                    continue
                raw_url = getattr(ann, "url", None)
                if not raw_url:
                    continue
                url = _clean_url(raw_url)
                if url in seen_urls:
                    continue
                seen_urls.add(url)
                start = getattr(ann, "start_index", 0)
                quoted = _claim_before(text, start)
                sources.append(TrustedSource(url=url, title=getattr(ann, "title", "") or url, quoted_text=quoted))

    if not sources:
        logger.warning("Trusted source research returned no real citations (topic=%r)", topic)
        return None
    return sources[:max_sources]


@dataclass
class SourcePlacement:
    source_index: int
    paragraph_index: int


def _domain_label(url: str) -> str:
    netloc = urlsplit(url).netloc
    return netloc[4:] if netloc.startswith("www.") else netloc


def _parse_placements(text: str, *, n_sources: int, n_paragraphs: int) -> List[SourcePlacement]:
    start, end = text.find("["), text.rfind("]")
    if start == -1 or end <= start:
        return []
    try:
        import json

        parsed = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return []

    placements = []
    for p in parsed:
        if not isinstance(p, dict):
            continue
        si, pi = p.get("source_index"), p.get("paragraph_index")
        if isinstance(si, int) and isinstance(pi, int) and 0 <= si < n_sources and 0 <= pi < n_paragraphs:
            placements.append(SourcePlacement(source_index=si, paragraph_index=pi))
    return placements


def match_sources_to_paragraphs(
    content_html: str, sources: List[TrustedSource], *, site_id: Optional[int] = None
) -> List[SourcePlacement]:
    """Never raises — returns [] on failure or an empty match; a source
    with no good paragraph match is simply left out, never forced onto an
    unrelated paragraph.

    Retries once on an empty/unparseable reply — confirmed live this fires
    in real use: this task defaults to the small local Ollama model
    (no override was set), and a live post with 6 real, good sources came
    back with zero placements on the first pass, then found all 6 on an
    immediate retry with the identical input — the same "small local
    model doesn't reliably produce clean structured output on the first
    try" failure mode ai/seo/blog_content.py's own docstring already
    documents and retries for."""
    paragraphs = re.findall(r"<p[^>]*>.*?</p>", content_html, re.IGNORECASE | re.DOTALL)
    if not paragraphs or not sources:
        return []

    para_block = "\n".join(f"{i}: {re.sub('<[^>]+>', '', p)[:300]}" for i, p in enumerate(paragraphs))
    src_block = "\n".join(f"{i}: {s.quoted_text}" for i, s in enumerate(sources))
    prompt = (
        "Below are an article's paragraphs (numbered) and a list of real, separately-researched claims "
        "(numbered), each backed by a real source. For each source claim, say which article paragraph "
        "makes a similar factual point, if any does. Only match a source to a paragraph when the claims "
        "genuinely overlap — never force a weak or unrelated match, and it's fine for a source to have no "
        "match at all.\n\n"
        f"ARTICLE PARAGRAPHS:\n{para_block}\n\nSOURCE CLAIMS:\n{src_block}\n\n"
        'Return ONLY a JSON array of genuine matches: [{"source_index": 0, "paragraph_index": 2}, ...] — '
        "omit any source with no real match. No markdown, no explanation, the JSON array only."
    )

    for attempt in (1, 2):
        result = get_provider(task="source_placement", site_id=site_id).generate(prompt, fast=True)
        if not result.ok:
            logger.warning("Source-to-paragraph matching failed (attempt %d): %s", attempt, result.error)
            continue
        placements = _parse_placements(result.text.strip(), n_sources=len(sources), n_paragraphs=len(paragraphs))
        if placements:
            return placements
        logger.info("Source-to-paragraph matching found no placements on attempt %d — %s", attempt, "retrying" if attempt == 1 else "giving up")
    return []



# Inline, not a CSS class: this HTML gets published verbatim into the user's own CMS (WordPress/
# Webflow) via the normal publish flow, where none of this app's own stylesheet is loaded — an
# external class would render as a plain unstyled link on the live site. class="trusted-source-
# citation" is kept alongside purely as a hook for this app's own Preview/View surfaces, in case a
# future design pass wants to restyle it there without touching already-published posts.
_CITATION_STYLE = (
    "display:inline-block;margin-left:4px;padding:1px 8px;border-radius:999px;"
    "background:#eef2ff;color:#4338ca;font-size:0.75em;font-weight:500;text-decoration:none;"
    "white-space:nowrap;"
)


def insert_citation_links(content_html: str, sources: List[TrustedSource], placements: List[SourcePlacement]) -> str:
    """Purely deterministic HTML manipulation — no LLM call, so the
    article's existing sentences are never altered, only appended to.
    Inserts a small citation link just before each matched paragraph's
    closing </p>, working from the last matched paragraph backward so
    each insertion's offset can't shift the position of an earlier one."""
    if not placements:
        return content_html

    by_paragraph: Dict[int, List[SourcePlacement]] = {}
    for p in placements:
        by_paragraph.setdefault(p.paragraph_index, []).append(p)

    para_matches = list(re.finditer(r"<p[^>]*>.*?</p>", content_html, re.IGNORECASE | re.DOTALL))
    result = content_html
    for idx in sorted(by_paragraph.keys(), reverse=True):
        if idx >= len(para_matches):
            continue
        links_html = "".join(
            f' <a class="trusted-source-citation" style="{_CITATION_STYLE}" '
            f'href="{html_lib.escape(sources[p.source_index].url)}" '
            f'target="_blank" rel="noopener noreferrer" title="{html_lib.escape(sources[p.source_index].title)}">'
            f"{html_lib.escape(_domain_label(sources[p.source_index].url))}</a>"
            for p in by_paragraph[idx]
        )
        if not links_html:
            continue
        insert_at = para_matches[idx].end() - len("</p>")
        result = result[:insert_at] + links_html + result[insert_at:]
    return result


def add_inline_trusted_sources(
    content_html: str, topic: str, primary_keyword: Optional[str] = None, *, site_id: Optional[int] = None
) -> "tuple[str, Optional[List[TrustedSource]]]":
    """The full pipeline used automatically on every blog generation (user instruction): research real
    sources, match them to the article's own paragraphs without rewriting anything, and insert real
    citation links. Never raises. Returns (content_html, sources) — content_html is returned unchanged
    (not an error) if research or matching finds nothing usable, so a research hiccup never blocks a
    post being created."""
    sources = research_trusted_sources(topic, primary_keyword)
    if not sources:
        return content_html, None
    placements = match_sources_to_paragraphs(content_html, sources, site_id=site_id)
    if not placements:
        logger.info("Trusted sources found but none matched an article paragraph closely enough (topic=%r)", topic)
        return content_html, sources
    return insert_citation_links(content_html, sources, placements), sources
