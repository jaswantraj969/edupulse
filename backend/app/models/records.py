"""Day-to-day records: attendance, assessments and grades."""

from __future__ import annotations

import datetime as dt
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import AssessmentKind, AttendanceStatus, str_enum

if TYPE_CHECKING:
    from app.models.academic import ClassGroup, TeachingAssignment, Term
    from app.models.people import Student


class AttendanceRecord(TimestampMixin, Base):
    """Daily attendance: one record per student per school day."""

    __tablename__ = "attendance_records"
    __table_args__ = (
        UniqueConstraint("student_id", "date"),
        Index("ix_attendance_class_date", "class_id", "date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"))
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id", ondelete="CASCADE"))
    date: Mapped[dt.date] = mapped_column(Date)
    status: Mapped[AttendanceStatus] = mapped_column(str_enum(AttendanceStatus, "attendance"))
    note: Mapped[str | None] = mapped_column(String(255))
    recorded_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    student: Mapped[Student] = relationship()
    class_group: Mapped[ClassGroup] = relationship()


class Assessment(TimestampMixin, Base):
    """A graded piece of work for one teaching assignment (class + subject) in one term."""

    __tablename__ = "assessments"
    __table_args__ = (
        UniqueConstraint("assignment_id", "term_id", "title"),
        CheckConstraint("max_score > 0", name="max_score_positive"),
        CheckConstraint("weight > 0", name="weight_positive"),
        Index("ix_assessments_assignment_term", "assignment_id", "term_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    assignment_id: Mapped[int] = mapped_column(
        ForeignKey("teaching_assignments.id", ondelete="CASCADE")
    )
    term_id: Mapped[int] = mapped_column(ForeignKey("terms.id", ondelete="RESTRICT"))
    title: Mapped[str] = mapped_column(String(120))
    kind: Mapped[AssessmentKind] = mapped_column(str_enum(AssessmentKind, "assessment_kind"))
    max_score: Mapped[Decimal] = mapped_column(Numeric(6, 2))
    weight: Mapped[Decimal] = mapped_column(Numeric(4, 2), default=Decimal(1), server_default="1")
    assessed_on: Mapped[dt.date] = mapped_column(Date)

    assignment: Mapped[TeachingAssignment] = relationship(back_populates="assessments")
    term: Mapped[Term] = relationship()
    grades: Mapped[list[Grade]] = relationship(
        back_populates="assessment", cascade="all, delete-orphan"
    )


class Grade(TimestampMixin, Base):
    __tablename__ = "grades"
    __table_args__ = (
        UniqueConstraint("assessment_id", "student_id"),
        CheckConstraint("score >= 0", name="score_non_negative"),
        Index("ix_grades_student", "student_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    assessment_id: Mapped[int] = mapped_column(ForeignKey("assessments.id", ondelete="CASCADE"))
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"))
    # Upper bound (score <= assessment.max_score) spans two tables; enforced in the service layer.
    score: Mapped[Decimal] = mapped_column(Numeric(6, 2))
    comment: Mapped[str | None] = mapped_column(String(255))
    recorded_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    assessment: Mapped[Assessment] = relationship(back_populates="grades")
    student: Mapped[Student] = relationship()
