"""Attendance, assessment, grade and dashboard schemas."""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import AssessmentKind, AttendanceStatus
from app.schemas.common import ShortText

# --- attendance -----------------------------------------------------------------------------


class AttendanceMark(BaseModel):
    model_config = ConfigDict(extra="forbid")

    student_id: int
    status: AttendanceStatus
    note: ShortText | None = None


class AttendanceBulk(BaseModel):
    model_config = ConfigDict(extra="forbid")

    date: date
    records: list[AttendanceMark] = Field(min_length=1, max_length=200)


class AttendanceRow(BaseModel):
    student_id: int
    student_no: str
    first_name: str
    last_name: str
    status: AttendanceStatus | None
    note: str | None


class AttendanceSheet(BaseModel):
    class_id: int
    class_name: str
    date: date
    records: list[AttendanceRow]


class AttendanceMonth(BaseModel):
    month: str = Field(description="YYYY-MM")
    present: int
    absent: int
    late: int
    excused: int


class AttendanceSummary(BaseModel):
    student_id: int
    present: int
    absent: int
    late: int
    excused: int
    total: int
    attendance_rate: float | None = Field(description="(present + late) / total")
    by_month: list[AttendanceMonth]


# --- assessments and grades -------------------------------------------------------------------


class AssessmentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assignment_id: int
    term_id: int
    title: str = Field(min_length=1, max_length=120)
    kind: AssessmentKind
    max_score: Decimal = Field(gt=0, le=1000, decimal_places=2)
    weight: Decimal = Field(default=Decimal(1), gt=0, le=10, decimal_places=2)
    assessed_on: date


class AssessmentUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=1, max_length=120)
    kind: AssessmentKind | None = None
    max_score: Decimal | None = Field(default=None, gt=0, le=1000, decimal_places=2)
    weight: Decimal | None = Field(default=None, gt=0, le=10, decimal_places=2)
    assessed_on: date | None = None


class AssessmentRead(BaseModel):
    id: int
    assignment_id: int
    class_id: int
    subject_id: int
    subject_name: str
    teacher_id: int
    term_id: int
    term_name: str
    title: str
    kind: AssessmentKind
    max_score: float
    weight: float
    assessed_on: date
    graded_count: int = 0


class GradeEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    student_id: int
    score: Decimal = Field(ge=0, decimal_places=2)
    comment: ShortText | None = None


class GradeBulk(BaseModel):
    model_config = ConfigDict(extra="forbid")

    grades: list[GradeEntry] = Field(min_length=1, max_length=200)


class GradeRow(BaseModel):
    student_id: int
    student_no: str
    first_name: str
    last_name: str
    score: float | None
    comment: str | None


class GradeSheet(BaseModel):
    assessment: AssessmentRead
    grades: list[GradeRow]


class StudentGradeRead(BaseModel):
    assessment_id: int
    title: str
    kind: AssessmentKind
    subject_name: str
    term_number: int
    assessed_on: date
    score: float
    max_score: float
    percentage: float


# --- dashboard ------------------------------------------------------------------------------


class DashboardCounts(BaseModel):
    students: int
    teachers: int
    staff: int
    classes: int


class AttendancePoint(BaseModel):
    week_start: date
    attendance_rate: float
    records: int


class GradeBucket(BaseModel):
    label: str = Field(description="Percentage band, e.g. '60-70'")
    students: int


class DashboardSummary(BaseModel):
    scope: str = Field(description="'school' for admins, 'my_classes' for teachers")
    counts: DashboardCounts
    attendance_trend: list[AttendancePoint]
    grade_distribution: list[GradeBucket]
