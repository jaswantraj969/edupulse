"""Reusable constrained field types."""

from typing import Annotated

from pydantic import AfterValidator, StringConstraints

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]
LongName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
ShortText = Annotated[str, StringConstraints(strip_whitespace=True, max_length=255)]
Phone = Annotated[str, StringConstraints(strip_whitespace=True, pattern=r"^[0-9+()\-. ]{5,40}$")]
Code = Annotated[str, StringConstraints(strip_whitespace=True, pattern=r"^[A-Za-z0-9-]{2,20}$")]


def _lower(value: str) -> str:
    return value.strip().lower()


LowerEmail = AfterValidator(_lower)
