"""Classes (sections). Teachers only see classes they teach or are homeroom teacher of."""

from typing import Annotated, Any

from fastapi import APIRouter, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.api.deps import CurrentUser, DbDep
from app.api.pagination import Page, PageDep, apply_sort, paginate, search_clause
from app.core.errors import ERROR_RESPONSES, not_found
from app.models import ClassGroup, Enrolment
from app.schemas.classes import ClassRead
from app.services.access import ensure_class_access, visible_class_ids

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


@router.get("/{class_id}", response_model=ClassRead, summary="Get a class")
def get_class(class_id: int, db: DbDep, user: CurrentUser) -> ClassRead:
    class_group = db.get(ClassGroup, class_id)
    if class_group is None:
        raise not_found("Class")
    ensure_class_access(db, user, class_id)
    return to_read(class_group, _student_counts(db, [class_id]).get(class_id, 0))
