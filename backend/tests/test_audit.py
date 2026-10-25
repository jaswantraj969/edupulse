"""Audit log of risk-score access, risk CSV export and the admin audit listing."""

import csv
import io
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditAction, AuditLog, Grade, TeachingAssignment
from tests import factories as f
from tests.conftest import School

AUDIT = "/api/v1/audit-logs"


def _grade_student_b(db: Session, school: School) -> None:
    assignment = db.scalars(
        select(TeachingAssignment).where(TeachingAssignment.class_id == school.class_b.id)
    ).one()
    quiz = f.make_assessment(db, assignment, assignment.class_group.academic_year.terms[0])
    db.add(Grade(assessment_id=quiz.id, student_id=school.student_b.id, score=Decimal(7)))
    db.commit()


def _entries(db: Session) -> list[AuditLog]:
    db.expire_all()
    return list(db.scalars(select(AuditLog).order_by(AuditLog.id)))


def test_views_and_exports_are_audited(client: TestClient, db: Session, school: School) -> None:
    _grade_student_b(db, school)
    h = school.headers(school.teacher_b)
    client.get(f"/api/v1/risk/classes/{school.class_b.id}", headers=h)
    client.get(f"/api/v1/risk/students/{school.student_b.id}", headers=h)
    client.get(f"/api/v1/risk/classes/{school.class_b.id}/export", headers=h)
    entries = _entries(db)
    assert [e.action for e in entries] == [
        AuditAction.RISK_VIEW_CLASS,
        AuditAction.RISK_VIEW_STUDENT,
        AuditAction.RISK_EXPORT_CLASS,
    ]
    assert {e.user_id for e in entries} == {school.teacher_b.id}
    assert entries[0].user_email == school.teacher_b.email
    assert (entries[0].target_type, entries[0].target_id) == ("class", school.class_b.id)
    assert entries[1].detail == school.student_b.student_no
    assert entries[0].ip_address  # TestClient reports "testclient"


def test_denied_requests_are_not_logged_as_views(
    client: TestClient, db: Session, school: School
) -> None:
    h = school.headers(school.teacher_a)
    assert client.get(f"/api/v1/risk/classes/{school.class_b.id}", headers=h).status_code == 403
    assert (
        client.get(f"/api/v1/risk/classes/{school.class_b.id}/export", headers=h).status_code == 403
    )
    assert _entries(db) == []


def test_export_csv_contents(client: TestClient, db: Session, school: School) -> None:
    _grade_student_b(db, school)
    response = client.get(
        f"/api/v1/risk/classes/{school.class_b.id}/export", headers=school.headers(school.admin)
    )
    assert response.status_code == 200
    assert (
        f'filename="risk-{school.class_b.name}-demo.csv"' in response.headers["content-disposition"]
    )
    rows = list(csv.DictReader(io.StringIO(response.text)))
    assert len(rows) == 1
    row = rows[0]
    assert row["student_no"] == school.student_b.student_no
    assert row["status"] == "scored"
    assert row["band"] in {"high", "medium", "low"}
    assert float(row["term1_average_0_20"]) == 7.0
    assert "Demo" in row["notice"]
    assert "never use this score as an automatic sanction" in row["notice"]


def test_audit_listing_is_admin_only_and_filterable(
    client: TestClient, db: Session, school: School
) -> None:
    _grade_student_b(db, school)
    client.get(
        f"/api/v1/risk/classes/{school.class_b.id}", headers=school.headers(school.teacher_b)
    )
    client.get(f"/api/v1/risk/students/{school.student_b.id}", headers=school.headers(school.admin))

    assert client.get(AUDIT, headers=school.headers(school.teacher_b)).status_code == 403
    assert client.get(AUDIT).status_code == 401

    admin = school.headers(school.admin)
    listing = client.get(AUDIT, headers=admin).json()
    assert listing["total"] == 2
    assert listing["items"][0]["action"] == "risk.view_student"  # newest first by default
    by_action = client.get(AUDIT, params={"action": "risk.view_class"}, headers=admin).json()
    assert [i["user_email"] for i in by_action["items"]] == [school.teacher_b.email]
    by_user = client.get(AUDIT, params={"user_id": school.admin.id}, headers=admin).json()
    assert by_user["total"] == 1
    searched = client.get(AUDIT, params={"q": school.student_b.student_no}, headers=admin).json()
    assert searched["total"] == 1
    oldest = client.get(AUDIT, params={"sort": "created_at", "order": "asc"}, headers=admin).json()
    assert oldest["items"][0]["action"] == "risk.view_class"
    assert client.get(AUDIT, params={"action": "deleted"}, headers=admin).status_code == 422


def test_risk_export_neutralises_formulas(client: TestClient, db: Session, school: School) -> None:
    _grade_student_b(db, school)
    school.student_b.last_name = '=HYPERLINK("http://evil.example")'
    school.student_b.first_name = "@cmd"
    db.merge(school.student_b)
    db.commit()
    response = client.get(
        f"/api/v1/risk/classes/{school.class_b.id}/export", headers=school.headers(school.admin)
    )
    row = next(csv.DictReader(io.StringIO(response.text)))
    assert row["last_name"].startswith("'=")
    assert row["first_name"] == "'@cmd"
