"""Role boundaries: admin-only routes and teacher class scoping."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Role
from tests import factories as f
from tests.conftest import ALLOWED_ORIGIN, School

REGISTER = "/api/v1/auth/register"
CLASSES = "/api/v1/classes"


def _new_user(
    teacher_id: int | None = None, role: str = "teacher", **kw: object
) -> dict[str, object]:
    return {
        "email": "new.user@edupulse.example",
        "full_name": "New User",
        "password": "Str0ng-Password",
        "role": role,
        "teacher_id": teacher_id,
        **kw,
    }


def test_admin_can_register_teacher_account(
    client: TestClient, school: School, db: Session
) -> None:
    teacher = f.make_teacher(db)
    db.commit()
    response = client.post(
        REGISTER, json=_new_user(teacher.id), headers=school.headers(school.admin)
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["role"] == "teacher"
    assert body["teacher_id"] == teacher.id
    assert "password" not in body
    assert "hashed_password" not in body


def test_teacher_cannot_register_users(client: TestClient, school: School) -> None:
    payload = _new_user(role="admin")
    response = client.post(REGISTER, json=payload, headers=school.headers(school.teacher_a))
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"


def test_register_requires_authentication(client: TestClient) -> None:
    assert client.post(REGISTER, json=_new_user(role="admin")).status_code == 401


def test_register_duplicate_email_conflicts(client: TestClient, school: School) -> None:
    payload = _new_user(role="admin", email=school.teacher_a.email.upper())
    response = client.post(REGISTER, json=payload, headers=school.headers(school.admin))
    assert response.status_code == 409


def test_register_teacher_already_linked_conflicts(client: TestClient, school: School) -> None:
    payload = _new_user(school.teacher_a.teacher_id)
    response = client.post(REGISTER, json=payload, headers=school.headers(school.admin))
    assert response.status_code == 409


def test_register_unknown_teacher_profile(client: TestClient, school: School) -> None:
    response = client.post(REGISTER, json=_new_user(9999), headers=school.headers(school.admin))
    assert response.status_code == 422


@pytest.mark.parametrize(
    ("overrides", "fragment"),
    [
        ({"password": "short"}, "between"),
        ({"password": "nouppercase123"}, "upper-case"),
        ({"role": "teacher", "teacher_id": None}, "teacher_id is required"),
        ({"role": "admin", "teacher_id": 1}, "cannot be linked"),
        ({"role": "superuser"}, "Input should be"),
        ({"email": "not-an-email"}, "email"),
    ],
)
def test_register_validation(
    client: TestClient, school: School, overrides: dict[str, object], fragment: str
) -> None:
    payload = {**_new_user(role="admin"), **overrides}
    response = client.post(REGISTER, json=payload, headers=school.headers(school.admin))
    assert response.status_code == 422
    body = response.json()["error"]
    assert body["code"] == "validation_error"
    assert any(fragment in d["message"] for d in body["details"]), body


def test_admin_sees_all_classes(client: TestClient, school: School) -> None:
    response = client.get(CLASSES, headers=school.headers(school.admin))
    assert response.status_code == 200
    assert response.json()["total"] == 3


def test_teacher_sees_only_own_classes(client: TestClient, school: School) -> None:
    response = client.get(CLASSES, headers=school.headers(school.teacher_a))
    ids = {c["id"] for c in response.json()["items"]}
    assert ids == {school.class_a_homeroom.id, school.class_a_taught.id}

    response = client.get(CLASSES, headers=school.headers(school.teacher_b))
    assert {c["id"] for c in response.json()["items"]} == {school.class_b.id}


def test_teacher_cannot_open_other_teachers_class(client: TestClient, school: School) -> None:
    own = client.get(
        f"{CLASSES}/{school.class_a_taught.id}", headers=school.headers(school.teacher_a)
    )
    assert own.status_code == 200
    other = client.get(f"{CLASSES}/{school.class_b.id}", headers=school.headers(school.teacher_a))
    assert other.status_code == 403


def test_class_not_found(client: TestClient, school: School) -> None:
    response = client.get(f"{CLASSES}/9999", headers=school.headers(school.admin))
    assert response.status_code == 404
    request_id = response.headers["x-request-id"]
    assert response.json() == {
        "error": {
            "code": "not_found",
            "message": "Class not found",
            "details": None,
            "request_id": request_id,
        }
    }


def test_classes_require_authentication(client: TestClient) -> None:
    assert client.get(CLASSES).status_code == 401


def test_class_list_sort_search_and_paging(client: TestClient, school: School) -> None:
    headers = school.headers(school.admin)
    desc = client.get(CLASSES, params={"sort": "section", "order": "desc"}, headers=headers).json()
    assert [c["section"] for c in desc["items"]] == ["C", "B", "A"]
    assert desc["items"][0]["student_count"] == 1

    page = client.get(CLASSES, params={"page": 2, "page_size": 2}, headers=headers).json()
    assert page["total"] == 3
    assert len(page["items"]) == 1

    found = client.get(CLASSES, params={"q": "10-b"}, headers=headers).json()
    assert [c["section"] for c in found["items"]] == ["B"]

    filtered = client.get(CLASSES, params={"grade_level": 11}, headers=headers).json()
    assert filtered["total"] == 0
    year = client.get(
        CLASSES, params={"academic_year_id": school.class_b.academic_year_id}, headers=headers
    ).json()
    assert year["total"] == 3

    bad = client.get(CLASSES, params={"sort": "password"}, headers=headers)
    assert bad.status_code == 422
    assert "allowed" in bad.json()["error"]["details"]


def test_teacher_role_checked_from_database_not_token(
    client: TestClient, school: School, db: Session
) -> None:
    # A token minted while the user was an admin stops granting admin rights once demoted.
    headers = school.headers(school.admin)
    teacher = f.make_teacher(db)
    school.admin.role = Role.TEACHER
    school.admin.teacher_id = teacher.id
    db.merge(school.admin)
    db.commit()
    assert client.post(REGISTER, json=_new_user(role="admin"), headers=headers).status_code == 403


def test_cors_allows_configured_origin_only(client: TestClient) -> None:
    preflight = {"Access-Control-Request-Method": "GET"}
    allowed = client.options(CLASSES, headers={"Origin": ALLOWED_ORIGIN, **preflight})
    assert allowed.headers["access-control-allow-origin"] == ALLOWED_ORIGIN
    assert allowed.headers["access-control-allow-credentials"] == "true"
    denied = client.options(CLASSES, headers={"Origin": "http://evil.example", **preflight})
    assert "access-control-allow-origin" not in denied.headers
