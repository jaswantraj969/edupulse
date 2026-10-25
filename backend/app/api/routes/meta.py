"""Public facts about this installation, read by the login page before anyone signs in."""

from fastapi import APIRouter, Response
from sqlalchemy import select

from app.api.deps import DbDep, SettingsDep
from app.core.errors import ERROR_RESPONSES
from app.models import AccountStatus, ClassGroup, Role, Teacher, User
from app.schemas.meta import DemoAccount, Meta

router = APIRouter(tags=["meta"], responses=ERROR_RESPONSES)


@router.get("/meta", response_model=Meta, summary="Installation facts (public)")
def meta(db: DbDep, settings: SettingsDep, response: Response) -> Meta:
    """In demo mode, also the demo admin and one demo teacher with the seed password, so a
    visitor can try the app. Outside demo mode ``demo_accounts`` is always empty."""
    response.headers["Cache-Control"] = "no-store"
    password = settings.demo_password.get_secret_value()
    if not settings.demo_mode or not password:
        return Meta(demo_mode=settings.demo_mode, demo_accounts=[])
    active = User.status == AccountStatus.ACTIVE
    admin = db.scalar(select(User).where(active, User.role == Role.ADMIN).order_by(User.id))
    # A teacher with a homeroom class, so the demo shows a teacher's own classes.
    teacher = db.scalar(
        select(User)
        .join(Teacher, Teacher.id == User.teacher_id)
        .join(ClassGroup, ClassGroup.homeroom_teacher_id == Teacher.id)
        .where(active, User.role == Role.TEACHER)
        .order_by(User.id)
    )
    accounts = []
    if admin is not None:
        accounts.append(
            DemoAccount(role="admin", label="Administrator", email=admin.email, password=password)
        )
    if teacher is not None:
        accounts.append(
            DemoAccount(
                role="teacher",
                label=f"Teacher ({teacher.full_name})",
                email=teacher.email,
                password=password,
            )
        )
    return Meta(demo_mode=True, demo_accounts=accounts)
