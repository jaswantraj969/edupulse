"""Shared fixtures. Tests run against in-memory SQLite (Postgres is used outside tests)."""

import os

# Settings are read at import time by app.main; make sure tests never touch a real database.
os.environ["EDUPULSE_ENVIRONMENT"] = "test"
os.environ["EDUPULSE_DATABASE_URL"] = "sqlite://"
os.environ.setdefault("EDUPULSE_JWT_SECRET", "test-secret-" + "x" * 40)

from collections.abc import Callable, Iterator
from dataclasses import dataclass

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.core.security import create_access_token
from app.db.base import Base
from app.db.session import build_engine, get_db
from app.main import create_app
from app.models import ClassGroup, Role, Student, User
from tests import factories as f

ALLOWED_ORIGIN = "http://allowed.example"


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


@pytest.fixture
def settings() -> Settings:
    return Settings(
        environment="test",
        database_url="sqlite://",
        jwt_secret=SecretStr("test-secret-" + "y" * 40),
        cors_origins=[ALLOWED_ORIGIN],
        login_rate_limit_attempts=3,
        login_rate_limit_window_seconds=60,
    )


@pytest.fixture
def client(session_factory: sessionmaker[Session], settings: Settings) -> Iterator[TestClient]:
    app = create_app(settings)

    def _db() -> Iterator[Session]:
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = _db
    # HTTPS like a real deployment, so Secure cookies are sent back as a browser would.
    with TestClient(app, base_url="https://testserver") as test_client:
        yield test_client


@dataclass
class School:
    """Two teachers with disjoint classes, an admin, and one enrolled student per teacher."""

    admin: User
    teacher_a: User
    teacher_b: User
    class_a_homeroom: ClassGroup
    class_a_taught: ClassGroup
    class_b: ClassGroup
    student_a: Student
    student_b: Student
    headers: Callable[[User], dict[str, str]]


@pytest.fixture
def school(db: Session, settings: Settings) -> School:
    year = f.make_year(db)
    t_a, t_b = f.make_teacher(db), f.make_teacher(db)
    class_a_homeroom = f.make_class(db, year, homeroom=t_a, section="A")
    class_a_taught = f.make_class(db, year, homeroom=None, section="B")
    f.assign(db, class_a_taught, t_a)
    class_b = f.make_class(db, year, homeroom=t_b, section="C")
    f.assign(db, class_b, t_b)
    student_a, student_b = f.make_student(db), f.make_student(db)
    f.enrol(db, student_a, class_a_homeroom)
    f.enrol(db, student_b, class_b)
    admin = f.make_user(db, Role.ADMIN)
    teacher_a = f.make_user(db, Role.TEACHER, t_a)
    teacher_b = f.make_user(db, Role.TEACHER, t_b)
    db.commit()

    def headers(user: User) -> dict[str, str]:
        role = user.role.value if user.role is not None else "none"
        token, _ = create_access_token(user.id, role, settings)
        return {"Authorization": f"Bearer {token}"}

    return School(
        admin=admin,
        teacher_a=teacher_a,
        teacher_b=teacher_b,
        class_a_homeroom=class_a_homeroom,
        class_a_taught=class_a_taught,
        class_b=class_b,
        student_a=student_a,
        student_b=student_b,
        headers=headers,
    )
