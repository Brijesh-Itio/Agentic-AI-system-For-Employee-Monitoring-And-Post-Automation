"""
MODULE 19.2 — RAG Email Writer

For each lead, builds context from ai/rag.py (ChromaDB + the lead's own
SQL fields) and asks Ollama to write a subject/body that actually
references that lead's specific situation — not a generic template with
{{name}} substituted in.
"""
import logging
import re
from typing import Optional, TypedDict

from ai.ollama_client import generate
from ai.rag import build_context_for_lead

logger = logging.getLogger(__name__)


class WrittenEmail(TypedDict):
    subject: str
    body: str


def _build_prompt(lead: dict, context: str) -> str:
    return (
        "Write a short, personalised outreach email to the lead described below. "
        "Rules:\n"
        "- The email must reference at least one specific detail from the lead's "
        "context (their company, role, or interest) — a generic email that could be "
        "sent to anyone is a failure.\n"
        "- Professional but conversational tone, no corporate buzzwords.\n"
        "- 3-4 short paragraphs maximum.\n"
        "- Do NOT include a sign-off/signature line or bracketed placeholders like "
        "[Your Name] — the body ends after the last paragraph, nothing else.\n"
        "- Respond in EXACTLY this format, nothing else:\n"
        "SUBJECT: <subject line>\n"
        "BODY:\n<email body>\n\n"
        f"LEAD CONTEXT:\n{context}"
    )


def _parse_response(raw: str) -> Optional[WrittenEmail]:
    match = re.search(r"SUBJECT:\s*(.+?)\nBODY:\s*\n?(.+)", raw, re.DOTALL)
    if not match:
        return None
    subject = match.group(1).strip()
    body = match.group(2).strip()

    # Small/quantized models sometimes echo the prompt's own section
    # headers back at the end of their response — strip anything from the
    # first such echoed header onward rather than sending it to a real lead.
    for marker in ("LEAD CONTEXT:", "SUBJECT:", "RULES:"):
        idx = body.find(marker)
        if idx > 0:
            body = body[:idx].rstrip()

    if not subject or not body:
        return None
    return {"subject": subject, "body": body}


def _references_lead_specifics(email: WrittenEmail, lead: dict) -> bool:
    """19.2's "validate that the email actually references the lead's
    specific information" — checks the written body actually mentions at
    least one of the lead's concrete details rather than trusting the
    model blindly."""
    body_lower = email["body"].lower()
    candidates = [lead.get("company"), lead.get("role"), lead.get("interest"), lead.get("name")]
    return any(c and c.lower() in body_lower for c in candidates if c)


def write_email(lead: dict) -> Optional[WrittenEmail]:
    """Returns None (never raises) if Ollama is unreachable, the response
    can't be parsed, or it fails the personalisation check — a generic
    email is treated as a failure, not sent as a lesser success."""
    context = build_context_for_lead(lead)
    raw = generate(_build_prompt(lead, context), fast=False)
    if raw is None:
        logger.error("RAG email writer: Ollama unreachable/timed out for lead %s", lead.get("email"))
        return None

    email = _parse_response(raw)
    if email is None:
        logger.error("RAG email writer: could not parse SUBJECT/BODY from model response for lead %s", lead.get("email"))
        return None

    if not _references_lead_specifics(email, lead):
        logger.warning(
            "RAG email writer: generated email for %s doesn't reference any specific "
            "lead detail — treating as not personalised enough to send",
            lead.get("email"),
        )
        return None

    logger.info("RAG email writer: wrote email for %s (subject=%r)", lead.get("email"), email["subject"])
    return email


if __name__ == "__main__":
    from agent.logging_config import setup_logging

    setup_logging()
    logger.info("Module 19.2 manual test: writing a RAG-personalised email")
    test_lead = {"id": 0, "name": "Jane Doe", "email": "jane@example.com", "company": "Acme Robotics", "role": "Head of Engineering", "interest": "agentic AI", "notes": None}
    print(write_email(test_lead))
