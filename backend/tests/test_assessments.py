"""Assessments and grade entry permissions and validation."""

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Grade, TeachingAssignment
from tests.conftest import School

ASSESSMENTS = "/api/v1/assessments"


@pytest.fixture
def assignment_b(db: Session, school: School) -> TeachingAssignment:
    return db.scalars(
        select(TeachingAssignment).where(TeachingAssignment.class_id == school.class_b.id)
    ).one()


def _body(assignment: TeachingAssignment, **kw: object) -> dict[str, object]:
    term = assignment.class_group.academic_year.terms[0]
    return {
        "assignment_id": assignment.id,
        "term_id": term.id,
        "title": "Unit test 1",
        "kind": "test",
        "max_score": 20,
        "assessed_on": "2025-10-01",
        **kw,
    }


def _create(client: TestClient, school: School, assignment: TeachingAssignment) -> int:
    response = client.post(
        ASSESSMENTS, json=_body(assignment), headers=school.headers(school.teacher_b)
    )
    assert response.status_code == 201, response.text
    return int(response.json()["id"])


def test_subject_teacher_creates_and_grades(
    client: TestClient, school: School, assignment_b: TeachingAssignment
) -> None:
    h = school.headers(school.teacher_b)
    aid = _create(client, school, assignment_b)

    listing = client.get(f"/api/v1/classes/{school.class_b.id}/assessments", headers=h).json()
    assert [a["id"] for a in listing] == [aid]
    term_id = listing[0]["term_id"]
    filtered = client.get(
        f"/api/v1/classes/{school.class_b.id}/assessments",
        params={"term_id": term_id, "subject_id": assignment_b.subject_id},
        headers=h,
    ).json()
    assert len(filtered) == 1

    sheet = client.get(f"{ASSESSMENTS}/{aid}/grades", headers=h).json()
    assert [g["score"] for g in sheet["grades"]] == [None]

    entry = {"grades": [{"student_id": school.student_b.id, "score": 17.5, "comment": "Good"}]}
    saved = client.put(f"{ASSESSMENTS}/{aid}/grades", json=entry, headers=h)
    assert saved.status_code == 200, saved.text
    assert saved.json()["grades"][0]["score"] == 17.5
    assert saved.json()["assessment"]["graded_count"] == 1

    entry["grades"][0]["score"] = 18
    updated = client.put(f"{ASSESSMENTS}/{aid}/grades", json=entry, headers=h)
    assert updated.json()["grades"][0]["score"] == 18.0
    assert client.get(f"{ASSESSMENTS}/{aid}", headers=h).json()["graded_count"] == 1


def test_score_above_maximum_or_outsider_rejected(
    client: TestClient, school: School, assignment_b: TeachingAssignment, db: Session
) -> None:
    aid = _create(client, school, assignment_b)
    h = school.headers(school.teacher_b)
    too_high = {"grades": [{"student_id": school.student_b.id, "score": 20.5}]}
    response = client.put(f"{ASSESSMENTS}/{aid}/grades", json=too_high, headers=h)
    assert response.status_code == 422
    assert response.json()["error"]["details"] == [
        {"field": "grades.0.score", "message": "Score exceeds maximum of 20.00"}
    ]
    outsider = {"grades": [{"student_id": school.student_a.id, "score": 5}]}
    assert client.put(f"{ASSESSMENTS}/{aid}/grades", json=outsider, headers=h).status_code == 422
    twice = {"grades": [{"student_id": school.student_b.id, "score": 5}] * 2}
    assert client.put(f"{ASSESSMENTS}/{aid}/grades", json=twice, headers=h).status_code == 422
    negative = {"grades": [{"student_id": school.student_b.id, "score": -1}]}
    assert client.put(f"{ASSESSMENTS}/{aid}/grades", json=negative, headers=h).status_code == 422
    assert db.scalars(select(Grade)).all() == []


def test_other_teachers_cannot_create_or_grade(
    client: TestClient, school: School, assignment_b: TeachingAssignment
) -> None:
    other = school.headers(school.teacher_a)
    assert client.post(ASSESSMENTS, json=_body(assignment_b), headers=other).status_code == 403
    aid = _create(client, school, assignment_b)
    entry = {"grades": [{"student_id": school.student_b.id, "score": 5}]}
    assert client.put(f"{ASSESSMENTS}/{aid}/grades", json=entry, headers=other).status_code == 403
    assert client.get(f"{ASSESSMENTS}/{aid}/grades", headers=other).status_code == 403
    assert client.get(f"{ASSESSMENTS}/{aid}", headers=other).status_code == 403
    assert (
        client.patch(f"{ASSESSMENTS}/{aid}", json={"title": "X"}, headers=other).status_code == 403
    )
    assert client.delete(f"{ASSESSMENTS}/{aid}", headers=other).status_code == 403
    listing = client.get(f"/api/v1/classes/{school.class_b.id}/assessments", headers=other)
    assert listing.status_code == 403


def test_homeroom_teacher_can_view_but_not_grade_other_subjects(
    client: TestClient, school: School, db: Session, assignment_b: TeachingAssignment
) -> None:
    # Teacher A is homeroom of class A; give class A a subject taught by teacher B.
    from tests import factories as f

    t_b = assignment_b.teacher
    assignment = f.assign(db, school.class_a_homeroom, t_b)
    db.commit()
    created = client.post(
        ASSESSMENTS, json=_body(assignment), headers=school.headers(school.teacher_b)
    )
    aid = created.json()["id"]
    homeroom = school.headers(school.teacher_a)
    assert client.get(f"{ASSESSMENTS}/{aid}/grades", headers=homeroom).status_code == 200
    entry = {"grades": [{"student_id": school.student_a.id, "score": 5}]}
    assert (
        client.put(f"{ASSESSMENTS}/{aid}/grades", json=entry, headers=homeroom).status_code == 403
    )


def test_assessment_validation(
    client: TestClient, school: School, assignment_b: TeachingAssignment, db: Session
) -> None:
    h = school.headers(school.admin)
    assert (
        client.post(ASSESSMENTS, json=_body(assignment_b, assignment_id=999), headers=h).status_code
        == 422
    )
    assert (
        client.post(ASSESSMENTS, json=_body(assignment_b, term_id=999), headers=h).status_code
        == 422
    )
    outside = client.post(
        ASSESSMENTS, json=_body(assignment_b, assessed_on="2026-02-01"), headers=h
    )
    assert outside.status_code == 422
    assert "within Term 1" in outside.json()["error"]["message"]
    assert (
        client.post(ASSESSMENTS, json=_body(assignment_b, max_score=0), headers=h).status_code
        == 422
    )
    assert (
        client.post(ASSESSMENTS, json=_body(assignment_b, kind="essay"), headers=h).status_code
        == 422
    )

    _create(client, school, assignment_b)
    assert client.post(ASSESSMENTS, json=_body(assignment_b), headers=h).status_code == 409


def test_update_and_delete_assessment(
    client: TestClient, school: School, assignment_b: TeachingAssignment, db: Session
) -> None:
    aid = _create(client, school, assignment_b)
    h = school.headers(school.teacher_b)
    db.add(Grade(assessment_id=aid, student_id=school.student_b.id, score=Decimal(15)))
    db.commit()

    lowered = client.patch(f"{ASSESSMENTS}/{aid}", json={"max_score": 10}, headers=h)
    assert lowered.status_code == 422
    renamed = client.patch(
        f"{ASSESSMENTS}/{aid}", json={"title": "Renamed", "max_score": 25, "weight": 2}, headers=h
    )
    assert renamed.status_code == 200
    assert (renamed.json()["title"], renamed.json()["max_score"]) == ("Renamed", 25.0)
    bad_date = client.patch(f"{ASSESSMENTS}/{aid}", json={"assessed_on": "2026-05-01"}, headers=h)
    assert bad_date.status_code == 422

    second = client.post(ASSESSMENTS, json=_body(assignment_b, title="Second"), headers=h).json()
    clash = client.patch(f"{ASSESSMENTS}/{second['id']}", json={"title": "Renamed"}, headers=h)
    assert clash.status_code == 409

    assert client.delete(f"{ASSESSMENTS}/{aid}", headers=h).status_code == 204
    assert client.get(f"{ASSESSMENTS}/{aid}", headers=h).status_code == 404
    db.expire_all()
    assert db.scalars(select(Grade).where(Grade.assessment_id == aid)).all() == []


def test_unknown_assessment_404(client: TestClient, school: School) -> None:
    h = school.headers(school.admin)
    for method, url in (("get", f"{ASSESSMENTS}/999"), ("get", f"{ASSESSMENTS}/999/grades")):
        assert client.request(method, url, headers=h).status_code == 404
    assert client.get("/api/v1/classes/999/assessments", headers=h).status_code == 404
