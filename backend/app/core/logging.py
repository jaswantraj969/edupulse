"""Structured (JSON) logging with a per-request id available to every log record."""

import json
import logging
import sys
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
user_id_var: ContextVar[int | None] = ContextVar("user_id", default=None)

# Attributes every LogRecord has; anything else passed via ``extra=`` is emitted as a field.
_STANDARD = set(logging.LogRecord("", 0, "", 0, "", None, None).__dict__) | {"message", "asctime"}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if (request_id := request_id_var.get()) is not None:
            payload["request_id"] = request_id
        if (user_id := user_id_var.get()) is not None:
            payload["user_id"] = user_id
        for key, value in record.__dict__.items():
            if key not in _STANDARD and not key.startswith("_"):
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


class TextFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        base = super().format(record)
        request_id = request_id_var.get()
        return f"{base} [request_id={request_id}]" if request_id else base


def configure_logging(level: str = "INFO", json_output: bool = True) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        JsonFormatter() if json_output else TextFormatter("%(levelname)s %(name)s: %(message)s")
    )
    handler.set_name("edupulse")
    root = logging.getLogger()
    # Replace only our own handler (idempotent; keeps handlers installed by the host or tests).
    root.handlers = [h for h in root.handlers if h.get_name() != "edupulse"] + [handler]
    root.setLevel(level.upper())
    # Uvicorn's own access log is replaced by the structured one from our middleware.
    logging.getLogger("uvicorn.access").disabled = True
