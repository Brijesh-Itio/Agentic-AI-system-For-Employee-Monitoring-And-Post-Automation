"""
MODULE — ChromaDB RAG for lead personalisation (module 19.2's dependency)

A `leads` ChromaDB collection (named by function per DEVELOPMENT.md
section 8) storing free-text context per lead — notes from research,
enrichment findings, past interactions. Module 20 (lead research) is what
would populate this richly once built; until then, it holds whatever a
lead's own `notes` field says, so the RAG layer is genuinely wired up
end-to-end rather than a stub waiting for later modules.
"""
import logging
from typing import Optional

import chromadb

from ai.ollama_client import embed
from api.config import settings

logger = logging.getLogger(__name__)


class _OllamaEmbeddingFunction(chromadb.EmbeddingFunction):
    """Matches ai/productivity_scorer.py's own embedding function — same
    convention, separate instance, since each ChromaDB-using module owns
    its own collections per the "collections named by function" rule."""

    def __call__(self, input):  # noqa: A002 - Chroma's required parameter name
        return [embed(text) or [0.0] * 768 for text in input]

    @staticmethod
    def name() -> str:
        return "ollama_nomic_embed_text"

    def get_config(self) -> dict:
        return {"model": "nomic-embed-text"}

    @staticmethod
    def build_from_config(config: dict) -> "_OllamaEmbeddingFunction":
        return _OllamaEmbeddingFunction()


_chroma_client = chromadb.PersistentClient(path=settings.CHROMADB_PATH)
_embedding_fn = _OllamaEmbeddingFunction()
_leads_collection = _chroma_client.get_or_create_collection("leads", embedding_function=_embedding_fn)


def upsert_lead_context(lead_id: int, text: str) -> None:
    """Stores/replaces the RAG document for one lead. Called whenever new
    information about a lead becomes available (manual notes today;
    module 20's research/enrichment findings once built)."""
    if not text or not text.strip():
        return
    try:
        _leads_collection.upsert(ids=[str(lead_id)], documents=[text])
    except Exception:
        logger.exception("Failed to upsert RAG context for lead %d", lead_id)


def get_lead_context(lead_id: int) -> Optional[str]:
    """Exact document lookup for a lead, if one has ever been stored."""
    try:
        result = _leads_collection.get(ids=[str(lead_id)])
        documents = result.get("documents") or []
        return documents[0] if documents else None
    except Exception:
        logger.exception("Failed to fetch RAG context for lead %d", lead_id)
        return None


def build_context_for_lead(lead: dict) -> str:
    """19.2's "query ChromaDB for all stored information about that lead,
    build a rich context string" — combines whatever's in ChromaDB with
    the lead's own SQL fields, so personalisation always has *something*
    concrete to reference even before module 20 exists to enrich it."""
    parts = [
        f"Name: {lead.get('name')}",
        f"Company: {lead.get('company')}" if lead.get("company") else None,
        f"Role: {lead.get('role')}" if lead.get("role") else None,
        f"Interest: {lead.get('interest')}" if lead.get("interest") else None,
        f"Notes: {lead.get('notes')}" if lead.get("notes") else None,
    ]
    base_context = "\n".join(p for p in parts if p)

    rag_context = get_lead_context(lead["id"])
    if rag_context and rag_context.strip() not in base_context:
        return f"{base_context}\n\nAdditional context:\n{rag_context}"
    return base_context


if __name__ == "__main__":
    from agent.logging_config import setup_logging

    setup_logging()
    logger.info("RAG module manual test: upsert + retrieve")
    upsert_lead_context(999999, "Test lead interested in agentic AI tooling for their startup.")
    print(get_lead_context(999999))
