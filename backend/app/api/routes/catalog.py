"""Reference data: subjects and academic years."""

from fastapi import APIRouter, Response, status
from sqlalchemy import exists, select
from sqlalchemy.orm import selectinload

from app.api.deps import AdminUser, CurrentUser, DbDep
from app.core.errors import ERROR_RESPONSES, conflict
from app.models import AcademicYear, Subject, TeachingAssignment
from app.schemas.academic import AcademicYearRead, SubjectCreate, SubjectRead, SubjectUpdate
from app.services.crud import apply_changes, ensure_unique, get_or_404

router = APIRouter(tags=["reference data"], responses=ERROR_RESPONSES)


@router.get("/subjects", response_model=list[SubjectRead], summary="List subjects")
def list_subjects(db: DbDep, _user: CurrentUser) -> list[Subject]:
    return list(db.scalars(select(Subject).order_by(Subject.name)))


@router.post(
    "/subjects",
    response_model=SubjectRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create subject",
)
def create_subject(payload: SubjectCreate, db: DbDep, _admin: AdminUser) -> Subject:
    code = payload.code.upper()
    ensure_unique(
        db, {"Subject code": (Subject.code, code), "Subject name": (Subject.name, payload.name)}
    )
    subject = Subject(code=code, name=payload.name)
    db.add(subject)
    db.commit()
    db.refresh(subject)
    return subject


@router.patch("/subjects/{subject_id}", response_model=SubjectRead, summary="Update subject")
def update_subject(
    subject_id: int, payload: SubjectUpdate, db: DbDep, _admin: AdminUser
) -> Subject:
    subject = get_or_404(db, Subject, subject_id, "Subject")
    if payload.code is not None:
        payload.code = payload.code.upper()
    ensure_unique(
        db,
        {
            "Subject code": (Subject.code, payload.code),
            "Subject name": (Subject.name, payload.name),
        },
        exclude_id=subject_id,
    )
    apply_changes(subject, payload)
    db.commit()
    db.refresh(subject)
    return subject


@router.delete(
    "/subjects/{subject_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete subject"
)
def delete_subject(subject_id: int, db: DbDep, _admin: AdminUser) -> Response:
    subject = get_or_404(db, Subject, subject_id, "Subject")
    if db.scalar(select(exists().where(TeachingAssignment.subject_id == subject_id))):
        raise conflict("Subject is taught in at least one class")
    db.delete(subject)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/academic-years", response_model=list[AcademicYearRead], summary="Academic years and terms"
)
def list_years(db: DbDep, _user: CurrentUser) -> list[AcademicYear]:
    return list(
        db.scalars(
            select(AcademicYear)
            .options(selectinload(AcademicYear.terms))
            .order_by(AcademicYear.start_date.desc())
        )
    )
