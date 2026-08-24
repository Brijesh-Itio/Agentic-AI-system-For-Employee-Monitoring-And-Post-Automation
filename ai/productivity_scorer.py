"""
MODULE 6 — Productivity Scorer (app/website classification + scoring)

Real agentic behaviour, not a rules engine pretending to be one: every app
and website is classified by asking the local Ollama model to reason about
what it is, with ChromaDB as genuine long-term memory — first an exact
cache-hit lookup, then a semantic similarity search (via nomic-embed-text
embeddings) that lets the agent recognise "this is basically the same thing
I classified before" even when the app/window title differs slightly, and
only fails through to a fresh Ollama call when neither is confident. This
means classification quality can only improve over time, and the Ollama
call is truly only made once per genuinely distinct entity.

Sub-modules implemented (in order):
    6.1 App classifier
    6.2 Website classifier
    6.3 Score calculator (wires real categories into module 2's engine)
"""
import logging
import threading
from datetime import date as date_cls
from typing import Optional

import chromadb
import schedule

from agent import database
from agent.config import USER_ID
from agent.time_intelligence import TimeIntelligenceEngine
from ai.ollama_client import embed, generate
from api.config import settings

logger = logging.getLogger(__name__)

VALID_CATEGORIES = {"productive", "neutral", "distraction"}
DEFAULT_CATEGORY = "neutral"  # safe fallback if Ollama is unreachable

# Cosine distance below which a semantically similar past classification is
# trusted instead of asking Ollama again (0 = identical embedding).
SIMILARITY_DISTANCE_THRESHOLD = 0.08

# 6.2 — deterministic overrides, applied before any AI call. These are the
# spec's explicit hard rules ("social media is always distraction", "dev
# docs are always productive") — not guesses, so they should never go
# through the classifier at all.
_SOCIAL_MEDIA_DOMAINS = {
    "facebook.com", "instagram.com", "twitter.com", "x.com", "tiktok.com",
    "reddit.com", "snapchat.com", "pinterest.com",
}
_DEV_DOCS_HINTS = (
    "docs.", "developer.", "github.com", "stackoverflow.com", "readthedocs.io",
    "pypi.org", "npmjs.com", "developer.mozilla.org", "devdocs.io",
)
_NEWS_HINTS = ("news", "cnn.com", "bbc.com", "nytimes.com", "reuters.com", "theguardian.com")


class _OllamaEmbeddingFunction(chromadb.EmbeddingFunction):
    """ChromaDB embedding function backed by the local nomic-embed-text
    model, matching the tech stack's own "Embeddings" row rather than
    Chroma's bundled default embedder."""

    def __init__(self):
        pass

    def __call__(self, input):  # noqa: A002 - Chroma's required parameter name
        vectors = []
        for text in input:
            vector = embed(text)
            vectors.append(vector if vector is not None else [0.0] * 768)
        return vectors

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

# ChromaDB collections named by function per convention — never mixed.
_app_collection = _chroma_client.get_or_create_collection(
    "app_classifications", embedding_function=_embedding_fn
)
_website_collection = _chroma_client.get_or_create_collection(
    "website_classifications", embedding_function=_embedding_fn
)


def _parse_category(raw: Optional[str]) -> str:
    if not raw:
        return DEFAULT_CATEGORY
    lowered = raw.strip().lower()
    for category in VALID_CATEGORIES:
        if category in lowered:
            return category
    return DEFAULT_CATEGORY


def _memory_lookup(collection, key: str, query_text: str) -> Optional[str]:
    """Exact cache hit first, then a semantic-similarity fallback."""
    try:
        exact = collection.get(ids=[key])
        if exact["ids"]:
            return exact["metadatas"][0]["category"]
    except Exception:
        logger.exception("ChromaDB exact lookup failed for %r", key)

    try:
        similar = collection.query(query_texts=[query_text], n_results=1)
        if similar["ids"] and similar["ids"][0]:
            distance = similar["distances"][0][0]
            if distance <= SIMILARITY_DISTANCE_THRESHOLD:
                return similar["metadatas"][0][0]["category"]
    except Exception:
        logger.exception("ChromaDB similarity lookup failed for %r", query_text)

    return None


def _memory_store(collection, key: str, document: str, category: str) -> None:
    try:
        collection.upsert(ids=[key], documents=[document], metadatas=[{"category": category}])
    except Exception:
        logger.exception("Failed to store classification in ChromaDB for %r", key)


# ── 6.1 App classifier ──

def classify_app(app_name: str, window_title: Optional[str] = None) -> str:
    key = app_name.strip().lower()
    cached = _memory_lookup(_app_collection, key, app_name)
    if cached is not None:
        return cached

    prompt = (
        "You are classifying a desktop application for a work-productivity tracker.\n"
        f"Process name: {app_name}\n"
        f"Window title: {window_title or 'N/A'}\n\n"
        "Classify this application into exactly one of: productive, neutral, distraction.\n"
        "Respond with ONLY that one word."
    )
    category = _parse_category(generate(prompt, fast=True))
    _memory_store(_app_collection, key, app_name, category)
    return category


# ── 6.2 Website classifier ──

def classify_website(domain: Optional[str], page_title: Optional[str] = None) -> str:
    if not domain:
        return DEFAULT_CATEGORY

    lowered = domain.lower()

    if lowered in _SOCIAL_MEDIA_DOMAINS:
        return "distraction"
    if any(hint in lowered for hint in _DEV_DOCS_HINTS):
        return "productive"
    if any(hint in lowered for hint in _NEWS_HINTS):
        # "neutral unless the user is a journalist" — no per-user role
        # profile exists yet, so the safe default applies to everyone.
        return "neutral"

    key = lowered
    cached = _memory_lookup(_website_collection, key, f"{domain} {page_title or ''}".strip())
    if cached is not None:
        return cached

    prompt = (
        "You are classifying a website for a work-productivity tracker.\n"
        f"Domain: {domain}\n"
        f"Page title: {page_title or 'N/A'}\n\n"
        "Classify this website into exactly one of: productive, neutral, distraction.\n"
        "Respond with ONLY that one word."
    )
    category = _parse_category(generate(prompt, fast=True))
    _memory_store(_website_collection, key, f"{domain} {page_title or ''}".strip(), category)
    return category


# ── 6.3 Score calculator (categorize real data, then reuse module 2's engine) ──

def categorize_pending_activity(day: date_cls, user_id: str = USER_ID) -> int:
    conn = database.get_connection()
    rows = conn.execute(
        """
        SELECT id, app_name, window_title FROM activity_logs
        WHERE user_id = ? AND date = ? AND category = 'uncategorised'
        """,
        (user_id, day.isoformat()),
    ).fetchall()

    for row in rows:
        category = classify_app(row["app_name"], row["window_title"])
        try:
            with database.write_cursor() as cur:
                cur.execute("UPDATE activity_logs SET category = ? WHERE id = ?", (category, row["id"]))
        except Exception:
            logger.exception("Failed to persist category for activity_logs id=%s", row["id"])

    return len(rows)


def categorize_pending_websites(day: date_cls, user_id: str = USER_ID) -> int:
    conn = database.get_connection()
    rows = conn.execute(
        """
        SELECT id, domain, page_title FROM websites
        WHERE user_id = ? AND date = ? AND category = 'uncategorised'
        """,
        (user_id, day.isoformat()),
    ).fetchall()

    for row in rows:
        category = classify_website(row["domain"], row["page_title"])
        try:
            with database.write_cursor() as cur:
                cur.execute("UPDATE websites SET category = ? WHERE id = ?", (category, row["id"]))
        except Exception:
            logger.exception("Failed to persist category for websites id=%s", row["id"])

    return len(rows)


def rescore_day(day: date_cls, user_id: str = USER_ID) -> None:
    """Classify any pending activity/website rows for the day, then recompute
    every hourly score, the daily score, and the longest focus session —
    reusing module 2's engine rather than duplicating its logic."""
    categorize_pending_activity(day, user_id)
    categorize_pending_websites(day, user_id)

    engine = TimeIntelligenceEngine(user_id=user_id)
    for hour in range(24):
        engine.calculate_hourly_focus_score(day, hour)
    engine.calculate_daily_focus_score(day)
    engine.detect_longest_focus_session(day)


LIVE_RESCORE_INTERVAL_SECONDS = 60


class LiveScoringScheduler:
    """Keeps today's focus_score/productive_seconds current *during* the
    day, not just at the 18:00 completion cycle or when a DAR is manually
    generated — those were the only two callers of rescore_day() before
    this, so the dashboard's "Active Hours"/"Focus Score" stayed frozen at
    0 all day even while activity_logs was genuinely accumulating in real
    time. Runs every 60s (not e.g. every 10 minutes) because the user
    correctly rejected that as not actually feeling real-time — cheap to
    run this often: classify_app()/classify_website() only call Ollama for
    a genuinely new app/window or domain, everything else is a ChromaDB
    cache hit, and the rescore itself is pure SQL/arithmetic."""

    def __init__(self, user_id: str = USER_ID):
        self.user_id = user_id
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        # A private Scheduler(), not the bare `schedule` module — see
        # time_intelligence.py's TimeIntelligenceEngine for the full
        # explanation of why every scheduler class needs its own instance.
        self._scheduler = schedule.Scheduler()
        self._scheduler.every(LIVE_RESCORE_INTERVAL_SECONDS).seconds.do(self._safe_rescore)

    def _safe_rescore(self) -> None:
        try:
            rescore_day(date_cls.today(), self.user_id)
        except Exception:
            logger.exception("Live rescore tick failed")

    def start(self) -> None:
        self._safe_rescore()  # don't wait a full interval before the first real numbers show up
        self._thread = threading.Thread(target=self._run_loop, name="LiveScoringSchedulerThread", daemon=True)
        self._thread.start()
        logger.info("LiveScoringScheduler started (every %ds)", LIVE_RESCORE_INTERVAL_SECONDS)

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
        logger.info("LiveScoringScheduler stopped")

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self._scheduler.run_pending()
            except Exception:
                logger.exception("Live rescore scheduler tick failed; continuing")
            self._stop_event.wait(10)


if __name__ == "__main__":
    from agent.logging_config import setup_logging

    setup_logging()
    today = date_cls.today()
    logger.info("Module 6 manual test: rescoring %s", today)
    rescore_day(today)
