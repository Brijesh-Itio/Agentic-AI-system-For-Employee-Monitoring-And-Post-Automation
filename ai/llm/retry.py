"""
MODULE 25.1 — Retry/backoff helper for LLM provider calls.

Nothing like this existed anywhere in the codebase before this module
(confirmed by searching broadly for retry/backoff/circuit-breaker
patterns). It was never needed: Ollama is one local server, and every
existing caller already treats a failed call as final and degrades to a
safe default. Paid, rate-limited APIs (Claude, OpenAI, and later GSC/
PageSpeed/GA4 in module 26) are a different story — a 429 or a transient
5xx/timeout is meant to be retried a bounded number of times, not treated
as a permanent failure on the first hiccup.
"""
import logging
import random
import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from typing import Callable, Tuple, Type, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


def with_retry(
    fn: Callable[[], T],
    *,
    max_attempts: int = 3,
    base_delay_seconds: float = 1.0,
    max_delay_seconds: float = 20.0,
    retry_on: Tuple[Type[BaseException], ...] = (Exception,),
) -> T:
    """Calls fn() with exponential backoff + jitter on any exception type
    in retry_on. Re-raises the final attempt's exception if every attempt
    fails — callers (provider adapters) catch that at their own boundary
    and convert it into an LLMResult with error set, same as every other
    failure path in this codebase never raises past its caller."""
    attempt = 0
    while True:
        attempt += 1
        try:
            return fn()
        except retry_on as exc:
            if attempt >= max_attempts:
                logger.error("Retry exhausted after %d attempts: %s", attempt, exc)
                raise
            delay = min(max_delay_seconds, base_delay_seconds * (2 ** (attempt - 1)))
            delay += random.uniform(0, delay * 0.25)  # jitter avoids retry storms
            logger.warning(
                "Attempt %d/%d failed (%s), retrying in %.1fs", attempt, max_attempts, exc, delay
            )
            time.sleep(delay)


def call_with_hard_timeout(fn: Callable[[], T], timeout_seconds: float) -> T:
    """Runs fn() with an OS-thread-level deadline that fires even if fn()
    ignores or mishandles its own timeout — observed live against
    automation/seo/indexing_client.py's Search Console call, which hung
    for minutes with zero socket activity (confirmed via 0% CPU and all
    threads in Wait state) despite requests' own `timeout=` argument,
    something curl against the same endpoint never reproduced. Raises
    TimeoutError past the deadline; the stuck worker thread is abandoned
    (not killed — Python has no safe way to do that) rather than waited
    on, so a hang here can't wedge the caller or FastAPI's thread pool."""
    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(fn)
    try:
        return future.result(timeout=timeout_seconds)
    except FutureTimeoutError as exc:
        raise TimeoutError(f"Call exceeded hard timeout of {timeout_seconds}s") from exc
    finally:
        executor.shutdown(wait=False)
