"""
Login/logout + role-based access control (RBAC).

Not one of the original 24 modules — added afterward so managers/admins can
log in and see what every employee is doing, and so an employee's own
dashboard is separated from everyone else's data. Three roles, ascending
authority: `employee` (own data only), `manager` (read access to every
employee's tracked data + AI team analysis), `admin` — "the boss" — (same
as manager, plus full control over accounts: create/deactivate users,
change anyone's role, reset passwords).

JWT access tokens (python-jose, already a project dependency for module 5's
planned auth) carry `sub` (user id) and `role`. Logout is stateless — the
token simply isn't sent again; there is no server-side session to
invalidate, matching how the rest of this project avoids state it doesn't
need (see module 8/18/19's similarly stateless designs).
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer 
from jose import JWTError, jwt 
from sqlalchemy.orm import Session

from api.config import settings
from api.database import User, get_db

logger = logging.getLogger(__name__)

ALGORITHM = "HS256"
ROLES = ("employee", "manager", "admin")
# Roles with oversight of everyone's data, not just their own.
OVERSIGHT_ROLES = ("manager", "admin")

_bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(plain_password: str) -> str:
    return bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool: 
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        # Malformed/legacy hash (or None) — never a valid login, never a crash.
        return False


def create_access_token(user: User) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": user.id, "role": user.role, "name": user.name, "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def _decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    payload = _decode_token(credentials.credentials)
    user = db.query(User).filter(User.id == payload.get("sub")).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User no longer exists")
    return user


def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """Same as get_current_user but returns None instead of 401 when no
    token is present — only for the account-bootstrap endpoint, where the
    very first admin account has no one logged in yet to create it."""
    if credentials is None:
        return None
    payload = _decode_token(credentials.credentials)
    return db.query(User).filter(User.id == payload.get("sub")).first()


def require_role(*allowed_roles: str):
    """Dependency factory: `Depends(require_role("manager", "admin"))`."""

    def _check(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of roles: {', '.join(allowed_roles)}",
            )
        return current_user

    return _check


require_oversight = require_role(*OVERSIGHT_ROLES)
require_admin = require_role("admin")
