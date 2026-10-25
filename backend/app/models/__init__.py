"""ORM models. Importing this package registers every table on ``Base.metadata``."""

from app.models.academic import (
    AcademicYear,
    ClassGroup,
    Enrolment,
    Subject,
    TeachingAssignment,
    Term,
)
from app.models.enums import AssessmentKind, AttendanceStatus, Role, StudentStatus
from app.models.people import Staff, Student, Teacher
from app.models.records import Assessment, AttendanceRecord, Grade
from app.models.user import User

__all__ = [
    "AcademicYear",
    "Assessment",
    "AssessmentKind",
    "AttendanceRecord",
    "AttendanceStatus",
    "ClassGroup",
    "Enrolment",
    "Grade",
    "Role",
    "Staff",
    "Student",
    "StudentStatus",
    "Subject",
    "Teacher",
    "TeachingAssignment",
    "Term",
    "User",
]
