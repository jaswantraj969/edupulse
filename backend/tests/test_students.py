"""Student CRUD, listing, scoping and per-student records."""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AttendanceRecord, AttendanceStatus, Enrolment, Grade, TeachingAssignment
from tests import factories as f
from tests.conftest import School

URL = "/api/v1/students"


def _payload(**kw: object) -> dict[str, object]:
    base: dict[str, object] = {
        "student_no": "ST-9001",
        "first_name": " Maria ",
        "last_name": "Costa",
        "date_of_birth": "2009-03-14",
        "email": "Maria.Costa@Edupulse.Example",
        "enrolled_on": "2023-09-01",
        "prior_failures": 1,
    }
    base.update(kw)
    return base


def test_admin_creates_reads_updates_and_deletes_student(
    client: TestClient, school: School
) -> None:
    h = school.headers(school.admin)
    created = client.post(URL, json=_payload(class_id=school.class_b.id), headers=h)
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["first_name"] == "Maria"  # whitespace stripped
    assert body["email"] == "maria.costa@edupulse.example"  # normalised
    assert body["class_name"] == school.class_b.name
    assert body["status"] == "active"
    sid = body["id"]

    assert client.get(f"{URL}/{sid}", headers=h).json()["student_no"] == "ST-9001"

    moved = client.patch(
        f"{URL}/{sid}",
        json={"last_name": "Costa Silva", "class_id": school.class_a_homeroom.id},
        headers=h,
    )
    assert moved.status_code == 200
    assert moved.json()["last_name"] == "Costa Silva"
    assert moved.json()["class_id"] == school.class_a_homeroom.id

    assert client.delete(f"{URL}/{sid}", headers=h).status_code == 204
    assert client.get(f"{URL}/{sid}", headers=h).status_code == 404


def test_create_without_class_then_enrol_via_update(client: TestClient, school: School) -> None:
    h = school.headers(school.admin)
    sid = client.post(URL, json=_payload(), headers=h).json()["id"]
    assert client.get(f"{URL}/{sid}", headers=h).json()["class_id"] is None
    response = client.patch(f"{URL}/{sid}", json={"class_id": school.class_b.id}, headers=h)
    assert response.json()["class_name"] == school.class_b.name


def test_teacher_cannot_write_students(client: TestClient, school: School) -> None:
    h = school.headers(school.teacher_a)
    sid = school.student_a.id
    assert client.post(URL, json=_payload(), headers=h).status_code == 403
    assert client.patch(f"{URL}/{sid}", json={"last_name": "X"}, headers=h).status_code == 403
    assert client.delete(f"{URL}/{sid}", headers=h).status_code == 403


def test_teacher_sees_only_students_in_own_classes(client: TestClient, school: School) -> None:
    h = school.headers(school.teacher_a)
    listed = client.get(URL, headers=h).json()
    assert [s["id"] for s in listed["items"]] == [school.student_a.id]
    assert client.get(f"{URL}/{school.student_a.id}", headers=h).status_code == 200
    assert client.get(f"{URL}/{school.student_b.id}", headers=h).status_code == 403
    for sub in ("attendance", "grades"):
        assert client.get(f"{URL}/{school.student_b.id}/{sub}", headers=h).status_code == 403


def test_missing_student_is_404(client: TestClient, school: School) -> None:
    h = school.headers(school.admin)
    assert client.get(f"{URL}/9999", headers=h).status_code == 404
    assert client.patch(f"{URL}/9999", json={"last_name": "X"}, headers=h).status_code == 404
    assert client.delete(f"{URL}/9999", headers=h).status_code == 404
    assert client.get(f"{URL}/9999/attendance", headers=h).status_code == 404


def test_duplicate_student_number_or_email_conflicts(client: TestClient, school: School) -> None:
    h = school.headers(school.admin)
    first = client.post(URL, json=_payload(), headers=h).json()
    dup_no = client.post(URL, json=_payload(email=None), headers=h)
    assert dup_no.status_code == 409
    assert dup_no.json()["error"]["details"] == {"field": "student_no"}
    dup_mail = client.post(URL, json=_payload(student_no="ST-9002"), headers=h)
    assert dup_mail.status_code == 409

    other = client.post(URL, json=_payload(student_no="ST-9003", email=None), headers=h).json()
    clash = client.patch(f"{URL}/{other['id']}", json={"student_no": "ST-9001"}, headers=h)
    assert clash.status_code == 409
    # Updating a record with its own unique values is not a conflict.
    same = client.patch(f"{URL}/{first['id']}", json={"student_no": "ST-9001"}, headers=h)
    assert same.status_code == 200


@pytest.mark.parametrize(
    ("overrides", "fragment"),
    [
        ({"date_of_birth": (date.today() + timedelta(days=1)).isoformat()}, "in the past"),
        ({"enrolled_on": "2000-01-01"}, "before date_of_birth"),
        ({"prior_failures": 4}, "less than or equal to 3"),
        ({"student_no": "bad no!"}, "pattern"),
        ({"first_name": "  "}, "at least 1 character"),
        ({"phone": "call me"}, "pattern"),
        ({"status": "expelled"}, "Input should be"),
        ({"unexpected": 1}, "Extra inputs"),
    ],
)
def test_create_validation_errors(
    client: TestClient, school: School, overrides: dict[str, object], fragment: str
) -> None:
    response = client.post(URL, json=_payload(**overrides), headers=school.headers(school.admin))
    assert response.status_code == 422
    messages = [d["message"] for d in response.json()["error"]["details"]]
    assert any(fragment in m for m in messages), messages


def test_update_cannot_break_date_order(client: TestClient, school: School) -> None:
    h = school.headers(school.admin)
    sid = school.student_a.id
    response = client.patch(f"{URL}/{sid}", json={"enrolled_on": "1990-01-01"}, headers=h)
    assert response.status_code == 422


def test_unknown_class_on_create_is_404(client: TestClient, school: School) -> None:
    response = client.post(URL, json=_payload(class_id=9999), headers=school.headers(school.admin))
    assert response.status_code == 404


def test_list_filters_search_sort_and_pagination(
    client: TestClient, school: School, db: Session
) -> None:
    h = school.headers(school.admin)
    f.make_student(db, first_name="Zoe", last_name="Almeida", status="withdrawn")
    db.commit()

    everyone = client.get(URL, headers=h).json()
    assert everyone["total"] == 3
    assert everyone["items"][0]["last_name"] == "Almeida"  # default sort: last_name asc

    assert client.get(URL, params={"q": "zoe"}, headers=h).json()["total"] == 1
    assert client.get(URL, params={"status": "withdrawn"}, headers=h).json()["total"] == 1
    by_class = client.get(URL, params={"class_id": school.class_b.id}, headers=h).json()
    assert [s["id"] for s in by_class["items"]] == [school.student_b.id]
    assert client.get(URL, params={"grade_level": 10}, headers=h).json()["total"] == 2

    desc = client.get(URL, params={"sort": "student_no", "order": "desc"}, headers=h).json()
    numbers = [s["student_no"] for s in desc["items"]]
    assert numbers == sorted(numbers, reverse=True)
    by_class_name = client.get(URL, params={"sort": "class_name"}, headers=h)
    assert by_class_name.status_code == 200

    page = client.get(URL, params={"page": 2, "page_size": 2}, headers=h).json()
    assert (page["page"], page["page_size"], len(page["items"])) == (2, 2, 1)

    assert client.get(URL, params={"page": 0}, headers=h).status_code == 422
    assert client.get(URL, params={"page_size": 101}, headers=h).status_code == 422
    assert client.get(URL, params={"sort": "hashed_password"}, headers=h).status_code == 422


def test_delete_student_removes_their_records(
    client: TestClient, school: School, db: Session
) -> None:
    sid = school.student_a.id
    db.add(
        AttendanceRecord(
            student_id=sid,
            class_id=school.class_a_homeroom.id,
            date=date(2025, 9, 8),
            status=AttendanceStatus.PRESENT,
        )
    )
    db.commit()
    assert client.delete(f"{URL}/{sid}", headers=school.headers(school.admin)).status_code == 204
    db.expire_all()
    assert (
        db.scalars(select(AttendanceRecord).where(AttendanceRecord.student_id == sid)).all() == []
    )
    assert db.scalars(select(Enrolment).where(Enrolment.student_id == sid)).all() == []


def test_student_attendance_summary(client: TestClient, school: School, db: Session) -> None:
    sid = school.student_b.id
    statuses = [
        (date(2025, 9, 8), AttendanceStatus.PRESENT),
        (date(2025, 9, 9), AttendanceStatus.ABSENT),
        (date(2025, 9, 10), AttendanceStatus.LATE),
        (date(2025, 10, 1), AttendanceStatus.EXCUSED),
    ]
    for day, status in statuses:
        db.add(
            AttendanceRecord(student_id=sid, class_id=school.class_b.id, date=day, status=status)
        )
    db.commit()
    body = client.get(f"{URL}/{sid}/attendance", headers=school.headers(school.teacher_b)).json()
    assert (body["present"], body["absent"], body["late"], body["excused"]) == (1, 1, 1, 1)
    assert body["total"] == 4
    assert body["attendance_rate"] == 0.5
    assert [m["month"] for m in body["by_month"]] == ["2025-09", "2025-10"]

    empty = client.get(
        f"{URL}/{school.student_a.id}/attendance", headers=school.headers(school.admin)
    ).json()
    assert empty["total"] == 0
    assert empty["attendance_rate"] is None


def test_student_grades(client: TestClient, school: School, db: Session) -> None:
    assignment = db.scalars(
        select(TeachingAssignment).where(TeachingAssignment.class_id == school.class_b.id)
    ).one()
    term = assignment.class_group.academic_year.terms[0]
    assessment = f.make_assessment(db, assignment, term, max_score=20)
    db.add(Grade(assessment_id=assessment.id, student_id=school.student_b.id, score=Decimal(15)))
    db.commit()
    body = client.get(
        f"{URL}/{school.student_b.id}/grades", headers=school.headers(school.teacher_b)
    ).json()
    assert len(body) == 1
    assert body[0]["percentage"] == 75.0
    assert body[0]["term_number"] == 1
