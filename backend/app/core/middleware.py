"""Request id + structured access log, and security headers.

Pure ASGI middleware (no BaseHTTPMiddleware) so streaming responses and context variables
behave correctly.
"""

import logging
import re
import time
import uuid
from collections.abc import Iterable

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.logging import request_id_var, user_id_var

access_log = logging.getLogger("edupulse.access")

REQUEST_ID_HEADER = "X-Request-ID"
# Accept a caller's id only if it is short and plain; otherwise generate one (log injection).
_VALID_ID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


class RequestContextMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        incoming = (
            dict(scope["headers"]).get(REQUEST_ID_HEADER.lower().encode(), b"").decode("latin-1")
        )
        request_id = incoming if _VALID_ID.match(incoming) else uuid.uuid4().hex
        rid_token = request_id_var.set(request_id)
        uid_token = user_id_var.set(None)
        scope.setdefault("state", {})["request_id"] = request_id
        started = time.perf_counter()
        status_code = 500

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                MutableHeaders(scope=message)[REQUEST_ID_HEADER] = request_id
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            access_log.info(
                "request",
                extra={
                    "method": scope["method"],
                    "path": scope["path"],
                    "status": status_code,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 1),
                    "client": (scope.get("client") or ("-",))[0],
                },
            )
            user_id_var.reset(uid_token)
            request_id_var.reset(rid_token)


# OpenAPI docs pages load Swagger UI / ReDoc assets from a CDN, so they get a looser CSP.
_DOCS_PATHS = ("/api/v1/docs", "/api/v1/redoc")
_API_CSP = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"
_DOCS_CSP = (
    "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
    "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
    "img-src 'self' data: https://fastapi.tiangolo.com https://cdn.redoc.ly; "
    "font-src 'self' https://fonts.gstatic.com; worker-src blob:; frame-ancestors 'none'"
)


class SecurityHeadersMiddleware:
    def __init__(self, app: ASGIApp, hsts: bool = False) -> None:
        self.app = app
        self.hsts = hsts

    def _headers(self, path: str) -> Iterable[tuple[str, str]]:
        yield "X-Content-Type-Options", "nosniff"
        yield "X-Frame-Options", "DENY"
        yield "Referrer-Policy", "no-referrer"
        yield "Permissions-Policy", "camera=(), microphone=(), geolocation=(), payment=()"
        yield "Cross-Origin-Opener-Policy", "same-origin"
        yield "Content-Security-Policy", _DOCS_CSP if path.startswith(_DOCS_PATHS) else _API_CSP
        if not path.startswith(_DOCS_PATHS):
            # API responses carry personal data: never cache them in shared or browser caches.
            yield "Cache-Control", "no-store"
        if self.hsts:
            yield "Strict-Transport-Security", "max-age=31536000; includeSubDomains"

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                for name, value in self._headers(scope["path"]):
                    if name not in headers:
                        headers[name] = value
            await send(message)

        await self.app(scope, receive, send_wrapper)
