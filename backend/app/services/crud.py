"""Small generic helpers used by the CRUD routes."""

from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import DeclarativeBase, InstrumentedAttribute, Session

from app.core.errors import conflict, not_found
from app.models import AcademicYear


def get_or_404[M: DeclarativeBase](db: Session, model: type[M], obj_id: int, label: str) -> M:
    obj = db.get(model, obj_id)
    if obj is None:
        raise not_found(label)
    return obj


def apply_changes(
    obj: object, payload: BaseModel, exclude: set[str] | None = None
) -> dict[str, Any]:
    """Copy explicitly-set fields from ``payload`` onto ``obj``; returns the applied changes."""
    changes = payload.model_dump(exclude_unset=True, exclude=exclude or set())
    for field, value in changes.items():
        setattr(obj, field, value)
    return changes


def ensure_unique(
    db: Session,
    checks: Mapping[str, tuple[InstrumentedAttribute[Any], Any]],
    exclude_id: int | None = None,
) -> None:
    """Raise 409 when another row already holds one of the given unique values."""
    for label, (column, value) in checks.items():
        if value is None:
            continue
        stmt = select(column.class_.id).where(column == value)
        if exclude_id is not None:
            stmt = stmt.where(column.class_.id != exclude_id)
        if db.scalar(stmt.limit(1)) is not None:
            raise conflict(f"{label} '{value}' is already in use", details={"field": column.key})


def current_year(db: Session) -> AcademicYear | None:
    """The academic year with the latest start date (EduPulse runs one active year at a time)."""
    return db.scalar(select(AcademicYear).order_by(AcademicYear.start_date.desc()).limit(1))
