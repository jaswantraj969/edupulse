"""Assessments and grade entry.

Anyone who can see a class can read its assessments and grades. Creating assessments and
entering grades is limited to admins and the teacher who teaches that subject in that class.
"""

from typing import Any

from fastapi import APIRouter, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.api.deps import CurrentUser, DbDep
from app.api.routes.classes import roster
from app.core.errors import ERROR_RESPONSES, AppError, conflict, forbidden
from app.models import Assessment, ClassGroup, Grade, TeachingAssignment, Term, User
from app.schemas.records import (
    AssessmentCreate,
    AssessmentRead,
    AssessmentUpdate,
    GradeBulk,
    GradeRow,
    GradeSheet,
)
from app.services.access import ensure_class_access, is_admin
from app.services.crud import get_or_404

router = APIRouter(tags=["assessments"], responses=ERROR_RESPONSES)


def _invalid(message: str, details: Any = None) -> AppError:
    return AppError(
        status.HTTP_422_UNPROCESSABLE_CONTENT, message, code="validation_error", details=details
    )


def _ensure_can_edit(user: User, assignment: TeachingAssignment) -> None:
    if not is_admin(user) and assignment.teacher_id != user.teacher_id:
        raise forbidden("Only the subject teacher can change these assessments")


def _to_read(a: Assessment, graded: int) -> AssessmentRead:
    return AssessmentRead(
        id=a.id,
        assignment_id=a.assignment_id,
        class_id=a.assignment.class_id,
        subject_id=a.assignment.subject_id,
        subject_name=a.assignment.subject.name,
        teacher_id=a.assignment.teacher_id,
        term_id=a.term_id,
        term_name=a.term.name,
        title=a.title,
        kind=a.kind,
        max_score=float(a.max_score),
        weight=float(a.weight),
        assessed_on=a.assessed_on,
        graded_count=graded,
    )


def _graded_counts(db: Session, ids: list[int]) -> dict[int, int]:
    if not ids:
        return {}
    rows = db.execute(
        select(Grade.assessment_id, func.count())
        .where(Grade.assessment_id.in_(ids))
        .group_by(Grade.assessment_id)
    )
    return {row[0]: row[1] for row in rows}


def _load(db: Session, assessment_id: int) -> AssessmentRead:
    a = get_or_404(db, Assessment, assessment_id, "Assessment")
    return _to_read(a, _graded_counts(db, [a.id]).get(a.id, 0))


def _check_term_and_date(db: Session, assignment: TeachingAssignment, term_id: int, a: Any) -> Term:
    term = db.get(Term, term_id)
    if term is None or term.academic_year_id != assignment.class_group.academic_year_id:
        raise _invalid("Term does not belong to the class's academic year")
    if not term.start_date <= a.assessed_on <= term.end_date:
        raise _invalid(f"assessed_on must fall within {term.name}")
    return term


def _check_title_free(
    db: Session, assignment_id: int, term_id: int, title: str, exclude_id: int | None = None
) -> None:
    stmt = select(Assessment.id).where(
        Assessment.assignment_id == assignment_id,
        Assessment.term_id == term_id,
        Assessment.title == title,
    )
    if exclude_id is not None:
        stmt = stmt.where(Assessment.id != exclude_id)
    if db.scalar(stmt) is not None:
        raise conflict(f"An assessment titled '{title}' already exists for this term")


@router.get(
    "/classes/{class_id}/assessments",
    response_model=list[AssessmentRead],
    summary="Assessments of a class",
)
def list_assessments(
    class_id: int,
    db: DbDep,
    user: CurrentUser,
    term_id: int | None = None,
    subject_id: int | None = None,
) -> list[AssessmentRead]:
    get_or_404(db, ClassGroup, class_id, "Class")
    ensure_class_access(db, user, class_id)
    stmt = (
        select(Assessment)
        .join(TeachingAssignment)
        .where(TeachingAssignment.class_id == class_id)
        .options(
            joinedload(Assessment.assignment).joinedload(TeachingAssignment.subject),
            joinedload(Assessment.term),
        )
        .order_by(Assessment.assessed_on, Assessment.id)
    )
    if term_id is not None:
        stmt = stmt.where(Assessment.term_id == term_id)
    if subject_id is not None:
        stmt = stmt.where(TeachingAssignment.subject_id == subject_id)
    items = list(db.scalars(stmt).unique())
    counts = _graded_counts(db, [a.id for a in items])
    return [_to_read(a, counts.get(a.id, 0)) for a in items]


@router.post(
    "/assessments",
    response_model=AssessmentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create assessment",
)
def create_assessment(payload: AssessmentCreate, db: DbDep, user: CurrentUser) -> AssessmentRead:
    assignment = db.get(TeachingAssignment, payload.assignment_id)
    if assignment is None:
        raise _invalid("Teaching assignment not found")
    _ensure_can_edit(user, assignment)
    _check_term_and_date(db, assignment, payload.term_id, payload)
    title = payload.title.strip()
    _check_title_free(db, assignment.id, payload.term_id, title)
    assessment = Assessment(**payload.model_dump(exclude={"title"}), title=title)
    db.add(assessment)
    db.commit()
    return _load(db, assessment.id)


@router.get("/assessments/{assessment_id}", response_model=AssessmentRead, summary="Get assessment")
def get_assessment(assessment_id: int, db: DbDep, user: CurrentUser) -> AssessmentRead:
    a = get_or_404(db, Assessment, assessment_id, "Assessment")
    ensure_class_access(db, user, a.assignment.class_id)
    return _load(db, assessment_id)


@router.patch(
    "/assessments/{assessment_id}", response_model=AssessmentRead, summary="Update assessment"
)
def update_assessment(
    assessment_id: int, payload: AssessmentUpdate, db: DbDep, user: CurrentUser
) -> AssessmentRead:
    a = get_or_404(db, Assessment, assessment_id, "Assessment")
    _ensure_can_edit(user, a.assignment)
    changes = payload.model_dump(exclude_unset=True)
    if changes.get("max_score") is not None:
        highest = db.scalar(select(func.max(Grade.score)).where(Grade.assessment_id == a.id))
        if highest is not None and highest > changes["max_score"]:
            raise _invalid(f"max_score cannot be below an existing score ({highest})")
    if "title" in changes:
        changes["title"] = changes["title"].strip()
        _check_title_free(db, a.assignment_id, a.term_id, changes["title"], exclude_id=a.id)
    for field, value in changes.items():
        if value is not None:
            setattr(a, field, value)
    _check_term_and_date(db, a.assignment, a.term_id, a)
    db.commit()
    return _load(db, assessment_id)


@router.delete(
    "/assessments/{assessment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete assessment and its grades",
)
def delete_assessment(assessment_id: int, db: DbDep, user: CurrentUser) -> Response:
    a = get_or_404(db, Assessment, assessment_id, "Assessment")
    _ensure_can_edit(user, a.assignment)
    db.delete(a)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _grade_sheet(db: Session, a: Assessment) -> GradeSheet:
    grades = {g.student_id: g for g in db.scalars(select(Grade).where(Grade.assessment_id == a.id))}
    rows = [
        GradeRow(
            student_id=s.id,
            student_no=s.student_no,
            first_name=s.first_name,
            last_name=s.last_name,
            score=float(grades[s.id].score) if s.id in grades else None,
            comment=grades[s.id].comment if s.id in grades else None,
        )
        for s in roster(db, a.assignment.class_id)
    ]
    return GradeSheet(assessment=_to_read(a, len(grades)), grades=rows)


@router.get(
    "/assessments/{assessment_id}/grades",
    response_model=GradeSheet,
    summary="Grade sheet (every student in the class)",
)
def get_grades(assessment_id: int, db: DbDep, user: CurrentUser) -> GradeSheet:
    a = get_or_404(db, Assessment, assessment_id, "Assessment")
    ensure_class_access(db, user, a.assignment.class_id)
    return _grade_sheet(db, a)


@router.put(
    "/assessments/{assessment_id}/grades",
    response_model=GradeSheet,
    summary="Enter grades (bulk upsert)",
)
def put_grades(assessment_id: int, payload: GradeBulk, db: DbDep, user: CurrentUser) -> GradeSheet:
    """Each score must be between 0 and the assessment's ``max_score``; every student must be
    enrolled in the class. Invalid rows are reported in ``details`` and nothing is saved."""
    a = get_or_404(db, Assessment, assessment_id, "Assessment")
    _ensure_can_edit(user, a.assignment)
    enrolled = {s.id for s in roster(db, a.assignment.class_id)}
    errors, seen = [], set()
    for i, entry in enumerate(payload.grades):
        field = f"grades.{i}"
        if entry.student_id in seen:
            errors.append({"field": f"{field}.student_id", "message": "Duplicate student"})
        elif entry.student_id not in enrolled:
            errors.append(
                {"field": f"{field}.student_id", "message": "Student is not in this class"}
            )
        if entry.score > a.max_score:
            errors.append(
                {"field": f"{field}.score", "message": f"Score exceeds maximum of {a.max_score}"}
            )
        seen.add(entry.student_id)
    if errors:
        raise _invalid("Grades contain invalid rows", errors)

    existing = {
        g.student_id: g
        for g in db.scalars(
            select(Grade).where(Grade.assessment_id == a.id, Grade.student_id.in_(seen))
        )
    }
    for entry in payload.grades:
        grade = existing.get(entry.student_id)
        if grade is None:
            db.add(
                Grade(
                    assessment_id=a.id,
                    student_id=entry.student_id,
                    score=entry.score,
                    comment=entry.comment,
                    recorded_by_id=user.id,
                )
            )
        else:
            grade.score, grade.comment, grade.recorded_by_id = entry.score, entry.comment, user.id
    db.commit()
    db.refresh(a)
    return _grade_sheet(db, a)
