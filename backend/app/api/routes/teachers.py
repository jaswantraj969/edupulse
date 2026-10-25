"""Teachers. Any signed-in user can read the directory; only admins can change it."""

from typing import Annotated, Any

from fastapi import APIRouter, File, Response, UploadFile, status
from fastapi.responses import Response as RawResponse
from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from app.api.deps import AdminUser, CurrentUser, DbDep
from app.api.pagination import Page, PageDep, apply_sort, paginate_rows, search_clause
from app.core.errors import ERROR_RESPONSES, conflict
from app.models import Teacher, TeachingAssignment, User
from app.schemas.csv_io import ImportResult, RowError
from app.schemas.people import TeacherCreate, TeacherRead, TeacherUpdate
from app.services.crud import apply_changes, ensure_unique, get_or_404
from app.services.csv_io import ParsedRow, csv_response, run_import

router = APIRouter(prefix="/teachers", tags=["teachers"], responses=ERROR_RESPONSES)

SORTABLE: dict[str, Any] = {
    "last_name": Teacher.last_name,
    "first_name": Teacher.first_name,
    "employee_no": Teacher.employee_no,
    "hire_date": Teacher.hire_date,
    "specialization": Teacher.specialization,
}
CSV_COLUMNS = [
    "employee_no",
    "first_name",
    "last_name",
    "email",
    "phone",
    "hire_date",
    "specialization",
    "is_active",
]
CSV_REQUIRED = ["employee_no", "first_name", "last_name", "email", "hire_date"]

_has_account = exists().where(User.teacher_id == Teacher.id).label("has_account")


def _read(teacher: Teacher, has_account: bool) -> TeacherRead:
    return TeacherRead.model_validate(teacher).model_copy(update={"has_account": has_account})


def _load(db: Session, teacher_id: int) -> TeacherRead:
    teacher = get_or_404(db, Teacher, teacher_id, "Teacher")
    has_account = bool(db.scalar(select(exists().where(User.teacher_id == teacher_id))))
    return _read(teacher, has_account)


def _unique_checks(payload: TeacherCreate | TeacherUpdate) -> dict[str, Any]:
    return {
        "Employee number": (Teacher.employee_no, payload.employee_no),
        "E-mail": (Teacher.email, payload.email),
    }


@router.get("", response_model=Page[TeacherRead], summary="List teachers")
def list_teachers(
    db: DbDep,
    _user: CurrentUser,
    params: PageDep,
    is_active: bool | None = None,
    specialization: str | None = None,
) -> Page[TeacherRead]:
    stmt = select(Teacher, _has_account)
    columns = [Teacher.first_name, Teacher.last_name, Teacher.employee_no, Teacher.email]
    if (clause := search_clause(params.q, columns)) is not None:
        stmt = stmt.where(clause)
    if is_active is not None:
        stmt = stmt.where(Teacher.is_active == is_active)
    if specialization:
        stmt = stmt.where(Teacher.specialization == specialization)
    stmt = apply_sort(stmt, params, SORTABLE, "last_name", Teacher.id)
    rows, total = paginate_rows(db, stmt, params)
    return Page(
        items=[_read(t, bool(a)) for t, a in rows],
        total=total,
        page=params.page,
        page_size=params.page_size,
    )


@router.get("/export", summary="Export teachers as CSV", response_class=RawResponse)
def export_teachers(db: DbDep, _admin: AdminUser) -> Response:
    teachers = db.scalars(select(Teacher).order_by(Teacher.last_name, Teacher.id))
    return csv_response(
        "teachers.csv", CSV_COLUMNS, ([getattr(t, c) for c in CSV_COLUMNS] for t in teachers)
    )


@router.post("/import", response_model=ImportResult, summary="Import teachers from CSV")
async def import_teachers(
    db: DbDep,
    _admin: AdminUser,
    file: Annotated[UploadFile, File()],
    dry_run: bool = False,
) -> ImportResult:
    def build(row: ParsedRow[TeacherCreate], _errors: list[RowError]) -> Teacher:
        return Teacher(**row.data.model_dump())

    return await run_import(
        db,
        file,
        schema=TeacherCreate,
        columns=CSV_COLUMNS,
        required=CSV_REQUIRED,
        unique={"employee_no": Teacher.employee_no, "email": Teacher.email},
        build=build,
        dry_run=dry_run,
    )


@router.post(
    "", response_model=TeacherRead, status_code=status.HTTP_201_CREATED, summary="Create teacher"
)
def create_teacher(payload: TeacherCreate, db: DbDep, _admin: AdminUser) -> TeacherRead:
    ensure_unique(db, _unique_checks(payload))
    teacher = Teacher(**payload.model_dump())
    db.add(teacher)
    db.commit()
    return _load(db, teacher.id)


@router.get("/{teacher_id}", response_model=TeacherRead, summary="Get teacher")
def get_teacher(teacher_id: int, db: DbDep, _user: CurrentUser) -> TeacherRead:
    return _load(db, teacher_id)


@router.patch("/{teacher_id}", response_model=TeacherRead, summary="Update teacher")
def update_teacher(
    teacher_id: int, payload: TeacherUpdate, db: DbDep, _admin: AdminUser
) -> TeacherRead:
    teacher = get_or_404(db, Teacher, teacher_id, "Teacher")
    ensure_unique(db, _unique_checks(payload), exclude_id=teacher_id)
    apply_changes(teacher, payload)
    db.commit()
    return _load(db, teacher_id)


@router.delete("/{teacher_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete teacher")
def delete_teacher(teacher_id: int, db: DbDep, _admin: AdminUser) -> Response:
    """Refused (409) while the teacher still has teaching assignments. The teacher's login
    account, if any, is deleted with the profile."""
    teacher = get_or_404(db, Teacher, teacher_id, "Teacher")
    if db.scalar(select(exists().where(TeachingAssignment.teacher_id == teacher_id))):
        raise conflict("Teacher still has teaching assignments; reassign them first")
    if teacher.user is not None:
        db.delete(teacher.user)
        db.flush()
    db.delete(teacher)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
