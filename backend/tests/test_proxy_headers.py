"""Per-client login limits behind the reverse proxy (review T-R3, M1).

In docker compose the browser reaches the API through nginx (the ``web`` container), so the
API's peer address is nginx's. Uvicorn runs with ``--proxy-headers`` and trusts
``X-Forwarded-For`` only from that address. These tests run the app behind the same uvicorn
middleware with the same setting.
"""

import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any, cast

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker
from starlette.types import ASGIApp
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from app.core.config import Settings
from app.db.session import get_db
from app.main import create_app

LOGIN = "/api/v1/auth/login"
REPO = Path(__file__).resolve().parents[2]
PROXY = "172.30.57.10"  # the web container's address in docker-compose.yml


@pytest.fixture
def app(session_factory: sessionmaker[Session], settings: Settings) -> ASGIApp:
    api = create_app(settings)

    def _db() -> Iterator[Session]:
        with session_factory() as session:
            yield session

    api.dependency_overrides[get_db] = _db
    # uvicorn and Starlette type the same ASGI interface differently.
    return cast(ASGIApp, ProxyHeadersMiddleware(cast(Any, api), trusted_hosts=PROXY))


def _fail(client: TestClient, email: str, forwarded_for: str | None = None) -> int:
    headers = {"X-Forwarded-For": forwarded_for} if forwarded_for else {}
    data = {"username": email, "password": "Wrong-pass-123"}
    return client.post(LOGIN, data=data, headers=headers).status_code


def _per_client_limit(settings: Settings) -> int:
    return settings.login_rate_limit_attempts * 4


def test_clients_behind_the_proxy_do_not_share_a_limit(app: ASGIApp, settings: Settings) -> None:
    limit = _per_client_limit(settings)
    with TestClient(app, base_url="https://testserver", client=(PROXY, 40000)) as proxy:
        # Client 1 exhausts its per-client limit (distinct e-mails, so only that limit applies).
        codes = [_fail(proxy, f"u{i}@example.org", "198.51.100.1") for i in range(limit)]
        assert set(codes) == {401}
        assert _fail(proxy, "next@example.org", "198.51.100.1") == 429
        # Client 2 arrives through the same proxy and is not blocked by client 1's failures.
        assert _fail(proxy, "other@example.org", "198.51.100.2") == 401


def test_forged_forwarded_for_from_untrusted_peer_is_ignored(
    app: ASGIApp, settings: Settings
) -> None:
    limit = _per_client_limit(settings)
    # A client reaching the API port directly (not via nginx) invents a new address each time.
    with TestClient(app, base_url="https://testserver", client=("172.30.57.1", 40000)) as direct:
        codes = [_fail(direct, f"u{i}@example.org", f"203.0.113.{i}") for i in range(limit)]
        assert set(codes) == {401}
        # Still counted as one client: blocked despite yet another forged address.
        assert _fail(direct, "next@example.org", "203.0.113.250") == 429
        assert _fail(direct, "plain@example.org") == 429
    # The forged addresses were never used as keys: a real client behind the proxy that happens
    # to have one of them is unaffected.
    with TestClient(app, base_url="https://testserver", client=(PROXY, 40000)) as proxy:
        assert _fail(proxy, "real@example.org", "203.0.113.1") == 401


def test_deployment_trusts_only_the_proxy_address() -> None:
    """The entrypoint never trusts '*', and compose pins the proxy to the trusted address."""
    entrypoint = (REPO / "backend" / "docker-entrypoint.sh").read_text(encoding="utf-8")
    command = next(line for line in entrypoint.splitlines() if line.startswith("exec uvicorn"))
    assert "--proxy-headers" in command
    assert '--forwarded-allow-ips="$TRUSTED_PROXY"' in command
    assert "'*'" not in command
    assert '"*"' not in command
    compose = (REPO / "docker-compose.yml").read_text(encoding="utf-8")
    trusted = re.search(r"EDUPULSE_TRUSTED_PROXY: \$\{EDUPULSE_PROXY_IP:-([\d.]+)\}", compose)
    pinned = re.search(r"ipv4_address: \$\{EDUPULSE_PROXY_IP:-([\d.]+)\}", compose)
    assert trusted is not None
    assert pinned is not None
    assert trusted.group(1) == pinned.group(1) == PROXY
    nginx = (REPO / "frontend" / "nginx.conf").read_text(encoding="utf-8")
    assert "proxy_set_header X-Forwarded-For $remote_addr;" in nginx
