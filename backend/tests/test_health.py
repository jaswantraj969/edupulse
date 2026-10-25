from fastapi.testclient import TestClient

from app.main import create_app


def test_health_returns_ok() -> None:
    client = TestClient(create_app())
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_openapi_is_served() -> None:
    client = TestClient(create_app())
    assert client.get("/api/v1/openapi.json").json()["info"]["title"] == "EduPulse API"
