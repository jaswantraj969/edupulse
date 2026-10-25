"""Student, teacher and staff schemas."""

from datetime import date, datetime
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from app.models.enums import StudentStatus
from app.schemas.common import Code, LongName, LowerEmail, Name, Phone

Email = Annotated[EmailStr, LowerEmail]

MIN_BIRTH_DATE = date(1950, 1, 1)


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


# --- students -------------------------------------------------------------------------------


class StudentFields(_Strict):
    first_name: Name
    last_name: Name
    date_of_birth: date
    email: Email | None = None
    phone: Phone | None = None
    guardian_name: LongName | None = None
    guardian_phone: Phone | None = None
    enrolled_on: date
    status: StudentStatus = StudentStatus.ACTIVE
    prior_failures: int = Field(default=0, ge=0, le=3, description="Past year failures (0-3)")

    @model_validator(mode="after")
    def _dates(self) -> Self:
        check_student_dates(self.date_of_birth, self.enrolled_on)
        return self


def check_student_dates(date_of_birth: date, enrolled_on: date) -> None:
    if not MIN_BIRTH_DATE <= date_of_birth < date.today():
        raise ValueError("date_of_birth must be in the past (after 1950-01-01)")
    if enrolled_on < date_of_birth:
        raise ValueError("enrolled_on cannot be before date_of_birth")


class StudentCreate(StudentFields):
    student_no: Code
    class_id: int | None = Field(default=None, description="Enrol in this class (current year)")


class StudentUpdate(_Strict):
    student_no: Code | None = None
    first_name: Name | None = None
    last_name: Name | None = None
    date_of_birth: date | None = None
    email: Email | None = None
    phone: Phone | None = None
    guardian_name: LongName | None = None
    guardian_phone: Phone | None = None
    enrolled_on: date | None = None
    status: StudentStatus | None = None
    prior_failures: int | None = Field(default=None, ge=0, le=3)
    class_id: int | None = Field(default=None, description="Move to this class (current year)")


class StudentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_no: str
    first_name: str
    last_name: str
    date_of_birth: date
    email: str | None
    phone: str | None
    guardian_name: str | None
    guardian_phone: str | None
    enrolled_on: date
    status: StudentStatus
    prior_failures: int
    class_id: int | None = None
    class_name: str | None = None
    created_at: datetime
    updated_at: datetime


class StudentBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_no: str
    first_name: str
    last_name: str


# --- teachers -------------------------------------------------------------------------------


class TeacherFields(_Strict):
    first_name: Name
    last_name: Name
    email: Email
    phone: Phone | None = None
    hire_date: date
    specialization: Name | None = None
    is_active: bool = True


class TeacherCreate(TeacherFields):
    employee_no: Code


class TeacherUpdate(_Strict):
    employee_no: Code | None = None
    first_name: Name | None = None
    last_name: Name | None = None
    email: Email | None = None
    phone: Phone | None = None
    hire_date: date | None = None
    specialization: Name | None = None
    is_active: bool | None = None


class TeacherRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_no: str
    first_name: str
    last_name: str
    email: str
    phone: str | None
    hire_date: date
    specialization: str | None
    is_active: bool
    has_account: bool = False
    created_at: datetime
    updated_at: datetime


# --- staff ----------------------------------------------------------------------------------


class StaffFields(_Strict):
    first_name: Name
    last_name: Name
    email: Email
    phone: Phone | None = None
    job_title: Name
    department: Name
    hire_date: date
    is_active: bool = True


class StaffCreate(StaffFields):
    employee_no: Code


class StaffUpdate(_Strict):
    employee_no: Code | None = None
    first_name: Name | None = None
    last_name: Name | None = None
    email: Email | None = None
    phone: Phone | None = None
    job_title: Name | None = None
    department: Name | None = None
    hire_date: date | None = None
    is_active: bool | None = None


class StaffRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_no: str
    first_name: str
    last_name: str
    email: str
    phone: str | None
    job_title: str
    department: str
    hire_date: date
    is_active: bool
    created_at: datetime
    updated_at: datetime
