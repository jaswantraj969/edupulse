"""CSV import (validated, all-or-nothing, per-row errors) and export (formula-safe)."""

import csv
import io
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from fastapi import UploadFile, status
from fastapi.responses import Response
from pydantic import BaseModel, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import InstrumentedAttribute, Session

from app.core.errors import AppError
from app.schemas.csv_io import ImportResult, RowError

MAX_BYTES = 2 * 1024 * 1024
MAX_ROWS = 5000
_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


@dataclass
class ParsedRow[S: BaseModel]:
    line: int
    data: S
    raw: dict[str, str | None]


async def read_upload(file: UploadFile) -> str:
    content = await file.read(MAX_BYTES + 1)
    if len(content) > MAX_BYTES:
        raise AppError(
            status.HTTP_413_CONTENT_TOO_LARGE, f"CSV file exceeds {MAX_BYTES // 1024} KiB"
        )
    try:
        return content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise AppError(status.HTTP_400_BAD_REQUEST, "CSV file must be UTF-8 encoded") from exc


def parse_rows[S: BaseModel](
    text: str,
    schema: type[S],
    columns: Sequence[str],
    required: Iterable[str],
) -> tuple[list[ParsedRow[S]], list[RowError], int]:
    """Validate every data row against ``schema``. Returns rows, errors and the row count."""
    reader = csv.DictReader(io.StringIO(text))
    header = [h.strip() for h in (reader.fieldnames or [])]
    missing = [c for c in required if c not in header]
    unknown = [c for c in header if c not in columns]
    if missing or unknown:
        problems = []
        if missing:
            problems.append(f"missing columns: {', '.join(missing)}")
        if unknown:
            problems.append(f"unknown columns: {', '.join(unknown)}")
        raise AppError(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "CSV header is invalid: " + "; ".join(problems),
            code="invalid_csv",
            details={"expected": list(columns)},
        )
    reader.fieldnames = header

    rows: list[ParsedRow[S]] = []
    errors: list[RowError] = []
    count = 0
    for count, record in enumerate(reader, start=1):
        if count > MAX_ROWS:
            raise AppError(status.HTTP_413_CONTENT_TOO_LARGE, f"CSV file exceeds {MAX_ROWS} rows")
        line = count + 1
        if None in record:  # more cells than header columns
            errors.append(RowError(row=line, field=None, message="Too many values in row"))
            continue
        raw = {k: _clean(v) for k, v in record.items()}
        try:
            rows.append(ParsedRow(line, schema.model_validate(_drop_none(raw)), raw))
        except ValidationError as exc:
            for err in exc.errors():
                field = ".".join(str(p) for p in err["loc"]) or None
                errors.append(RowError(row=line, field=field, message=err["msg"]))
    return rows, errors, count


def _clean(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip()
    # Undo the formula escaping applied by ``safe_cell`` so exported files re-import cleanly.
    if value.startswith("'") and value[1:2] in _FORMULA_PREFIXES and value[1:2]:
        value = value[1:]
    return value or None


def _drop_none(raw: Mapping[str, str | None]) -> dict[str, str]:
    return {k: v for k, v in raw.items() if v is not None}


def check_unique[S: BaseModel](
    db: Session,
    rows: Sequence[ParsedRow[S]],
    fields: Mapping[str, InstrumentedAttribute[Any]],
) -> list[RowError]:
    """Duplicates inside the file and against existing database rows."""
    errors: list[RowError] = []
    for field, column in fields.items():
        values = [getattr(r.data, field) for r in rows]
        present = [v for v in values if v is not None]
        existing = set(db.scalars(select(column).where(column.in_(present)))) if present else set()
        seen: dict[Any, int] = {}
        for row, value in zip(rows, values, strict=True):
            if value is None:
                continue
            if value in existing:
                errors.append(
                    RowError(row=row.line, field=field, message=f"'{value}' already exists")
                )
            elif value in seen:
                errors.append(
                    RowError(
                        row=row.line,
                        field=field,
                        message=f"'{value}' duplicates line {seen[value]}",
                    )
                )
            else:
                seen[value] = row.line
    return errors


async def run_import[S: BaseModel](
    db: Session,
    file: UploadFile,
    *,
    schema: type[S],
    columns: Sequence[str],
    required: Iterable[str],
    unique: Mapping[str, InstrumentedAttribute[Any]],
    build: Callable[[ParsedRow[S], list[RowError]], object | None],
    dry_run: bool,
) -> ImportResult:
    """Validate the whole file; write nothing unless every row is valid and ``dry_run`` is off.

    ``build`` turns a valid row into a model instance (or appends to the error list).
    """
    text = await read_upload(file)
    rows, errors, total = parse_rows(text, schema, columns, required)
    errors += check_unique(db, rows, unique)
    objects = []
    for row in rows:
        obj = build(row, errors)
        if obj is not None:
            objects.append(obj)
    errors.sort(key=lambda e: (e.row, e.field or ""))
    if errors or dry_run:
        db.rollback()
        result = ImportResult(dry_run=dry_run, total_rows=total, created=0, errors=errors)
        if errors:
            raise AppError(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                f"CSV contains {len(errors)} error(s); nothing was imported",
                code="csv_validation_error",
                details=result.model_dump(),
            )
        return result
    db.add_all(objects)
    db.commit()
    return ImportResult(dry_run=False, total_rows=total, created=len(objects), errors=[])


def safe_cell(value: object) -> str:
    """Neutralise spreadsheet formula injection (CWE-1236)."""
    if value is None:
        return ""
    text = str(value)
    return "'" + text if text.startswith(_FORMULA_PREFIXES) else text


def csv_response(
    filename: str, header: Sequence[str], rows: Iterable[Sequence[object]]
) -> Response:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(header)
    for row in rows:
        writer.writerow([safe_cell(v) for v in row])
    return Response(
        content=buffer.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
