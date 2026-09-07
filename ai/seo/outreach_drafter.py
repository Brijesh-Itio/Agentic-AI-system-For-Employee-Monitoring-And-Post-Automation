"""
MODULE 31.2 — Link outreach email drafting.

Uses the module 25 LLM factory to draft a link-request email for an
unlinked brand mention (automation/seo/backlinks — a page that mentioned
the brand without linking to it), matching the blueprint's "agent drafts
link-request emails for unlinked brand mentions" spec. Drafting only —
sending stays a human action (automation/email/sender.py already exists
for actually sending mail, and a cold outreach email is exactly the kind
of relationship-sensitive action this codebase's own convention keeps
human-triggered, same as module 18's LinkedIn posting requiring explicit
credentials and this session's LinkedIn near-miss underscoring why).
"""
import logging
from dataclasses import dataclass
from typing import Optional

from ai.llm.factory import get_provider

logger = logging.getLogger(__name__)


@dataclass
class OutreachDraft:
    subject: str
    body: str


def draft_outreach_email(
    mention_url: str, mention_title: Optional[str], site_name: str, site_url: str, *, site_id: Optional[int] = None
) -> Optional[OutreachDraft]:
    """Never raises — returns None on LLM failure or unparseable output."""
    prompt = (
        f'Write a short, polite link-request email to the author of the page at "{mention_url}" '
        f'(titled "{mention_title or "unknown"}"), which mentioned "{site_name}" without linking to it. '
        f"Ask them to add a link to {site_url}. Keep it brief, genuine, not pushy — one short "
        "paragraph. Return ONLY valid JSON: {\"subject\": \"...\", \"body\": \"...\"}. No markdown, "
        "no explanation, the JSON object only."
    )
    result = get_provider(task="outreach_email", site_id=site_id).generate(prompt, fast=True)
    if not result.ok:
        logger.warning("Outreach email drafting failed: %s", result.error)
        return None

    import json

    text = result.text.strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        logger.warning("Outreach email drafting returned unparseable output: %r", text)
        return None
    try:
        parsed = json.loads(text[start : end + 1])
        return OutreachDraft(subject=str(parsed["subject"]).strip(), body=str(parsed["body"]).strip())
    except (json.JSONDecodeError, KeyError, TypeError):
        logger.warning("Outreach email JSON parse failed: %r", text)
        return None
