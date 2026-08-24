"""
MODULE 19.1 / 20.4 / 20.5 — Lead Loader, Deduplicator & Store

19.1's read side (load_leads_for_campaign) and 20.4/20.5's write side
(store_lead, deduping by name+company and syncing to ChromaDB) live in
one file since they're both "the leads table's data-access layer" — the
same reasoning module 5's api/routes/leads.py already applies for its own
dedup-on-create logic, mirrored here for the research pipeline's direct
DB access path (outside the API layer).
"""
import logging
from datetime import datetime
from typing import Optional

from agent import database
from automation.email.logger import already_contacted

logger = logging.getLogger(__name__)


def load_leads_for_campaign(limit: int) -> list[dict]:
    """Returns up to `limit` leads with an email address that have never
    appeared in campaign_log, oldest-first (fairest ordering — leads that
    have been waiting longest get contacted first)."""
    conn = database.get_connection()
    rows = conn.execute(
        "SELECT * FROM leads WHERE email IS NOT NULL AND email != '' ORDER BY created_at ASC"
    ).fetchall()

    selected = []
    for row in rows:
        lead = dict(row)
        if already_contacted(lead["email"]):
            continue
        selected.append(lead)
        if len(selected) >= limit:
            break

    logger.info("Lead loader: %d lead(s) selected for campaign (limit=%d)", len(selected), limit)
    return selected


# ── 20.4 Lead deduplicator + 20.5 Lead store ──

def store_lead(
    name: str,
    company: Optional[str] = None,
    role: Optional[str] = None,
    interest: Optional[str] = None,
    email: Optional[str] = None,
    notes: Optional[str] = None,
    source: Optional[str] = None,
    rag_context: Optional[str] = None,
) -> int:
    """20.4: same name+company already present -> update that row instead
    of inserting a duplicate (matches api/routes/leads.py's create_lead
    dedup rule exactly, for the research pipeline's direct-DB path).
    20.5: stores in SQLite (structured queries) and, when rag_context is
    given, ChromaDB (semantic search / RAG personalisation for module 19).
    Returns the lead's id either way."""
    conn = database.get_connection()
    existing = None
    if company:
        existing = conn.execute(
            "SELECT id FROM leads WHERE name = ? AND company = ?", (name, company)
        ).fetchone()

    if existing is not None:
        lead_id = existing["id"]
        with database.write_cursor() as cur:
            cur.execute(
                """
                UPDATE leads SET
                    role = COALESCE(?, role), interest = COALESCE(?, interest),
                    email = COALESCE(?, email), notes = COALESCE(?, notes),
                    source = COALESCE(?, source)
                WHERE id = ?
                """,
                (role, interest, email, notes, source, lead_id),
            )
        logger.info("Lead store: updated existing lead %d (%s @ %s)", lead_id, name, company)
    else:
        with database.write_cursor() as cur:
            cur.execute(
                """
                INSERT INTO leads (name, company, role, interest, email, notes, source, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'new', ?)
                """,
                (name, company, role, interest, email, notes, source, datetime.now().isoformat(sep=" ")),
            )
            lead_id = cur.lastrowid
        logger.info("Lead store: created new lead %d (%s @ %s)", lead_id, name, company)

    if rag_context:
        from ai.rag import upsert_lead_context

        upsert_lead_context(lead_id, rag_context)

    return lead_id
