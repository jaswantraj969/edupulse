import pytest
from pydantic import SecretStr, ValidationError

from app.core.config import Settings


def test_cors_origins_parsed_from_comma_separated_string() -> None:
    settings = Settings(cors_origins="http://a.test, http://b.test,")
    assert settings.cors_origins == ["http://a.test", "http://b.test"]


def test_short_jwt_secret_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(jwt_secret=SecretStr("too-short"))


@pytest.mark.parametrize("value", ["change-me", "CHANGE-ME-LOCAL-ONLY", "your-secret-here"])
def test_placeholder_jwt_secret_rejected(value: str) -> None:
    with pytest.raises(ValidationError, match="placeholder"):
        Settings(jwt_secret=SecretStr(value))


def test_jwt_secret_length_counts_bytes() -> None:
    with pytest.raises(ValidationError, match="32 bytes"):
        Settings(jwt_secret=SecretStr("x" * 31))
    assert Settings(jwt_secret=SecretStr("é" * 16)).jwt_secret  # 16 characters, 32 bytes


def test_secure_cookie_by_default_and_hsts_opt_in() -> None:
    settings = Settings()
    assert settings.cookie_secure is True
    assert settings.hsts is False


def test_app_refuses_to_start_without_secret() -> None:
    from app.main import create_app

    with pytest.raises(RuntimeError, match="not set"):
        create_app(Settings(jwt_secret=SecretStr("")))


def test_missing_jwt_secret_raises_when_required() -> None:
    with pytest.raises(RuntimeError):
        Settings(jwt_secret=SecretStr("")).require_jwt_secret()


def test_jwt_secret_returned_when_set() -> None:
    secret = "x" * 40
    assert Settings(jwt_secret=SecretStr(secret)).require_jwt_secret() == secret
