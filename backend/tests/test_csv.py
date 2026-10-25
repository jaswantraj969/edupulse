"""CSV import (validation and per-row errors) and export."""

import csv
import io
from typing import Any

import httpx2
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Staff, Student, Teacher
from app.services import csv_io
from tests.conftest import School

STUDENTS = "/api/v1/students"
HEADER = "student_no,first_name,last_name,date_of_birth,email,enrolled_on,class_name\n"


def _upload(
    client: TestClient, url: str, text: str | bytes, headers: dict[str, str], **params: Any
) -> httpx2.Response:
    data = text.encode() if isinstance(text, str) else text
    response: httpx2.Response = client.post(
        f"{url}/import",
        files={"file": ("data.csv", data, "text/csv")},
        params=params,
        headers=headers,
    )
    return response


def _count(db: Session, model: type) -> int:
    return db.scalar(select(func.count()).select_from(model)) or 0


def test_import_students_creates_rows_and_enrols(
    client: TestClient, school: School, db: Session
) -> None:
    text = HEADER + (
        "IMP-1,Ana,Lopes,2009-01-02,ana.lopes@edupulse.example,2024-09-01,10-B\n"
        "IMP-2,Rui,Mota,2009-05-06,,2024-09-01,\n"
    )
    response = _upload(client, STUDENTS, text, school.headers(school.admin))
    assert response.status_code == 200, response.text
    assert response.json() == {"dry_run": False, "total_rows": 2, "created": 2, "errors": []}
    listed = client.get(STUDENTS, params={"q": "IMP-1"}, headers=school.headers(school.admin))
    assert listed.json()["items"][0]["class_name"] == "10-B"


def test_import_dry_run_writes_nothing(client: TestClient, school: School, db: Session) -> None:
    before = _count(db, Student)
    text = HEADER + "IMP-3,Ana,Lopes,2009-01-02,,2024-09-01,\n"
    response = _upload(client, STUDENTS, text, school.headers(school.admin), dry_run=True)
    assert response.status_code == 200
    assert response.json()["dry_run"] is True
    assert response.json()["created"] == 0
    assert _count(db, Student) == before


def test_import_reports_every_row_error_and_writes_nothing(
    client: TestClient, school: School, db: Session
) -> None:
    existing_no = school.student_a.student_no
    text = HEADER + (
        "OK-1,Ana,Lopes,2009-01-02,,2024-09-01,\n"  # line 2: valid
        "OK-1,Ana,Again,2009-01-02,,2024-09-01,\n"  # line 3: duplicate within file
        f"{existing_no},Old,Number,2009-01-02,,2024-09-01,\n"  # line 4: exists in DB
        "BAD-1,Ana,Lopes,not-a-date,,2024-09-01,\n"  # line 5: bad date
        "BAD-2,,Lopes,2009-01-02,bad-email,2024-09-01,\n"  # line 6: two errors
        "BAD-3,Ana,Lopes,2009-01-02,,2024-09-01,99-Z\n"  # line 7: unknown class
        "BAD-4,Ana,Lopes,2009-01-02,,2024-09-01,,extra\n"  # line 8: too many values
    )
    before = _count(db, Student)
    response = _upload(client, STUDENTS, text, school.headers(school.admin))
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "csv_validation_error"
    rows = {(e["row"], e["field"]) for e in error["details"]["errors"]}
    assert (3, "student_no") in rows
    assert (4, "student_no") in rows
    assert (5, "date_of_birth") in rows
    assert (6, "first_name") in rows
    assert (6, "email") in rows
    assert (7, "class_name") in rows
    assert (8, None) in rows
    assert not any(r == 2 for r, _ in rows)
    assert _count(db, Student) == before


def test_import_rejects_bad_header(client: TestClient, school: School) -> None:
    response = _upload(
        client, STUDENTS, "student_no,first_name,shoe_size\nX,Y,42\n", school.headers(school.admin)
    )
    assert response.status_code == 422
    message = response.json()["error"]["message"]
    assert "missing columns" in message
    assert "unknown columns: shoe_size" in message


def test_import_rejects_non_utf8_and_oversized_files(
    client: TestClient, school: School, monkeypatch: pytest.MonkeyPatch
) -> None:
    h = school.headers(school.admin)
    assert _upload(client, STUDENTS, HEADER.encode("utf-16"), h).status_code == 400
    monkeypatch.setattr(csv_io, "MAX_BYTES", 10)
    assert _upload(client, STUDENTS, HEADER, h).status_code == 413


def test_import_rejects_too_many_rows(
    client: TestClient, school: School, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(csv_io, "MAX_ROWS", 1)
    text = HEADER + "A-1,A,B,2009-01-01,,2024-09-01,\n" * 2
    assert _upload(client, STUDENTS, text, school.headers(school.admin)).status_code == 413


def test_import_requires_admin(client: TestClient, school: School) -> None:
    for url in (STUDENTS, "/api/v1/teachers", "/api/v1/staff"):
        assert _upload(client, url, HEADER, school.headers(school.teacher_a)).status_code == 403


def test_export_escapes_formulas_and_round_trips(
    client: TestClient, school: School, db: Session
) -> None:
    h = school.headers(school.admin)
    school.student_a.guardian_name = "=HYPERLINK(evil)"
    school.student_a.phone = "+1-555-0100"
    db.merge(school.student_a)
    db.commit()

    response = client.get(f"{STUDENTS}/export", headers=h)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "attachment" in response.headers["content-disposition"]
    rows = list(csv.DictReader(io.StringIO(response.text)))
    row = next(r for r in rows if r["student_no"] == school.student_a.student_no)
    assert row["guardian_name"] == "'=HYPERLINK(evil)"
    assert row["class_name"] == school.class_a_homeroom.name

    # Re-import the exported file after deleting the students: escaping is undone on import.
    for student in db.scalars(select(Student)).all():
        db.delete(student)
    db.commit()
    reimport = _upload(client, STUDENTS, response.text, h)
    assert reimport.status_code == 200, reimport.text
    restored = db.scalar(select(Student).where(Student.student_no == school.student_a.student_no))
    assert restored is not None
    assert restored.phone == "+1-555-0100"
    assert restored.guardian_name == "=HYPERLINK(evil)"


def test_teacher_export_is_scoped(client: TestClient, school: School) -> None:
    response = client.get(f"{STUDENTS}/export", headers=school.headers(school.teacher_b))
    numbers = [r["student_no"] for r in csv.DictReader(io.StringIO(response.text))]
    assert numbers == [school.student_b.student_no]


def test_teachers_and_staff_import_export(client: TestClient, school: School, db: Session) -> None:
    h = school.headers(school.admin)
    teachers = (
        "employee_no,first_name,last_name,email,hire_date,specialization\n"
        "TX-1,Ines,Faria,ines.faria@edupulse.example,2019-09-01,Physics\n"
    )
    assert _upload(client, "/api/v1/teachers", teachers, h).json()["created"] == 1
    staff = (
        "employee_no,first_name,last_name,email,job_title,department,hire_date\n"
        "SX-1,Paulo,Reis,paulo.reis@edupulse.example,Librarian,Library,2018-01-15\n"
        "SX-2,Rita,Reis,paulo.reis@edupulse.example,Nurse,Health,2018-01-15\n"
    )
    bad = _upload(client, "/api/v1/staff", staff, h)
    assert bad.status_code == 422
    assert bad.json()["error"]["details"]["errors"][0]["row"] == 3
    good = _upload(client, "/api/v1/staff", staff.rsplit("SX-2", 1)[0], h)
    assert good.json()["created"] == 1
    assert _count(db, Staff) == 1

    t_csv = client.get("/api/v1/teachers/export", headers=h).text
    assert "ines.faria@edupulse.example" in t_csv
    assert _count(db, Teacher) == 3
    s_csv = client.get("/api/v1/staff/export", headers=h).text
    assert s_csv.splitlines()[0].startswith("employee_no,")
    assert (
        client.get("/api/v1/staff/export", headers=school.headers(school.teacher_a)).status_code
        == 403
    )


def test_safe_cell() -> None:
    assert csv_io.safe_cell(None) == ""
    assert csv_io.safe_cell("@SUM(A1)") == "'@SUM(A1)"
    assert csv_io.safe_cell("plain") == "plain"
    assert csv_io.safe_cell(3) == "3"


@pytest.mark.parametrize("payload", ["=1+1", "+SUM(A1:A2)", "-2+3", "@cmd", "\tTAB", "\rCR"])
def test_export_neutralises_every_formula_prefix(
    client: TestClient, school: School, db: Session, payload: str
) -> None:
    school.student_a.guardian_name = payload
    db.merge(school.student_a)
    db.commit()
    text = client.get(f"{STUDENTS}/export", headers=school.headers(school.admin)).text
    row = next(
        r
        for r in csv.DictReader(io.StringIO(text))
        if r["student_no"] == school.student_a.student_no
    )
    assert row["guardian_name"] == "'" + payload
    assert csv_io.safe_cell("safe text") == "safe text"
