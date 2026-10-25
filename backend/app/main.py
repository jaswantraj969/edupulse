"""FastAPI application factory."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import (
    assessments,
    attendance,
    auth,
    catalog,
    classes,
    dashboard,
    health,
    risk,
    staff,
    students,
    teachers,
)
from app.core.config import Settings, get_settings
from app.core.errors import install_error_handlers
from app.core.rate_limit import LoginRateLimiter

API_PREFIX = "/api/v1"


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    settings.require_jwt_secret()  # fail fast at startup rather than on first login
    app = FastAPI(
        title="EduPulse API",
        version="0.1.0",
        description="School management API with an explainable early-warning module.",
        openapi_url=f"{API_PREFIX}/openapi.json",
        docs_url=f"{API_PREFIX}/docs",
        redoc_url=f"{API_PREFIX}/redoc",
    )
    app.state.settings = settings
    app.state.login_limiter = LoginRateLimiter(
        settings.login_rate_limit_attempts, settings.login_rate_limit_window_seconds
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    )
    install_error_handlers(app)
    routers = (
        health.router,
        auth.router,
        dashboard.router,
        students.router,
        teachers.router,
        staff.router,
        classes.router,
        attendance.router,
        assessments.router,
        catalog.router,
        risk.router,
    )
    for router in routers:
        app.include_router(router, prefix=API_PREFIX)
    return app


app = create_app()
