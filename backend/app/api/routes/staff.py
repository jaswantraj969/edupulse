"""Non-teaching staff (administrator access only)."""

from typing import Annotated, Any

from fastapi import APIRouter, File, Response, UploadFile, status
from fastapi.responses import Response as RawResponse
from sqlalchemy import select

from app.api.deps import AdminUser, DbDep, NotInPublicDemo
from app.api.pagination import Page, PageDep, apply_sort, paginate, search_clause
from app.core.errors import ERROR_RESPONSES
from app.models import Staff
from app.schemas.csv_io import ImportResult, RowError
from app.schemas.people import StaffCreate, StaffRead, StaffUpdate
from app.services.crud import apply_changes, ensure_unique, get_or_404
from app.services.csv_io import ParsedRow, csv_response, run_import

router = APIRouter(prefix="/staff", tags=["staff"], responses=ERROR_RESPONSES)

SORTABLE: dict[str, Any] = {
    "last_name": Staff.last_name,
    "first_name": Staff.first_name,
    "employee_no": Staff.employee_no,
    "job_title": Staff.job_title,
    "department": Staff.department,
    "hire_date": Staff.hire_date,
}
CSV_COLUMNS = [
    "employee_no",
    "first_name",
    "last_name",
    "email",
    "phone",
    "job_title",
    "department",
    "hire_date",
    "is_active",
]
CSV_REQUIRED = [
    "employee_no",
    "first_name",
    "last_name",
    "email",
    "job_title",
    "department",
    "hire_date",
]


def _unique_checks(payload: StaffCreate | StaffUpdate) -> dict[str, Any]:
    return {
        "Employee number": (Staff.employee_no, payload.employee_no),
        "E-mail": (Staff.email, payload.email),
    }


@router.get("", response_model=Page[StaffRead], summary="List staff")
def list_staff(
    db: DbDep,
    _admin: AdminUser,
    params: PageDep,
    department: str | None = None,
    is_active: bool | None = None,
) -> Page[StaffRead]:
    stmt = select(Staff)
    columns = [Staff.first_name, Staff.last_name, Staff.employee_no, Staff.email, Staff.job_title]
    if (clause := search_clause(params.q, columns)) is not None:
        stmt = stmt.where(clause)
    if department:
        stmt = stmt.where(Staff.department == department)
    if is_active is not None:
        stmt = stmt.where(Staff.is_active == is_active)
    stmt = apply_sort(stmt, params, SORTABLE, "last_name", Staff.id)
    items, total = paginate(db, stmt, params)
    return Page(
        items=[StaffRead.model_validate(m) for m in items],
        total=total,
        page=params.page,
        page_size=params.page_size,
    )


@router.get("/export", summary="Export staff as CSV", response_class=RawResponse)
def export_staff(db: DbDep, _admin: AdminUser) -> Response:
    members = db.scalars(select(Staff).order_by(Staff.last_name, Staff.id))
    return csv_response(
        "staff.csv", CSV_COLUMNS, ([getattr(m, c) for c in CSV_COLUMNS] for m in members)
    )


@router.post(
    "/import",
    response_model=ImportResult,
    summary="Import staff from CSV",
    dependencies=[NotInPublicDemo],
)
async def import_staff(
    db: DbDep,
    _admin: AdminUser,
    file: Annotated[UploadFile, File()],
    dry_run: bool = False,
) -> ImportResult:
    def build(row: ParsedRow[StaffCreate], _errors: list[RowError]) -> Staff:
        return Staff(**row.data.model_dump())

    return await run_import(
        db,
        file,
        schema=StaffCreate,
        columns=CSV_COLUMNS,
        required=CSV_REQUIRED,
        unique={"employee_no": Staff.employee_no, "email": Staff.email},
        build=build,
        dry_run=dry_run,
    )


@router.post(
    "", response_model=StaffRead, status_code=status.HTTP_201_CREATED, summary="Create staff member"
)
def create_staff(payload: StaffCreate, db: DbDep, _admin: AdminUser) -> Staff:
    ensure_unique(db, _unique_checks(payload))
    member = Staff(**payload.model_dump())
    db.add(member)
    db.commit()
    db.refresh(member)
    return member


@router.get("/{staff_id}", response_model=StaffRead, summary="Get staff member")
def get_staff(staff_id: int, db: DbDep, _admin: AdminUser) -> Staff:
    return get_or_404(db, Staff, staff_id, "Staff member")


@router.patch("/{staff_id}", response_model=StaffRead, summary="Update staff member")
def update_staff(staff_id: int, payload: StaffUpdate, db: DbDep, _admin: AdminUser) -> Staff:
    member = get_or_404(db, Staff, staff_id, "Staff member")
    ensure_unique(db, _unique_checks(payload), exclude_id=staff_id)
    apply_changes(member, payload)
    db.commit()
    db.refresh(member)
    return member


@router.delete(
    "/{staff_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete staff member",
    dependencies=[NotInPublicDemo],
)
def delete_staff(staff_id: int, db: DbDep, _admin: AdminUser) -> Response:
    db.delete(get_or_404(db, Staff, staff_id, "Staff member"))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
