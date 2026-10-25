"""Students: CRUD, search/filter/sort/pagination, CSV import/export, per-student records."""

from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, File, Query, Response, UploadFile, status
from fastapi.responses import Response as RawResponse
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.api.deps import AdminUser, CurrentUser, DbDep
from app.api.pagination import AnySelect, Page, PageDep, apply_sort, paginate_rows, search_clause
from app.core.errors import ERROR_RESPONSES, AppError, not_found
from app.models import (
    Assessment,
    AttendanceRecord,
    AttendanceStatus,
    ClassGroup,
    Enrolment,
    Grade,
    Student,
    StudentStatus,
    Subject,
    TeachingAssignment,
    Term,
)
from app.schemas.csv_io import ImportResult, RowError
from app.schemas.people import StudentCreate, StudentRead, StudentUpdate, check_student_dates
from app.schemas.records import AttendanceMonth, AttendanceSummary, StudentGradeRead
from app.services.access import ensure_student_access, visible_student_ids
from app.services.crud import apply_changes, current_year, ensure_unique, get_or_404
from app.services.csv_io import ParsedRow, csv_response, run_import

router = APIRouter(prefix="/students", tags=["students"], responses=ERROR_RESPONSES)

SORTABLE: dict[str, Any] = {
    "last_name": Student.last_name,
    "first_name": Student.first_name,
    "student_no": Student.student_no,
    "date_of_birth": Student.date_of_birth,
    "enrolled_on": Student.enrolled_on,
    "status": Student.status,
    "class_name": ClassGroup.name,
}
CSV_COLUMNS = [
    "student_no",
    "first_name",
    "last_name",
    "date_of_birth",
    "email",
    "phone",
    "guardian_name",
    "guardian_phone",
    "enrolled_on",
    "status",
    "prior_failures",
    "class_name",
]
CSV_REQUIRED = ["student_no", "first_name", "last_name", "date_of_birth", "enrolled_on"]


class StudentImportRow(StudentCreate):
    class_name: str | None = None


def _base_query(db: Session) -> AnySelect:
    """Students joined with their class in the current academic year (if any)."""
    year = current_year(db)
    year_id = year.id if year else -1
    return (
        select(Student, ClassGroup.id, ClassGroup.name)
        .outerjoin(
            Enrolment,
            and_(Enrolment.student_id == Student.id, Enrolment.academic_year_id == year_id),
        )
        .outerjoin(ClassGroup, ClassGroup.id == Enrolment.class_id)
    )


def _read(student: Student, class_id: int | None, class_name: str | None) -> StudentRead:
    return StudentRead.model_validate(student).model_copy(
        update={"class_id": class_id, "class_name": class_name}
    )


def _load(db: Session, student_id: int) -> StudentRead:
    row = db.execute(_base_query(db).where(Student.id == student_id)).first()
    if row is None:
        raise not_found("Student")
    return _read(*row)


def _set_class(db: Session, student: Student, class_id: int | None) -> None:
    """Enrol the student in ``class_id`` for its academic year, replacing any enrolment."""
    if class_id is None:
        return
    class_group = get_or_404(db, ClassGroup, class_id, "Class")
    existing = db.scalar(
        select(Enrolment).where(
            Enrolment.student_id == student.id,
            Enrolment.academic_year_id == class_group.academic_year_id,
        )
    )
    if existing is not None:
        existing.class_id = class_group.id
    else:
        db.add(
            Enrolment(
                student_id=student.id,
                class_id=class_group.id,
                academic_year_id=class_group.academic_year_id,
                enrolled_on=date.today(),
            )
        )


def _scoped(stmt: AnySelect, user: CurrentUser) -> AnySelect:
    scope = visible_student_ids(user)
    return stmt if scope is None else stmt.where(Student.id.in_(scope))


@router.get("", response_model=Page[StudentRead], summary="List students")
def list_students(
    db: DbDep,
    user: CurrentUser,
    params: PageDep,
    status_: Annotated[StudentStatus | None, Query(alias="status")] = None,
    class_id: int | None = None,
    grade_level: Annotated[int | None, Query(ge=1, le=13)] = None,
) -> Page[StudentRead]:
    """Search (`q`) matches name, student number and e-mail. Teachers see only their students."""
    stmt = _scoped(_base_query(db), user)
    columns = [Student.first_name, Student.last_name, Student.student_no, Student.email]
    if (clause := search_clause(params.q, columns)) is not None:
        stmt = stmt.where(clause)
    if status_ is not None:
        stmt = stmt.where(Student.status == status_)
    if class_id is not None:
        stmt = stmt.where(ClassGroup.id == class_id)
    if grade_level is not None:
        stmt = stmt.where(ClassGroup.grade_level == grade_level)
    stmt = apply_sort(stmt, params, SORTABLE, "last_name", Student.id)
    rows, total = paginate_rows(db, stmt, params)
    return Page(
        items=[_read(*row) for row in rows],
        total=total,
        page=params.page,
        page_size=params.page_size,
    )


@router.get("/export", summary="Export students as CSV", response_class=RawResponse)
def export_students(db: DbDep, user: CurrentUser) -> Response:
    stmt = _scoped(_base_query(db), user).order_by(Student.last_name, Student.id)
    rows = [
        [getattr(s, c) for c in CSV_COLUMNS[:-1]] + [class_name]
        for s, _class_id, class_name in db.execute(stmt).all()
    ]
    for row in rows:
        row[CSV_COLUMNS.index("status")] = row[CSV_COLUMNS.index("status")].value
    return csv_response("students.csv", CSV_COLUMNS, rows)


@router.post("/import", response_model=ImportResult, summary="Import students from CSV")
async def import_students(
    db: DbDep,
    _admin: AdminUser,
    file: Annotated[UploadFile, File(description="UTF-8 CSV with a header row")],
    dry_run: bool = False,
) -> ImportResult:
    """Validates every row first. If any row is invalid nothing is imported and the response is
    422 with ``details.errors`` listing ``{row, field, message}`` for each problem."""
    year = current_year(db)
    classes = (
        {
            c.name: c
            for c in db.scalars(select(ClassGroup).where(ClassGroup.academic_year_id == year.id))
        }
        if year
        else {}
    )

    def build(row: ParsedRow[StudentImportRow], errors: list[RowError]) -> Student | None:
        data = row.data
        class_group = None
        if data.class_name:
            class_group = classes.get(data.class_name)
            if class_group is None:
                errors.append(
                    RowError(
                        row=row.line, field="class_name", message="Unknown class in current year"
                    )
                )
                return None
        student = Student(**data.model_dump(exclude={"class_id", "class_name"}))
        if class_group is not None:
            student.enrolments.append(
                Enrolment(
                    class_group=class_group,
                    academic_year_id=class_group.academic_year_id,
                    enrolled_on=data.enrolled_on,
                )
            )
        return student

    return await run_import(
        db,
        file,
        schema=StudentImportRow,
        columns=CSV_COLUMNS,
        required=CSV_REQUIRED,
        unique={"student_no": Student.student_no, "email": Student.email},
        build=build,
        dry_run=dry_run,
    )


@router.post(
    "", response_model=StudentRead, status_code=status.HTTP_201_CREATED, summary="Create student"
)
def create_student(payload: StudentCreate, db: DbDep, _admin: AdminUser) -> StudentRead:
    ensure_unique(
        db,
        {
            "Student number": (Student.student_no, payload.student_no),
            "E-mail": (Student.email, payload.email),
        },
    )
    student = Student(**payload.model_dump(exclude={"class_id"}))
    db.add(student)
    db.flush()
    _set_class(db, student, payload.class_id)
    db.commit()
    return _load(db, student.id)


@router.get("/{student_id}", response_model=StudentRead, summary="Get student")
def get_student(student_id: int, db: DbDep, user: CurrentUser) -> StudentRead:
    get_or_404(db, Student, student_id, "Student")
    ensure_student_access(db, user, student_id)
    return _load(db, student_id)


@router.patch("/{student_id}", response_model=StudentRead, summary="Update student")
def update_student(
    student_id: int, payload: StudentUpdate, db: DbDep, _admin: AdminUser
) -> StudentRead:
    student = get_or_404(db, Student, student_id, "Student")
    ensure_unique(
        db,
        {
            "Student number": (Student.student_no, payload.student_no),
            "E-mail": (Student.email, payload.email),
        },
        exclude_id=student_id,
    )
    apply_changes(student, payload, exclude={"class_id"})
    try:
        check_student_dates(student.date_of_birth, student.enrolled_on)
    except ValueError as exc:
        raise AppError(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    _set_class(db, student, payload.class_id)
    db.commit()
    return _load(db, student_id)


@router.delete("/{student_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete student")
def delete_student(student_id: int, db: DbDep, _admin: AdminUser) -> Response:
    """Permanently deletes the student with their enrolments, attendance and grades."""
    db.delete(get_or_404(db, Student, student_id, "Student"))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/{student_id}/attendance", response_model=AttendanceSummary, summary="Attendance summary"
)
def student_attendance(student_id: int, db: DbDep, user: CurrentUser) -> AttendanceSummary:
    get_or_404(db, Student, student_id, "Student")
    ensure_student_access(db, user, student_id)
    rows = db.execute(
        select(AttendanceRecord.date, AttendanceRecord.status, func.count())
        .where(AttendanceRecord.student_id == student_id)
        .group_by(AttendanceRecord.date, AttendanceRecord.status)
    ).all()
    months: dict[str, dict[str, int]] = {}
    for day, record_status, n in sorted(rows):
        bucket = months.setdefault(day.strftime("%Y-%m"), {s.value: 0 for s in AttendanceStatus})
        bucket[record_status.value] += n
    totals = {s.value: sum(m[s.value] for m in months.values()) for s in AttendanceStatus}
    total = sum(totals.values())
    attended = totals["present"] + totals["late"]
    return AttendanceSummary(
        student_id=student_id,
        **totals,
        total=total,
        attendance_rate=round(attended / total, 4) if total else None,
        by_month=[AttendanceMonth(month=k, **v) for k, v in months.items()],
    )


@router.get(
    "/{student_id}/grades", response_model=list[StudentGradeRead], summary="Grades of a student"
)
def student_grades(student_id: int, db: DbDep, user: CurrentUser) -> list[StudentGradeRead]:
    get_or_404(db, Student, student_id, "Student")
    ensure_student_access(db, user, student_id)
    rows = db.execute(
        select(Grade, Assessment, Subject.name, Term.number)
        .join(Assessment, Assessment.id == Grade.assessment_id)
        .join(TeachingAssignment, TeachingAssignment.id == Assessment.assignment_id)
        .join(Subject, Subject.id == TeachingAssignment.subject_id)
        .join(Term, Term.id == Assessment.term_id)
        .where(Grade.student_id == student_id)
        .order_by(Assessment.assessed_on, Subject.name)
    ).all()
    return [
        StudentGradeRead(
            assessment_id=a.id,
            title=a.title,
            kind=a.kind,
            subject_name=subject_name,
            term_number=term_number,
            assessed_on=a.assessed_on,
            score=float(g.score),
            max_score=float(a.max_score),
            percentage=round(float(g.score / a.max_score * 100), 1),
        )
        for g, a, subject_name, term_number in rows
    ]
