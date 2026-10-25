"""Students, teachers and non-teaching staff."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, Date, Index, SmallInteger, String, true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import StudentStatus, str_enum

if TYPE_CHECKING:
    from app.models.academic import ClassGroup, Enrolment, TeachingAssignment
    from app.models.user import User


class PersonMixin:
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100), index=True)
    phone: Mapped[str | None] = mapped_column(String(40))

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


class Teacher(PersonMixin, TimestampMixin, Base):
    __tablename__ = "teachers"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_no: Mapped[str] = mapped_column(String(20), unique=True)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    hire_date: Mapped[date] = mapped_column(Date)
    specialization: Mapped[str | None] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())

    user: Mapped[User | None] = relationship(back_populates="teacher")
    assignments: Mapped[list[TeachingAssignment]] = relationship(back_populates="teacher")
    homeroom_classes: Mapped[list[ClassGroup]] = relationship(back_populates="homeroom_teacher")


class Staff(PersonMixin, TimestampMixin, Base):
    __tablename__ = "staff"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_no: Mapped[str] = mapped_column(String(20), unique=True)
    email: Mapped[str] = mapped_column(String(254), unique=True)
    job_title: Mapped[str] = mapped_column(String(100))
    department: Mapped[str] = mapped_column(String(100), index=True)
    hire_date: Mapped[date] = mapped_column(Date)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())


class Student(PersonMixin, TimestampMixin, Base):
    __tablename__ = "students"
    __table_args__ = (
        CheckConstraint("prior_failures BETWEEN 0 AND 3", name="prior_failures_range"),
        Index("ix_students_name", "last_name", "first_name"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    student_no: Mapped[str] = mapped_column(String(20), unique=True)
    date_of_birth: Mapped[date] = mapped_column(Date)
    email: Mapped[str | None] = mapped_column(String(254), unique=True)
    guardian_name: Mapped[str | None] = mapped_column(String(200))
    guardian_phone: Mapped[str | None] = mapped_column(String(40))
    enrolled_on: Mapped[date] = mapped_column(Date)
    status: Mapped[StudentStatus] = mapped_column(
        str_enum(StudentStatus, "student_status"),
        default=StudentStatus.ACTIVE,
        server_default=StudentStatus.ACTIVE.value,
        index=True,
    )
    # Number of past class (year) failures, capped at 3 — one of the early-warning features.
    prior_failures: Mapped[int] = mapped_column(SmallInteger, default=0, server_default="0")

    enrolments: Mapped[list[Enrolment]] = relationship(
        back_populates="student", cascade="all, delete-orphan"
    )
