"""Application user accounts."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, String, true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import Role, str_enum

if TYPE_CHECKING:
    from app.models.people import Teacher


class User(TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        # Every teacher account must be linked to a teacher profile.
        CheckConstraint("role = 'admin' OR teacher_id IS NOT NULL", name="teacher_has_profile"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(200))
    role: Mapped[Role] = mapped_column(str_enum(Role, "role"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
    teacher_id: Mapped[int | None] = mapped_column(
        ForeignKey("teachers.id", ondelete="SET NULL"), unique=True
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    teacher: Mapped[Teacher | None] = relationship(back_populates="user")
