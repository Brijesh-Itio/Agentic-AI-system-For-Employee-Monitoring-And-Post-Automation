"""
MODULE 35 — Technical issue remediation.

technical_audit.py's own docstring (module 28.2) already drew the line
here: detection is deterministic and safe to automate, but *applying* a
fix to a live site was deliberately left as a human action, because a
wrong automatic edit to a real page's <head> is a genuine "catastrophic
misapplication" risk — most of what a technical audit finds (a missing
meta description, a canonical tag) isn't even a WordPress-core field;
it lives in whichever SEO plugin (Yoast, RankMath, ...) the site
happens to run, and guessing wrong is worse than not fixing it at all.

This module draws the same line, now that real fixes exist to test:

- generate_fix_value() produces a real, ready-to-use replacement for the
  handful of rules where a "correct" value is knowable at all — a real
  page title, a real meta description, or (trivially, no LLM needed) a
  page's own canonical URL. Every other rule (broken links, redirect
  chains, crawl depth, robots.txt conflicts, hreflang) is a structural
  or cross-page problem a single field edit can't safely resolve, and
  generate_fix_value returns None for those rather than guessing.

- REMEDIABLE_RULES is the single source of truth both the API layer and
  the frontend check before even offering a "Generate fix" / "Apply to
  website" action — see api/routes/seo.py's remediation endpoints.

Applying the generated value (writing it to the real CMS post, then
re-reading the post to confirm it actually took — since an unregistered
SEO-plugin meta key is silently ignored by WordPress, not rejected) is
automation/seo/issue_applier.py, not this module: this module only ever
reads the live page (to have real content to react to) and calls the
LLM factory — it makes no write of its own.
"""
import logging
from dataclasses import dataclass
from typing import Optional

import requests
from bs4 import BeautifulSoup

from ai.llm.factory import get_provider
from ai.llm.sanitize import strip_leaked_prompt_markers
from automation.seo.crawler import USER_AGENT

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT_SECONDS = 15

# The only issue types where a "correct" replacement value is even
# knowable from a page's own content — everything else technical_audit.py
# detects is structural/cross-page/file-level and stays manual-fix-only.
REMEDIABLE_RULES = ("duplicate_title", "missing_meta_description", "missing_canonical")


@dataclass
class FixValueResult:
    value: Optional[str]
    error: Optional[str] = None


def _fetch_page_context(url: str) -> Optional[tuple]:
    """Returns (current_title, plain_text_excerpt) for the live page, or
    None on any fetch failure. Read-only — this never writes anything."""
    try:
        response = requests.get(url, timeout=REQUEST_TIMEOUT_SECONDS, headers={"User-Agent": USER_AGENT})
        response.raise_for_status()
    except requests.RequestException:
        logger.exception("issue_remediation: failed to fetch %s for context", url)
        return None
    soup = BeautifulSoup(response.text, "html.parser")
    title_tag = soup.find("title")
    current_title = title_tag.get_text(strip=True) if title_tag else ""
    plain_text = soup.get_text(" ", strip=True)
    return current_title, plain_text[:2000]


def generate_fix_value(rule: str, url: str, message: str, *, site_id: Optional[int] = None) -> FixValueResult:
    """Never raises — returns FixValueResult(value=None, error=...) on
    any failure, matching this codebase's graceful-degrade convention."""
    if rule not in REMEDIABLE_RULES:
        return FixValueResult(value=None, error=f"{rule!r} is a structural issue — no auto-generatable fix exists")

    if rule == "missing_canonical":
        # No LLM needed — absent any other signal, a page's own canonical
        # URL is itself. This is exactly what the audit's own static
        # suggested_fix text already recommends.
        return FixValueResult(value=url)

    context = _fetch_page_context(url)
    if context is None:
        return FixValueResult(value=None, error="Could not fetch the live page to generate a fix")
    current_title, excerpt = context

    if rule == "duplicate_title":
        prompt = (
            f'This page\'s current title, "{current_title}", is duplicated on another page of the '
            "same site (a real SEO problem — search engines can't tell the pages apart). Write ONE new, "
            "specific title for THIS page only, grounded in its actual content below. 50-60 characters, "
            "no site name suffix, no quotes, no explanation — the title text only.\n\n"
            f"PAGE CONTENT:\n{excerpt}"
        )
        result = get_provider(task="issue_fix_title", site_id=site_id).generate(prompt, fast=True)
        if not result.ok:
            return FixValueResult(value=None, error=result.error)
        value = strip_leaked_prompt_markers(result.text.strip().strip('"'), prompt=prompt)
        if not value:
            return FixValueResult(value=None, error="Generated output was empty after removing a leaked prompt fragment")
        return FixValueResult(value=value)

    if rule == "missing_meta_description":
        prompt = (
            f'Write a meta description for the page titled "{current_title}", grounded in its actual '
            "content below. 140-155 characters, factual, no marketing fluff, no quotes, no explanation "
            "— the description text only.\n\n"
            f"PAGE CONTENT:\n{excerpt}"
        )
        result = get_provider(task="issue_fix_meta_description", site_id=site_id).generate(prompt, fast=True)
        if not result.ok:
            return FixValueResult(value=None, error=result.error)
        value = strip_leaked_prompt_markers(result.text.strip().strip('"'), prompt=prompt)
        if not value:
            return FixValueResult(value=None, error="Generated output was empty after removing a leaked prompt fragment")
        return FixValueResult(value=value)

    return FixValueResult(value=None, error=f"No generator implemented for {rule!r}")
