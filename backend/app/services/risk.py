"""Early-warning risk scores computed from EduPulse's own data with the persisted model.

The model (``backend/model/model.joblib``, produced by ``ml/``) was trained on the UCI Student
Performance data with two inputs, both of which EduPulse records itself:

* ``g1``       - first-period grade on the 0-20 scale. Here: the weight-averaged percentage of
                 the student's Term 1 assessments across all subjects, divided by 5.
* ``failures`` - past year failures (0-3), from ``students.prior_failures``.

The prediction moment is after first-period grades (end of Term 1). Absences are not an input:
the UCI count covers the whole year and so is not known at that moment (review T-R2).
Attendance is still shown in the app, just not used for the score. Scores are decision support
for staff, never an automatic sanction.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Iterable
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

import joblib
import pandas as pd
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import AcademicYear, Assessment, Grade, Student, Term

FEATURES = ("g1", "failures")
EPS = 1e-6
Band = Literal["high", "medium", "low"]

DISCLAIMER = (
    "Decision support only. Review with the student's context before acting; "
    "never use this score as an automatic sanction."
)


class ModelUnavailableError(RuntimeError):
    pass


@dataclass(frozen=True)
class RiskModel:
    estimator: Any
    meta: dict[str, Any]

    @property
    def version(self) -> str:
        return str(self.meta["model_version"])

    @property
    def high(self) -> float:
        return float(self.meta["thresholds"]["high"])

    @property
    def medium(self) -> float:
        return float(self.meta["thresholds"]["medium"])

    @property
    def reference(self) -> dict[str, float]:
        return {k: float(v) for k, v in self.meta["reference_values"].items()}

    def probabilities(self, rows: pd.DataFrame) -> list[float]:
        return [float(p) for p in self.estimator.predict_proba(rows[list(FEATURES)])[:, 1]]


@lru_cache(maxsize=4)
def load_model(model_dir: Path) -> RiskModel:
    """Load the model after verifying its SHA-256 against the metadata written at training.

    joblib files are pickles; refusing a file whose hash does not match the recorded one keeps
    a swapped or corrupted file from being unpickled.
    """
    meta_path, model_path = model_dir / "model_meta.json", model_dir / "model.joblib"
    if not meta_path.exists() or not model_path.exists():
        raise ModelUnavailableError(f"Model files not found in {model_dir.name}/")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    digest = hashlib.sha256(model_path.read_bytes()).hexdigest()
    if digest != meta.get("model_sha256"):
        raise ModelUnavailableError("Model file does not match the SHA-256 in model_meta.json")
    estimator = joblib.load(model_path)
    return RiskModel(estimator=estimator, meta=meta)


# --- feature computation ----------------------------------------------------------------------


@dataclass
class StudentFeatures:
    student_id: int
    g1: float | None
    failures: int
    assessments_term1: int

    @property
    def complete(self) -> bool:
        return self.g1 is not None

    def as_row(self) -> dict[str, float]:
        return {
            "g1": float(self.g1 if self.g1 is not None else math.nan),
            "failures": float(self.failures),
        }


def first_term(year: AcademicYear) -> Term:
    terms = sorted(year.terms, key=lambda t: t.number)
    if not terms:
        raise ModelUnavailableError(f"Academic year {year.name} has no terms")
    return terms[0]


def compute_features(
    db: Session, students: Iterable[Student], year: AcademicYear
) -> dict[int, StudentFeatures]:
    student_list = list(students)
    ids = [s.id for s in student_list]
    term = first_term(year)

    weighted = Grade.score / Assessment.max_score * 100 * Assessment.weight
    grade_rows = db.execute(
        select(Grade.student_id, func.sum(weighted), func.sum(Assessment.weight), func.count())
        .join(Assessment, Assessment.id == Grade.assessment_id)
        .where(Assessment.term_id == term.id, Grade.student_id.in_(ids))
        .group_by(Grade.student_id)
    ).all()
    grades = {
        sid: (float(total) / float(weights) / 5, n)
        for sid, total, weights, n in grade_rows
        if weights
    }

    out = {}
    for s in student_list:
        g1, n = grades.get(s.id, (None, 0))
        out[s.id] = StudentFeatures(
            student_id=s.id,
            g1=round(g1, 2) if g1 is not None else None,
            failures=s.prior_failures,
            assessments_term1=n,
        )
    return out


# --- scoring and explanation ------------------------------------------------------------------


@dataclass
class Factor:
    feature: str
    value: float
    contribution: float  # log-odds; positive raises the estimate
    direction: Literal["raises", "lowers"]
    text: str


@dataclass
class RiskResult:
    student_id: int
    status: Literal["scored", "insufficient_data"]
    probability: float | None = None
    band: Band | None = None
    factors: list[Factor] = field(default_factory=list)
    features: StudentFeatures | None = None


def band_for(model: RiskModel, probability: float) -> Band:
    if probability >= model.high:
        return "high"
    if probability >= model.medium:
        return "medium"
    return "low"


def _logit(p: float) -> float:
    p = min(max(p, EPS), 1 - EPS)
    return math.log(p / (1 - p))


def _describe(name: str, feats: StudentFeatures, reference: float, raises: bool) -> str:
    effect = "raises" if raises else "lowers"
    if name == "g1":
        g1 = feats.g1 or 0.0
        relation = "below" if g1 < reference else "at or above"
        return (
            f"Term 1 average of {g1:.1f}/20 ({g1 * 5:.0f}%) is {relation} the typical "
            f"{reference:.0f}/20; this {effect} the estimate."
        )
    if feats.failures == 0:
        return f"No previous school-year failures; this {effect} the estimate."
    years = "year" if feats.failures == 1 else "years"
    return f"Failed {feats.failures} previous school {years}; this {effect} the estimate."


def score_students(model: RiskModel, feats: dict[int, StudentFeatures]) -> dict[int, RiskResult]:
    """Probability, band and per-feature contributions (reference substitution, log-odds)."""
    results = {sid: RiskResult(sid, "insufficient_data", features=f) for sid, f in feats.items()}
    complete = [f for f in feats.values() if f.complete]
    if not complete:
        return results
    reference = model.reference
    base = pd.DataFrame([f.as_row() for f in complete])
    probs = model.probabilities(base)
    swapped_probs = {}
    for name in FEATURES:
        swapped = base.copy()
        swapped[name] = reference[name]
        swapped_probs[name] = model.probabilities(swapped)
    for i, f in enumerate(complete):
        factors = []
        for name in FEATURES:
            contribution = _logit(probs[i]) - _logit(swapped_probs[name][i])
            factors.append(
                Factor(
                    feature=name,
                    value=float(base.iloc[i][name]),
                    contribution=round(contribution, 4),
                    direction="raises" if contribution > 0 else "lowers",
                    text=_describe(name, f, reference[name], contribution > 0),
                )
            )
        factors.sort(key=lambda fac: abs(fac.contribution), reverse=True)
        results[f.student_id] = RiskResult(
            student_id=f.student_id,
            status="scored",
            probability=round(probs[i], 4),
            band=band_for(model, probs[i]),
            factors=factors,
            features=f,
        )
    return results
