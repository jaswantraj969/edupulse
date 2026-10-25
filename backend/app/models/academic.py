"""Academic structure: years, terms, subjects, classes, teaching assignments, enrolments."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Date,
    ForeignKey,
    ForeignKeyConstraint,
    SmallInteger,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.people import Student, Teacher
    from app.models.records import Assessment


class AcademicYear(TimestampMixin, Base):
    __tablename__ = "academic_years"
    __table_args__ = (CheckConstraint("start_date < end_date", name="dates_ordered"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(20), unique=True)
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)

    terms: Mapped[list[Term]] = relationship(
        back_populates="academic_year", order_by="Term.number", cascade="all, delete-orphan"
    )


class Term(TimestampMixin, Base):
    __tablename__ = "terms"
    __table_args__ = (
        UniqueConstraint("academic_year_id", "number"),
        CheckConstraint("number BETWEEN 1 AND 4", name="number_range"),
        CheckConstraint("start_date < end_date", name="dates_ordered"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    academic_year_id: Mapped[int] = mapped_column(
        ForeignKey("academic_years.id", ondelete="CASCADE")
    )
    number: Mapped[int] = mapped_column(SmallInteger)
    name: Mapped[str] = mapped_column(String(50))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)

    academic_year: Mapped[AcademicYear] = relationship(back_populates="terms")


class Subject(TimestampMixin, Base):
    __tablename__ = "subjects"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(10), unique=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)


class ClassGroup(TimestampMixin, Base):
    """A class/section for one academic year, e.g. grade 10 section B ("10-B")."""

    __tablename__ = "classes"
    __table_args__ = (
        UniqueConstraint("academic_year_id", "grade_level", "section"),
        # Target for the composite foreign key on enrolments.
        UniqueConstraint("id", "academic_year_id", name="uq_classes_id_year"),
        CheckConstraint("grade_level BETWEEN 1 AND 13", name="grade_level_range"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    academic_year_id: Mapped[int] = mapped_column(
        ForeignKey("academic_years.id", ondelete="RESTRICT"), index=True
    )
    grade_level: Mapped[int] = mapped_column(SmallInteger)
    section: Mapped[str] = mapped_column(String(5))
    name: Mapped[str] = mapped_column(String(50))
    room: Mapped[str | None] = mapped_column(String(20))
    homeroom_teacher_id: Mapped[int | None] = mapped_column(
        ForeignKey("teachers.id", ondelete="SET NULL"), index=True
    )

    academic_year: Mapped[AcademicYear] = relationship()
    homeroom_teacher: Mapped[Teacher | None] = relationship(back_populates="homeroom_classes")
    assignments: Mapped[list[TeachingAssignment]] = relationship(
        back_populates="class_group", cascade="all, delete-orphan"
    )
    enrolments: Mapped[list[Enrolment]] = relationship(
        back_populates="class_group",
        cascade="all, delete-orphan",
    )


class TeachingAssignment(TimestampMixin, Base):
    """A teacher teaching one subject to one class."""

    __tablename__ = "teaching_assignments"
    __table_args__ = (UniqueConstraint("class_id", "subject_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id", ondelete="CASCADE"))
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id", ondelete="RESTRICT"))
    teacher_id: Mapped[int] = mapped_column(
        ForeignKey("teachers.id", ondelete="RESTRICT"), index=True
    )

    class_group: Mapped[ClassGroup] = relationship(back_populates="assignments")
    subject: Mapped[Subject] = relationship()
    teacher: Mapped[Teacher] = relationship(back_populates="assignments")
    assessments: Mapped[list[Assessment]] = relationship(
        back_populates="assignment", cascade="all, delete-orphan"
    )


class Enrolment(TimestampMixin, Base):
    """A student's membership of a class. At most one class per student per academic year."""

    __tablename__ = "enrolments"
    __table_args__ = (
        UniqueConstraint("student_id", "academic_year_id"),
        ForeignKeyConstraint(
            ["class_id", "academic_year_id"],
            ["classes.id", "classes.academic_year_id"],
            ondelete="CASCADE",
            name="fk_enrolments_class_year",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"))
    class_id: Mapped[int] = mapped_column(index=True)
    academic_year_id: Mapped[int] = mapped_column()
    enrolled_on: Mapped[date] = mapped_column(Date)

    student: Mapped[Student] = relationship(back_populates="enrolments")
    class_group: Mapped[ClassGroup] = relationship(back_populates="enrolments")
