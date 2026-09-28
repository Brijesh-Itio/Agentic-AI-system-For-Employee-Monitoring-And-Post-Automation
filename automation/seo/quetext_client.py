"""
Quetext API client — real, paid plagiarism and AI-content detection
(DeepSearch), billed against the account's Quetext word-balance wallet
at $0.10 per 1,000 words. Endpoints, auth, request/response shapes and
billing rules below are taken from Quetext's own published developer
docs (https://www.quetext.com/developers-api), read this session — not
guessed. Only Plagiarism and AI Detection are documented there as real
API endpoints; the Essential plan's Humanizer, Summarizer and Grammar
Checker are web-app tools with no published REST endpoint, so this
module deliberately does not claim to wire them up (same "an honest gap
beats a guessed-at integration" stance this codebase already takes with
Ahrefs — see DEVELOPMENT.md).

This is separate from, and never replaces, ai/seo/content_quality.py's
free, always-on local heuristic check that already runs automatically
on every generated post: that one is free and instant. This one costs
real money and takes anywhere from a few seconds to a few minutes
(Quetext processes the report server-side and this client polls until
it's done), so callers must only run it when a human explicitly asks —
never on an automatic generate/regenerate path.
"""
import logging
import re
import time
from dataclasses import dataclass, field
from typing import List, Optional

import requests

from api.config import settings

logger = logging.getLogger(__name__)

BASE_URL = "https://www.quetext.com/api/v2"
REQUEST_TIMEOUT_SECONDS = 30
POLL_INTERVAL_SECONDS = 3
# Quetext's own docs say to poll every 2-3s "until progress reaches 1.0" with
# no stated upper bound — this caps how long a caller waits before giving up
# and showing a real "still processing" message instead of hanging forever.
MAX_POLL_SECONDS = 180


def is_configured() -> bool:
    return bool(settings.QUETEXT_API_KEY)


def _headers() -> dict:
    return {"X-API-Key": settings.QUETEXT_API_KEY, "Content-Type": "application/json"}


def _strip_html(content_html: str) -> str:
    text = re.sub(r"<[^>]+>", " ", content_html)
    return re.sub(r"\s+", " ", text).strip()


def _request(method: str, path: str, **kwargs) -> requests.Response:
    return requests.request(method, f"{BASE_URL}{path}", headers=_headers(), timeout=REQUEST_TIMEOUT_SECONDS, **kwargs)


def _error_detail(response: requests.Response) -> str:
    """Quetext's documented error shape is {"status": false, "code", "message"};
    402 additionally carries balance_words/needed_words — verified live these are nested under a "data"
    object ({"data": {"balance_words": ..., "needed_words": ...}}), not top-level as the docs summary this
    was first written from implied — worth surfacing directly since it tells the user exactly what to do
    (top up)."""
    try:
        body = response.json()
    except ValueError:
        return response.text[:300] or f"Quetext returned HTTP {response.status_code}"
    if response.status_code == 402:
        data = body.get("data") or {}
        return (
            f"Not enough Quetext word balance ({data.get('balance_words', '?')} words left, "
            f"{data.get('needed_words', '?')} needed for this check) — top up at quetext.com."
        )
    if response.status_code == 429:
        return "Quetext rate limit reached (10 requests per 5 seconds) — wait a moment and try again."
    return body.get("message") or f"Quetext returned HTTP {response.status_code}"


@dataclass
class QuetextMatch:
    percent_similar: float
    source_url: Optional[str] = None
    snippet: Optional[str] = None


@dataclass
class QuetextPlagiarismResult:
    ok: bool
    score: Optional[float] = None
    word_count: Optional[int] = None
    matches: List[QuetextMatch] = field(default_factory=list)
    report_id: Optional[str] = None
    error: Optional[str] = None


@dataclass
class QuetextAiMatch:
    sentence: str
    generated_prob: float


@dataclass
class QuetextAiDetectResult:
    ok: bool
    ai_score: Optional[float] = None
    summary: Optional[str] = None
    matches: List[QuetextAiMatch] = field(default_factory=list)
    report_id: Optional[str] = None
    error: Optional[str] = None


def check_plagiarism(content_html: str, title: Optional[str] = None) -> QuetextPlagiarismResult:
    """Submits the text, polls /report-progress until Quetext reports it
    done, then fetches the full report. Never raises — any failure
    (unconfigured key, network error, a real Quetext error response,
    running out of word balance, or still processing past the poll
    cap) comes back as ok=False with a real, displayable reason, same
    convention as every other integration client in this codebase."""
    if not is_configured():
        return QuetextPlagiarismResult(ok=False, error="QUETEXT_API_KEY is not set in .env")
    text = _strip_html(content_html)
    if len(text.split()) < 20:
        return QuetextPlagiarismResult(ok=False, error="Quetext needs at least 20 words to run a plagiarism check")

    payload = {"text": text, "title": title} if title else {"text": text}
    try:
        submit = _request("POST", "/report", json=payload)
    except requests.RequestException as exc:
        logger.exception("Quetext plagiarism submit failed")
        return QuetextPlagiarismResult(ok=False, error=f"Could not reach Quetext: {exc}")
    if submit.status_code != 200:
        return QuetextPlagiarismResult(ok=False, error=_error_detail(submit))

    report_id = (submit.json().get("data") or {}).get("id")
    if not report_id:
        return QuetextPlagiarismResult(ok=False, error="Quetext accepted the request but returned no report id")

    poll_error = _poll_progress(f"/report-progress/{report_id}")
    if poll_error:
        return QuetextPlagiarismResult(ok=False, report_id=report_id, error=poll_error)

    try:
        result = _request("GET", f"/report/{report_id}")
    except requests.RequestException as exc:
        logger.exception("Quetext plagiarism report fetch failed (report_id=%s)", report_id)
        return QuetextPlagiarismResult(ok=False, report_id=report_id, error=f"Could not reach Quetext: {exc}")
    if result.status_code != 200:
        return QuetextPlagiarismResult(ok=False, report_id=report_id, error=_error_detail(result))

    data = (result.json().get("data") or {})
    matches = [
        QuetextMatch(
            percent_similar=_to_float(m.get("percent_similar")) or 0.0,
            # Verified live: the source URL is nested under `source.url`, not a top-level field, and
            # `input_text_match` (the matched portion of OUR OWN input) reads far better than
            # `highlighted_snippet` (the matched source page's own surrounding text, HTML tags and all).
            source_url=(m.get("source") or {}).get("url"),
            snippet=m.get("input_text_match"),
        )
        for m in (data.get("matches") or [])
    ]
    return QuetextPlagiarismResult(
        ok=True, score=_to_float(data.get("score")), word_count=data.get("word_count"),
        matches=matches, report_id=report_id,
    )


def check_ai_detection(content_html: str, title: Optional[str] = None) -> QuetextAiDetectResult:
    """Same submit-then-poll shape as check_plagiarism, but Quetext's docs
    don't show a dedicated progress endpoint for AI-detection reports —
    only the retrieval endpoint's own `status`/`percentage` fields — so
    this polls that endpoint directly until `status` reads 'completed'."""
    if not is_configured():
        return QuetextAiDetectResult(ok=False, error="QUETEXT_API_KEY is not set in .env")
    text = _strip_html(content_html)
    # Quetext's own error message ("AI detection requires a minimum of 50 words") confirmed this is a
    # word count, not a character count as the docs summary this was first written from implied.
    if len(text.split()) < 50:
        return QuetextAiDetectResult(ok=False, error="Quetext needs at least 50 words to run an AI detection check")

    payload = {"text": text, "title": title} if title else {"text": text}
    try:
        submit = _request("POST", "/ai-detect-report", json=payload)
    except requests.RequestException as exc:
        logger.exception("Quetext AI-detection submit failed")
        return QuetextAiDetectResult(ok=False, error=f"Could not reach Quetext: {exc}")
    if submit.status_code != 200:
        return QuetextAiDetectResult(ok=False, error=_error_detail(submit))

    report_id = (submit.json().get("data") or {}).get("id")
    if not report_id:
        return QuetextAiDetectResult(ok=False, error="Quetext accepted the request but returned no report id")

    deadline = time.monotonic() + MAX_POLL_SECONDS
    data: dict = {}
    while time.monotonic() < deadline:
        try:
            result = _request("GET", f"/ai-detect-report/{report_id}")
        except requests.RequestException as exc:
            logger.exception("Quetext AI-detection report fetch failed (report_id=%s)", report_id)
            return QuetextAiDetectResult(ok=False, report_id=report_id, error=f"Could not reach Quetext: {exc}")
        if result.status_code != 200:
            return QuetextAiDetectResult(ok=False, report_id=report_id, error=_error_detail(result))
        data = result.json().get("data") or {}
        status = data.get("status")
        percentage = data.get("percentage")
        if status == "completed" or (isinstance(percentage, (int, float)) and percentage >= 100):
            break
        time.sleep(POLL_INTERVAL_SECONDS)
    else:
        return QuetextAiDetectResult(
            ok=False, report_id=report_id,
            error="Quetext is still processing after 3 minutes — try again shortly.",
        )

    matches = [
        QuetextAiMatch(sentence=m.get("sentence", ""), generated_prob=_to_float(m.get("generated_prob")) or 0.0)
        for m in (data.get("ai_matches") or [])
    ]
    return QuetextAiDetectResult(
        ok=True, ai_score=_to_float(data.get("ai_score")), summary=data.get("ai_summary"),
        matches=matches, report_id=report_id,
    )


def _poll_progress(progress_path: str) -> Optional[str]:
    """Returns None once Progress reaches 1.0, or an error string on
    failure/timeout. Verified live that /report-progress's "data" is a
    single object ({"Progress": ..., "id": ...}), not the list the
    published docs example showed — handles either shape defensively."""
    deadline = time.monotonic() + MAX_POLL_SECONDS
    while time.monotonic() < deadline:
        try:
            resp = _request("GET", progress_path)
        except requests.RequestException as exc:
            return f"Could not reach Quetext: {exc}"
        if resp.status_code != 200:
            return _error_detail(resp)
        # Verified live: the real field is lowercase "progress" (0-1, as an int once done, e.g. 1 not
        # 1.0) — the published docs example showed "Progress" (capital P); both are checked defensively.
        data = resp.json().get("data")
        if isinstance(data, list):
            row = data[0] if data else {}
        elif isinstance(data, dict):
            row = data
        else:
            row = {}
        progress = row.get("progress", row.get("Progress"))
        if isinstance(progress, (int, float)) and progress >= 1.0:
            return None
        time.sleep(POLL_INTERVAL_SECONDS)
    return "Quetext is still processing after 3 minutes — try again shortly."


def _to_float(value) -> Optional[float]:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None
