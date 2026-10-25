"""Application settings, loaded from environment variables (prefix ``EDUPULSE_``)."""

from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]

MIN_SECRET_BYTES = 32
# The .env.example value (empty) plus common placeholders that must never sign real tokens.
PLACEHOLDER_SECRETS = {
    "",
    "change-me",
    "changeme",
    "change-me-local-only",
    "secret",
    "your-secret",
    "your-secret-here",
    "jwt-secret",
    "please-change-me",
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="EDUPULSE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: Literal["development", "test", "production"] = "development"
    database_url: str = "postgresql+psycopg://edupulse:edupulse@127.0.0.1:5432/edupulse"

    # Secret used to sign JWTs. There is deliberately no usable default outside tests.
    jwt_secret: SecretStr = SecretStr("")
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = Field(default=15, ge=1, le=120)
    refresh_token_days: int = Field(default=7, ge=1, le=60)

    cors_origins: Annotated[list[str], NoDecode] = ["http://localhost:5173"]

    login_rate_limit_attempts: int = Field(default=5, ge=1)
    login_rate_limit_window_seconds: int = Field(default=60, ge=1)

    # Refresh-token cookie is Secure by default. Browsers accept Secure cookies on http://localhost
    # and http://127.0.0.1, so local Docker use works; set false only for plain-HTTP LAN testing.
    cookie_secure: bool = True
    # Strict-Transport-Security header; enable when the site is served over HTTPS.
    hsts: bool = False

    model_dir: Path = BACKEND_DIR / "model"
    # True while the database holds synthetic demo data: risk scores are then labelled as demo.
    demo_mode: bool = True
    log_level: str = "INFO"
    log_json: bool = True

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("jwt_secret")
    @classmethod
    def _secret_strength(cls, value: SecretStr) -> SecretStr:
        secret = value.get_secret_value()
        if secret and secret.strip().lower() in PLACEHOLDER_SECRETS:
            raise ValueError("EDUPULSE_JWT_SECRET is a placeholder value; generate a random one")
        if secret and len(secret.encode()) < MIN_SECRET_BYTES:
            raise ValueError(f"EDUPULSE_JWT_SECRET must be at least {MIN_SECRET_BYTES} bytes")
        return value

    def require_jwt_secret(self) -> str:
        """The signing secret, or an error if it is missing (startup refuses to continue)."""
        secret = self.jwt_secret.get_secret_value()
        if not secret:
            raise RuntimeError("EDUPULSE_JWT_SECRET is not set")
        return secret


@lru_cache
def get_settings() -> Settings:
    return Settings()
