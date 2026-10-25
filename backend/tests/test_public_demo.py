"""Public demo mode: abusable actions are refused, the banner flag, and the periodic reset."""

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import httpx2
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.db.base import Base
from app.demo_reset import reset_demo
from app.models import AccountStatus, AuditAction, AuditLog, RefreshToken, Student, User
from app.seed import SeedConfig, seed
from tests import factories as f
from tests.conftest import School

PASSWORD = "Applicant-Pass-42"
SMALL = SeedConfig(students=30, teachers=8, staff=3, password="Demo-Password-123")

Action = Callable[[TestClient, Session, School], httpx2.Response]


def _csv(client: TestClient, url: str, text: str, school: School) -> httpx2.Response:
    return client.post(
        f"{url}/import",
        files={"file": ("data.csv", text.encode(), "text/csv")},
        headers=school.headers(school.admin),
    )


def _pending_id(client: TestClient, db: Session) -> int:
    client.post(
        "/api/v1/auth/signup",
        json={"full_name": "Ada Applicant", "email": "ada@example.org", "password": PASSWORD},
    )
    db.expire_all()
    user_id = db.scalar(select(User.id).where(User.email == "ada@example.org"))
    assert user_id is not None
    return user_id


def _delete_student(client: TestClient, db: Session, school: School) -> httpx2.Response:
    student = f.make_student(db)
    db.commit()
    return client.delete(f"/api/v1/students/{student.id}", headers=school.headers(school.admin))


def _delete_teacher(client: TestClient, db: Session, school: School) -> httpx2.Response:
    teacher = f.make_teacher(db)
    db.commit()
    return client.delete(f"/api/v1/teachers/{teacher.id}", headers=school.headers(school.admin))


def _delete_staff(client: TestClient, db: Session, school: School) -> httpx2.Response:
    created = client.post(
        "/api/v1/staff",
        json={
            "employee_no": "SX-9",
            "first_name": "Paulo",
            "last_name": "Reis",
            "email": "paulo.reis@edupulse.example",
            "job_title": "Librarian",
            "department": "Library",
            "hire_date": "2018-01-15",
        },
        headers=school.headers(school.admin),
    )
    assert created.status_code == 201, created.text
    return client.delete(
        f"/api/v1/staff/{created.json()['id']}", headers=school.headers(school.admin)
    )


def _delete_class(client: TestClient, db: Session, school: School) -> httpx2.Response:
    empty = f.make_class(db, school.class_b.academic_year, section="Z")
    db.commit()
    return client.delete(f"/api/v1/classes/{empty.id}", headers=school.headers(school.admin))


def _import_students(client: TestClient, db: Session, school: School) -> httpx2.Response:
    header = "student_no,first_name,last_name,date_of_birth,email,enrolled_on,class_name\n"
    return _csv(
        client, "/api/v1/students", header + "IMP-1,Ana,Lopes,2009-01-02,,2024-09-01,\n", school
    )


def _import_teachers(client: TestClient, db: Session, school: School) -> httpx2.Response:
    header = "employee_no,first_name,last_name,email,hire_date,specialization\n"
    row = "TX-1,Ines,Faria,ines.faria@edupulse.example,2019-09-01,Physics\n"
    return _csv(client, "/api/v1/teachers", header + row, school)


def _import_staff(client: TestClient, db: Session, school: School) -> httpx2.Response:
    header = "employee_no,first_name,last_name,email,job_title,department,hire_date\n"
    row = "SX-1,Paulo,Reis,paulo.reis@edupulse.example,Librarian,Library,2018-01-15\n"
    return _csv(client, "/api/v1/staff", header + row, school)


def _approve(client: TestClient, db: Session, school: School) -> httpx2.Response:
    user_id = _pending_id(client, db)
    return client.post(
        f"/api/v1/account-requests/{user_id}/approve",
        json={"role": "admin"},
        headers=school.headers(school.admin),
    )


def _reject(client: TestClient, db: Session, school: School) -> httpx2.Response:
    user_id = _pending_id(client, db)
    return client.post(
        f"/api/v1/account-requests/{user_id}/reject",
        json={"reason": "test"},
        headers=school.headers(school.admin),
    )


def _create_admin(client: TestClient, db: Session, school: School) -> httpx2.Response:
    return client.post(
        "/api/v1/auth/register",
        json={
            "email": "second.admin@edupulse.example",
            "full_name": "Second Admin",
            "password": PASSWORD,
            "role": "admin",
        },
        headers=school.headers(school.admin),
    )


BLOCKED: dict[str, tuple[Action, int]] = {
    "delete student": (_delete_student, 204),
    "delete teacher": (_delete_teacher, 204),
    "delete staff": (_delete_staff, 204),
    "delete class": (_delete_class, 204),
    "import students": (_import_students, 200),
    "import teachers": (_import_teachers, 200),
    "import staff": (_import_staff, 200),
    "approve account": (_approve, 200),
    "reject account": (_reject, 200),
    "create admin user": (_create_admin, 201),
}


@pytest.mark.parametrize("name", list(BLOCKED))
def test_blocked_in_public_demo(
    name: str, client: TestClient, db: Session, school: School, settings: Settings
) -> None:
    settings.public_demo = True
    action, _ = BLOCKED[name]
    response = action(client, db, school)
    assert response.status_code == 403, response.text
    error = response.json()["error"]
    assert error["code"] == "disabled_in_public_demo"
    assert "disabled in the public demo" in error["message"]


@pytest.mark.parametrize("name", list(BLOCKED))
def test_allowed_when_public_demo_is_off(
    name: str, client: TestClient, db: Session, school: School, settings: Settings
) -> None:
    assert settings.public_demo is False  # the default
    action, expected = BLOCKED[name]
    response = action(client, db, school)
    assert response.status_code == expected, response.text


def test_public_demo_still_allows_ordinary_work(
    client: TestClient, db: Session, school: School, settings: Settings
) -> None:
    """Viewing, editing and creating records (and teacher accounts) keep working."""
    settings.public_demo = True
    admin = school.headers(school.admin)
    assert client.get("/api/v1/students", headers=admin).status_code == 200
    patched = client.patch(
        f"/api/v1/students/{school.student_a.id}", json={"first_name": "Renamed"}, headers=admin
    )
    assert patched.status_code == 200
    teacher = f.make_teacher(db)
    db.commit()
    created = client.post(
        "/api/v1/auth/register",
        json={
            "email": teacher.email,
            "full_name": teacher.full_name,
            "password": PASSWORD,
            "role": "teacher",
            "teacher_id": teacher.id,
        },
        headers=admin,
    )
    assert created.status_code == 201, created.text
    # Sign-up still works (the account is removed at the next reset).
    assert (
        client.post(
            "/api/v1/auth/signup",
            json={"full_name": "A", "email": "a@example.org", "password": PASSWORD},
        ).status_code
        == 202
    )


def test_no_endpoint_changes_a_password(client: TestClient) -> None:
    """Passwords are only set when an account is created (sign-up, register); there is no route
    that changes an existing account's password, so demo passwords cannot be changed."""
    schema = client.get("/api/v1/openapi.json").json()
    components = schema["components"]["schemas"]

    def fields(body: dict[str, Any]) -> set[str]:
        names: set[str] = set()
        for media in body.get("content", {}).values():
            ref = media.get("schema", {}).get("$ref", "")
            names |= set(components.get(ref.rsplit("/", 1)[-1], {}).get("properties", {}))
        return names

    sets_password = {
        path
        for path, ops in schema["paths"].items()
        for method, op in ops.items()
        if "password" in fields(op.get("requestBody", {}))
    }
    assert sets_password == {
        "/api/v1/auth/login",  # checks a password, does not set one
        "/api/v1/auth/signup",
        "/api/v1/auth/register",
    }


def test_meta_reports_public_demo(client: TestClient, settings: Settings) -> None:
    body = client.get("/api/v1/meta").json()
    assert (body["public_demo"], body["demo_reset_hours"]) == (False, 6)
    settings.public_demo = True
    settings.demo_reset_hours = 6
    assert client.get("/api/v1/meta").json()["public_demo"] is True


# --- reset ------------------------------------------------------------------------------------


def _snapshot(db: Session) -> dict[str, Any]:
    counts = {
        table.name: db.scalar(select(func.count()).select_from(table))
        for table in Base.metadata.sorted_tables
    }
    return {
        "counts": counts,
        "students": list(db.scalars(select(Student.student_no).order_by(Student.student_no))),
        "users": list(db.scalars(select(User.email).order_by(User.email))),
    }


def test_reset_leaves_exactly_the_seeded_data(session_factory: sessionmaker[Session]) -> None:
    with session_factory() as db:
        seed(db, SMALL)
        db.commit()
        expected = _snapshot(db)

        # A visitor's day: a sign-up, an approval, an audit entry, a session, a new student and
        # a deleted one.
        admin = db.scalars(select(User).where(User.email.startswith("admin@"))).one()
        db.add(
            User(
                email="visitor@example.org",
                full_name="Visitor",
                hashed_password="x",
                role=None,
                status=AccountStatus.PENDING,
            )
        )
        db.add(
            AuditLog(
                user_id=admin.id,
                user_email=admin.email,
                action=AuditAction.ACCOUNT_REJECT,
                target_type="user",
                target_id=1,
            )
        )
        db.add(
            RefreshToken(
                user_id=admin.id, token_hash="0" * 64, expires_at=datetime(2030, 1, 1, tzinfo=UTC)
            )
        )
        f.make_student(db)
        db.commit()
        assert _snapshot(db) != expected

        reset_demo(db, SMALL)
        db.commit()
        assert _snapshot(db) == expected
        assert db.scalar(select(func.count()).select_from(AuditLog)) == 0
        assert db.scalar(select(func.count()).select_from(RefreshToken)) == 0
        assert db.scalar(select(func.count()).where(User.status == AccountStatus.PENDING)) == 0
