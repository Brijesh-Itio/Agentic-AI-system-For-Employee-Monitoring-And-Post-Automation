"""
MODULE 34.1 — Blog post generation.

Writes a full, structured blog post (title, excerpt, HTML body) from a
topic via the module 25 LLM factory — fast=False, same as ai/dar_
generator.py and ai/master_agent.py's report compilation, since a real
post is long-form content worth the slower/better model, not the
short-copy fast=True path module 30's social posts use. The body is
generated WITH its own single H1 matching the title (not left to the
CMS theme to render one) specifically so content_structure.analyze_
structure (module 27.5) — run automatically right after generation, see
api/routes/seo.py's /blog/generate — checks a real, complete document
instead of one that would always fail its own H1-count rule.
"""
import html
import logging
import re
from dataclasses import dataclass
from typing import Optional

from ai.llm.factory import get_provider
from ai.seo.content_structure import analyze_structure

logger = logging.getLogger(__name__)


@dataclass
class BlogPostDraft:
    title: str
    excerpt: str
    content_html: str


# A draft at or above this share of the minimum is accepted without another attempt.
RETRY_FLOOR_RATIO = 0.85


def generate_blog_post(
    topic: str,
    primary_keyword: Optional[str] = None,
    *,
    site_id: Optional[int] = None,
    min_words: int = 700,
    max_words: int = 800,
    max_attempts: int = 2,
) -> Optional[BlogPostDraft]:
    """Never raises — returns None on LLM failure or unparseable output,
    matching this codebase's graceful-degrade convention.

    A local Ollama model routinely ignores a length/structure ask on the
    first try (a well-documented small-model failure mode) — the original
    version of this function just asked once and accepted whatever came
    back, which is why posts were showing up under 600 words with no real
    H1/H2/H3 tags despite the prompt asking for them. This now checks the
    draft against the same rules the reviewer sees (ai.seo.content_
    structure.analyze_structure) and retries up to max_attempts times
    whenever the two things a retry can actually fix — word count and a
    real single H1 — are still wrong, before falling back to the best
    attempt seen. H2/H3 counts are surfaced to the reviewer as warnings
    either way (see analyze_structure) but don't trigger a retry on their
    own, since local-model variance there is less predictable and a
    reviewer can fix a missing subheading far faster than another 1-3
    minute regeneration."""
    # The topic the user typed IS the post's title and its H1, word for word
    # (enforced deterministically below — a small model rewords titles no
    # matter how it's asked, so the prompt alone can't be trusted with this).
    topic = " ".join(topic.split())
    keyword_line = f'Primary SEO keyword to work naturally into the first paragraph: "{primary_keyword}".\n' if primary_keyword else ""
    prompt = (
        f'Write a complete, in-depth blog post about: "{topic}".\n'
        f'The post title, and the single <h1>, must be exactly: "{topic}" — do not reword it.\n'
        f"{keyword_line}"
        f"Target length: {min_words}-{max_words} words — this is a real constraint, not a suggestion. Reach it "
        "with genuinely useful detail, examples, and explanation; never pad with repetition or filler.\n\n"
        "Output ONLY these three sections, each on its own line, in this exact format "
        "(no markdown code fences, no extra commentary):\n"
        "TITLE: <the post title, no HTML>\n"
        "EXCERPT: <a 1-2 sentence summary, no HTML>\n"
        "CONTENT: <the full post body as HTML — exactly one <h1> matching the title, "
        "at least 4 <h2> section headings, and at least 2 <h3> subheadings nested under different <h2> "
        "sections for more detailed sub-topics, <p> paragraphs, no <html>/<body> wrapper tags. "
        "Use real HTML heading/formatting tags for ALL structure — <strong> for bold, <em> for italics, "
        "<ul><li> for lists. Never use markdown syntax like **bold**, *italic*, or \"- item\" bullet dashes, "
        "and never fake a heading with bold text instead of a real <h2>/<h3> tag.>"
    )

    best_draft: Optional[BlogPostDraft] = None
    for attempt in range(1, max_attempts + 1):
        result = get_provider(task="blog_post", site_id=site_id).generate(prompt, fast=False)
        if not result.ok:
            logger.warning("Blog post generation failed for topic %r (attempt %d): %s", topic, attempt, result.error)
            continue

        parsed = _parse_sections(result.text)
        if parsed is None:
            logger.warning(
                "Blog post generation returned unparseable output for topic %r (attempt %d): %r",
                topic, attempt, result.text[:300],
            )
            continue

        draft = BlogPostDraft(
            title=topic,
            excerpt=_clean_markdown_artifacts(parsed.excerpt),
            content_html=f"<h1>{html.escape(topic)}</h1>\n"
            + _strip_existing_h1(_clean_markdown_artifacts(parsed.content_html)),
        )
        check = analyze_structure(draft.content_html, min_words=min_words, max_words=max_words)
        if best_draft is None:
            best_draft = draft
        # A post a little under the target is fine (the reviewer still sees the word-count note): only a
        # clearly short draft is worth another full generation, which costs minutes on local hardware.
        if check.h1_count == 1 and check.word_count >= int(min_words * RETRY_FLOOR_RATIO):
            return draft

        logger.info(
            "Blog post draft for topic %r (attempt %d/%d) under target — %d words, %d H1 — retrying",
            topic, attempt, max_attempts, check.word_count, check.h1_count,
        )
        best_draft = draft  # keep the most recent attempt as the fallback — usually closer than an earlier one

    if best_draft is None:
        return None

    # Final deterministic fix for the one structural defect that's safe to
    # correct without fabricating content: a missing/duplicated H1 is
    # replaced with a single one built from the real title, exactly what
    # the prompt already asked the model to write itself. Word count is
    # never padded here — an honestly-short post still shows as a
    # word_count issue to the reviewer (see analyze_structure) rather than
    # being silently stretched with filler.
    if _count_h1(best_draft.content_html) != 1:
        best_draft = BlogPostDraft(
            title=best_draft.title,
            excerpt=best_draft.excerpt,
            content_html=f"<h1>{best_draft.title}</h1>\n{_strip_existing_h1(best_draft.content_html)}",
        )
    return best_draft


def _count_h1(content_html: str) -> int:
    return len(re.findall(r"<h1[\s>]", content_html, re.IGNORECASE))


def _strip_existing_h1(content_html: str) -> str:
    """Removes any existing (wrong-count) <h1> tags before this module
    prepends the one real one it trusts — avoids ending up with two H1s
    when the model emitted zero or several."""
    return re.sub(r"<h1[^>]*>.*?</h1>\s*", "", content_html, flags=re.IGNORECASE | re.DOTALL)


def _clean_markdown_artifacts(text: str) -> str:
    """The prompt above explicitly asks for real HTML tags, not
    markdown — but LLMs slip into markdown syntax anyway even when told
    not to (verified live: published posts showing literal "**Grammarly**"
    instead of bold text). This is a defensive normalization pass, not a
    general markdown parser — the content is already real HTML for
    structure (h1/h2/p, per the prompt), so this only converts the
    specific inline-emphasis patterns actually observed, leaving any
    genuine HTML already present untouched."""
    # **bold** / __bold__ -> <strong>bold</strong> (checked before single
    # */_ so "**x**" doesn't first get mangled by the single-char rules).
    text = re.sub(r"\*\*(\S.*?\S|\S)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"__(\S.*?\S|\S)__", r"<strong>\1</strong>", text)
    # *italic* / _italic_ -> <em>italic</em>. Requires a non-space right
    # after the opening marker so it doesn't fire on a stray "*" used as
    # a literal asterisk (e.g. a footnote marker) or on already-consumed
    # ** pairs (those are gone by this point).
    text = re.sub(r"\*(\S.*?\S|\S)\*", r"<em>\1</em>", text)
    text = re.sub(r"(?<![a-zA-Z0-9])_(\S.*?\S|\S)_(?![a-zA-Z0-9])", r"<em>\1</em>", text)
    return text


def _parse_sections(text: str) -> Optional[BlogPostDraft]:
    title_idx = text.find("TITLE:")
    excerpt_idx = text.find("EXCERPT:")
    content_idx = text.find("CONTENT:")
    if title_idx == -1 or excerpt_idx == -1 or content_idx == -1:
        return None
    if not (title_idx < excerpt_idx < content_idx):
        return None

    title = text[title_idx + len("TITLE:") : excerpt_idx].strip()
    excerpt = text[excerpt_idx + len("EXCERPT:") : content_idx].strip()
    content_html = text[content_idx + len("CONTENT:") :].strip()
    if not title or not content_html:
        return None

    return BlogPostDraft(title=title, excerpt=excerpt, content_html=content_html)
