"""Authentication: credential checks and refresh-token lifecycle."""

from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.passwords import hash_password, needs_rehash, verify_password
from app.core.security import (
    as_utc,
    create_access_token,
    hash_refresh_token,
    new_refresh_token,
    utcnow,
)
from app.models import User
from app.models.auth import RefreshToken

# Verifying against a real hash when the user does not exist keeps response times similar,
# so the login endpoint does not reveal which e-mail addresses have accounts.
_DUMMY_HASH = hash_password("dummy-password-for-timing-1A")


@dataclass(frozen=True)
class IssuedTokens:
    access_token: str
    expires_in: int
    refresh_token: str


def authenticate(db: Session, email: str, password: str) -> User | None:
    user = db.scalar(select(User).where(User.email == email.strip().lower()))
    if user is None:
        verify_password(password, _DUMMY_HASH)
        return None
    # Rejected and disabled accounts get the same answer as a wrong password.
    if not verify_password(password, user.hashed_password) or not user.can_sign_in:
        return None
    if needs_rehash(user.hashed_password):
        user.hashed_password = hash_password(password)
    user.last_login_at = utcnow()
    return user


def issue_tokens(db: Session, user: User, settings: Settings) -> IssuedTokens:
    role = user.role.value if user.role is not None else "none"
    access, lifetime = create_access_token(user.id, role, settings)
    raw_refresh = new_refresh_token()
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_refresh_token(raw_refresh),
            expires_at=utcnow() + timedelta(days=settings.refresh_token_days),
        )
    )
    db.flush()
    return IssuedTokens(access_token=access, expires_in=lifetime, refresh_token=raw_refresh)


def revoke_all(db: Session, user_id: int) -> None:
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=utcnow())
    )


def rotate_refresh_token(db: Session, raw_token: str, settings: Settings) -> IssuedTokens | None:
    """Exchange a refresh token for a new pair; the old token is revoked.

    Presenting an already-revoked token is treated as token theft: every session of that user
    is revoked.
    """
    stored = db.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == hash_refresh_token(raw_token))
    )
    if stored is None:
        return None
    if stored.revoked_at is not None:
        revoke_all(db, stored.user_id)
        return None
    if as_utc(stored.expires_at) <= utcnow() or not stored.user.can_sign_in:
        return None
    stored.revoked_at = utcnow()
    return issue_tokens(db, stored.user, settings)


def burn_password_hash(password: str) -> None:
    """Spend the same time as creating an account, so sign-up does not reveal existing e-mails
    through response time."""
    hash_password(password)


def revoke_refresh_token(db: Session, raw_token: str) -> None:
    stored = db.scalar(
        select(RefreshToken).where(RefreshToken.token_hash == hash_refresh_token(raw_token))
    )
    if stored is not None and stored.revoked_at is None:
        stored.revoked_at = utcnow()
