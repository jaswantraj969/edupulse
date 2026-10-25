"""account status and self sign-up

Adds ``users.status`` (pending / active / rejected / disabled) in place of ``users.is_active``,
lets accounts without a role exist while pending, stores the sign-up note and the review
decision, and allows the account approval actions in the audit log. Existing users become
active (or disabled when ``is_active`` was false).

Revision ID: 41ade5bff306
Revises: 0d96e7cbb08f
Create Date: 2026-10-26

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "41ade5bff306"
down_revision: Union[str, Sequence[str], None] = "0d96e7cbb08f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

STATUSES = "'pending', 'active', 'rejected', 'disabled'"
RISK_ACTIONS = "'risk.view_class', 'risk.view_student', 'risk.export_class'"
ACCOUNT_ACTIONS = "'account.approve', 'account.reject'"

users = sa.table(
    "users",
    sa.column("is_active", sa.Boolean()),
    sa.column("status", sa.String()),
)


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("status", sa.String(length=20), server_default="active", nullable=False)
        )
        batch_op.add_column(sa.Column("signup_note", sa.String(length=500), nullable=True))
        batch_op.add_column(sa.Column("review_note", sa.String(length=500), nullable=True))
        batch_op.add_column(sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("reviewed_by_id", sa.Integer(), nullable=True))

    op.execute(users.update().where(users.c.is_active.is_(sa.false())).values(status="disabled"))

    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_constraint(op.f("ck_users_teacher_has_profile"), type_="check")
        batch_op.drop_column("is_active")
        batch_op.alter_column("role", existing_type=sa.String(length=20), nullable=True)
        batch_op.create_check_constraint(
            op.f("ck_users_account_status"), f"status IN ({STATUSES})"
        )
        batch_op.create_check_constraint(
            op.f("ck_users_active_has_role"),
            "status <> 'active' OR role = 'admin' OR (role = 'teacher' AND teacher_id IS NOT NULL)",
        )
        batch_op.create_foreign_key(
            op.f("fk_users_reviewed_by_id_users"),
            "users",
            ["reviewed_by_id"],
            ["id"],
            ondelete="SET NULL",
        )

    with op.batch_alter_table("audit_logs", schema=None) as batch_op:
        batch_op.drop_constraint(op.f("ck_audit_logs_audit_action"), type_="check")
        batch_op.create_check_constraint(
            op.f("ck_audit_logs_audit_action"), f"action IN ({RISK_ACTIONS}, {ACCOUNT_ACTIONS})"
        )


def downgrade() -> None:
    """Downgrade schema. Pending and rejected accounts cannot be represented before this
    revision and are removed, as are the account audit entries."""
    op.execute(sa.text("DELETE FROM audit_logs WHERE action LIKE 'account.%'"))
    op.execute(sa.text("UPDATE users SET reviewed_by_id = NULL"))
    op.execute(sa.text("DELETE FROM users WHERE status IN ('pending', 'rejected')"))

    with op.batch_alter_table("audit_logs", schema=None) as batch_op:
        batch_op.drop_constraint(op.f("ck_audit_logs_audit_action"), type_="check")
        batch_op.create_check_constraint(
            op.f("ck_audit_logs_audit_action"), f"action IN ({RISK_ACTIONS})"
        )

    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False)
        )

    op.execute(
        users.update().where(users.c.status == "disabled").values(is_active=sa.false())
    )

    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_constraint(op.f("fk_users_reviewed_by_id_users"), type_="foreignkey")
        batch_op.drop_constraint(op.f("ck_users_active_has_role"), type_="check")
        batch_op.drop_constraint(op.f("ck_users_account_status"), type_="check")
        batch_op.alter_column("role", existing_type=sa.String(length=20), nullable=False)
        batch_op.drop_column("reviewed_by_id")
        batch_op.drop_column("reviewed_at")
        batch_op.drop_column("review_note")
        batch_op.drop_column("signup_note")
        batch_op.drop_column("status")
        batch_op.create_check_constraint(
            op.f("ck_users_teacher_has_profile"), "role = 'admin' OR teacher_id IS NOT NULL"
        )
