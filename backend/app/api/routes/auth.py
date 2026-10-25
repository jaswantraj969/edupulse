"""Authentication endpoints (OAuth2 password flow + refresh-token rotation).

The refresh token is only ever sent as an httpOnly, Secure, SameSite=Strict cookie scoped to
``/api/v1/auth``; it never appears in a response body, so page JavaScript cannot read it.
"""

from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select

from app.api.deps import (
    AdminUser,
    DbDep,
    SettingsDep,
    SignedInUser,
    disabled_in_public_demo,
    get_login_limiter,
    get_signup_limiter,
)
from app.core.config import Settings
from app.core.errors import ERROR_RESPONSES, AppError, conflict
from app.core.passwords import hash_password
from app.core.rate_limit import LoginRateLimiter, SlidingWindowLimiter
from app.models import AccountStatus, Role, Teacher, User
from app.schemas.auth import (
    SignupAccepted,
    SignupRequest,
    TokenResponse,
    UserCreate,
    UserRead,
)
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


def _clear_refresh_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        REFRESH_COOKIE,
        path=REFRESH_COOKIE_PATH,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="strict",
    )


def _token_response(
    response: Response, issued: auth_service.IssuedTokens, settings: Settings
) -> TokenResponse:
    _set_refresh_cookie(response, issued.refresh_token, settings)
    response.headers["Cache-Control"] = "no-store"
    return TokenResponse(access_token=issued.access_token, expires_in=issued.expires_in)


def _invalid_refresh(settings: Settings) -> AppError:
    """401 that also clears the cookie (errors are rendered as a new response, so the header
    has to travel with the exception)."""
    clearing = Response()
    _clear_refresh_cookie(clearing, settings)
    return AppError(
        status.HTTP_401_UNAUTHORIZED,
        "Invalid or expired refresh token",
        headers={"set-cookie": clearing.headers["set-cookie"]},
    )


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
    cookie_token: Annotated[str | None, Cookie(alias=REFRESH_COOKIE)] = None,
) -> TokenResponse:
    """Uses the refresh cookie; returns a new access token and rotates the cookie."""
    if not cookie_token:
        raise _invalid_refresh(settings)
    issued = auth_service.rotate_refresh_token(db, cookie_token, settings)
    db.commit()  # persist revocations even when the token is rejected
    if issued is None:
        raise _invalid_refresh(settings)
    return _token_response(response, issued, settings)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="Revoke a refresh token")
def logout(
    db: DbDep,
    settings: SettingsDep,
    cookie_token: Annotated[str | None, Cookie(alias=REFRESH_COOKIE)] = None,
) -> Response:
    if cookie_token:
        auth_service.revoke_refresh_token(db, cookie_token)
        db.commit()
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    _clear_refresh_cookie(response, settings)
    return response


@router.get("/me", response_model=UserRead, summary="Current user")
def me(user: SignedInUser) -> User:
    """Also answers for accounts pending approval, so the app can show their status."""
    return user


SIGNUP_ACCEPTED = (
    "Thank you. If the request can be accepted, an administrator will review it; you can sign in "
    "to see its status."
)


@router.post(
    "/signup",
    response_model=SignupAccepted,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Request an account (self sign-up)",
)
def signup(
    payload: SignupRequest,
    request: Request,
    db: DbDep,
    limiter: Annotated[SlidingWindowLimiter, Depends(get_signup_limiter)],
) -> SignupAccepted:
    """Creates an account with status ``pending`` and no role: it can sign in, but every data
    route answers 403 ``account_pending`` until an administrator approves it.

    The response is the same whether or not the e-mail already has an account, and takes about
    as long, so the endpoint cannot be used to discover accounts. Requests are rate-limited per
    client (HTTP 429 with ``Retry-After``).
    """
    client = request.client.host if request.client else "unknown"
    wait = limiter.retry_after(client)
    if wait:
        raise AppError(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Too many requests. Try again later.",
            headers={"Retry-After": str(wait)},
        )
    limiter.hit(client)
    if db.scalar(select(User.id).where(User.email == payload.email)) is not None:
        auth_service.burn_password_hash(payload.password)
    else:
        db.add(
            User(
                email=payload.email,
                full_name=payload.full_name,
                hashed_password=hash_password(payload.password),
                role=None,
                status=AccountStatus.PENDING,
                signup_note=payload.note or None,
            )
        )
        db.commit()
    return SignupAccepted(message=SIGNUP_ACCEPTED)


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a user account (admin only)",
)
def register(payload: UserCreate, db: DbDep, settings: SettingsDep, _admin: AdminUser) -> User:
    """In the public demo, administrator accounts cannot be created."""
    if settings.public_demo and payload.role == Role.ADMIN:
        raise disabled_in_public_demo()
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
