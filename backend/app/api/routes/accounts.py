"""Account requests: administrators approve or reject self sign-ups."""

from fastapi import APIRouter, Request, status
from sqlalchemy import func, select

from app.api.deps import AdminUser, DbDep, NotInPublicDemo
from app.core.errors import ERROR_RESPONSES, AppError, conflict, not_found
from app.core.security import utcnow
from app.models import AccountStatus, AuditAction, Role, Teacher, User
from app.schemas.accounts import (
    AccountRequest,
    AccountRequestList,
    ApproveRequest,
    RejectRequest,
    UnlinkedTeacher,
)
from app.services import audit
from app.services import auth as auth_service

router = APIRouter(prefix="/account-requests", tags=["account requests"], responses=ERROR_RESPONSES)


def _pending(db: DbDep, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None or user.status != AccountStatus.PENDING:
        raise not_found("Account request")
    return user


@router.get("", response_model=AccountRequestList, summary="Pending account requests")
def list_requests(db: DbDep, _admin: AdminUser) -> AccountRequestList:
    """Oldest first, so requests are handled in the order they arrived."""
    users = list(
        db.scalars(
            select(User)
            .where(User.status == AccountStatus.PENDING)
            .order_by(User.created_at, User.id)
        )
    )
    return AccountRequestList(
        items=[AccountRequest.model_validate(u) for u in users], total=len(users)
    )


@router.get(
    "/unlinked-teachers",
    response_model=list[UnlinkedTeacher],
    summary="Teacher profiles without an account",
)
def unlinked_teachers(db: DbDep, _admin: AdminUser) -> list[UnlinkedTeacher]:
    """Candidates for approving a request as a teacher."""
    linked = select(User.teacher_id).where(User.teacher_id.is_not(None))
    teachers = db.scalars(
        select(Teacher)
        .where(Teacher.id.not_in(linked))
        .order_by(Teacher.last_name, Teacher.first_name, Teacher.id)
    )
    return [
        UnlinkedTeacher(id=t.id, employee_no=t.employee_no, full_name=t.full_name, email=t.email)
        for t in teachers
    ]


@router.get("/count", summary="Number of pending requests (sidebar badge)")
def pending_count(db: DbDep, _admin: AdminUser) -> dict[str, int]:
    count = db.scalar(
        select(func.count()).select_from(User).where(User.status == AccountStatus.PENDING)
    )
    return {"pending": count or 0}


@router.post(
    "/{user_id}/approve",
    response_model=AccountRequest,
    summary="Approve a request",
    dependencies=[NotInPublicDemo],
)
def approve(
    user_id: int, payload: ApproveRequest, request: Request, db: DbDep, admin: AdminUser
) -> User:
    """Grants the chosen role. A teacher must be linked to an existing teacher profile that has
    no account yet; their access is then exactly that teacher's classes. Recorded in the audit
    log."""
    user = _pending(db, user_id)
    if payload.role == Role.TEACHER:
        teacher = db.get(Teacher, payload.teacher_id)
        if teacher is None:
            raise AppError(status.HTTP_422_UNPROCESSABLE_CONTENT, "Teacher profile not found")
        if db.scalar(select(User.id).where(User.teacher_id == teacher.id)) is not None:
            raise conflict("This teacher profile is already linked to an account")
    user.role = payload.role
    user.teacher_id = payload.teacher_id
    user.status = AccountStatus.ACTIVE
    user.reviewed_at = utcnow()
    user.reviewed_by_id = admin.id
    db.flush()
    audit.record(
        db,
        request,
        admin,
        AuditAction.ACCOUNT_APPROVE,
        "user",
        user.id,
        f"{user.email} as {payload.role.value}",
    )
    db.refresh(user)
    return user


@router.post(
    "/{user_id}/reject",
    response_model=AccountRequest,
    summary="Reject a request",
    dependencies=[NotInPublicDemo],
)
def reject(
    user_id: int, payload: RejectRequest, request: Request, db: DbDep, admin: AdminUser
) -> User:
    """The account can no longer sign in (it gets the same error as a wrong password) and its
    sessions are revoked. Recorded in the audit log."""
    user = _pending(db, user_id)
    user.status = AccountStatus.REJECTED
    user.review_note = payload.reason.strip() if payload.reason else None
    user.reviewed_at = utcnow()
    user.reviewed_by_id = admin.id
    auth_service.revoke_all(db, user.id)
    db.flush()
    audit.record(db, request, admin, AuditAction.ACCOUNT_REJECT, "user", user.id, user.email)
    db.refresh(user)
    return user
