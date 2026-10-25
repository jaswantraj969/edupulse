"""Audit log (administrators only, read-only)."""

from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select

from app.api.deps import AdminUser, DbDep
from app.api.pagination import Page, PageDep, apply_sort, paginate, search_clause
from app.core.errors import ERROR_RESPONSES
from app.models.audit import AuditAction, AuditLog

router = APIRouter(prefix="/audit-logs", tags=["audit"], responses=ERROR_RESPONSES)

SORTABLE: dict[str, Any] = {"created_at": AuditLog.created_at, "user_email": AuditLog.user_email}


class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    user_id: int | None
    user_email: str
    action: AuditAction
    target_type: str
    target_id: int
    detail: str | None
    ip_address: str | None


@router.get("", response_model=Page[AuditLogRead], summary="List audit entries")
def list_audit_logs(
    db: DbDep,
    _admin: AdminUser,
    params: PageDep,
    action: Annotated[AuditAction | None, Query()] = None,
    user_id: int | None = None,
) -> Page[AuditLogRead]:
    """Newest first by default. ``q`` searches the user e-mail and detail."""
    stmt = select(AuditLog)
    if (clause := search_clause(params.q, [AuditLog.user_email, AuditLog.detail])) is not None:
        stmt = stmt.where(clause)
    if action is not None:
        stmt = stmt.where(AuditLog.action == action)
    if user_id is not None:
        stmt = stmt.where(AuditLog.user_id == user_id)
    if params.sort is None:
        params = params.model_copy(update={"sort": "created_at", "order": "desc"})
    stmt = apply_sort(stmt, params, SORTABLE, "created_at", AuditLog.id)
    items, total = paginate(db, stmt, params)
    return Page(
        items=[AuditLogRead.model_validate(i) for i in items],
        total=total,
        page=params.page,
        page_size=params.page_size,
    )
