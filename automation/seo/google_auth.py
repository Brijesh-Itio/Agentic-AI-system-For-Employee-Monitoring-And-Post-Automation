"""
MODULE 26.5 — Google service-account OAuth2 (JWT Bearer flow).

Shared by the GSC (26.5) and GA4 (26.6) clients. Signs a JWT assertion
with the service account's private key (RS256, via python-jose
[cryptography] — already a dependency for this app's own JWT auth in
api/auth.py, so no new package is needed) and exchanges it for a
short-lived OAuth2 access token, talking to Google's token endpoint
directly over REST rather than pulling in google-auth/
google-api-python-client — consistent with this codebase's lean-
dependency style (same reasoning as automation/seo/pagespeed_client.py
and the wordpress/webflow CMS clients).
"""
import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests
from jose import jwt

from ai.llm.retry import with_retry  # generic backoff helper, not LLM-specific
from api.config import settings

logger = logging.getLogger(__name__)

TOKEN_URL = "https://oauth2.googleapis.com/token"
TIMEOUT_SECONDS = 20

# scope string -> (access_token, expires_at_epoch_seconds). Module-level
# since tokens are valid for this whole process regardless of which
# request triggered the fetch — same reasoning as ai/llm/factory.py
# caching provider adapters, just for tokens instead of SDK clients.
_token_cache: Dict[str, Tuple[str, float]] = {}


def _load_service_account() -> Optional[dict]:
    path = settings.GOOGLE_SERVICE_ACCOUNT_JSON_PATH
    if not path:
        return None
    try:
        return json.loads(Path(path).read_text())
    except Exception:
        logger.exception("Failed to read GOOGLE_SERVICE_ACCOUNT_JSON_PATH=%s", path)
        return None


def service_account_email() -> Optional[str]:
    """The Google account this app acts as — the address that has to be
    added as a user on a Search Console / Analytics property."""
    account = _load_service_account()
    return account.get("client_email") if account else None


def get_access_token(scopes: List[str]) -> Optional[str]:
    """Returns a cached or freshly minted OAuth2 access token for the
    given scopes. Never raises — returns None on any failure (missing
    config, bad key, network, Google rejecting the assertion), same
    graceful-degrade convention as every other credential-gated client
    in this codebase."""
    scope_key = " ".join(sorted(scopes))
    cached = _token_cache.get(scope_key)
    if cached and cached[1] > time.time() + 30:  # 30s safety margin before real expiry
        return cached[0]

    account = _load_service_account()
    if account is None:
        logger.error(
            "Google service account not configured — set "
            "GOOGLE_SERVICE_ACCOUNT_JSON_PATH in .env"
        )
        return None

    now = int(time.time())
    claims = {
        "iss": account.get("client_email"),
        "scope": scope_key,
        "aud": TOKEN_URL,
        "iat": now,
        "exp": now + 3600,
    }
    try:
        assertion = jwt.encode(claims, account["private_key"], algorithm="RS256")
    except Exception:
        logger.exception("Failed to sign Google service-account JWT")
        return None

    def _do_exchange():
        response = requests.post(
            TOKEN_URL,
            data={
                "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                "assertion": assertion,
            },
            timeout=TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return response

    try:
        response = with_retry(_do_exchange, max_attempts=3, retry_on=(requests.RequestException,))
        data = response.json()
    except Exception:
        logger.exception("Google OAuth2 token exchange failed (scope=%s)", scope_key)
        return None

    access_token = data.get("access_token")
    if not access_token:
        logger.error("Google OAuth2 token exchange returned no access_token (scope=%s)", scope_key)
        return None

    expires_in = data.get("expires_in", 3600)
    _token_cache[scope_key] = (access_token, time.time() + expires_in)
    return access_token
