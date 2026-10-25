"""Shared FastAPI dependencies: settings, database session, current user, role guards."""

from typing import Annotated

from fastapi import Depends, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import AppError, forbidden
from app.core.logging import user_id_var
from app.core.rate_limit import LoginRateLimiter
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models import Role, User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def get_app_settings(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


def get_login_limiter(request: Request) -> LoginRateLimiter:
    limiter: LoginRateLimiter = request.app.state.login_limiter
    return limiter


SettingsDep = Annotated[Settings, Depends(get_app_settings)]
DbDep = Annotated[Session, Depends(get_db)]


def _unauthorized(message: str = "Not authenticated") -> AppError:
    return AppError(status.HTTP_401_UNAUTHORIZED, message, headers={"WWW-Authenticate": "Bearer"})


def get_current_user(
    db: DbDep,
    settings: SettingsDep,
    token: Annotated[str | None, Depends(oauth2_scheme)],
) -> User:
    if not token:
        raise _unauthorized()
    claims = decode_access_token(token, settings)
    if claims is None:
        raise _unauthorized("Invalid or expired token")
    user = db.get(User, claims.user_id)
    if user is None or not user.is_active:
        raise _unauthorized("Invalid or expired token")
    user_id_var.set(user.id)  # attached to every log line of this request
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_admin(user: CurrentUser) -> User:
    if user.role != Role.ADMIN:
        raise forbidden("Administrator role required")
    return user


AdminUser = Annotated[User, Depends(require_admin)]
