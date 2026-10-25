"""The synthetic seed is deterministic, consistent and refuses to overwrite data."""

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app import seed as seed_module
from app.core.passwords import verify_password
from app.models import AttendanceRecord, Enrolment, Grade, Role, Student, User
from app.seed import DEMO_DOMAIN, SeedConfig, database_has_data, reset, resolve_password, seed

PASSWORD = "Demo-Password-123"
SMALL = SeedConfig(students=30, teachers=8, staff=3, password=PASSWORD)


def _names(db: Session) -> list[str]:
    return list(db.scalars(select(Student.last_name).order_by(Student.student_no)))


def test_seed_creates_consistent_synthetic_data(db: Session) -> None:
    summary = seed(db, SMALL)
    assert summary.counts["students"] == 30
    assert summary.counts["teachers"] == 8
    assert summary.counts["staff"] == 3
    assert summary.counts["users"] == 9  # admin + one per teacher
    assert summary.counts["enrolments"] == 30
    assert summary.counts["attendance_records"] > 30 * 150
    assert summary.counts["grades"] > 0

    emails = db.scalars(select(User.email)).all()
    assert all(e.endswith("@" + DEMO_DOMAIN) for e in emails)
    admin = db.scalars(select(User).where(User.role == Role.ADMIN)).one()
    assert verify_password(PASSWORD, admin.hashed_password)
    teacher_users = db.scalars(select(User).where(User.role == Role.TEACHER)).all()
    assert all(u.teacher_id is not None for u in teacher_users)

    # Every grade belongs to a student enrolled in the assessment's class.
    orphan = db.scalar(
        select(func.count())
        .select_from(Grade)
        .where(~Grade.student_id.in_(select(Enrolment.student_id)))
    )
    assert orphan == 0


def test_seed_is_deterministic(session_factory: sessionmaker[Session]) -> None:
    with session_factory() as first:
        seed(first, SMALL)
        names_a = _names(first)
        reset(first)
        assert not database_has_data(first)
        seed(first, SMALL)
        names_b = _names(first)
    assert names_a == names_b


def test_resolve_password_enforces_policy() -> None:
    assert resolve_password("Valid-Password-1") == "Valid-Password-1"
    for bad in (None, "", "   ", "weak", "change-me-local-only", "Password123"):
        with pytest.raises(SystemExit):
            resolve_password(bad)


def test_main_refuses_to_overwrite_and_resets(
    session_factory: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(seed_module, "get_session_factory", lambda: session_factory)
    monkeypatch.setenv("EDUPULSE_DEMO_PASSWORD", PASSWORD)
    args = ["--students", "10", "--teachers", "8", "--staff", "2"]

    seed_module.main(args)
    out = capsys.readouterr().out
    assert "SYNTHETIC" in out
    assert PASSWORD not in out

    with pytest.raises(SystemExit):
        seed_module.main(args)

    seed_module.main([*args, "--reset"])
    with session_factory() as s:
        assert s.scalar(select(func.count()).select_from(Student)) == 10
        assert (s.scalar(select(func.count()).select_from(AttendanceRecord)) or 0) > 0


@pytest.mark.parametrize("value", [None, "", "change-me"])
def test_main_refuses_missing_or_default_password(
    session_factory: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch, value: str | None
) -> None:
    monkeypatch.setattr(seed_module, "get_session_factory", lambda: session_factory)
    if value is None:
        monkeypatch.delenv("EDUPULSE_DEMO_PASSWORD", raising=False)
    else:
        monkeypatch.setenv("EDUPULSE_DEMO_PASSWORD", value)
    with pytest.raises(SystemExit):
        seed_module.main(["--students", "5", "--teachers", "8", "--staff", "1"])
    with session_factory() as s:
        assert not seed_module.database_has_data(s)
