"""ORM models. Importing this package registers every table on ``Base.metadata``."""

from app.models.academic import (
    AcademicYear,
    ClassGroup,
    Enrolment,
    Subject,
    TeachingAssignment,
    Term,
)
from app.models.audit import AuditAction, AuditLog
from app.models.auth import RefreshToken
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
    "AuditAction",
    "AuditLog",
    "ClassGroup",
    "Enrolment",
    "Grade",
    "RefreshToken",
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
