"""Early-warning risk scores (decision support). Teachers only see their own classes.

Each (student, subject) pair is scored separately; a student's band is that of their
highest-risk subject."""

from typing import Annotated, Literal

from fastapi import APIRouter, Query, Request, Response, status
from fastapi.responses import Response as RawResponse
from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, DbDep, SettingsDep
from app.api.routes.classes import roster
from app.core.config import Settings
from app.core.errors import ERROR_RESPONSES, AppError
from app.models import ClassGroup, Enrolment, Student, User
from app.models.audit import AuditAction
from app.schemas.risk import (
    ClassRisk,
    RiskFactor,
    RiskInputs,
    RiskModelInfo,
    StudentRisk,
    StudentRiskRow,
    SubjectRisk,
)
from app.services import audit, risk
from app.services.access import ensure_class_access, ensure_student_access
from app.services.crud import current_year, get_or_404
from app.services.csv_io import csv_response

router = APIRouter(prefix="/risk", tags=["early warning"], responses=ERROR_RESPONSES)

FEATURE_LABELS = {
    "g1": "Term 1 subject average",
    "failures": "Previous failures",
}
DEMO_NOTICE = "Demo — synthetic data. Scores are illustrative and refer to no real student."


def _model(settings: Settings) -> risk.RiskModel:
    try:
        return risk.load_model(settings.model_dir)
    except risk.ModelUnavailableError as exc:
        raise AppError(
            status.HTTP_503_SERVICE_UNAVAILABLE, str(exc), code="model_unavailable"
        ) from exc


def model_info(model: risk.RiskModel, settings: Settings) -> RiskModelInfo:
    meta = model.meta
    return RiskModelInfo(
        version=model.version,
        model_type=meta["model_type"],
        trained_at=meta["trained_at"],
        prediction_moment=(
            "After first-period grades (end of Term 1): Term 1 grades are used; "
            "later grades are not"
        ),
        thresholds={"high": model.high, "medium": model.medium},
        evaluation=meta.get("evaluation", {}),
        training_data=(
            "Trained on the UCI Student Performance data (two Portuguese secondary schools, "
            "2005-06, CC BY 4.0). It must be re-validated on local data before real use."
        ),
        disclaimer=risk.DISCLAIMER,
        data_notice=DEMO_NOTICE if settings.demo_mode else None,
    )


def _inputs(f: risk.SubjectFeatures) -> RiskInputs:
    return RiskInputs(g1=f.g1, failures=f.failures, assessments_term1=f.assessments_term1)


def _factors(result: risk.RiskResult) -> list[RiskFactor]:
    return [
        RiskFactor(
            feature=f.feature,
            label=FEATURE_LABELS[f.feature],
            value=f.value,
            contribution=f.contribution,
            direction=f.direction,
            text=f.text,
        )
        for f in result.factors
    ]


def _subject(result: risk.RiskResult) -> SubjectRisk:
    return SubjectRisk(
        subject_id=result.features.subject_id,
        subject_name=result.features.subject_name,
        status=result.status,
        probability=result.probability,
        band=result.band,
        factors=_factors(result),
        inputs=_inputs(result.features),
    )


def score_class(
    db: Session, model: risk.RiskModel, class_group: ClassGroup
) -> tuple[list[Student], dict[int, risk.StudentResult]]:
    students = roster(db, class_group.id)
    feats = risk.compute_features(db, students, class_group)
    return students, risk.score_students(model, feats)


@router.get("/model", response_model=RiskModelInfo, summary="About the early-warning model")
def get_model_info(_user: CurrentUser, settings: SettingsDep) -> RiskModelInfo:
    return model_info(_model(settings), settings)


SortKey = Annotated[Literal["probability", "name"], Query()]
SortOrder = Annotated[Literal["asc", "desc"], Query()]


def _top_probability(result: risk.StudentResult) -> float:
    top = result.top
    return top.probability or 0.0 if top else 0.0


def _class_rows(
    db: Session, user: User, model: risk.RiskModel, class_id: int, sort: str, order: str
) -> tuple[ClassGroup, list[tuple[Student, risk.StudentResult]]]:
    """Students with their per-subject results, sorted by the highest-risk subject."""
    class_group = get_or_404(db, ClassGroup, class_id, "Class")
    ensure_class_access(db, user, class_id)
    students, results = score_class(db, model, class_group)
    pairs = [(s, results[s.id]) for s in students]
    if sort == "name":
        pairs.sort(key=lambda p: (p[0].last_name, p[0].first_name), reverse=order == "desc")
    else:
        # Unscored students always last, whatever the direction.
        scored = sorted(
            (p for p in pairs if p[1].top is not None),
            key=lambda p: _top_probability(p[1]),
            reverse=order == "desc",
        )
        pairs = scored + [p for p in pairs if p[1].top is None]
    return class_group, pairs


def _row(student: Student, result: risk.StudentResult) -> StudentRiskRow:
    top = result.top
    scored = sum(r.status == "scored" for r in result.subjects)
    return StudentRiskRow(
        student_id=student.id,
        student_no=student.student_no,
        first_name=student.first_name,
        last_name=student.last_name,
        status="scored" if top else "insufficient_data",
        probability=top.probability if top else None,
        band=top.band if top else None,
        top_subject_id=top.features.subject_id if top else None,
        top_subject=top.features.subject_name if top else None,
        top_factor=top.factors[0].text if top and top.factors else None,
        inputs=_inputs(top.features) if top else None,
        subjects_scored=scored,
        subjects_insufficient=len(result.subjects) - scored,
    )


@router.get("/classes/{class_id}", response_model=ClassRisk, summary="Risk list for a class")
def class_risk(
    class_id: int,
    request: Request,
    db: DbDep,
    user: CurrentUser,
    settings: SettingsDep,
    sort: SortKey = "probability",
    order: SortOrder = "desc",
) -> ClassRisk:
    """Each student is shown with their highest-risk subject; ``sort=probability`` sorts by
    that subject's probability. Students without any Term 1 grades are listed with
    ``status = insufficient_data``. Every successful call is recorded in the audit log."""
    model = _model(settings)
    class_group, pairs = _class_rows(db, user, model, class_id, sort, order)
    audit.record(
        db, request, user, AuditAction.RISK_VIEW_CLASS, "class", class_id, class_group.name
    )
    return ClassRisk(
        class_id=class_group.id,
        class_name=class_group.name,
        as_of=risk.first_term(class_group.academic_year).end_date,
        model=model_info(model, settings),
        students=[_row(s, r) for s, r in pairs],
    )


@router.get(
    "/classes/{class_id}/export",
    summary="Export a class risk list as CSV",
    response_class=RawResponse,
)
def export_class_risk(
    class_id: int, request: Request, db: DbDep, user: CurrentUser, settings: SettingsDep
) -> Response:
    """One row per (student, subject) pair, students ordered by their highest-risk subject.
    Recorded in the audit log. Each row repeats the decision-support notice."""
    model = _model(settings)
    class_group, pairs = _class_rows(db, user, model, class_id, "probability", "desc")
    audit.record(
        db, request, user, AuditAction.RISK_EXPORT_CLASS, "class", class_id, class_group.name
    )
    notice = " ".join(filter(None, [DEMO_NOTICE if settings.demo_mode else None, risk.DISCLAIMER]))
    header = [
        "student_no",
        "last_name",
        "first_name",
        "subject",
        "status",
        "band",
        "probability",
        "term1_subject_average_0_20",
        "prior_failures",
        "main_factor",
        "notice",
    ]
    body = [
        [
            student.student_no,
            student.last_name,
            student.first_name,
            r.features.subject_name,
            r.status,
            r.band or "",
            "" if r.probability is None else f"{r.probability:.3f}",
            "" if r.features.g1 is None else r.features.g1,
            r.features.failures,
            r.factors[0].text if r.factors else "",
            notice,
        ]
        for student, result in pairs
        for r in result.subjects
    ]
    suffix = "-demo" if settings.demo_mode else ""
    return csv_response(f"risk-{class_group.name}{suffix}.csv", header, body)


@router.get(
    "/students/{student_id}", response_model=StudentRisk, summary="Risk panel for a student"
)
def student_risk(
    student_id: int, request: Request, db: DbDep, user: CurrentUser, settings: SettingsDep
) -> StudentRisk:
    """Recorded in the audit log."""
    student = get_or_404(db, Student, student_id, "Student")
    ensure_student_access(db, user, student_id)
    model = _model(settings)
    year = current_year(db)
    class_group = (
        db.scalar(
            select(ClassGroup)
            .join(
                Enrolment,
                and_(Enrolment.class_id == ClassGroup.id, Enrolment.student_id == student_id),
            )
            .where(ClassGroup.academic_year_id == year.id)
        )
        if year
        else None
    )
    result = risk.StudentResult(student_id, [])
    if class_group is not None:
        feats = risk.compute_features(db, [student], class_group)
        result = risk.score_students(model, feats)[student_id]
    top = result.top
    audit.record(
        db, request, user, AuditAction.RISK_VIEW_STUDENT, "student", student_id, student.student_no
    )
    return StudentRisk(
        student_id=student.id,
        student_no=student.student_no,
        first_name=student.first_name,
        last_name=student.last_name,
        class_id=class_group.id if class_group else None,
        class_name=class_group.name if class_group else None,
        as_of=risk.first_term(class_group.academic_year).end_date if class_group else None,
        status="scored" if top else "insufficient_data",
        probability=top.probability if top else None,
        band=top.band if top else None,
        top_subject=top.features.subject_name if top else None,
        subjects=[_subject(r) for r in result.subjects],
        model=model_info(model, settings),
    )
