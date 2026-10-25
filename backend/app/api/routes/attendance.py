"""Daily attendance per class: read the sheet for a day, and mark it in bulk."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DbDep
from app.api.routes.classes import roster
from app.core.errors import ERROR_RESPONSES, AppError
from app.models import AttendanceRecord, ClassGroup
from app.schemas.records import AttendanceBulk, AttendanceRow, AttendanceSheet
from app.services.access import ensure_class_access
from app.services.crud import get_or_404

router = APIRouter(prefix="/classes", tags=["attendance"], responses=ERROR_RESPONSES)


def _sheet(db: DbDep, class_group: ClassGroup, day: date) -> AttendanceSheet:
    students = roster(db, class_group.id)
    records = {
        r.student_id: r
        for r in db.scalars(
            select(AttendanceRecord).where(
                AttendanceRecord.date == day,
                AttendanceRecord.student_id.in_([s.id for s in students]),
            )
        )
    }
    return AttendanceSheet(
        class_id=class_group.id,
        class_name=class_group.name,
        date=day,
        records=[
            AttendanceRow(
                student_id=s.id,
                student_no=s.student_no,
                first_name=s.first_name,
                last_name=s.last_name,
                status=records[s.id].status if s.id in records else None,
                note=records[s.id].note if s.id in records else None,
            )
            for s in students
        ],
    )


def _check_day(class_group: ClassGroup, day: date) -> None:
    year = class_group.academic_year
    if day > date.today():
        raise AppError(status.HTTP_422_UNPROCESSABLE_CONTENT, "Attendance cannot be in the future")
    if not year.start_date <= day <= year.end_date:
        raise AppError(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            f"Date is outside academic year {year.name}",
        )


@router.get(
    "/{class_id}/attendance", response_model=AttendanceSheet, summary="Attendance sheet for a day"
)
def get_attendance(
    class_id: int,
    db: DbDep,
    user: CurrentUser,
    day: Annotated[date, Query(alias="date")],
) -> AttendanceSheet:
    """Every student in the class with their status for the day (``null`` = not yet marked)."""
    class_group = get_or_404(db, ClassGroup, class_id, "Class")
    ensure_class_access(db, user, class_id)
    return _sheet(db, class_group, day)


@router.put(
    "/{class_id}/attendance",
    response_model=AttendanceSheet,
    summary="Mark attendance for a class on one day (bulk upsert)",
)
def mark_attendance(
    class_id: int, payload: AttendanceBulk, db: DbDep, user: CurrentUser
) -> AttendanceSheet:
    """Creates or updates one record per listed student. Students not listed are untouched.
    Every listed student must be enrolled in the class."""
    class_group = get_or_404(db, ClassGroup, class_id, "Class")
    ensure_class_access(db, user, class_id)
    _check_day(class_group, payload.date)

    enrolled = {s.id for s in roster(db, class_id)}
    errors, seen = [], set()
    for i, mark in enumerate(payload.records):
        if mark.student_id in seen:
            errors.append({"field": f"records.{i}.student_id", "message": "Duplicate student"})
        elif mark.student_id not in enrolled:
            errors.append(
                {"field": f"records.{i}.student_id", "message": "Student is not in this class"}
            )
        seen.add(mark.student_id)
    if errors:
        raise AppError(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Attendance contains invalid rows",
            code="validation_error",
            details=errors,
        )

    existing = {
        r.student_id: r
        for r in db.scalars(
            select(AttendanceRecord).where(
                AttendanceRecord.date == payload.date, AttendanceRecord.student_id.in_(seen)
            )
        )
    }
    for mark in payload.records:
        record = existing.get(mark.student_id)
        if record is None:
            db.add(
                AttendanceRecord(
                    student_id=mark.student_id,
                    class_id=class_id,
                    date=payload.date,
                    status=mark.status,
                    note=mark.note,
                    recorded_by_id=user.id,
                )
            )
        else:
            record.status, record.note = mark.status, mark.note
            record.class_id, record.recorded_by_id = class_id, user.id
    db.commit()
    return _sheet(db, class_group, payload.date)
