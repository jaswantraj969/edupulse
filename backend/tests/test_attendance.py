"""Bulk attendance marking per class per day."""

from datetime import date, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AttendanceRecord
from tests import factories as f
from tests.conftest import School

DAY = "2025-09-15"


def _url(class_id: int) -> str:
    return f"/api/v1/classes/{class_id}/attendance"


def test_mark_then_read_then_update(client: TestClient, school: School, db: Session) -> None:
    h = school.headers(school.teacher_b)
    url = _url(school.class_b.id)
    blank = client.get(url, params={"date": DAY}, headers=h).json()
    assert [r["status"] for r in blank["records"]] == [None]

    marked = client.put(
        url,
        json={"date": DAY, "records": [{"student_id": school.student_b.id, "status": "absent"}]},
        headers=h,
    )
    assert marked.status_code == 200, marked.text
    assert marked.json()["records"][0]["status"] == "absent"

    corrected = client.put(
        url,
        json={
            "date": DAY,
            "records": [{"student_id": school.student_b.id, "status": "late", "note": "bus"}],
        },
        headers=h,
    )
    assert corrected.json()["records"][0] == {
        "student_id": school.student_b.id,
        "student_no": school.student_b.student_no,
        "first_name": school.student_b.first_name,
        "last_name": school.student_b.last_name,
        "status": "late",
        "note": "bus",
    }
    records = db.scalars(select(AttendanceRecord)).all()
    assert len(records) == 1
    assert records[0].recorded_by_id == school.teacher_b.id


def test_bulk_marks_whole_class(client: TestClient, school: School, db: Session) -> None:
    extra = f.make_student(db)
    f.enrol(db, extra, school.class_b)
    db.commit()
    body = {
        "date": DAY,
        "records": [
            {"student_id": school.student_b.id, "status": "present"},
            {"student_id": extra.id, "status": "excused"},
        ],
    }
    sheet = client.put(_url(school.class_b.id), json=body, headers=school.headers(school.admin))
    assert sorted(r["status"] for r in sheet.json()["records"]) == ["excused", "present"]


def test_teacher_cannot_mark_other_class(client: TestClient, school: School) -> None:
    body = {"date": DAY, "records": [{"student_id": school.student_b.id, "status": "present"}]}
    h = school.headers(school.teacher_a)
    assert client.put(_url(school.class_b.id), json=body, headers=h).status_code == 403
    assert client.get(_url(school.class_b.id), params={"date": DAY}, headers=h).status_code == 403


def test_invalid_rows_rejected(client: TestClient, school: School) -> None:
    h = school.headers(school.admin)
    url = _url(school.class_b.id)
    outsider = {"student_id": school.student_a.id, "status": "present"}
    response = client.put(url, json={"date": DAY, "records": [outsider]}, headers=h)
    assert response.status_code == 422
    assert response.json()["error"]["details"][0]["field"] == "records.0.student_id"

    twice = {"student_id": school.student_b.id, "status": "present"}
    duplicate = client.put(url, json={"date": DAY, "records": [twice, twice]}, headers=h)
    assert duplicate.status_code == 422
    assert duplicate.json()["error"]["details"][0]["message"] == "Duplicate student"

    assert client.put(url, json={"date": DAY, "records": []}, headers=h).status_code == 422
    bad_status = {"student_id": school.student_b.id, "status": "sleeping"}
    assert (
        client.put(url, json={"date": DAY, "records": [bad_status]}, headers=h).status_code == 422
    )


def test_date_must_be_in_year_and_not_future(client: TestClient, school: School) -> None:
    h = school.headers(school.admin)
    record = [{"student_id": school.student_b.id, "status": "present"}]
    future = (date.today() + timedelta(days=1)).isoformat()
    for day in (future, "2024-01-10"):
        response = client.put(
            _url(school.class_b.id), json={"date": day, "records": record}, headers=h
        )
        assert response.status_code == 422


def test_unknown_class_404(client: TestClient, school: School) -> None:
    h = school.headers(school.admin)
    assert client.get(_url(999), params={"date": DAY}, headers=h).status_code == 404
    body = {"date": DAY, "records": [{"student_id": 1, "status": "present"}]}
    assert client.put(_url(999), json=body, headers=h).status_code == 404
