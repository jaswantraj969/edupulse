"""Classes (sections), their rosters, teaching assignments and enrolments.

Teachers only see classes they teach or are homeroom teacher of; only admins change them.
"""

from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Query, Response, status
from sqlalchemy import exists, func, select
from sqlalchemy.orm import Session, joinedload

from app.api.deps import AdminUser, CurrentUser, DbDep, NotInPublicDemo
from app.api.pagination import Page, PageDep, apply_sort, paginate, search_clause
from app.core.errors import ERROR_RESPONSES, AppError, conflict, not_found
from app.models import (
    AcademicYear,
    Assessment,
    ClassGroup,
    Enrolment,
    Student,
    Subject,
    Teacher,
    TeachingAssignment,
)
from app.schemas.academic import AssignmentCreate, AssignmentRead, EnrolmentCreate
from app.schemas.classes import ClassCreate, ClassRead, ClassUpdate
from app.schemas.people import StudentBrief
from app.services.access import ensure_class_access, visible_class_ids
from app.services.crud import get_or_404

router = APIRouter(prefix="/classes", tags=["classes"], responses=ERROR_RESPONSES)

SORTABLE: dict[str, Any] = {
    "name": ClassGroup.name,
    "grade_level": ClassGroup.grade_level,
    "section": ClassGroup.section,
}


def _student_counts(db: Session, class_ids: list[int]) -> dict[int, int]:
    if not class_ids:
        return {}
    rows = db.execute(
        select(Enrolment.class_id, func.count())
        .where(Enrolment.class_id.in_(class_ids))
        .group_by(Enrolment.class_id)
    )
    return {row[0]: row[1] for row in rows}


def to_read(class_group: ClassGroup, student_count: int) -> ClassRead:
    teacher = class_group.homeroom_teacher
    return ClassRead(
        id=class_group.id,
        name=class_group.name,
        grade_level=class_group.grade_level,
        section=class_group.section,
        room=class_group.room,
        academic_year_id=class_group.academic_year_id,
        academic_year=class_group.academic_year.name,
        homeroom_teacher_id=class_group.homeroom_teacher_id,
        homeroom_teacher_name=teacher.full_name if teacher else None,
        student_count=student_count,
    )


def _load(db: Session, class_id: int) -> ClassRead:
    class_group = get_or_404(db, ClassGroup, class_id, "Class")
    return to_read(class_group, _student_counts(db, [class_id]).get(class_id, 0))


def _check_section_free(
    db: Session, year_id: int, grade_level: int, section: str, exclude_id: int | None = None
) -> None:
    stmt = select(ClassGroup.id).where(
        ClassGroup.academic_year_id == year_id,
        ClassGroup.grade_level == grade_level,
        ClassGroup.section == section,
    )
    if exclude_id is not None:
        stmt = stmt.where(ClassGroup.id != exclude_id)
    if db.scalar(stmt) is not None:
        raise conflict(f"Class {grade_level}-{section} already exists in this academic year")


def _check_teacher(db: Session, teacher_id: int | None) -> None:
    if teacher_id is not None and db.get(Teacher, teacher_id) is None:
        raise AppError(status.HTTP_422_UNPROCESSABLE_CONTENT, "Teacher not found")


@router.get("", response_model=Page[ClassRead], summary="List classes")
def list_classes(
    db: DbDep,
    user: CurrentUser,
    params: PageDep,
    grade_level: Annotated[int | None, Query(ge=1, le=13)] = None,
    academic_year_id: int | None = None,
) -> Page[ClassRead]:
    stmt = select(ClassGroup).options(
        joinedload(ClassGroup.homeroom_teacher), joinedload(ClassGroup.academic_year)
    )
    scope = visible_class_ids(user)
    if scope is not None:
        stmt = stmt.where(ClassGroup.id.in_(scope))
    if (clause := search_clause(params.q, [ClassGroup.name, ClassGroup.room])) is not None:
        stmt = stmt.where(clause)
    if grade_level is not None:
        stmt = stmt.where(ClassGroup.grade_level == grade_level)
    if academic_year_id is not None:
        stmt = stmt.where(ClassGroup.academic_year_id == academic_year_id)
    stmt = apply_sort(stmt, params, SORTABLE, "name", ClassGroup.id)
    items, total = paginate(db, stmt, params)
    counts = _student_counts(db, [c.id for c in items])
    return Page(
        items=[to_read(c, counts.get(c.id, 0)) for c in items],
        total=total,
        page=params.page,
        page_size=params.page_size,
    )


@router.post(
    "", response_model=ClassRead, status_code=status.HTTP_201_CREATED, summary="Create class"
)
def create_class(payload: ClassCreate, db: DbDep, _admin: AdminUser) -> ClassRead:
    if db.get(AcademicYear, payload.academic_year_id) is None:
        raise AppError(status.HTTP_422_UNPROCESSABLE_CONTENT, "Academic year not found")
    _check_teacher(db, payload.homeroom_teacher_id)
    section = payload.section.upper()
    _check_section_free(db, payload.academic_year_id, payload.grade_level, section)
    class_group = ClassGroup(
        academic_year_id=payload.academic_year_id,
        grade_level=payload.grade_level,
        section=section,
        name=f"{payload.grade_level}-{section}",
        room=payload.room,
        homeroom_teacher_id=payload.homeroom_teacher_id,
    )
    db.add(class_group)
    db.commit()
    return _load(db, class_group.id)


@router.get("/{class_id}", response_model=ClassRead, summary="Get class")
def get_class(class_id: int, db: DbDep, user: CurrentUser) -> ClassRead:
    get_or_404(db, ClassGroup, class_id, "Class")
    ensure_class_access(db, user, class_id)
    return _load(db, class_id)


@router.patch("/{class_id}", response_model=ClassRead, summary="Update class")
def update_class(class_id: int, payload: ClassUpdate, db: DbDep, _admin: AdminUser) -> ClassRead:
    class_group = get_or_404(db, ClassGroup, class_id, "Class")
    changes = payload.model_dump(exclude_unset=True)
    if "homeroom_teacher_id" in changes:
        _check_teacher(db, changes["homeroom_teacher_id"])
        class_group.homeroom_teacher_id = changes["homeroom_teacher_id"]
    if "room" in changes:
        class_group.room = changes["room"]
    grade_level = changes.get("grade_level") or class_group.grade_level
    section = (changes.get("section") or class_group.section).upper()
    if (grade_level, section) != (class_group.grade_level, class_group.section):
        _check_section_free(db, class_group.academic_year_id, grade_level, section, class_id)
        class_group.grade_level, class_group.section = grade_level, section
        class_group.name = f"{grade_level}-{section}"
    db.commit()
    return _load(db, class_id)


@router.delete(
    "/{class_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete class",
    dependencies=[NotInPublicDemo],
)
def delete_class(class_id: int, db: DbDep, _admin: AdminUser) -> Response:
    """Only empty classes (no enrolled students) can be deleted."""
    class_group = get_or_404(db, ClassGroup, class_id, "Class")
    if db.scalar(select(exists().where(Enrolment.class_id == class_id))):
        raise conflict("Class still has enrolled students; move them first")
    db.delete(class_group)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- roster and enrolments -------------------------------------------------------------------


def roster(db: Session, class_id: int) -> list[Student]:
    return list(
        db.scalars(
            select(Student)
            .join(Enrolment, Enrolment.student_id == Student.id)
            .where(Enrolment.class_id == class_id)
            .order_by(Student.last_name, Student.first_name, Student.id)
        )
    )


@router.get("/{class_id}/students", response_model=list[StudentBrief], summary="Class roster")
def class_roster(class_id: int, db: DbDep, user: CurrentUser) -> list[Student]:
    get_or_404(db, ClassGroup, class_id, "Class")
    ensure_class_access(db, user, class_id)
    return roster(db, class_id)


@router.post(
    "/{class_id}/enrolments",
    response_model=list[StudentBrief],
    status_code=status.HTTP_201_CREATED,
    summary="Enrol a student",
)
def enrol_student(
    class_id: int, payload: EnrolmentCreate, db: DbDep, _admin: AdminUser
) -> list[Student]:
    class_group = get_or_404(db, ClassGroup, class_id, "Class")
    get_or_404(db, Student, payload.student_id, "Student")
    existing = db.scalar(
        select(Enrolment).where(
            Enrolment.student_id == payload.student_id,
            Enrolment.academic_year_id == class_group.academic_year_id,
        )
    )
    if existing is not None:
        other = db.get(ClassGroup, existing.class_id)
        raise conflict(f"Student is already enrolled in {other.name if other else 'a class'}")
    db.add(
        Enrolment(
            student_id=payload.student_id,
            class_id=class_id,
            academic_year_id=class_group.academic_year_id,
            enrolled_on=date.today(),
        )
    )
    db.commit()
    return roster(db, class_id)


@router.delete(
    "/{class_id}/enrolments/{student_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a student from a class",
)
def unenrol_student(class_id: int, student_id: int, db: DbDep, _admin: AdminUser) -> Response:
    enrolment = db.scalar(
        select(Enrolment).where(Enrolment.class_id == class_id, Enrolment.student_id == student_id)
    )
    if enrolment is None:
        raise not_found("Enrolment")
    db.delete(enrolment)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- teaching assignments --------------------------------------------------------------------


def _assignment_read(a: TeachingAssignment) -> AssignmentRead:
    return AssignmentRead(
        id=a.id,
        class_id=a.class_id,
        class_name=a.class_group.name,
        subject_id=a.subject_id,
        subject_code=a.subject.code,
        subject_name=a.subject.name,
        teacher_id=a.teacher_id,
        teacher_name=a.teacher.full_name,
    )


@router.get(
    "/{class_id}/assignments",
    response_model=list[AssignmentRead],
    summary="Subjects taught in a class and by whom",
)
def list_assignments(class_id: int, db: DbDep, user: CurrentUser) -> list[AssignmentRead]:
    get_or_404(db, ClassGroup, class_id, "Class")
    ensure_class_access(db, user, class_id)
    assignments = db.scalars(
        select(TeachingAssignment)
        .join(Subject)
        .where(TeachingAssignment.class_id == class_id)
        .options(joinedload(TeachingAssignment.subject), joinedload(TeachingAssignment.teacher))
        .order_by(Subject.name)
    )
    return [_assignment_read(a) for a in assignments]


@router.post(
    "/{class_id}/assignments",
    response_model=AssignmentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Assign a teacher to teach a subject in a class",
)
def create_assignment(
    class_id: int, payload: AssignmentCreate, db: DbDep, _admin: AdminUser
) -> AssignmentRead:
    get_or_404(db, ClassGroup, class_id, "Class")
    if db.get(Subject, payload.subject_id) is None:
        raise AppError(status.HTTP_422_UNPROCESSABLE_CONTENT, "Subject not found")
    if db.get(Teacher, payload.teacher_id) is None:
        raise AppError(status.HTTP_422_UNPROCESSABLE_CONTENT, "Teacher not found")
    duplicate = select(TeachingAssignment.id).where(
        TeachingAssignment.class_id == class_id,
        TeachingAssignment.subject_id == payload.subject_id,
    )
    if db.scalar(duplicate) is not None:
        raise conflict("This subject is already assigned in this class")
    assignment = TeachingAssignment(class_id=class_id, **payload.model_dump())
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return _assignment_read(assignment)


@router.delete(
    "/{class_id}/assignments/{assignment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a teaching assignment",
)
def delete_assignment(class_id: int, assignment_id: int, db: DbDep, _admin: AdminUser) -> Response:
    """Refused (409) once assessments exist for the assignment."""
    assignment = db.get(TeachingAssignment, assignment_id)
    if assignment is None or assignment.class_id != class_id:
        raise not_found("Teaching assignment")
    if db.scalar(select(exists().where(Assessment.assignment_id == assignment_id))):
        raise conflict("Assessments exist for this assignment; delete them first")
    db.delete(assignment)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
