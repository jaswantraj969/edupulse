"""Self sign-up, pending accounts, admin approval and the public meta endpoint."""

from typing import Any

from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.routes.auth import REFRESH_COOKIE
from app.core.config import Settings
from app.models import AccountStatus, AuditAction, AuditLog, Role, Teacher, User
from tests import factories as f
from tests.conftest import School

SIGNUP = "/api/v1/auth/signup"
LOGIN = "/api/v1/auth/login"
ME = "/api/v1/auth/me"
REQUESTS = "/api/v1/account-requests"
META = "/api/v1/meta"
PASSWORD = "Applicant-Pass-42"


def _signup(
    client: TestClient, email: str = "new.teacher@example.org", **extra: str
) -> dict[str, Any]:
    body = {"full_name": "Nora New", "email": email, "password": PASSWORD, **extra}
    response = client.post(SIGNUP, json=body)
    assert response.status_code == 202, response.text
    accepted: dict[str, Any] = response.json()
    return accepted


def _login(client: TestClient, email: str, password: str = PASSWORD) -> dict[str, str]:
    response = client.post(LOGIN, data={"username": email, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _user(db: Session, email: str) -> User:
    db.expire_all()
    user = db.scalar(select(User).where(User.email == email))
    assert user is not None
    return user


def _teacher_b(school: School) -> Teacher:
    teacher = school.class_b.homeroom_teacher
    assert teacher is not None
    return teacher


# --- sign-up ----------------------------------------------------------------------------------


def test_signup_creates_a_pending_account_without_role(
    client: TestClient, db: Session, school: School
) -> None:
    body = _signup(client, "  Nora.New@Example.org ", note=" I teach biology in 10-A ")
    assert "administrator will review" in body["message"]
    user = _user(db, "nora.new@example.org")
    assert user.status == AccountStatus.PENDING
    assert user.role is None
    assert user.teacher_id is None
    assert user.signup_note == "I teach biology in 10-A"
    assert user.hashed_password != PASSWORD


def test_duplicate_email_gets_the_same_response_and_changes_nothing(
    client: TestClient, db: Session, school: School
) -> None:
    existing = school.teacher_a.email
    first = client.post(
        SIGNUP, json={"full_name": "A", "email": "fresh@example.org", "password": PASSWORD}
    )
    duplicate = client.post(
        SIGNUP, json={"full_name": "Imposter", "email": existing, "password": PASSWORD}
    )
    assert (duplicate.status_code, duplicate.json()) == (first.status_code, first.json())
    user = _user(db, existing)
    assert user.full_name != "Imposter"
    assert user.status == AccountStatus.ACTIVE
    # The existing password still works and the applicant's does not.
    assert client.post(LOGIN, data={"username": existing, "password": PASSWORD}).status_code == 401
    _login(client, existing, f.PASSWORD)


def test_signup_validates_without_revealing_accounts(client: TestClient) -> None:
    weak = client.post(
        SIGNUP, json={"full_name": "A", "email": "weak@example.org", "password": "short"}
    )
    assert weak.status_code == 422
    assert "Password" in weak.text
    missing = client.post(SIGNUP, json={"email": "x@example.org", "password": PASSWORD})
    assert missing.status_code == 422
    long_note = client.post(
        SIGNUP,
        json={"full_name": "A", "email": "n@example.org", "password": PASSWORD, "note": "x" * 501},
    )
    assert long_note.status_code == 422


def test_signup_is_rate_limited_per_client(client: TestClient, settings: Settings) -> None:
    for i in range(settings.signup_rate_limit_attempts):
        _signup(client, f"applicant{i}@example.org")
    blocked = client.post(
        SIGNUP, json={"full_name": "A", "email": "late@example.org", "password": PASSWORD}
    )
    assert blocked.status_code == 429
    assert blocked.json()["error"]["message"] == "Too many requests. Try again later."
    assert int(blocked.headers["retry-after"]) >= 1


# --- pending accounts -------------------------------------------------------------------------


def test_pending_account_signs_in_but_every_data_route_is_forbidden(
    client: TestClient, school: School
) -> None:
    _signup(client)
    headers = _login(client, "new.teacher@example.org")
    me = client.get(ME, headers=headers).json()
    assert (me["status"], me["role"]) == ("pending", None)
    for path in (
        "/api/v1/dashboard",
        "/api/v1/students",
        f"/api/v1/students/{school.student_a.id}",
        "/api/v1/students/export",
        "/api/v1/teachers/export",
        "/api/v1/classes",
        f"/api/v1/classes/{school.class_b.id}",
        f"/api/v1/risk/classes/{school.class_b.id}",
        f"/api/v1/risk/classes/{school.class_b.id}/export",
        f"/api/v1/risk/students/{school.student_b.id}",
        "/api/v1/risk/model",
        REQUESTS,
    ):
        response = client.get(path, headers=headers)
        assert response.status_code == 403, path
        assert response.json()["error"]["code"] == "account_pending", path
    # The session itself works: refresh and logout behave normally.
    assert client.post("/api/v1/auth/refresh").status_code == 200
    assert client.post("/api/v1/auth/logout").status_code == 204


# --- administrator review ---------------------------------------------------------------------


def test_admin_lists_pending_requests_and_unlinked_teachers(
    client: TestClient, db: Session, school: School
) -> None:
    _signup(client, "first@example.org", note="Maths, 10-B")
    _signup(client, "second@example.org")
    spare = f.make_teacher(db)
    db.commit()
    admin = school.headers(school.admin)
    listing = client.get(REQUESTS, headers=admin).json()
    assert listing["total"] == 2
    assert [r["email"] for r in listing["items"]] == ["first@example.org", "second@example.org"]
    assert listing["items"][0]["signup_note"] == "Maths, 10-B"
    assert client.get(f"{REQUESTS}/count", headers=admin).json() == {"pending": 2}
    unlinked = client.get(f"{REQUESTS}/unlinked-teachers", headers=admin).json()
    assert [t["id"] for t in unlinked] == [spare.id]  # school teachers all have accounts


def test_approve_as_teacher_grants_exactly_that_teachers_scope(
    client: TestClient, db: Session, school: School
) -> None:
    teacher = f.make_teacher(db)
    own_class = f.make_class(db, school.class_b.academic_year, homeroom=teacher, section="Q")
    pupil = f.make_student(db)
    f.enrol(db, pupil, own_class)
    db.commit()
    _signup(client)
    user = _user(db, "new.teacher@example.org")
    admin = school.headers(school.admin)

    approved = client.post(
        f"{REQUESTS}/{user.id}/approve",
        json={"role": "teacher", "teacher_id": teacher.id},
        headers=admin,
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "active"

    headers = _login(client, "new.teacher@example.org")
    me = client.get(ME, headers=headers).json()
    assert (me["status"], me["role"], me["teacher_id"]) == ("active", "teacher", teacher.id)
    classes = client.get("/api/v1/classes", headers=headers).json()
    assert [c["id"] for c in classes["items"]] == [own_class.id]
    students = client.get("/api/v1/students", headers=headers).json()
    assert [s["id"] for s in students["items"]] == [pupil.id]
    assert client.get(f"/api/v1/classes/{school.class_b.id}", headers=headers).status_code == 403
    assert client.get(f"/api/v1/students/{school.student_b.id}", headers=headers).status_code == 403
    assert client.get(REQUESTS, headers=headers).status_code == 403  # not an admin
    assert client.get("/api/v1/staff", headers=headers).status_code == 403

    entry = db.scalar(select(AuditLog).where(AuditLog.action == AuditAction.ACCOUNT_APPROVE))
    assert entry is not None
    assert (entry.user_id, entry.target_type, entry.target_id) == (school.admin.id, "user", user.id)
    assert entry.detail == "new.teacher@example.org as teacher"
    # A handled request is no longer pending.
    assert client.get(REQUESTS, headers=admin).json()["total"] == 0
    again = client.post(f"{REQUESTS}/{user.id}/approve", json={"role": "admin"}, headers=admin)
    assert again.status_code == 404


def test_approve_as_admin(client: TestClient, db: Session, school: School) -> None:
    _signup(client)
    user = _user(db, "new.teacher@example.org")
    response = client.post(
        f"{REQUESTS}/{user.id}/approve",
        json={"role": "admin"},
        headers=school.headers(school.admin),
    )
    assert response.status_code == 200
    headers = _login(client, "new.teacher@example.org")
    assert client.get("/api/v1/staff", headers=headers).status_code == 200
    assert _user(db, "new.teacher@example.org").reviewed_by_id == school.admin.id


def test_approve_validates_the_teacher_link(
    client: TestClient, db: Session, school: School
) -> None:
    _signup(client)
    user = _user(db, "new.teacher@example.org")
    admin = school.headers(school.admin)
    url = f"{REQUESTS}/{user.id}/approve"
    assert client.post(url, json={"role": "teacher"}, headers=admin).status_code == 422
    assert (
        client.post(url, json={"role": "admin", "teacher_id": 1}, headers=admin).status_code == 422
    )
    unknown = client.post(url, json={"role": "teacher", "teacher_id": 99999}, headers=admin)
    assert unknown.status_code == 422
    linked = client.post(
        url, json={"role": "teacher", "teacher_id": _teacher_b(school).id}, headers=admin
    )
    assert linked.status_code == 409
    assert _user(db, "new.teacher@example.org").status == AccountStatus.PENDING
    assert (
        client.post(f"{REQUESTS}/99999/approve", json={"role": "admin"}, headers=admin).status_code
        == 404
    )


def test_reject_blocks_login_and_revokes_the_session(
    client: TestClient, db: Session, school: School
) -> None:
    _signup(client)
    _login(client, "new.teacher@example.org")
    assert client.cookies.get(REFRESH_COOKIE)
    user = _user(db, "new.teacher@example.org")
    rejected = client.post(
        f"{REQUESTS}/{user.id}/reject",
        json={"reason": "Not on our staff list"},
        headers=school.headers(school.admin),
    )
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"
    assert _user(db, "new.teacher@example.org").review_note == "Not on our staff list"

    login = client.post(LOGIN, data={"username": "new.teacher@example.org", "password": PASSWORD})
    assert login.status_code == 401
    assert login.json()["error"]["message"] == "Incorrect e-mail or password"  # generic
    assert client.post("/api/v1/auth/refresh").status_code == 401

    entry = db.scalar(select(AuditLog).where(AuditLog.action == AuditAction.ACCOUNT_REJECT))
    assert entry is not None
    assert (entry.target_id, entry.detail) == (user.id, "new.teacher@example.org")


def test_non_admins_cannot_review_requests(client: TestClient, db: Session, school: School) -> None:
    _signup(client)
    user = _user(db, "new.teacher@example.org")
    pending = _login(client, "new.teacher@example.org")
    for headers in (school.headers(school.teacher_a), pending, {}):
        expected = 401 if not headers else 403
        for method, path, body in (
            ("get", REQUESTS, None),
            ("get", f"{REQUESTS}/unlinked-teachers", None),
            ("post", f"{REQUESTS}/{user.id}/approve", {"role": "admin"}),
            ("post", f"{REQUESTS}/{user.id}/reject", {}),
        ):
            response = client.request(method, path, json=body, headers=headers)
            assert response.status_code == expected, (path, headers)
    # A pending user cannot approve themselves.
    assert _user(db, "new.teacher@example.org").status == AccountStatus.PENDING
    assert _user(db, "new.teacher@example.org").role is None


def test_existing_accounts_are_active(school: School) -> None:
    assert school.admin.status == AccountStatus.ACTIVE
    assert school.teacher_a.role == Role.TEACHER


# --- public meta ------------------------------------------------------------------------------


def test_meta_shows_demo_accounts_only_in_demo_mode(
    client: TestClient, school: School, settings: Settings
) -> None:
    settings.demo_password = SecretStr("Demo-Password-77")
    settings.demo_mode = True
    body = client.get(META).json()  # public: no token
    assert body["demo_mode"] is True
    accounts = {a["role"]: a for a in body["demo_accounts"]}
    assert accounts["admin"]["email"] == school.admin.email
    # The demo teacher has a homeroom class (so the demo shows their own classes).
    assert accounts["teacher"]["email"] == school.teacher_a.email
    assert {a["password"] for a in accounts.values()} == {"Demo-Password-77"}

    settings.demo_mode = False
    response = client.get(META)
    assert response.json() == {"demo_mode": False, "demo_accounts": []}
    assert "Demo-Password-77" not in response.text
    assert response.headers["cache-control"] == "no-store"


def test_meta_without_demo_password_lists_no_accounts(
    client: TestClient, school: School, settings: Settings
) -> None:
    settings.demo_mode = True
    settings.demo_password = SecretStr("")
    assert client.get(META).json() == {"demo_mode": True, "demo_accounts": []}
