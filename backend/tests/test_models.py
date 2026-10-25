"""Database constraints enforced by the schema itself."""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, StatementError
from sqlalchemy.orm import Session

from app.models import (
    AttendanceRecord,
    AttendanceStatus,
    Enrolment,
    Grade,
    Role,
    Student,
    User,
)
from tests import factories as f


def test_student_number_is_unique(db: Session) -> None:
    f.make_student(db, student_no="DUP1")
    with pytest.raises(IntegrityError):
        f.make_student(db, student_no="DUP1")


def test_prior_failures_must_be_between_0_and_3(db: Session) -> None:
    with pytest.raises(IntegrityError):
        f.make_student(db, prior_failures=4)


def test_invalid_enum_value_rejected(db: Session) -> None:
    with pytest.raises((StatementError, LookupError)):
        f.make_student(db, status="expelled")


def test_teacher_account_requires_teacher_profile(db: Session) -> None:
    db.add(User(email="t@edupulse.example", hashed_password="x", full_name="T", role=Role.TEACHER))
    with pytest.raises(IntegrityError):
        db.flush()


def test_student_has_at_most_one_class_per_year(db: Session) -> None:
    year = f.make_year(db)
    a, b = f.make_class(db, year), f.make_class(db, year)
    student = f.make_student(db)
    f.enrol(db, student, a)
    with pytest.raises(IntegrityError):
        f.enrol(db, student, b)


def test_enrolment_year_must_match_class_year(db: Session) -> None:
    year, other_year = f.make_year(db), f.make_year(db, "2026-2027")
    class_group = f.make_class(db, year)
    student = f.make_student(db)
    db.add(
        Enrolment(
            student_id=student.id,
            class_id=class_group.id,
            academic_year_id=other_year.id,
            enrolled_on=date(2025, 9, 1),
        )
    )
    with pytest.raises(IntegrityError):
        db.flush()


def test_one_attendance_record_per_student_per_day(db: Session) -> None:
    year = f.make_year(db)
    class_group = f.make_class(db, year)
    student = f.make_student(db)
    for _ in range(2):
        db.add(
            AttendanceRecord(
                student_id=student.id,
                class_id=class_group.id,
                date=date(2025, 9, 8),
                status=AttendanceStatus.PRESENT,
            )
        )
    with pytest.raises(IntegrityError):
        db.flush()


def test_one_grade_per_student_per_assessment_and_non_negative(db: Session) -> None:
    year = f.make_year(db)
    class_group = f.make_class(db, year)
    assignment = f.assign(db, class_group, f.make_teacher(db))
    assessment = f.make_assessment(db, assignment, year.terms[0])
    student = f.make_student(db)
    db.add(Grade(assessment_id=assessment.id, student_id=student.id, score=Decimal(-1)))
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()

    db.add(Grade(assessment_id=assessment.id, student_id=student.id, score=Decimal(5)))
    db.add(Grade(assessment_id=assessment.id, student_id=student.id, score=Decimal(6)))
    with pytest.raises(IntegrityError):
        db.flush()


def test_class_section_unique_within_year(db: Session) -> None:
    year = f.make_year(db)
    f.make_class(db, year, section="A")
    with pytest.raises(IntegrityError):
        f.make_class(db, year, section="A")


def test_deleting_student_cascades_to_records(db: Session) -> None:
    year = f.make_year(db)
    class_group = f.make_class(db, year)
    student = f.make_student(db)
    f.enrol(db, student, class_group)
    db.add(
        AttendanceRecord(
            student_id=student.id,
            class_id=class_group.id,
            date=date(2025, 9, 8),
            status=AttendanceStatus.ABSENT,
        )
    )
    db.flush()
    db.delete(student)
    db.flush()
    db.expire_all()
    assert db.scalars(select(AttendanceRecord)).all() == []
    assert db.scalars(select(Enrolment)).all() == []
    assert db.scalars(select(Student)).all() == []


def test_full_name_property(db: Session) -> None:
    student = f.make_student(db, first_name="Ana", last_name="Silva")
    assert student.full_name == "Ana Silva"
