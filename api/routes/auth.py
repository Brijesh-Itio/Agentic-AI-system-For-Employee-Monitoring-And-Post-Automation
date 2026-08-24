"""Login/logout endpoints. See api/auth.py for the JWT/RBAC mechanics."""
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from api.auth import create_access_token, get_current_user, hash_password, verify_password
from api.database import User, get_db
from api.schemas import LoginRequest, SetPasswordRequest, TokenResponse, UserOut

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["auth"])


def _to_user_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        name=user.name,
        email=user.email,
        role=user.role,
        organisation_id=user.organisation_id,
        created_at=user.created_at,
        has_password=bool(user.password_hash),
    )


@router.get("/bootstrap-status")
def bootstrap_status(db: Session = Depends(get_db)):
    """Public — lets the frontend show 'create the first admin account'
    instead of a login form when no accounts exist yet at all."""
    return {"needs_setup": db.query(User).count() == 0}


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    # Accept either the account's ID or its email — the login form only
    # asks for one field, and people whose ID and email don't match (e.g.
    # id="ramesh", email="ramesh@gmail.com") naturally try whichever one
    # they think of first.
    identifier = payload.user_id.strip()
    user = db.query(User).filter(or_(User.id == identifier, User.email == identifier)).first()
    if user is None or not user.password_hash or not verify_password(payload.password, user.password_hash):
        # Same message for "no such user" and "wrong password" — don't leak
        # which accounts exist to an unauthenticated caller.
        raise HTTPException(status_code=401, detail="Incorrect user ID or password")
    logger.info("Login: %s (role=%s)", user.id, user.role)
    return TokenResponse(access_token=create_access_token(user), user=_to_user_out(user))


@router.post("/logout", status_code=204)
def logout(current_user: User = Depends(get_current_user)):
    """Stateless JWT — there's no server-side session to invalidate. This
    endpoint exists so the frontend has a real call to make (and so a bad/
    expired token gets a clean 401 instead of nothing) before it discards
    its locally stored token."""
    logger.info("Logout: %s", current_user.id)


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return _to_user_out(current_user)


@router.post("/change-password", status_code=204)
def change_password(
    payload: SetPasswordRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    if len(payload.password) < 6:
        raise HTTPException(status_code=422, detail="Password must be at least 6 characters")
    current_user.password_hash = hash_password(payload.password)
    db.commit()
