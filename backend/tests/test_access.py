"""Row-level access helpers."""

import pytest
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.services import access
from tests.conftest import School


def test_admin_has_unrestricted_scope(db: Session, school: School) -> None:
    assert access.visible_class_ids(school.admin) is None
    assert access.visible_student_ids(school.admin) is None
    assert access.can_access_student(db, school.admin, school.student_b.id)
    assert access.can_access_class(db, school.admin, school.class_b.id)


def test_teacher_student_scope_follows_enrolment(db: Session, school: School) -> None:
    assert access.can_access_student(db, school.teacher_a, school.student_a.id)
    assert not access.can_access_student(db, school.teacher_a, school.student_b.id)
    access.ensure_student_access(db, school.teacher_b, school.student_b.id)
    with pytest.raises(AppError) as exc:
        access.ensure_student_access(db, school.teacher_b, school.student_a.id)
    assert exc.value.status_code == 403


def test_teacher_class_scope_includes_homeroom_and_taught(db: Session, school: School) -> None:
    assert access.can_access_class(db, school.teacher_a, school.class_a_homeroom.id)
    assert access.can_access_class(db, school.teacher_a, school.class_a_taught.id)
    with pytest.raises(AppError):
        access.ensure_class_access(db, school.teacher_a, school.class_b.id)
