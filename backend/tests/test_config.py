import pytest
from pydantic import SecretStr, ValidationError

from app.core.config import Settings


def test_cors_origins_parsed_from_comma_separated_string() -> None:
    settings = Settings(cors_origins="http://a.test, http://b.test,")
    assert settings.cors_origins == ["http://a.test", "http://b.test"]


def test_short_jwt_secret_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(jwt_secret=SecretStr("too-short"))


def test_missing_jwt_secret_raises_when_required() -> None:
    with pytest.raises(RuntimeError):
        Settings(jwt_secret=SecretStr("")).require_jwt_secret()


def test_jwt_secret_returned_when_set() -> None:
    secret = "x" * 40
    assert Settings(jwt_secret=SecretStr(secret)).require_jwt_secret() == secret
