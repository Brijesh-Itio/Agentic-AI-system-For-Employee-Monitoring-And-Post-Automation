"""
MODULE 24.4 — Optional MinIO (S3-compatible) screenshot storage.

Entirely opt-in via env vars (MINIO_ENDPOINT/MINIO_ACCESS_KEY/
MINIO_SECRET_KEY/MINIO_BUCKET). When they're unset — the default, and every
local/single-machine setup so far — `is_configured()` is False, nothing in
this module ever runs, and screenshots behave exactly as before: local disk
only, `cloud_url` stays NULL. When set, screenshots additionally upload to
MinIO after being saved locally (local copy is never removed — MinIO is a
mirror for remote/dashboard access, not the source of truth), and the
resulting object URL is recorded via `agent.database.set_screenshot_cloud_url`.

The `minio` package is imported lazily inside `_client()`, not at module
level, so a machine that never configures MinIO doesn't need it installed
at all despite it being listed in requirements.txt.
"""
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

_ENDPOINT = os.environ.get("MINIO_ENDPOINT", "")
_ACCESS_KEY = os.environ.get("MINIO_ACCESS_KEY", "")
_SECRET_KEY = os.environ.get("MINIO_SECRET_KEY", "")
_BUCKET = os.environ.get("MINIO_BUCKET", "workpulse-screenshots")
_SECURE = os.environ.get("MINIO_SECURE", "true").lower() == "true"

_client_singleton = None
_bucket_ready = False


def is_configured() -> bool:
    return bool(_ENDPOINT and _ACCESS_KEY and _SECRET_KEY)


def _client():
    global _client_singleton, _bucket_ready
    if _client_singleton is None:
        from minio import Minio

        _client_singleton = Minio(_ENDPOINT, access_key=_ACCESS_KEY, secret_key=_SECRET_KEY, secure=_SECURE)
    if not _bucket_ready:
        if not _client_singleton.bucket_exists(_BUCKET):
            _client_singleton.make_bucket(_BUCKET)
        _bucket_ready = True
    return _client_singleton


def upload_screenshot(local_path: str, object_name: str) -> Optional[str]:
    """Uploads one file to the configured MinIO bucket and returns its URL,
    or None on any failure (never raises — a failed upload should never
    break screenshot capture, which has already succeeded locally)."""
    if not is_configured():
        return None
    try:
        client = _client()
        client.fput_object(_BUCKET, object_name, local_path)
        scheme = "https" if _SECURE else "http"
        return f"{scheme}://{_ENDPOINT}/{_BUCKET}/{object_name}"
    except Exception:
        logger.exception("MinIO upload failed for %s (screenshot remains available locally)", local_path)
        return None
