"""Auth request/response schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.core.passwords import MAX_LENGTH, password_policy_errors
from app.models.enums import Role


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"  # noqa: S105  (OAuth2 token type, not a secret)
    expires_in: int = Field(description="Access-token lifetime in seconds")
    # The refresh token is deliberately not part of this body: it is only set as an httpOnly,
    # Secure, SameSite=Strict cookie (see app/api/routes/auth.py).


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str
    role: Role
    is_active: bool
    teacher_id: int | None
    last_login_at: datetime | None


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=200)
    password: str = Field(max_length=MAX_LENGTH)
    role: Role
    teacher_id: int | None = None

    @field_validator("email")
    @classmethod
    def _normalise_email(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("password")
    @classmethod
    def _password_policy(cls, value: str) -> str:
        errors = password_policy_errors(value)
        if errors:
            raise ValueError("Password " + "; ".join(errors))
        return value

    @model_validator(mode="after")
    def _teacher_link(self) -> "UserCreate":
        if self.role == Role.TEACHER and self.teacher_id is None:
            raise ValueError("teacher_id is required for teacher accounts")
        if self.role == Role.ADMIN and self.teacher_id is not None:
            raise ValueError("admin accounts cannot be linked to a teacher profile")
        return self
