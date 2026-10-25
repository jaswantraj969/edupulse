"""Synthetic demo data generator.

ALL DATA PRODUCED HERE IS SYNTHETIC. Names come from Faker with a fixed seed, e-mail addresses use
the reserved ``.example`` domain and phone numbers use the fictional ``555-01xx`` range. No real
person's data is used.

Usage::

    python -m app.seed            # refuses to run if the database already has data
    python -m app.seed --reset    # deletes existing data first

The demo password for every account is read from ``EDUPULSE_DEMO_PASSWORD``; the script refuses
to run if it is empty, a known default, or does not meet the password policy.
"""

from __future__ import annotations

import argparse
import math
import os
import random
import unicodedata
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from faker import Faker
from sqlalchemy import delete, func, insert, select
from sqlalchemy.orm import Session

from app.core.passwords import hash_password, password_policy_errors
from app.db.session import get_session_factory
from app.models import (
    AcademicYear,
    Assessment,
    AssessmentKind,
    AttendanceRecord,
    AttendanceStatus,
    ClassGroup,
    Enrolment,
    Grade,
    Role,
    Staff,
    Student,
    StudentStatus,
    Subject,
    Teacher,
    TeachingAssignment,
    Term,
    User,
)

SEED = 20250901
DEMO_DOMAIN = "edupulse.example"
ADMIN_EMAIL = f"admin@{DEMO_DOMAIN}"

YEAR_NAME = "2025-2026"
TERMS = [
    (1, "Term 1", date(2025, 9, 8), date(2025, 12, 19)),
    (2, "Term 2", date(2026, 1, 5), date(2026, 3, 27)),
    (3, "Term 3", date(2026, 4, 13), date(2026, 6, 19)),
]
SUBJECTS = [
    ("MAT", "Mathematics"),
    ("ENG", "English"),
    ("PHY", "Physics"),
    ("CHE", "Chemistry"),
    ("BIO", "Biology"),
    ("HIS", "History"),
    ("GEO", "Geography"),
    ("CSC", "Computer Science"),
]
GRADE_LEVELS = [10, 11, 12]
SECTIONS = "ABCDE"
STAFF_ROLES = [
    ("School Secretary", "Administration"),
    ("Administrative Assistant", "Administration"),
    ("Receptionist", "Administration"),
    ("Accountant", "Finance"),
    ("Payroll Officer", "Finance"),
    ("Librarian", "Library"),
    ("Library Assistant", "Library"),
    ("School Counsellor", "Student Services"),
    ("Careers Adviser", "Student Services"),
    ("School Nurse", "Health"),
    ("IT Technician", "IT"),
    ("Systems Administrator", "IT"),
    ("Laboratory Technician", "Science"),
    ("Caretaker", "Facilities"),
    ("Facilities Manager", "Facilities"),
]
DELETE_ORDER = [
    Grade,
    Assessment,
    AttendanceRecord,
    Enrolment,
    TeachingAssignment,
    ClassGroup,
    Term,
    AcademicYear,
    Subject,
    User,
    Student,
    Staff,
    Teacher,
]


@dataclass
class SeedConfig:
    students: int = 400
    teachers: int = 30
    staff: int = 15
    seed: int = SEED
    password: str = ""


@dataclass
class SeedSummary:
    counts: dict[str, int] = field(default_factory=dict)
    password: str = ""


def _ascii(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return "".join(ch for ch in normalized.lower() if ch.isalnum())


def _phone(rng: random.Random) -> str:
    return f"+1-555-01{rng.randint(0, 99):02d}"  # fictional range reserved for media use


def _school_days(start: date, end: date) -> Iterator[date]:
    day = start
    while day <= end:
        if day.weekday() < 5:
            yield day
        day += timedelta(days=1)


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


@dataclass
class _Profile:
    """Hidden traits that make the synthetic data internally consistent (never stored)."""

    ability: float
    engagement: float
    declining: bool


def _chunks(rows: list[dict[str, Any]], size: int = 5000) -> Iterator[list[dict[str, Any]]]:
    for i in range(0, len(rows), size):
        yield rows[i : i + size]


def database_has_data(session: Session) -> bool:
    return bool(session.scalar(select(func.count()).select_from(Student)))


def reset(session: Session) -> None:
    for model in DELETE_ORDER:
        session.execute(delete(model))
    session.flush()


def seed(session: Session, config: SeedConfig) -> SeedSummary:
    rng = random.Random(config.seed)  # noqa: S311  (reproducible synthetic data, not crypto)
    fake = Faker(["en_GB", "pt_PT", "es_ES"])
    fake.seed_instance(config.seed)
    used_emails: set[str] = set()

    def unique_email(first: str, last: str) -> str:
        base = f"{_ascii(first)}.{_ascii(last)}"
        candidate, n = f"{base}@{DEMO_DOMAIN}", 1
        while candidate in used_emails:
            n += 1
            candidate = f"{base}{n}@{DEMO_DOMAIN}"
        used_emails.add(candidate)
        return candidate

    # --- academic structure -------------------------------------------------------------
    year = AcademicYear(name=YEAR_NAME, start_date=TERMS[0][2], end_date=TERMS[-1][3])
    year.terms = [Term(number=n, name=name, start_date=s, end_date=e) for n, name, s, e in TERMS]
    session.add(year)
    subjects = [Subject(code=code, name=name) for code, name in SUBJECTS]
    session.add_all(subjects)

    # --- teachers (spread evenly over subjects) and their accounts ----------------------
    teachers: list[Teacher] = []
    teachers_by_subject: dict[str, list[Teacher]] = {code: [] for code, _ in SUBJECTS}
    for i in range(config.teachers):
        code, subject_name = SUBJECTS[i % len(SUBJECTS)]
        first, last = fake.first_name(), fake.last_name()
        teacher = Teacher(
            employee_no=f"TCH{i + 1:03d}",
            first_name=first,
            last_name=last,
            email=unique_email(first, last),
            phone=_phone(rng),
            hire_date=date(rng.randint(2005, 2024), rng.randint(1, 12), 1),
            specialization=subject_name,
        )
        teachers.append(teacher)
        teachers_by_subject[code].append(teacher)
    session.add_all(teachers)

    password_hash = hash_password(config.password)
    session.add(
        User(
            email=ADMIN_EMAIL,
            hashed_password=password_hash,
            full_name="Demo Administrator",
            role=Role.ADMIN,
        )
    )
    teacher_users = [
        User(
            email=t.email,
            hashed_password=password_hash,
            full_name=t.full_name,
            role=Role.TEACHER,
            teacher=t,
        )
        for t in teachers
    ]
    session.add_all(teacher_users)

    # --- staff ----------------------------------------------------------------------------
    for i in range(config.staff):
        title, department = STAFF_ROLES[i % len(STAFF_ROLES)]
        first, last = fake.first_name(), fake.last_name()
        session.add(
            Staff(
                employee_no=f"STF{i + 1:03d}",
                first_name=first,
                last_name=last,
                email=unique_email(first, last),
                phone=_phone(rng),
                job_title=title,
                department=department,
                hire_date=date(rng.randint(2008, 2024), rng.randint(1, 12), 1),
            )
        )

    # --- classes and teaching assignments -------------------------------------------------
    homeroom_pool = teachers[:]
    rng.shuffle(homeroom_pool)
    classes: list[ClassGroup] = []
    for grade_level in GRADE_LEVELS:
        for section in SECTIONS:
            idx = len(classes)
            classes.append(
                ClassGroup(
                    academic_year=year,
                    grade_level=grade_level,
                    section=section,
                    name=f"{grade_level}-{section}",
                    room=f"R{grade_level}{idx % 5 + 1:02d}",
                    homeroom_teacher=homeroom_pool[idx % len(homeroom_pool)] if teachers else None,
                )
            )
    session.add_all(classes)
    assignments: list[TeachingAssignment] = []
    for subject in subjects:
        pool = teachers_by_subject[subject.code] or teachers
        for i, class_group in enumerate(classes):
            assignments.append(
                TeachingAssignment(
                    class_group=class_group, subject=subject, teacher=pool[i % len(pool)]
                )
            )
    session.add_all(assignments)

    # --- students, with hidden profiles ----------------------------------------------------
    students: list[Student] = []
    profiles: list[_Profile] = []
    student_class: list[ClassGroup] = []
    for i in range(config.students):
        class_group = classes[i % len(classes)]
        ability = rng.gauss(0, 1)
        engagement = 0.6 * ability + 0.8 * rng.gauss(0, 1)
        lam = math.exp(-2.0 - 1.1 * ability)
        failures = min(3, sum(1 for _ in range(6) if rng.random() < lam / 6 * 2))
        age_at_start = class_group.grade_level + 5 + min(failures, 2)
        birth = date(TERMS[0][2].year - age_at_start, 1, 1) + timedelta(days=rng.randint(0, 364))
        first, last = fake.first_name(), fake.last_name()
        students.append(
            Student(
                student_no=f"ST25{i + 1:04d}",
                first_name=first,
                last_name=last,
                date_of_birth=birth,
                email=unique_email(first, last),
                guardian_name=f"{fake.first_name()} {last}",
                guardian_phone=_phone(rng),
                enrolled_on=TERMS[0][2] - timedelta(days=rng.randint(0, 3 * 365)),
                status=StudentStatus.ACTIVE,
                prior_failures=failures,
            )
        )
        profiles.append(_Profile(ability, engagement, declining=rng.random() < 0.08))
        student_class.append(class_group)
    session.add_all(students)
    session.flush()  # assign primary keys before bulk inserts

    session.execute(
        insert(Enrolment),
        [
            {
                "student_id": s.id,
                "class_id": c.id,
                "academic_year_id": year.id,
                "enrolled_on": TERMS[0][2],
            }
            for s, c in zip(students, student_class, strict=True)
        ],
    )

    user_by_teacher = {u.teacher.id: u.id for u in teacher_users if u.teacher is not None}

    # --- attendance -------------------------------------------------------------------------
    attendance_rows: list[dict[str, Any]] = []
    for student, profile, class_group in zip(students, profiles, student_class, strict=True):
        recorder = (
            user_by_teacher.get(class_group.homeroom_teacher.id)
            if class_group.homeroom_teacher
            else None
        )
        for term_no, _name, start, end in TERMS:
            decline = 0.7 * (term_no - 1) if profile.declining else 0.0
            p_absent = _sigmoid(-3.4 - 0.9 * profile.engagement + decline)
            for day in _school_days(start, end):
                r = rng.random()
                if r < p_absent:
                    status = AttendanceStatus.ABSENT
                elif r < p_absent + 0.012:
                    status = AttendanceStatus.EXCUSED
                elif r < p_absent + 0.012 + 0.03:
                    status = AttendanceStatus.LATE
                else:
                    status = AttendanceStatus.PRESENT
                attendance_rows.append(
                    {
                        "student_id": student.id,
                        "class_id": class_group.id,
                        "date": day,
                        "status": status,
                        "recorded_by_id": recorder,
                    }
                )
    for chunk in _chunks(attendance_rows):
        session.execute(insert(AttendanceRecord), chunk)

    # --- assessments and grades ---------------------------------------------------------------
    subject_offset = {code: rng.uniform(-5, 5) for code, _ in SUBJECTS}
    students_by_class: dict[int, list[int]] = {}
    for idx, class_group in enumerate(student_class):
        students_by_class.setdefault(class_group.id, []).append(idx)

    assessment_specs = [
        ("Quiz", AssessmentKind.QUIZ, Decimal(20), Decimal(1), 30),
        ("Exam", AssessmentKind.EXAM, Decimal(100), Decimal(2), 7),
    ]
    grade_rows: list[dict[str, Any]] = []
    for assignment in assignments:
        recorder = user_by_teacher.get(assignment.teacher.id)
        for term in year.terms:
            for title, kind, max_score, weight, days_before_end in assessment_specs:
                assessment = Assessment(
                    assignment=assignment,
                    term=term,
                    title=f"{term.name} {title}",
                    kind=kind,
                    max_score=max_score,
                    weight=weight,
                    assessed_on=term.end_date - timedelta(days=days_before_end),
                )
                session.add(assessment)
                session.flush()
                for idx in students_by_class.get(assignment.class_group.id, []):
                    profile = profiles[idx]
                    drift = -6.0 * (term.number - 1) if profile.declining else 0.0
                    mean = (
                        66 + 12 * profile.ability + subject_offset[assignment.subject.code] + drift
                    )
                    pct = min(100.0, max(0.0, rng.gauss(mean, 9)))
                    score = (Decimal(str(round(pct, 1))) * max_score / 100).quantize(Decimal("0.1"))
                    grade_rows.append(
                        {
                            "assessment_id": assessment.id,
                            "student_id": students[idx].id,
                            "score": score,
                            "recorded_by_id": recorder,
                        }
                    )
    for chunk in _chunks(grade_rows):
        session.execute(insert(Grade), chunk)
    session.flush()

    counts = {
        model.__tablename__: session.scalar(select(func.count()).select_from(model)) or 0
        for model in reversed(DELETE_ORDER)
    }
    return SeedSummary(counts=counts, password=config.password)


# Values that appear in examples or are commonly guessed; never accepted as the demo password.
DEFAULT_PASSWORDS = {
    "change-me",
    "change-me-local-only",
    "password",
    "password123",
    "demo",
    "admin",
}


def resolve_password(value: str | None) -> str:
    password = (value or "").strip()
    if not password:
        raise SystemExit("Set EDUPULSE_DEMO_PASSWORD (see .env.example); refusing to seed.")
    if password.lower() in DEFAULT_PASSWORDS:
        raise SystemExit("EDUPULSE_DEMO_PASSWORD is a default value; choose your own.")
    problems = password_policy_errors(password)
    if problems:
        raise SystemExit("EDUPULSE_DEMO_PASSWORD " + "; ".join(problems))
    return password


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Load SYNTHETIC demo data into EduPulse.")
    parser.add_argument("--reset", action="store_true", help="delete existing data first")
    parser.add_argument("--students", type=int, default=400)
    parser.add_argument("--teachers", type=int, default=30)
    parser.add_argument("--staff", type=int, default=15)
    args = parser.parse_args(argv)

    env_password = os.environ.get("EDUPULSE_DEMO_PASSWORD")
    config = SeedConfig(
        students=args.students,
        teachers=args.teachers,
        staff=args.staff,
        password=resolve_password(env_password),
    )
    with get_session_factory()() as session, session.begin():
        if database_has_data(session):
            if not args.reset:
                raise SystemExit("Database already contains data; re-run with --reset.")
            reset(session)
        summary = seed(session, config)

    print("Seeded SYNTHETIC demo data (not real people):")
    for table, count in summary.counts.items():
        print(f"  {table:<22}{count:>8}")
    print(f"Demo logins: {ADMIN_EMAIL} (admin), any teacher e-mail @ {DEMO_DOMAIN} (teacher)")


if __name__ == "__main__":
    main()
