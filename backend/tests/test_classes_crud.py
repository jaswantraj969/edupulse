"""Class CRUD, enrolments, teaching assignments, subjects and academic years."""

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import TeachingAssignment
from tests import factories as f
from tests.conftest import School

CLASSES = "/api/v1/classes"


def test_class_create_update_delete(client: TestClient, school: School) -> None:
    h = school.headers(school.admin)
    year_id = school.class_b.academic_year_id
    created = client.post(
        CLASSES,
        json={"academic_year_id": year_id, "grade_level": 11, "section": "d", "room": "R2"},
        headers=h,
    )
    assert created.status_code == 201, created.text
    assert created.json()["name"] == "11-D"
    cid = created.json()["id"]

    dup = client.post(
        CLASSES, json={"academic_year_id": year_id, "grade_level": 11, "section": "D"}, headers=h
    )
    assert dup.status_code == 409

    patched = client.patch(
        f"{CLASSES}/{cid}",
        json={"section": "E", "homeroom_teacher_id": school.teacher_b.teacher_id, "room": None},
        headers=h,
    )
    assert patched.json()["name"] == "11-E"
    assert patched.json()["homeroom_teacher_name"] is not None
    assert patched.json()["room"] is None
    clash = client.patch(f"{CLASSES}/{cid}", json={"grade_level": 10, "section": "A"}, headers=h)
    assert clash.status_code == 409

    assert client.delete(f"{CLASSES}/{cid}", headers=h).status_code == 204
    assert client.get(f"{CLASSES}/{cid}", headers=h).status_code == 404


def test_class_create_validation(client: TestClient, school: School) -> None:
    h = school.headers(school.admin)
    year_id = school.class_b.academic_year_id
    bad_year = {"academic_year_id": 999, "grade_level": 11, "section": "A"}
    assert client.post(CLASSES, json=bad_year, headers=h).status_code == 422
    bad_teacher = {
        "academic_year_id": year_id,
        "grade_level": 11,
        "section": "A",
        "homeroom_teacher_id": 999,
    }
    assert client.post(CLASSES, json=bad_teacher, headers=h).status_code == 422
    bad_grade = {"academic_year_id": year_id, "grade_level": 14, "section": "A"}
    assert client.post(CLASSES, json=bad_grade, headers=h).status_code == 422


def test_class_with_students_cannot_be_deleted(client: TestClient, school: School) -> None:
    response = client.delete(f"{CLASSES}/{school.class_b.id}", headers=school.headers(school.admin))
    assert response.status_code == 409


def test_teacher_cannot_manage_classes(client: TestClient, school: School) -> None:
    h = school.headers(school.teacher_a)
    cid = school.class_a_homeroom.id
    body = {"academic_year_id": school.class_b.academic_year_id, "grade_level": 9, "section": "Z"}
    assert client.post(CLASSES, json=body, headers=h).status_code == 403
    assert client.patch(f"{CLASSES}/{cid}", json={"room": "X"}, headers=h).status_code == 403
    assert client.delete(f"{CLASSES}/{cid}", headers=h).status_code == 403
    enrol = {"student_id": school.student_b.id}
    assert client.post(f"{CLASSES}/{cid}/enrolments", json=enrol, headers=h).status_code == 403


def test_roster_and_enrolment_lifecycle(client: TestClient, school: School, db: Session) -> None:
    h = school.headers(school.admin)
    roster = client.get(
        f"{CLASSES}/{school.class_a_homeroom.id}/students", headers=school.headers(school.teacher_a)
    )
    assert [s["id"] for s in roster.json()] == [school.student_a.id]
    forbidden = client.get(
        f"{CLASSES}/{school.class_b.id}/students", headers=school.headers(school.teacher_a)
    )
    assert forbidden.status_code == 403

    newcomer = f.make_student(db)
    db.commit()
    url = f"{CLASSES}/{school.class_a_taught.id}/enrolments"
    enrolled = client.post(url, json={"student_id": newcomer.id}, headers=h)
    assert enrolled.status_code == 201
    assert [s["id"] for s in enrolled.json()] == [newcomer.id]

    again = client.post(
        f"{CLASSES}/{school.class_b.id}/enrolments", json={"student_id": newcomer.id}, headers=h
    )
    assert again.status_code == 409
    assert school.class_a_taught.name in again.json()["error"]["message"]

    assert client.post(url, json={"student_id": 999}, headers=h).status_code == 404
    assert client.delete(f"{url}/{newcomer.id}", headers=h).status_code == 204
    assert client.delete(f"{url}/{newcomer.id}", headers=h).status_code == 404


def test_teaching_assignments(client: TestClient, school: School, db: Session) -> None:
    h = school.headers(school.admin)
    cid = school.class_a_homeroom.id
    subject = f.make_subject(db)
    db.commit()
    url = f"{CLASSES}/{cid}/assignments"
    created = client.post(
        url, json={"subject_id": subject.id, "teacher_id": school.teacher_b.teacher_id}, headers=h
    )
    assert created.status_code == 201
    assert created.json()["subject_name"] == subject.name
    aid = created.json()["id"]

    # Teacher B now teaches in class A, so they can see it.
    listing = client.get(url, headers=school.headers(school.teacher_b))
    assert [a["id"] for a in listing.json()] == [aid]

    dup = client.post(
        url, json={"subject_id": subject.id, "teacher_id": school.teacher_a.teacher_id}, headers=h
    )
    assert dup.status_code == 409
    missing_subject = client.post(url, json={"subject_id": 999, "teacher_id": 1}, headers=h)
    assert missing_subject.status_code == 422
    missing_teacher = client.post(
        url, json={"subject_id": subject.id, "teacher_id": 999}, headers=h
    )
    assert missing_teacher.status_code == 422

    assert client.delete(f"{url}/{aid}", headers=h).status_code == 204
    assert client.delete(f"{url}/{aid}", headers=h).status_code == 404


def test_assignment_with_assessments_cannot_be_deleted(
    client: TestClient, school: School, db: Session
) -> None:
    assignment = db.scalars(
        select(TeachingAssignment).where(TeachingAssignment.class_id == school.class_b.id)
    ).one()
    f.make_assessment(db, assignment, assignment.class_group.academic_year.terms[0])
    db.commit()
    url = f"{CLASSES}/{school.class_b.id}/assignments/{assignment.id}"
    assert client.delete(url, headers=school.headers(school.admin)).status_code == 409


def test_subjects_crud(client: TestClient, school: School) -> None:
    h = school.headers(school.admin)
    created = client.post(
        "/api/v1/subjects", json={"code": "art", "name": "Visual Arts"}, headers=h
    )
    assert created.status_code == 201
    assert created.json()["code"] == "ART"
    sid = created.json()["id"]
    dup = client.post("/api/v1/subjects", json={"code": "ART", "name": "Other"}, headers=h)
    assert dup.status_code == 409
    renamed = client.patch(
        f"/api/v1/subjects/{sid}", json={"name": "Art & Design", "code": "artd"}, headers=h
    )
    assert renamed.json() == {"id": sid, "code": "ARTD", "name": "Art & Design"}
    names = [
        s["name"]
        for s in client.get("/api/v1/subjects", headers=school.headers(school.teacher_a)).json()
    ]
    assert "Art & Design" in names
    teacher_write = client.post(
        "/api/v1/subjects",
        json={"code": "X1", "name": "X"},
        headers=school.headers(school.teacher_a),
    )
    assert teacher_write.status_code == 403
    assert client.delete(f"/api/v1/subjects/{sid}", headers=h).status_code == 204
    assert client.delete(f"/api/v1/subjects/{sid}", headers=h).status_code == 404


def test_subject_in_use_cannot_be_deleted(client: TestClient, school: School, db: Session) -> None:
    assignment = db.scalars(select(TeachingAssignment)).first()
    assert assignment is not None
    response = client.delete(
        f"/api/v1/subjects/{assignment.subject_id}", headers=school.headers(school.admin)
    )
    assert response.status_code == 409


def test_academic_years_listed_with_terms(client: TestClient, school: School) -> None:
    years = client.get("/api/v1/academic-years", headers=school.headers(school.teacher_a)).json()
    assert len(years) == 1
    assert [t["number"] for t in years[0]["terms"]] == [1, 2, 3]
