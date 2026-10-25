"""Authentication endpoints (OAuth2 password flow + refresh-token rotation)."""

from typing import Annotated

from fastapi import APIRouter, Body, Cookie, Depends, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select

from app.api.deps import AdminUser, CurrentUser, DbDep, SettingsDep, get_login_limiter
from app.core.config import Settings
from app.core.errors import ERROR_RESPONSES, AppError, conflict
from app.core.passwords import hash_password
from app.core.rate_limit import LoginRateLimiter
from app.models import Role, Teacher, User
from app.schemas.auth import RefreshRequest, TokenResponse, UserCreate, UserRead
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["auth"], responses=ERROR_RESPONSES)

REFRESH_COOKIE = "edupulse_refresh"
REFRESH_COOKIE_PATH = "/api/v1/auth"


def _set_refresh_cookie(response: Response, token: str, settings: Settings) -> None:
    response.set_cookie(
        REFRESH_COOKIE,
        token,
        max_age=settings.refresh_token_days * 86400,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="strict",
        path=REFRESH_COOKIE_PATH,
    )


def _token_response(
    response: Response, issued: auth_service.IssuedTokens, settings: Settings
) -> TokenResponse:
    _set_refresh_cookie(response, issued.refresh_token, settings)
    response.headers["Cache-Control"] = "no-store"
    return TokenResponse(
        access_token=issued.access_token,
        expires_in=issued.expires_in,
        refresh_token=issued.refresh_token,
    )


def _invalid_refresh() -> AppError:
    return AppError(status.HTTP_401_UNAUTHORIZED, "Invalid or expired refresh token")


@router.post("/login", response_model=TokenResponse, summary="Log in with e-mail and password")
def login(
    request: Request,
    response: Response,
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: DbDep,
    settings: SettingsDep,
    limiter: Annotated[LoginRateLimiter, Depends(get_login_limiter)],
) -> TokenResponse:
    """OAuth2 password flow: send ``username`` (the e-mail) and ``password`` as form fields.

    Repeated failures from the same client are rate-limited (HTTP 429 with ``Retry-After``).
    """
    client = request.client.host if request.client else "unknown"
    wait = limiter.retry_after(client, form.username)
    if wait:
        raise AppError(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Too many failed login attempts. Try again later.",
            headers={"Retry-After": str(wait)},
        )
    user = auth_service.authenticate(db, form.username, form.password)
    if user is None:
        limiter.record_failure(client, form.username)
        raise AppError(
            status.HTTP_401_UNAUTHORIZED,
            "Incorrect e-mail or password",
            code="invalid_credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    limiter.record_success(client, form.username)
    issued = auth_service.issue_tokens(db, user, settings)
    db.commit()
    return _token_response(response, issued, settings)


@router.post("/refresh", response_model=TokenResponse, summary="Rotate the refresh token")
def refresh(
    response: Response,
    db: DbDep,
    settings: SettingsDep,
    body: Annotated[RefreshRequest | None, Body()] = None,
    cookie_token: Annotated[str | None, Cookie(alias=REFRESH_COOKIE)] = None,
) -> TokenResponse:
    raw = (body.refresh_token if body else None) or cookie_token
    if not raw:
        raise _invalid_refresh()
    issued = auth_service.rotate_refresh_token(db, raw, settings)
    db.commit()  # persist revocations even when the token is rejected
    if issued is None:
        response.delete_cookie(REFRESH_COOKIE, path=REFRESH_COOKIE_PATH)
        raise _invalid_refresh()
    return _token_response(response, issued, settings)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="Revoke a refresh token")
def logout(
    db: DbDep,
    body: Annotated[RefreshRequest | None, Body()] = None,
    cookie_token: Annotated[str | None, Cookie(alias=REFRESH_COOKIE)] = None,
) -> Response:
    raw = (body.refresh_token if body else None) or cookie_token
    if raw:
        auth_service.revoke_refresh_token(db, raw)
        db.commit()
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    response.delete_cookie(REFRESH_COOKIE, path=REFRESH_COOKIE_PATH)
    return response


@router.get("/me", response_model=UserRead, summary="Current user")
def me(user: CurrentUser) -> User:
    return user


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a user account (admin only)",
)
def register(payload: UserCreate, db: DbDep, _admin: AdminUser) -> User:
    if db.scalar(select(User.id).where(User.email == payload.email)) is not None:
        raise conflict("A user with this e-mail already exists")
    if payload.role == Role.TEACHER:
        teacher = db.get(Teacher, payload.teacher_id)
        if teacher is None:
            raise AppError(status.HTTP_422_UNPROCESSABLE_CONTENT, "Teacher profile not found")
        if db.scalar(select(User.id).where(User.teacher_id == teacher.id)) is not None:
            raise conflict("This teacher already has an account")
    user = User(
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        role=payload.role,
        teacher_id=payload.teacher_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
