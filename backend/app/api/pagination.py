"""Pagination, sorting and search helpers shared by list endpoints."""

from collections.abc import Mapping, Sequence
from typing import Annotated, Any, Literal

from fastapi import Depends, Query, status
from pydantic import BaseModel
from sqlalchemy import ColumnElement, Select, func, or_, select
from sqlalchemy.orm import InstrumentedAttribute, Session

from app.core.errors import AppError

MAX_PAGE_SIZE = 100

# Any select statement, whatever its column types (Select is variadic in SQLAlchemy 2.1).
type AnySelect = Select[*tuple[Any, ...]]


class PageParams(BaseModel):
    page: int
    page_size: int
    sort: str | None
    order: Literal["asc", "desc"]
    q: str | None


def page_params(
    page: Annotated[int, Query(ge=1, description="1-based page number")] = 1,
    page_size: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = 20,
    sort: Annotated[str | None, Query(description="Field to sort by")] = None,
    order: Annotated[Literal["asc", "desc"], Query()] = "asc",
    q: Annotated[str | None, Query(max_length=100, description="Free-text search")] = None,
) -> PageParams:
    return PageParams(
        page=page, page_size=page_size, sort=sort, order=order, q=(q or "").strip() or None
    )


PageDep = Annotated[PageParams, Depends(page_params)]


class Page[T](BaseModel):
    items: list[T]
    total: int
    page: int
    page_size: int


def search_clause(
    q: str | None, columns: Sequence[InstrumentedAttribute[Any]]
) -> ColumnElement[bool] | None:
    if not q:
        return None
    pattern = f"%{q.lower()}%"
    return or_(*(func.lower(col).like(pattern) for col in columns))


def apply_sort(
    stmt: AnySelect,
    params: PageParams,
    sortable: Mapping[str, InstrumentedAttribute[Any] | ColumnElement[Any]],
    default: str,
    tiebreaker: InstrumentedAttribute[Any],
) -> AnySelect:
    key = params.sort or default
    column = sortable.get(key)
    if column is None:
        raise AppError(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            f"Cannot sort by '{key}'",
            details={"allowed": sorted(sortable)},
        )
    if params.order == "desc":
        # The tie-breaker follows the direction so equal keys keep a consistent order.
        return stmt.order_by(column.desc(), tiebreaker.desc())
    return stmt.order_by(column.asc(), tiebreaker.asc())


def count_rows(db: Session, stmt: AnySelect) -> int:
    return db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0


def _window(stmt: AnySelect, params: PageParams) -> AnySelect:
    return stmt.limit(params.page_size).offset((params.page - 1) * params.page_size)


def paginate(db: Session, stmt: AnySelect, params: PageParams) -> tuple[list[Any], int]:
    """Paginate a single-entity select; returns ``(objects, total)``."""
    rows = db.scalars(_window(stmt, params))
    return list(rows.unique().all()), count_rows(db, stmt)


def paginate_rows(db: Session, stmt: AnySelect, params: PageParams) -> tuple[list[Any], int]:
    """Paginate a multi-column select; returns ``(rows, total)``."""
    return list(db.execute(_window(stmt, params)).all()), count_rows(db, stmt)
