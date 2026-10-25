"""Account requests (self sign-ups) reviewed by administrators."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from app.models.enums import AccountStatus, Role


class AccountRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str
    status: AccountStatus
    signup_note: str | None
    created_at: datetime


class AccountRequestList(BaseModel):
    items: list[AccountRequest]
    total: int


class ApproveRequest(BaseModel):
    role: Role
    teacher_id: int | None = Field(
        default=None, description="Required for teachers: an existing, unlinked teacher profile"
    )

    @model_validator(mode="after")
    def _teacher_link(self) -> "ApproveRequest":
        if self.role == Role.TEACHER and self.teacher_id is None:
            raise ValueError("teacher_id is required for teacher accounts")
        if self.role == Role.ADMIN and self.teacher_id is not None:
            raise ValueError("admin accounts cannot be linked to a teacher profile")
        return self


class RejectRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


class UnlinkedTeacher(BaseModel):
    id: int
    employee_no: str
    full_name: str
    email: str
