"""Early-warning risk scores (decision support). Teachers only see their own classes."""

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
)
from app.services import audit, risk
from app.services.access import ensure_class_access, ensure_student_access
from app.services.crud import current_year, get_or_404
from app.services.csv_io import csv_response

router = APIRouter(prefix="/risk", tags=["early warning"], responses=ERROR_RESPONSES)

FEATURE_LABELS = {
    "g1": "Term 1 average",
    "absences": "Absences",
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
        prediction_moment="End of Term 1 (first-period grades known; later grades not used)",
        thresholds={"high": model.high, "medium": model.medium},
        evaluation=meta.get("evaluation", {}),
        training_data=(
            "Trained on the UCI Student Performance data (two Portuguese secondary schools, "
            "2005-06, CC BY 4.0). It must be re-validated on local data before real use."
        ),
        disclaimer=risk.DISCLAIMER,
        data_notice=DEMO_NOTICE if settings.demo_mode else None,
    )


def _inputs(f: risk.StudentFeatures | None) -> RiskInputs | None:
    if f is None:
        return None
    return RiskInputs(
        g1=f.g1,
        absences_term1=f.absences_term1,
        absences_projected=f.absences_projected,
        failures=f.failures,
        assessments_term1=f.assessments_term1,
    )


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


def score_class(
    db: Session, model: risk.RiskModel, class_group: ClassGroup
) -> tuple[list[Student], dict[int, risk.RiskResult]]:
    students = roster(db, class_group.id)
    feats = risk.compute_features(db, students, class_group.academic_year)
    return students, risk.score_students(model, feats)


@router.get("/model", response_model=RiskModelInfo, summary="About the early-warning model")
def get_model_info(_user: CurrentUser, settings: SettingsDep) -> RiskModelInfo:
    return model_info(_model(settings), settings)


SortKey = Annotated[Literal["probability", "name"], Query()]
SortOrder = Annotated[Literal["asc", "desc"], Query()]


def _class_rows(
    db: Session, user: User, model: risk.RiskModel, class_id: int, sort: str, order: str
) -> tuple[ClassGroup, list[StudentRiskRow]]:
    class_group = get_or_404(db, ClassGroup, class_id, "Class")
    ensure_class_access(db, user, class_id)
    students, results = score_class(db, model, class_group)
    rows = []
    for s in students:
        r = results[s.id]
        rows.append(
            StudentRiskRow(
                student_id=s.id,
                student_no=s.student_no,
                first_name=s.first_name,
                last_name=s.last_name,
                status=r.status,
                probability=r.probability,
                band=r.band,
                top_factor=r.factors[0].text if r.factors else None,
                inputs=_inputs(r.features),
            )
        )
    if sort == "name":
        rows.sort(key=lambda r: (r.last_name, r.first_name), reverse=order == "desc")
    else:
        # Unscored students always last, whatever the direction.
        scored = sorted(
            (r for r in rows if r.probability is not None),
            key=lambda r: r.probability or 0.0,
            reverse=order == "desc",
        )
        rows = scored + [r for r in rows if r.probability is None]
    return class_group, rows


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
    """Students without Term 1 grades are listed with ``status = insufficient_data``.
    Every successful call is recorded in the audit log."""
    model = _model(settings)
    class_group, rows = _class_rows(db, user, model, class_id, sort, order)
    audit.record(
        db, request, user, AuditAction.RISK_VIEW_CLASS, "class", class_id, class_group.name
    )
    return ClassRisk(
        class_id=class_group.id,
        class_name=class_group.name,
        as_of=risk.first_term(class_group.academic_year).end_date,
        model=model_info(model, settings),
        students=rows,
    )


@router.get(
    "/classes/{class_id}/export",
    summary="Export a class risk list as CSV",
    response_class=RawResponse,
)
def export_class_risk(
    class_id: int, request: Request, db: DbDep, user: CurrentUser, settings: SettingsDep
) -> Response:
    """Recorded in the audit log. Each row repeats the decision-support notice."""
    model = _model(settings)
    class_group, rows = _class_rows(db, user, model, class_id, "probability", "desc")
    audit.record(
        db, request, user, AuditAction.RISK_EXPORT_CLASS, "class", class_id, class_group.name
    )
    notice = " ".join(filter(None, [DEMO_NOTICE if settings.demo_mode else None, risk.DISCLAIMER]))
    header = [
        "student_no",
        "last_name",
        "first_name",
        "status",
        "band",
        "probability",
        "term1_average_0_20",
        "absences_projected",
        "prior_failures",
        "main_factor",
        "notice",
    ]
    body = [
        [
            r.student_no,
            r.last_name,
            r.first_name,
            r.status,
            r.band or "",
            "" if r.probability is None else f"{r.probability:.3f}",
            "" if r.inputs is None or r.inputs.g1 is None else r.inputs.g1,
            "" if r.inputs is None else r.inputs.absences_projected,
            "" if r.inputs is None else r.inputs.failures,
            r.top_factor or "",
            notice,
        ]
        for r in rows
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
    result = risk.RiskResult(student_id, "insufficient_data")
    if class_group is not None:
        feats = risk.compute_features(db, [student], class_group.academic_year)
        result = risk.score_students(model, feats)[student_id]
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
        status=result.status,
        probability=result.probability,
        band=result.band,
        factors=_factors(result),
        inputs=_inputs(result.features),
        model=model_info(model, settings),
    )
