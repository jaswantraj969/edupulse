"""Dashboard aggregates. Teachers get figures for their own classes only."""

from collections import defaultdict
from datetime import date, timedelta

from fastapi import APIRouter
from sqlalchemy import func, select
from sqlalchemy.orm import InstrumentedAttribute

from app.api.deps import CurrentUser, DbDep, SettingsDep
from app.api.pagination import AnySelect
from app.core.errors import ERROR_RESPONSES
from app.models import (
    Assessment,
    AttendanceRecord,
    AttendanceStatus,
    ClassGroup,
    Grade,
    Staff,
    Student,
    Teacher,
    TeachingAssignment,
)
from app.schemas.records import AttendancePoint, DashboardCounts, DashboardSummary, GradeBucket
from app.services.access import visible_class_ids, visible_student_ids
from app.services.crud import current_year

router = APIRouter(prefix="/dashboard", tags=["dashboard"], responses=ERROR_RESPONSES)

BUCKETS = [(lo, lo + 10) for lo in range(0, 100, 10)]


def _bucket_label(pct: float) -> str:
    lo = min(int(pct // 10) * 10, 90)
    return f"{lo}-{lo + 10}"


@router.get("", response_model=DashboardSummary, summary="Dashboard figures")
def dashboard(db: DbDep, user: CurrentUser, settings: SettingsDep) -> DashboardSummary:
    year = current_year(db)
    class_scope = visible_class_ids(user)
    student_scope = visible_student_ids(user)

    def scoped_count(column: InstrumentedAttribute[int], scope: AnySelect | None) -> int:
        stmt = select(func.count(column))
        if scope is not None:
            stmt = stmt.where(column.in_(scope))
        return db.scalar(stmt) or 0

    class_stmt = select(func.count()).select_from(ClassGroup)
    if year is not None:
        class_stmt = class_stmt.where(ClassGroup.academic_year_id == year.id)
    if class_scope is not None:
        class_stmt = class_stmt.where(ClassGroup.id.in_(class_scope))
    teacher_scope = (
        None
        if class_scope is None
        else select(TeachingAssignment.teacher_id).where(
            TeachingAssignment.class_id.in_(class_scope)
        )
    )
    counts = DashboardCounts(
        students=scoped_count(Student.id, student_scope),
        teachers=scoped_count(Teacher.id, teacher_scope),
        staff=db.scalar(select(func.count()).select_from(Staff)) or 0,
        classes=db.scalar(class_stmt) or 0,
    )

    # Weekly attendance rate ((present + late) / all records) for the current year.
    att = select(AttendanceRecord.date, AttendanceRecord.status, func.count()).group_by(
        AttendanceRecord.date, AttendanceRecord.status
    )
    if year is not None:
        att = att.where(AttendanceRecord.date.between(year.start_date, year.end_date))
    if class_scope is not None:
        att = att.where(AttendanceRecord.class_id.in_(class_scope))
    weeks: dict[date, list[int]] = defaultdict(lambda: [0, 0])
    for day, record_status, n in db.execute(att):
        week = day - timedelta(days=day.weekday())
        weeks[week][1] += n
        if record_status in (AttendanceStatus.PRESENT, AttendanceStatus.LATE):
            weeks[week][0] += n
    trend = [
        AttendancePoint(week_start=w, attendance_rate=round(a / t, 4), records=t)
        for w, (a, t) in sorted(weeks.items())
        if t
    ]

    # Distribution of each student's mean percentage across all graded work.
    pct = func.avg(Grade.score * 100.0 / Assessment.max_score)
    grades = (
        select(Grade.student_id, pct)
        .join(Assessment, Assessment.id == Grade.assessment_id)
        .group_by(Grade.student_id)
    )
    if student_scope is not None:
        grades = grades.where(Grade.student_id.in_(student_scope))
    distribution = dict.fromkeys((f"{lo}-{hi}" for lo, hi in BUCKETS), 0)
    for _student_id, mean in db.execute(grades):
        if mean is not None:
            distribution[_bucket_label(float(mean))] += 1

    return DashboardSummary(
        scope="school" if class_scope is None else "my_classes",
        counts=counts,
        attendance_trend=trend,
        grade_distribution=[GradeBucket(label=k, students=v) for k, v in distribution.items()],
        demo_mode=settings.demo_mode,
    )
