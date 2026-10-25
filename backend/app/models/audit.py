"""Append-only audit log for access to early-warning risk scores."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import str_enum


class AuditAction(StrEnum):
    RISK_VIEW_CLASS = "risk.view_class"
    RISK_VIEW_STUDENT = "risk.view_student"
    RISK_EXPORT_CLASS = "risk.export_class"


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (Index("ix_audit_logs_created_at", "created_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.current_timestamp()
    )
    # Kept if the user is later deleted; the e-mail is copied so the trail stays readable.
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    user_email: Mapped[str] = mapped_column(String(254))
    action: Mapped[AuditAction] = mapped_column(str_enum(AuditAction, "audit_action"), index=True)
    target_type: Mapped[str] = mapped_column(String(20))
    target_id: Mapped[int] = mapped_column(Integer)
    detail: Mapped[str | None] = mapped_column(String(255))
    ip_address: Mapped[str | None] = mapped_column(String(45))
