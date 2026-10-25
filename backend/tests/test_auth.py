"""Login, refresh rotation, logout, current user and token validation."""

from datetime import timedelta

import jwt
from fastapi.testclient import TestClient
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.api.routes.auth import REFRESH_COOKIE
from app.core.config import Settings
from app.core.security import utcnow
from app.models import RefreshToken, User
from tests.conftest import School
from tests.factories import PASSWORD

LOGIN = "/api/v1/auth/login"
REFRESH = "/api/v1/auth/refresh"
LOGOUT = "/api/v1/auth/logout"
ME = "/api/v1/auth/me"


def login(client: TestClient, email: str, password: str = PASSWORD) -> str:
    """Log in; returns the refresh token from the cookie jar (it is never in the body)."""
    response = client.post(LOGIN, data={"username": email, "password": password})
    assert response.status_code == 200, response.text
    assert "refresh_token" not in response.json()
    token = client.cookies.get(REFRESH_COOKIE)
    assert token
    return token


def refresh_with(client: TestClient, token: str) -> int:
    """POST /refresh presenting exactly this refresh cookie; returns the status code."""
    client.cookies.clear()
    return client.post(REFRESH, headers={"Cookie": f"{REFRESH_COOKIE}={token}"}).status_code


def test_login_returns_tokens_and_secure_cookie(client: TestClient, school: School) -> None:
    response = client.post(LOGIN, data={"username": school.admin.email, "password": PASSWORD})
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"access_token", "token_type", "expires_in"}  # no refresh token in JSON
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 15 * 60
    assert response.headers["cache-control"] == "no-store"
    cookie = response.headers["set-cookie"]
    assert REFRESH_COOKIE in cookie
    assert "HttpOnly" in cookie
    assert "Secure" in cookie
    assert "SameSite=strict" in cookie
    assert "Path=/api/v1/auth" in cookie

    me = client.get(ME, headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200
    assert me.json()["email"] == school.admin.email
    assert me.json()["role"] == "admin"
    assert "hashed_password" not in me.json()


def test_login_email_is_case_insensitive(client: TestClient, school: School) -> None:
    login(client, school.admin.email.upper())


def test_login_failures_are_generic(client: TestClient, school: School) -> None:
    wrong = client.post(LOGIN, data={"username": school.admin.email, "password": "Wrong-pass-123"})
    unknown = client.post(LOGIN, data={"username": "nobody@edupulse.example", "password": "x"})
    for response in (wrong, unknown):
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "invalid_credentials"
        assert response.json()["error"]["message"] == "Incorrect e-mail or password"


def test_inactive_user_cannot_log_in_and_tokens_stop_working(
    client: TestClient, school: School, db: Session
) -> None:
    headers = school.headers(school.teacher_a)
    db.execute(update(User).where(User.id == school.teacher_a.id).values(is_active=False))
    db.commit()
    response = client.post(LOGIN, data={"username": school.teacher_a.email, "password": PASSWORD})
    assert response.status_code == 401
    assert client.get(ME, headers=headers).status_code == 401


def test_login_rate_limit_blocks_after_repeated_failures(
    client: TestClient, school: School
) -> None:
    for _ in range(3):
        bad = {"username": school.admin.email, "password": "Wrong-pass-123"}
        assert client.post(LOGIN, data=bad).status_code == 401
    blocked = client.post(LOGIN, data={"username": school.admin.email, "password": PASSWORD})
    assert blocked.status_code == 429
    assert blocked.json()["error"]["code"] == "rate_limited"
    assert int(blocked.headers["retry-after"]) >= 1
    # A different account from the same client is not blocked by the per-account limit.
    login(client, school.teacher_a.email)


def test_successful_login_resets_account_counter(client: TestClient, school: School) -> None:
    bad = {"username": school.admin.email, "password": "Wrong-pass-123"}
    for _ in range(2):
        client.post(LOGIN, data=bad)
    login(client, school.admin.email)
    for _ in range(2):
        assert client.post(LOGIN, data=bad).status_code == 401
    login(client, school.admin.email)


def test_refresh_rotates_and_detects_reuse(client: TestClient, school: School) -> None:
    first = login(client, school.admin.email)
    rotated = client.post(REFRESH)
    assert rotated.status_code == 200
    assert set(rotated.json()) == {"access_token", "token_type", "expires_in"}
    assert "Secure" in rotated.headers["set-cookie"]
    second = client.cookies.get(REFRESH_COOKIE)
    assert second
    assert second != first

    # Re-using the old (rotated) token is treated as theft: all sessions are revoked.
    assert refresh_with(client, first) == 401
    assert refresh_with(client, second) == 401  # the whole session family was revoked


def test_refresh_with_cookie(client: TestClient, school: School) -> None:
    login(client, school.admin.email)  # TestClient keeps the cookie jar
    response = client.post(REFRESH)
    assert response.status_code == 200
    assert response.json()["access_token"]


def test_refresh_without_cookie_or_with_unknown_token(client: TestClient) -> None:
    assert client.post(REFRESH).status_code == 401
    client.cookies.clear()
    rejected = client.post(REFRESH, headers={"Cookie": f"{REFRESH_COOKIE}=nope"})
    assert rejected.status_code == 401
    assert "Max-Age=0" in rejected.headers["set-cookie"]  # cookie cleared


def test_refresh_token_in_body_is_not_accepted(client: TestClient, school: School) -> None:
    token = login(client, school.admin.email)
    client.cookies.clear()
    assert client.post(REFRESH, json={"refresh_token": token}).status_code == 401


def test_expired_refresh_token_rejected(client: TestClient, school: School, db: Session) -> None:
    login(client, school.admin.email)
    db.execute(update(RefreshToken).values(expires_at=utcnow() - timedelta(seconds=1)))
    db.commit()
    assert client.post(REFRESH).status_code == 401


def test_logout_revokes_refresh_token(client: TestClient, school: School, db: Session) -> None:
    token = login(client, school.admin.email)
    response = client.post(LOGOUT)
    assert response.status_code == 204
    assert db.scalars(select(RefreshToken.revoked_at)).one() is not None
    assert refresh_with(client, token) == 401


def test_logout_via_cookie_and_without_token(client: TestClient, school: School) -> None:
    login(client, school.admin.email)
    assert client.post(LOGOUT).status_code == 204
    client.cookies.clear()
    assert client.post(LOGOUT).status_code == 204


def test_me_requires_valid_access_token(
    client: TestClient, school: School, settings: Settings
) -> None:
    assert client.get(ME).status_code == 401
    assert client.get(ME, headers={"Authorization": "Bearer garbage"}).status_code == 401

    secret = settings.require_jwt_secret()
    now = utcnow()
    base = {"sub": str(school.admin.id), "role": "admin", "iat": now, "type": "access"}
    expired = jwt.encode({**base, "exp": now - timedelta(minutes=1)}, secret, "HS256")
    wrong_type = jwt.encode({**base, "type": "refresh", "exp": now + timedelta(minutes=5)}, secret)
    other_key = jwt.encode({**base, "exp": now + timedelta(minutes=5)}, "z" * 40, "HS256")
    bad_sub = jwt.encode({**base, "sub": "abc", "exp": now + timedelta(minutes=5)}, secret)
    unknown_user = jwt.encode({**base, "sub": "9999", "exp": now + timedelta(minutes=5)}, secret)
    for token in (expired, wrong_type, other_key, bad_sub, unknown_user):
        response = client.get(ME, headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 401
        assert response.headers["www-authenticate"] == "Bearer"


def test_unsigned_token_rejected(client: TestClient, school: School) -> None:
    now = utcnow()
    token = jwt.encode(
        {
            "sub": str(school.admin.id),
            "type": "access",
            "iat": now,
            "exp": now + timedelta(hours=1),
        },
        key=None,
        algorithm="none",
    )
    assert client.get(ME, headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_last_login_recorded(client: TestClient, school: School, db: Session) -> None:
    login(client, school.teacher_b.email)
    db.expire_all()
    assert db.get(User, school.teacher_b.id).last_login_at is not None  # type: ignore[union-attr]
