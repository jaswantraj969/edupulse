"""CSV import result schemas."""

from pydantic import BaseModel, Field


class RowError(BaseModel):
    row: int = Field(description="1-based line number in the file (the header is line 1)")
    field: str | None
    message: str


class ImportResult(BaseModel):
    dry_run: bool
    total_rows: int
    created: int
    errors: list[RowError]
