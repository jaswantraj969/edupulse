"""Shared fixtures. Tests run against in-memory SQLite (Postgres is used outside tests)."""

import os
from collections.abc import Iterator

import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

os.environ["EDUPULSE_ENVIRONMENT"] = "test"
os.environ.setdefault("EDUPULSE_JWT_SECRET", "test-secret-" + "x" * 40)
os.environ["EDUPULSE_DATABASE_URL"] = "sqlite://"  # never touch a real database

import app.models  # noqa: F401
from app.db.base import Base
from app.db.session import build_engine


@pytest.fixture
def engine() -> Iterator[Engine]:
    eng = build_engine("sqlite://")
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture
def session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@pytest.fixture
def db(session_factory: sessionmaker[Session]) -> Iterator[Session]:
    with session_factory() as session:
        yield session
