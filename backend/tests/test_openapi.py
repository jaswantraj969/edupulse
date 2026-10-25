"""The OpenAPI document covers the API and every operation is documented."""

from fastapi.testclient import TestClient


def test_every_operation_has_summary_and_tag(client: TestClient) -> None:
    spec = client.get("/api/v1/openapi.json").json()
    operations = [
        (path, method, op)
        for path, methods in spec["paths"].items()
        for method, op in methods.items()
    ]
    assert len(operations) > 40
    for path, method, op in operations:
        assert op.get("summary"), f"{method.upper()} {path} has no summary"
        assert op.get("tags"), f"{method.upper()} {path} has no tag"


def test_key_paths_present_with_error_schema(client: TestClient) -> None:
    spec = client.get("/api/v1/openapi.json").json()
    for path in (
        "/api/v1/auth/login",
        "/api/v1/students",
        "/api/v1/students/import",
        "/api/v1/classes/{class_id}/attendance",
        "/api/v1/assessments/{assessment_id}/grades",
        "/api/v1/dashboard",
    ):
        assert path in spec["paths"], path
    assert "ErrorResponse" in spec["components"]["schemas"]
    responses = spec["paths"]["/api/v1/students/{student_id}"]["get"]["responses"]
    assert {"401", "403", "404"} <= set(responses)
