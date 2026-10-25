"""Liveness and readiness probes."""

from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.deps import DbDep, SettingsDep
from app.services import risk

router = APIRouter(tags=["health"])


@router.get("/health", summary="Liveness probe")
def health() -> dict[str, str]:
    """The process is up. Does not touch dependencies."""
    return {"status": "ok"}


@router.get(
    "/ready",
    summary="Readiness probe",
    responses={503: {"description": "A dependency is not available"}},
)
def ready(db: DbDep, settings: SettingsDep) -> JSONResponse:
    """The database answers and the early-warning model loads (hash verified)."""
    checks: dict[str, Any] = {}
    try:
        db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "unavailable"
    try:
        checks["model"] = f"ok (v{risk.load_model(settings.model_dir).version})"
    except risk.ModelUnavailableError:
        checks["model"] = "unavailable"
    ok = all(str(v).startswith("ok") for v in checks.values())
    return JSONResponse(
        {"status": "ready" if ok else "not_ready", "checks": checks},
        status_code=200 if ok else 503,
    )
