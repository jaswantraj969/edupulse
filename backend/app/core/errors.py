"""Consistent JSON error responses.

Every error leaves the API as::

    {"error": {"code": "not_found", "message": "Student not found", "details": null,
               "request_id": "3f2c..."}}

``request_id`` matches the ``X-Request-ID`` response header and the server logs.
"""

import logging
from typing import Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from starlette.exceptions import HTTPException as StarletteHTTPException

_DEFAULT_CODES = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    413: "payload_too_large",
    422: "validation_error",
    429: "rate_limited",
}


class AppError(HTTPException):
    """An HTTP error with a stable machine-readable ``code``."""

    def __init__(
        self,
        status_code: int,
        message: str,
        code: str | None = None,
        details: Any = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(status_code=status_code, detail=message, headers=headers)
        self.code = code or _DEFAULT_CODES.get(status_code, "error")
        self.details = details


def not_found(what: str) -> AppError:
    return AppError(status.HTTP_404_NOT_FOUND, f"{what} not found")


def forbidden(message: str = "You do not have access to this resource") -> AppError:
    return AppError(status.HTTP_403_FORBIDDEN, message)


def conflict(message: str, details: Any = None) -> AppError:
    return AppError(status.HTTP_409_CONFLICT, message, details=details)


class ErrorBody(BaseModel):
    code: str
    message: str
    details: Any = None
    request_id: str | None = None


class ErrorResponse(BaseModel):
    error: ErrorBody


ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    code: {"model": ErrorResponse} for code in (400, 401, 403, 404, 409, 422, 429)
}


log = logging.getLogger("edupulse.errors")


def _request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def _body(request: Request, code: str, message: str, details: Any = None) -> dict[str, Any]:
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details,
            "request_id": _request_id(request),
        }
    }


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def _http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = getattr(exc, "code", None) or _DEFAULT_CODES.get(exc.status_code, "error")
        return JSONResponse(
            _body(request, code, str(exc.detail), getattr(exc, "details", None)),
            status_code=exc.status_code,
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        details = [
            {
                "field": ".".join(str(p) for p in err["loc"] if p not in ("body", "query")),
                "message": err["msg"],
                "type": err["type"],
            }
            for err in exc.errors()
        ]
        return JSONResponse(
            _body(request, "validation_error", "Request validation failed", details),
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )

    @app.exception_handler(IntegrityError)
    async def _integrity_error(request: Request, exc: IntegrityError) -> JSONResponse:
        # Route handlers pre-check uniqueness and references for friendly messages; this is the
        # backstop for races. Database details are not echoed to the client.
        log.warning("integrity error", extra={"error": type(exc.orig).__name__})
        return JSONResponse(
            _body(request, "conflict", "The change conflicts with existing data"),
            status_code=status.HTTP_409_CONFLICT,
        )

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        # Runs outside the request-context middleware, so the id comes from request.state.
        request_id = _request_id(request)
        log.error(
            "unhandled error",
            exc_info=exc,
            extra={"request_id": request_id, "path": request.url.path},
        )
        return JSONResponse(
            _body(request, "internal_error", "Internal server error"),
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            headers={"X-Request-ID": request_id} if request_id else None,
        )
