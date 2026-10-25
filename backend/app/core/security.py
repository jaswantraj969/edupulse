"""JWT access tokens and opaque, rotating refresh tokens."""

import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import jwt

from app.core.config import Settings

ACCESS_TOKEN_TYPE = "access"  # noqa: S105  (token type label, not a secret)


@dataclass(frozen=True)
class AccessClaims:
    user_id: int
    role: str


def utcnow() -> datetime:
    return datetime.now(UTC)


def as_utc(value: datetime) -> datetime:
    """SQLite returns naive datetimes; treat them as UTC."""
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def create_access_token(user_id: int, role: str, settings: Settings) -> tuple[str, int]:
    """Return ``(token, lifetime_seconds)``."""
    lifetime = settings.access_token_minutes * 60
    now = utcnow()
    payload = {
        "sub": str(user_id),
        "role": role,
        "type": ACCESS_TOKEN_TYPE,
        "iat": now,
        "nbf": now,
        "exp": now + timedelta(seconds=lifetime),
        "jti": uuid.uuid4().hex,
    }
    token = jwt.encode(payload, settings.require_jwt_secret(), algorithm=settings.jwt_algorithm)
    return token, lifetime


def decode_access_token(token: str, settings: Settings) -> AccessClaims | None:
    """Validate signature, expiry and token type. Returns ``None`` for any invalid token."""
    try:
        payload = jwt.decode(
            token,
            settings.require_jwt_secret(),
            algorithms=[settings.jwt_algorithm],
            options={"require": ["exp", "iat", "sub", "type"]},
        )
    except jwt.PyJWTError:
        return None
    if payload.get("type") != ACCESS_TOKEN_TYPE:
        return None
    try:
        return AccessClaims(user_id=int(payload["sub"]), role=str(payload.get("role", "")))
    except (TypeError, ValueError):
        return None


def new_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
