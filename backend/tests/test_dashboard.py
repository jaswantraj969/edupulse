"""Dashboard aggregates and scoping."""

from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models import AttendanceRecord, AttendanceStatus, Grade, TeachingAssignment
from tests import factories as f
from tests.conftest import School

URL = "/api/v1/dashboard"


def _seed_records(db: Session, school: School) -> None:
    days = [date(2025, 9, 8), date(2025, 9, 9), date(2025, 9, 15)]
    statuses = [AttendanceStatus.PRESENT, AttendanceStatus.ABSENT, AttendanceStatus.LATE]
    for day, status in zip(days, statuses, strict=True):
        db.add(
            AttendanceRecord(
                student_id=school.student_b.id, class_id=school.class_b.id, date=day, status=status
            )
        )
    db.add(
        AttendanceRecord(
            student_id=school.student_a.id,
            class_id=school.class_a_homeroom.id,
            date=days[0],
            status=AttendanceStatus.ABSENT,
        )
    )
    assignment = db.scalars(
        select(TeachingAssignment).where(TeachingAssignment.class_id == school.class_b.id)
    ).one()
    assessment = f.make_assessment(db, assignment, assignment.class_group.academic_year.terms[0])
    db.add(Grade(assessment_id=assessment.id, student_id=school.student_b.id, score=Decimal(13)))
    db.commit()


def test_admin_dashboard(client: TestClient, school: School, db: Session) -> None:
    _seed_records(db, school)
    body = client.get(URL, headers=school.headers(school.admin)).json()
    assert body["scope"] == "school"
    assert body["counts"] == {"students": 2, "teachers": 2, "staff": 0, "classes": 3}
    # Week of 2025-09-08: student B present + absent, student A absent -> 1/3 attended.
    assert body["attendance_trend"][0] == {
        "week_start": "2025-09-08",
        "attendance_rate": 0.3333,
        "records": 3,
    }
    assert body["attendance_trend"][1]["attendance_rate"] == 1.0
    buckets = {b["label"]: b["students"] for b in body["grade_distribution"]}
    assert len(buckets) == 10
    assert buckets["60-70"] == 1  # 13/20 = 65 %
    assert body["demo_mode"] is True


def test_dashboard_reports_demo_mode(
    client: TestClient, school: School, settings: Settings
) -> None:
    settings.demo_mode = False
    assert client.get(URL, headers=school.headers(school.admin)).json()["demo_mode"] is False


def test_teacher_dashboard_is_scoped(client: TestClient, school: School, db: Session) -> None:
    _seed_records(db, school)
    body = client.get(URL, headers=school.headers(school.teacher_a)).json()
    assert body["scope"] == "my_classes"
    assert body["counts"]["students"] == 1
    assert body["counts"]["classes"] == 2
    assert [p["records"] for p in body["attendance_trend"]] == [1]
    assert sum(b["students"] for b in body["grade_distribution"]) == 0


def test_dashboard_requires_login(client: TestClient) -> None:
    assert client.get(URL).status_code == 401
