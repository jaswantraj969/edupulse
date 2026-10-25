"""Password hashing (argon2id) and password policy."""

import re

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

_hasher = PasswordHasher()

MIN_LENGTH = 12
MAX_LENGTH = 128
POLICY_DESCRIPTION = (
    f"Password must be {MIN_LENGTH}-{MAX_LENGTH} characters and contain an upper-case letter, "
    "a lower-case letter and a digit."
)


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    try:
        return _hasher.verify(hashed, password)
    except (VerificationError, InvalidHashError):
        return False


def needs_rehash(hashed: str) -> bool:
    return _hasher.check_needs_rehash(hashed)


def password_policy_errors(password: str) -> list[str]:
    """Return a list of human-readable policy violations (empty when the password is valid)."""
    errors: list[str] = []
    if not MIN_LENGTH <= len(password) <= MAX_LENGTH:
        errors.append(f"must be between {MIN_LENGTH} and {MAX_LENGTH} characters")
    if not re.search(r"[A-Z]", password):
        errors.append("must contain an upper-case letter")
    if not re.search(r"[a-z]", password):
        errors.append("must contain a lower-case letter")
    if not re.search(r"\d", password):
        errors.append("must contain a digit")
    return errors
