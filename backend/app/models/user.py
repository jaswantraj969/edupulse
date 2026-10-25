"""Application user accounts."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import AccountStatus, Role, str_enum

if TYPE_CHECKING:
    from app.models.people import Teacher


class User(TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        # An active account has a role, and every active teacher account is linked to a teacher
        # profile. Pending (self sign-up), rejected and disabled accounts may have no role.
        CheckConstraint(
            "status <> 'active' OR role = 'admin' OR (role = 'teacher' AND teacher_id IS NOT NULL)",
            name="active_has_role",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(200))
    role: Mapped[Role | None] = mapped_column(str_enum(Role, "role"))
    status: Mapped[AccountStatus] = mapped_column(
        str_enum(AccountStatus, "account_status"),
        default=AccountStatus.ACTIVE,
        server_default=AccountStatus.ACTIVE.value,
    )
    teacher_id: Mapped[int | None] = mapped_column(
        ForeignKey("teachers.id", ondelete="SET NULL"), unique=True
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Self sign-up: the applicant's note, and the administrator's decision.
    signup_note: Mapped[str | None] = mapped_column(String(500))
    review_note: Mapped[str | None] = mapped_column(String(500))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewed_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    @property
    def can_sign_in(self) -> bool:
        """Active and pending accounts can sign in; pending ones only reach /auth/me."""
        return self.status in (AccountStatus.ACTIVE, AccountStatus.PENDING)

    teacher: Mapped[Teacher | None] = relationship(back_populates="user")
