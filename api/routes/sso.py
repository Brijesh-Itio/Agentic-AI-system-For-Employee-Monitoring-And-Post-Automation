"""Google SSO (OAuth 2.0 Authorization Code flow) login.

Backend-only exchange — the browser never sees the client secret. The
frontend sends the browser to GET /google/login, which redirects to
Google; Google redirects back to GET /google/callback, which exchanges
the code, matches (or bootstraps) a local account, and hands the browser
one of this app's own access tokens via a redirect back to the frontend.

Sign-in only ever matches an *existing* account by email — SSO does not
auto-provision new users, same invite-only model as password accounts
(an admin adds each employee from the Team page, see api/routes/team.py)
— except for the very first account ever created, which bootstraps as
admin exactly like the password signup flow already does.

No server-side session store for the OAuth `state` value: it's a
short-lived signed JWT (same SECRET_KEY as the app's own access tokens),
so validating it is a stateless signature+expiry check, not a lookup —
matching how the rest of this project avoids state it doesn't need.
"""
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import urlencode

import requests
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from api.auth import ALGORITHM, create_access_token
from api.config import settings
from api.database import User, get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth/sso", tags=["sso"])

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

_STATE_EXPIRE_MINUTES = 10


def _google_configured() -> bool:
    return bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET)


def _redirect_uri() -> str:
    return f"{settings.API_PUBLIC_URL}/api/auth/sso/google/callback"


def _make_state() -> str:
    payload = {
        "nonce": secrets.token_urlsafe(16),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=_STATE_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def _state_is_valid(state: str) -> bool:
    try:
        jwt.decode(state, settings.SECRET_KEY, algorithms=[ALGORITHM])
        return True
    except JWTError:
        return False


@router.get("/status")
def sso_status():
    """Public — lets the frontend show/hide the 'Sign in with Google'
    button depending on whether an admin has configured credentials."""
    return {"google_enabled": _google_configured()}


@router.get("/google/login")
def google_login():
    if not _google_configured():
        raise HTTPException(status_code=503, detail="Google SSO is not configured")

    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": _redirect_uri(),
        "response_type": "code",
        "scope": "openid email profile",
        "state": _make_state(),
        "prompt": "select_account",
    }
    return RedirectResponse(f"{GOOGLE_AUTH_URL}?{urlencode(params)}")


@router.get("/google/callback")
def google_callback(
    db: Session = Depends(get_db),
    code: Optional[str] = Query(default=None),
    state: Optional[str] = Query(default=None),
    error: Optional[str] = Query(default=None),
):
    def _fail(reason: str) -> RedirectResponse:
        return RedirectResponse(f"{settings.FRONTEND_URL}/login?sso_error={reason}")

    if error:
        return _fail(error)
    if not _google_configured():
        return _fail("not_configured")
    if not code or not state:
        return _fail("missing_code")
    if not _state_is_valid(state):
        return _fail("invalid_state")

    try:
        token_resp = requests.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": _redirect_uri(),
                "grant_type": "authorization_code",
            },
            timeout=10,
        )
        token_resp.raise_for_status()
        google_access_token = token_resp.json()["access_token"]

        userinfo_resp = requests.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {google_access_token}"},
            timeout=10,
        )
        userinfo_resp.raise_for_status()
        info = userinfo_resp.json()
    except requests.RequestException:
        logger.exception("Google SSO token/userinfo exchange failed")
        return _fail("google_unreachable")

    email = info.get("email")
    if not email or not info.get("email_verified", True):
        return _fail("unverified_email")

    user = db.query(User).filter(User.email == email).first()

    if user is None:
        if db.query(User).count() > 0:
            # Invite-only, same as password accounts — an admin must add
            # this person from the Team page first.
            return _fail("no_account")
        # Bootstrap: the very first account ever created is always admin,
        # mirroring the password signup flow in api/routes/team.py.
        user = User(
            id=email.split("@")[0],
            name=info.get("name") or email,
            email=email,
            role="admin",
            created_at=datetime.now(),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info("SSO bootstrap admin created: %s", user.id)

    logger.info("SSO login: %s (role=%s)", user.id, user.role)
    access_token = create_access_token(user)
    return RedirectResponse(f"{settings.FRONTEND_URL}/sso-callback?token={access_token}")
