"""Class (section) schemas."""

from pydantic import BaseModel, ConfigDict, Field


class ClassRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    grade_level: int
    section: str
    room: str | None
    academic_year_id: int
    academic_year: str
    homeroom_teacher_id: int | None
    homeroom_teacher_name: str | None
    student_count: int = 0


class ClassCreate(BaseModel):
    academic_year_id: int
    grade_level: int = Field(ge=1, le=13)
    section: str = Field(min_length=1, max_length=5, pattern=r"^[A-Za-z0-9]+$")
    room: str | None = Field(default=None, max_length=20)
    homeroom_teacher_id: int | None = None


class ClassUpdate(BaseModel):
    grade_level: int | None = Field(default=None, ge=1, le=13)
    section: str | None = Field(default=None, min_length=1, max_length=5, pattern=r"^[A-Za-z0-9]+$")
    room: str | None = Field(default=None, max_length=20)
    homeroom_teacher_id: int | None = None
