"""Request ids, structured logs, error handling, probes and security headers."""

import json
import logging
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.core.logging import JsonFormatter, TextFormatter, configure_logging, request_id_var
from app.db.session import get_db
from app.main import create_app


def _boom_app(session_factory: sessionmaker[Session], settings: Settings) -> TestClient:
    app = create_app(settings)

    def _db() -> Iterator[Session]:
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = _db

    def boom() -> None:
        raise RuntimeError("secret internal detail")

    def conflict() -> None:
        raise IntegrityError("INSERT ...", {}, Exception("duplicate key value"))

    app.add_api_route("/api/v1/_boom", boom)
    app.add_api_route("/api/v1/_conflict", conflict)
    return TestClient(app, raise_server_exceptions=False)


def test_request_id_generated_echoed_and_sanitised(client: TestClient) -> None:
    generated = client.get("/api/v1/health").headers["x-request-id"]
    assert len(generated) == 32
    kept = client.get("/api/v1/health", headers={"X-Request-ID": "abc-123.x_y"})
    assert kept.headers["x-request-id"] == "abc-123.x_y"
    injected = client.get("/api/v1/health", headers={"X-Request-ID": "bad id\nwith newline"})
    assert injected.headers["x-request-id"] != "bad id\nwith newline"
    assert len(injected.headers["x-request-id"]) == 32


def test_error_body_carries_request_id(client: TestClient) -> None:
    response = client.get("/api/v1/students/1", headers={"X-Request-ID": "trace-me"})
    assert response.status_code == 401
    assert response.json()["error"]["request_id"] == "trace-me"


def test_unhandled_errors_return_generic_json_500(
    session_factory: sessionmaker[Session], settings: Settings, caplog: pytest.LogCaptureFixture
) -> None:
    client = _boom_app(session_factory, settings)
    with caplog.at_level(logging.ERROR, logger="edupulse.errors"):
        response = client.get("/api/v1/_boom", headers={"X-Request-ID": "req-500"})
    assert response.status_code == 500
    body = response.json()
    assert body == {
        "error": {
            "code": "internal_error",
            "message": "Internal server error",
            "details": None,
            "request_id": "req-500",
        }
    }
    assert "secret internal detail" not in response.text
    assert response.headers["x-request-id"] == "req-500"
    record = next(r for r in caplog.records if r.getMessage() == "unhandled error")
    assert record.exc_info is not None


def test_integrity_errors_become_409_without_db_details(
    session_factory: sessionmaker[Session], settings: Settings
) -> None:
    response = _boom_app(session_factory, settings).get("/api/v1/_conflict")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "conflict"
    assert "duplicate key" not in response.text


def test_security_headers_on_api_and_docs(client: TestClient) -> None:
    api = client.get("/api/v1/health")
    assert api.headers["x-content-type-options"] == "nosniff"
    assert api.headers["x-frame-options"] == "DENY"
    assert api.headers["referrer-policy"] == "no-referrer"
    assert api.headers["content-security-policy"].startswith("default-src 'none'")
    assert api.headers["cache-control"] == "no-store"
    assert "camera=()" in api.headers["permissions-policy"]
    assert "strict-transport-security" not in api.headers

    docs = client.get("/api/v1/docs")
    assert docs.status_code == 200
    assert "cdn.jsdelivr.net" in docs.headers["content-security-policy"]
    assert "cache-control" not in docs.headers


def test_hsts_when_enabled(session_factory: sessionmaker[Session], settings: Settings) -> None:
    settings.hsts = True
    response = _boom_app(session_factory, settings).get("/api/v1/health")
    assert response.headers["strict-transport-security"].startswith("max-age=31536000")


def test_readiness_ok(client: TestClient) -> None:
    response = client.get("/api/v1/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["checks"]["database"] == "ok"
    assert body["checks"]["model"].startswith("ok (v")


def test_readiness_reports_missing_model(
    client: TestClient, settings: Settings, tmp_path: Path
) -> None:
    settings.model_dir = tmp_path
    response = client.get("/api/v1/ready")
    assert response.status_code == 503
    assert response.json()["checks"]["model"] == "unavailable"


def test_readiness_reports_database_failure(settings: Settings) -> None:
    app = create_app(settings)

    class BrokenSession:
        def execute(self, *_args: object) -> None:
            raise ConnectionError("db down")

    app.dependency_overrides[get_db] = lambda: BrokenSession()
    response = TestClient(app).get("/api/v1/ready")
    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "checks": {"database": "unavailable", "model": response.json()["checks"]["model"]},
    }


def test_access_log_is_structured_json(
    client: TestClient, capsys: pytest.CaptureFixture[str]
) -> None:
    configure_logging("INFO", json_output=True)
    capsys.readouterr()
    client.get("/api/v1/health", headers={"X-Request-ID": "log-me"})
    lines = [
        json.loads(line) for line in capsys.readouterr().out.splitlines() if line.startswith("{")
    ]
    access = next(entry for entry in lines if entry.get("logger") == "edupulse.access")
    assert access["request_id"] == "log-me"
    assert access["path"] == "/api/v1/health"
    assert access["status"] == 200
    assert access["method"] == "GET"
    assert isinstance(access["duration_ms"], float)


def test_formatters_include_context_and_exceptions() -> None:
    token = request_id_var.set("ctx-1")
    try:
        try:
            raise ValueError("boom")
        except ValueError:
            record = logging.LogRecord("x", logging.ERROR, __file__, 1, "msg %s", ("a",), None)
            record.exc_info = sys.exc_info()
        record.custom = "field"
        payload = json.loads(JsonFormatter().format(record))
        assert payload["message"] == "msg a"
        assert payload["request_id"] == "ctx-1"
        assert payload["custom"] == "field"
        assert "ValueError: boom" in payload["exception"]
        text = TextFormatter("%(message)s").format(record)
        assert text.startswith("msg a")
        assert "[request_id=ctx-1]" in text
    finally:
        request_id_var.reset(token)
    plain = logging.LogRecord("x", logging.INFO, __file__, 1, "hello", None, None)
    assert TextFormatter("%(message)s").format(plain) == "hello"


def test_configure_logging_is_idempotent() -> None:
    configure_logging("DEBUG", json_output=False)
    configure_logging("INFO", json_output=True)
    ours = [h for h in logging.getLogger().handlers if h.get_name() == "edupulse"]
    assert len(ours) == 1
    assert isinstance(ours[0].formatter, JsonFormatter)
