"""Small helpers that build valid model instances for tests."""

from datetime import date
from decimal import Decimal
from itertools import count

from sqlalchemy.orm import Session

from app.core.passwords import hash_password
from app.models import (
    AcademicYear,
    Assessment,
    AssessmentKind,
    ClassGroup,
    Enrolment,
    Role,
    Student,
    Subject,
    Teacher,
    TeachingAssignment,
    Term,
    User,
)

PASSWORD = "Correct-Horse-9"
_seq = count(1)
_HASH: dict[str, str] = {}


def _password_hash() -> str:
    # argon2 is deliberately slow; hash the shared test password once.
    if "h" not in _HASH:
        _HASH["h"] = hash_password(PASSWORD)
    return _HASH["h"]


def make_year(db: Session, name: str = "2025-2026") -> AcademicYear:
    year = AcademicYear(name=name, start_date=date(2025, 9, 1), end_date=date(2026, 6, 30))
    year.terms = [
        Term(number=1, name="Term 1", start_date=date(2025, 9, 1), end_date=date(2025, 12, 19)),
        Term(number=2, name="Term 2", start_date=date(2026, 1, 5), end_date=date(2026, 3, 27)),
        Term(number=3, name="Term 3", start_date=date(2026, 4, 13), end_date=date(2026, 6, 30)),
    ]
    db.add(year)
    db.flush()
    return year


def make_teacher(db: Session, **kw: object) -> Teacher:
    n = next(_seq)
    teacher = Teacher(
        employee_no=f"T{n:04d}",
        first_name="Tea",
        last_name=f"Cher{n}",
        email=f"teacher{n}@edupulse.example",
        hire_date=date(2020, 1, 1),
        **kw,
    )
    db.add(teacher)
    db.flush()
    return teacher


def make_user(db: Session, role: Role = Role.ADMIN, teacher: Teacher | None = None) -> User:
    n = next(_seq)
    user = User(
        email=teacher.email if teacher else f"admin{n}@edupulse.example",
        hashed_password=_password_hash(),
        full_name=teacher.full_name if teacher else f"Admin {n}",
        role=role,
        teacher=teacher,
    )
    db.add(user)
    db.flush()
    return user


def make_student(db: Session, **kw: object) -> Student:
    n = next(_seq)
    fields: dict[str, object] = {
        "student_no": f"S{n:05d}",
        "first_name": "Stu",
        "last_name": f"Dent{n}",
        "date_of_birth": date(2009, 5, 1),
        "enrolled_on": date(2023, 9, 1),
    }
    fields.update(kw)
    student = Student(**fields)
    db.add(student)
    db.flush()
    return student


def make_subject(db: Session) -> Subject:
    n = next(_seq)
    subject = Subject(code=f"S{n}", name=f"Subject {n}")
    db.add(subject)
    db.flush()
    return subject


def make_class(
    db: Session, year: AcademicYear, homeroom: Teacher | None = None, section: str | None = None
) -> ClassGroup:
    n = next(_seq)
    section = section or f"X{n}"
    class_group = ClassGroup(
        academic_year=year,
        grade_level=10,
        section=section,
        name=f"10-{section}",
        homeroom_teacher=homeroom,
    )
    db.add(class_group)
    db.flush()
    return class_group


def assign(
    db: Session, class_group: ClassGroup, teacher: Teacher, subject: Subject | None = None
) -> TeachingAssignment:
    assignment = TeachingAssignment(
        class_group=class_group, teacher=teacher, subject=subject or make_subject(db)
    )
    db.add(assignment)
    db.flush()
    return assignment


def enrol(db: Session, student: Student, class_group: ClassGroup) -> Enrolment:
    enrolment = Enrolment(
        student_id=student.id,
        class_id=class_group.id,
        academic_year_id=class_group.academic_year_id,
        enrolled_on=date(2025, 9, 1),
    )
    db.add(enrolment)
    db.flush()
    return enrolment


def make_assessment(
    db: Session, assignment: TeachingAssignment, term: Term, max_score: int = 20
) -> Assessment:
    n = next(_seq)
    assessment = Assessment(
        assignment=assignment,
        term=term,
        title=f"Quiz {n}",
        kind=AssessmentKind.QUIZ,
        max_score=Decimal(max_score),
        assessed_on=term.start_date,
    )
    db.add(assessment)
    db.flush()
    return assessment
