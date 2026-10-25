"""Row-level access rules.

Admins can see everything. A teacher can see a class when they are its homeroom teacher or
teach any subject in it, and can see a student when the student is enrolled in such a class.
"""

from sqlalchemy import Select, or_, select
from sqlalchemy.orm import Session

from app.core.errors import forbidden
from app.models import ClassGroup, Enrolment, Role, TeachingAssignment, User


def is_admin(user: User) -> bool:
    return user.role == Role.ADMIN


def teacher_class_ids(teacher_id: int) -> Select[int]:
    """Subquery selecting the ids of every class the teacher has access to."""
    return select(ClassGroup.id).where(
        or_(
            ClassGroup.homeroom_teacher_id == teacher_id,
            ClassGroup.id.in_(
                select(TeachingAssignment.class_id).where(
                    TeachingAssignment.teacher_id == teacher_id
                )
            ),
        )
    )


def visible_class_ids(user: User) -> Select[int] | None:
    """``None`` means "no restriction" (admin)."""
    if is_admin(user):
        return None
    return teacher_class_ids(user.teacher_id or -1)


def visible_student_ids(user: User) -> Select[int] | None:
    class_ids = visible_class_ids(user)
    if class_ids is None:
        return None
    return select(Enrolment.student_id).where(Enrolment.class_id.in_(class_ids))


def can_access_class(db: Session, user: User, class_id: int) -> bool:
    class_ids = visible_class_ids(user)
    if class_ids is None:
        return True
    return db.scalar(class_ids.where(ClassGroup.id == class_id)) is not None


def can_access_student(db: Session, user: User, student_id: int) -> bool:
    student_ids = visible_student_ids(user)
    if student_ids is None:
        return True
    return db.scalar(student_ids.where(Enrolment.student_id == student_id).limit(1)) is not None


def ensure_class_access(db: Session, user: User, class_id: int) -> None:
    if not can_access_class(db, user, class_id):
        raise forbidden("You do not teach this class")


def ensure_student_access(db: Session, user: User, student_id: int) -> None:
    if not can_access_student(db, user, student_id):
        raise forbidden("This student is not in one of your classes")
