"""
MODULE 27.4 — Internal interlinking engine.

Builds a per-site semantic index of published pages (embedding via the
same local nomic-embed-text model every other ChromaDB-backed module
here uses) and, for a given page, finds the most semantically related
other pages on the same site — "meaning match," not just keyword
overlap, per the SEO blueprint's own framing of why this feature matters.
Own ChromaDB collection ("seo_interlinks"), same "collections named by
function, separate _OllamaEmbeddingFunction instance" convention as
ai/rag.py and ai/productivity_scorer.py.
"""
import logging
from dataclasses import dataclass
from typing import List

import chromadb

from ai.ollama_client import embed
from api.config import settings

logger = logging.getLogger(__name__)


class _OllamaEmbeddingFunction(chromadb.EmbeddingFunction):
    """Same convention, separate instance — see ai/rag.py's identical class."""

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
_interlinks_collection = _chroma_client.get_or_create_collection(
    "seo_interlinks", embedding_function=_embedding_fn
)


def _doc_id(site_id: int, url: str) -> str:
    return f"{site_id}:{url}"


@dataclass
class RelatedPage:
    url: str
    title: str
    distance: float


def index_page(site_id: int, url: str, title: str, content: str) -> bool:
    """Embeds and stores/replaces one page's entry in the interlink
    index. Call this whenever a page is published or its content
    materially changes. Never raises — returns False on failure."""
    text = f"{title}\n\n{content}"[:4000]  # embedding models have real input limits
    if not text.strip():
        return False
    try:
        _interlinks_collection.upsert(
            ids=[_doc_id(site_id, url)],
            documents=[text],
            metadatas=[{"site_id": site_id, "url": url, "title": title}],
        )
        return True
    except Exception:
        logger.exception("Failed to index page for interlinking (site_id=%s, url=%s)", site_id, url)
        return False


def find_related_pages(
    site_id: int, url: str, title: str, content: str, n_results: int = 8
) -> List[RelatedPage]:
    """Returns up to n_results other pages on the same site, ranked by
    semantic similarity to this page's content — excludes the page
    itself. Never raises — returns an empty list on failure, so a
    content pipeline can skip interlinking for this post rather than
    fail the whole publish."""
    text = f"{title}\n\n{content}"[:4000]
    if not text.strip():
        return []
    try:
        # Over-fetch by 1 to account for the page's own entry (if already
        # indexed) landing in its own top result, then filter it out below.
        result = _interlinks_collection.query(
            query_texts=[text],
            n_results=n_results + 1,
            where={"site_id": site_id},
        )
    except Exception:
        logger.exception("Interlink query failed (site_id=%s, url=%s)", site_id, url)
        return []

    metadatas = (result.get("metadatas") or [[]])[0]
    distances = (result.get("distances") or [[]])[0]

    related = [
        RelatedPage(url=meta["url"], title=meta["title"], distance=dist)
        for meta, dist in zip(metadatas, distances)
        if meta.get("url") != url
    ]
    return related[:n_results]


def remove_page(site_id: int, url: str) -> None:
    """Removes a page from the interlink index — e.g. when it's
    unpublished or deleted, so it stops being suggested as a link target."""
    try:
        _interlinks_collection.delete(ids=[_doc_id(site_id, url)])
    except Exception:
        logger.exception("Failed to remove page from interlink index (site_id=%s, url=%s)", site_id, url)
