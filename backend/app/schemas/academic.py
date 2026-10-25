"""Subjects, academic years, teaching assignments and enrolments."""

from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import Name


class SubjectCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=2, max_length=10, pattern=r"^[A-Za-z0-9]+$")
    name: Name


class SubjectUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str | None = Field(default=None, min_length=2, max_length=10, pattern=r"^[A-Za-z0-9]+$")
    name: Name | None = None


class SubjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str


class TermRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    number: int
    name: str
    start_date: date
    end_date: date


class AcademicYearRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    start_date: date
    end_date: date
    terms: list[TermRead]


class AssignmentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subject_id: int
    teacher_id: int


class AssignmentRead(BaseModel):
    id: int
    class_id: int
    class_name: str
    subject_id: int
    subject_code: str
    subject_name: str
    teacher_id: int
    teacher_name: str


class EnrolmentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    student_id: int
