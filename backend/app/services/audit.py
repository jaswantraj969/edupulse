"""Write audit entries for sensitive reads (risk scores)."""

from fastapi import Request
from sqlalchemy.orm import Session

from app.models import User
from app.models.audit import AuditAction, AuditLog


def record(
    db: Session,
    request: Request,
    user: User,
    action: AuditAction,
    target_type: str,
    target_id: int,
    detail: str | None = None,
) -> None:
    """Add and commit an audit entry. Called before the response is built, so a request that
    cannot be logged does not return risk data."""
    db.add(
        AuditLog(
            user_id=user.id,
            user_email=user.email,
            action=action,
            target_type=target_type,
            target_id=target_id,
            detail=detail[:255] if detail else None,
            ip_address=request.client.host if request.client else None,
        )
    )
    db.commit()
