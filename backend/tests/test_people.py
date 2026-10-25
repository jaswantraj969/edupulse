"""Teacher and staff CRUD."""

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User
from tests import factories as f
from tests.conftest import School

TEACHERS = "/api/v1/teachers"
STAFF = "/api/v1/staff"


def _teacher(**kw: object) -> dict[str, object]:
    return {
        "employee_no": "TCH-900",
        "first_name": "Joana",
        "last_name": "Pires",
        "email": "joana.pires@edupulse.example",
        "hire_date": "2018-09-01",
        "specialization": "History",
        **kw,
    }


def _staff(**kw: object) -> dict[str, object]:
    return {
        "employee_no": "STF-900",
        "first_name": "Luis",
        "last_name": "Matos",
        "email": "luis.matos@edupulse.example",
        "job_title": "Librarian",
        "department": "Library",
        "hire_date": "2017-01-10",
        **kw,
    }


def test_teacher_crud(client: TestClient, school: School) -> None:
    h = school.headers(school.admin)
    created = client.post(TEACHERS, json=_teacher(), headers=h)
    assert created.status_code == 201
    tid = created.json()["id"]
    assert created.json()["has_account"] is False

    updated = client.patch(f"{TEACHERS}/{tid}", json={"is_active": False}, headers=h)
    assert updated.json()["is_active"] is False
    assert client.get(TEACHERS, params={"is_active": False}, headers=h).json()["total"] == 1
    assert (
        client.get(TEACHERS, params={"specialization": "History"}, headers=h).json()["total"] == 1
    )
    assert client.get(TEACHERS, params={"q": "joana"}, headers=h).json()["total"] == 1

    assert client.delete(f"{TEACHERS}/{tid}", headers=h).status_code == 204
    assert client.get(f"{TEACHERS}/{tid}", headers=h).status_code == 404


def test_teacher_directory_readable_by_teachers_but_not_writable(
    client: TestClient, school: School
) -> None:
    h = school.headers(school.teacher_a)
    listing = client.get(TEACHERS, params={"sort": "employee_no"}, headers=h)
    assert listing.status_code == 200
    assert listing.json()["total"] == 2
    assert all(t["has_account"] for t in listing.json()["items"])
    assert client.get(f"{TEACHERS}/{school.teacher_b.teacher_id}", headers=h).status_code == 200
    assert client.post(TEACHERS, json=_teacher(), headers=h).status_code == 403
    tid = school.teacher_b.teacher_id
    assert client.patch(f"{TEACHERS}/{tid}", json={"phone": "123456"}, headers=h).status_code == 403
    assert client.delete(f"{TEACHERS}/{tid}", headers=h).status_code == 403
    assert client.get(f"{TEACHERS}/export", headers=h).status_code == 403


def test_teacher_conflicts(client: TestClient, school: School) -> None:
    h = school.headers(school.admin)
    client.post(TEACHERS, json=_teacher(), headers=h)
    assert (
        client.post(TEACHERS, json=_teacher(email="x@edupulse.example"), headers=h).status_code
        == 409
    )
    assert client.post(TEACHERS, json=_teacher(employee_no="TCH-901"), headers=h).status_code == 409
    other = school.teacher_a.teacher_id
    clash = client.patch(f"{TEACHERS}/{other}", json={"employee_no": "TCH-900"}, headers=h)
    assert clash.status_code == 409


def test_teacher_with_assignments_cannot_be_deleted(client: TestClient, school: School) -> None:
    response = client.delete(
        f"{TEACHERS}/{school.teacher_b.teacher_id}", headers=school.headers(school.admin)
    )
    assert response.status_code == 409
    assert "assignments" in response.json()["error"]["message"]


def test_deleting_teacher_removes_login_account(
    client: TestClient, school: School, db: Session
) -> None:
    teacher = f.make_teacher(db)
    user_id = f.make_user(db, teacher=teacher).id
    db.commit()
    assert (
        client.delete(f"{TEACHERS}/{teacher.id}", headers=school.headers(school.admin)).status_code
        == 204
    )
    db.expire_all()
    assert db.scalar(select(User).where(User.id == user_id)) is None


def test_teacher_validation_and_not_found(client: TestClient, school: School) -> None:
    h = school.headers(school.admin)
    assert client.post(TEACHERS, json=_teacher(email="nope"), headers=h).status_code == 422
    assert client.post(TEACHERS, json=_teacher(hire_date="soon"), headers=h).status_code == 422
    assert client.patch(f"{TEACHERS}/999", json={"phone": "123456"}, headers=h).status_code == 404
    assert client.delete(f"{TEACHERS}/999", headers=h).status_code == 404


def test_staff_crud_is_admin_only(client: TestClient, school: School) -> None:
    h = school.headers(school.admin)
    created = client.post(STAFF, json=_staff(), headers=h)
    assert created.status_code == 201
    sid = created.json()["id"]
    assert client.get(f"{STAFF}/{sid}", headers=h).json()["department"] == "Library"
    assert (
        client.patch(f"{STAFF}/{sid}", json={"job_title": "Head Librarian"}, headers=h).json()[
            "job_title"
        ]
        == "Head Librarian"
    )
    listing = client.get(
        STAFF, params={"department": "Library", "is_active": True, "q": "luis"}, headers=h
    )
    assert listing.json()["total"] == 1
    assert client.post(STAFF, json=_staff(employee_no="STF-901"), headers=h).status_code == 409

    teacher = school.headers(school.teacher_a)
    assert client.get(STAFF, headers=teacher).status_code == 403
    assert client.get(f"{STAFF}/{sid}", headers=teacher).status_code == 403
    assert (
        client.post(STAFF, json=_staff(employee_no="STF-902"), headers=teacher).status_code == 403
    )

    assert client.delete(f"{STAFF}/{sid}", headers=h).status_code == 204
    assert client.get(f"{STAFF}/{sid}", headers=h).status_code == 404
