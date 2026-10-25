"""Early-warning scoring: model loading, feature mapping, explanations and the API."""

import json
import shutil
from datetime import date
from decimal import Decimal
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models import (
    AttendanceRecord,
    AttendanceStatus,
    Grade,
    Student,
    TeachingAssignment,
)
from app.services import risk
from tests import factories as f
from tests.conftest import School

MODEL_DIR = Settings().model_dir


@pytest.fixture
def model() -> risk.RiskModel:
    return risk.load_model(MODEL_DIR)


def test_model_artifact_is_present_and_verified(model: risk.RiskModel) -> None:
    assert model.meta["model_type"] in {"logistic_regression", "gradient_boosting"}
    assert [f["name"] for f in model.meta["features"]] == list(risk.FEATURES)
    assert 0 < model.medium < model.high < 1
    assert set(model.reference) == set(risk.FEATURES)


def test_backend_reproduces_training_explanations(model: risk.RiskModel) -> None:
    """The same rows scored in ml/ (stored in the metadata) give the same numbers here."""
    examples = model.meta["explanation_examples"]
    assert examples
    for example in examples:
        x = example["features"]
        feats = risk.StudentFeatures(1, x["g1"], int(x["failures"]), 2)
        result = risk.score_students(model, {1: feats})[1]
        assert result.probability == pytest.approx(example["probability"], abs=1e-4)
        got = {fac.feature: fac.contribution for fac in result.factors}
        for name, value in example["contributions"].items():
            assert got[name] == pytest.approx(value, abs=1e-3)


def test_tampered_or_missing_model_is_refused(tmp_path: Path) -> None:
    with pytest.raises(risk.ModelUnavailableError, match="not found"):
        risk.load_model(tmp_path)
    for name in ("model.joblib", "model_meta.json"):
        shutil.copy(MODEL_DIR / name, tmp_path / name)
    meta = json.loads((tmp_path / "model_meta.json").read_text())
    meta["model_sha256"] = "0" * 64
    (tmp_path / "model_meta.json").write_text(json.dumps(meta))
    with pytest.raises(risk.ModelUnavailableError, match="SHA-256"):
        risk.load_model(tmp_path)


def test_risk_rises_as_grades_fall(model: risk.RiskModel) -> None:
    feats = {i: risk.StudentFeatures(i, g1, 0, 4) for i, g1 in enumerate([16.0, 11.0, 7.0, 4.0])}
    probs = [risk.score_students(model, feats)[i].probability for i in range(4)]
    assert probs == sorted(probs)  # type: ignore[type-var]
    assert risk.score_students(model, feats)[3].band == "high"
    assert risk.score_students(model, feats)[0].band == "low"


def test_factors_are_sorted_and_described(model: risk.RiskModel) -> None:
    feats = {1: risk.StudentFeatures(1, 6.5, 2, 8)}
    result = risk.score_students(model, feats)[1]
    assert result.status == "scored"
    magnitudes = [abs(fac.contribution) for fac in result.factors]
    assert magnitudes == sorted(magnitudes, reverse=True)
    texts = {fac.feature: fac.text for fac in result.factors}
    assert "6.5/20 (32%) is below the typical" in texts["g1"]
    assert texts["g1"].endswith("raises the estimate.")
    assert set(texts) == {"g1", "failures"}  # absences are not a model input
    assert "Failed 2 previous school years" in texts["failures"]
    good = risk.score_students(model, {2: risk.StudentFeatures(2, 17.0, 0, 8)})[2]
    good_texts = {fac.feature: fac.text for fac in good.factors}
    assert "at or above" in good_texts["g1"]
    assert "No previous school-year failures" in good_texts["failures"]
    one = risk.score_students(model, {3: risk.StudentFeatures(3, 9.0, 1, 8)})[3]
    assert any("Failed 1 previous school year;" in fac.text for fac in one.factors)


def test_insufficient_data_without_term1_grades(model: risk.RiskModel) -> None:
    result = risk.score_students(model, {1: risk.StudentFeatures(1, None, 0, 0)})[1]
    assert result.status == "insufficient_data"
    assert result.probability is None
    assert result.factors == []
    assert risk.score_students(model, {}) == {}


def _assignment(db: Session, school: School) -> TeachingAssignment:
    return db.scalars(
        select(TeachingAssignment).where(TeachingAssignment.class_id == school.class_b.id)
    ).one()


def _grade(db: Session, assessment_id: int, student: Student, score: int) -> None:
    db.add(Grade(assessment_id=assessment_id, student_id=student.id, score=Decimal(score)))


def test_compute_features_from_app_records(db: Session, school: School) -> None:
    assignment = _assignment(db, school)
    year = assignment.class_group.academic_year
    term1, term2 = year.terms[0], year.terms[1]
    quiz = f.make_assessment(db, assignment, term1, max_score=20)  # weight 1
    exam = f.make_assessment(db, assignment, term1, max_score=100)
    exam.weight = Decimal(3)
    later = f.make_assessment(db, assignment, term2, max_score=20)  # ignored: after Term 1
    student = school.student_b
    student.prior_failures = 2
    _grade(db, quiz.id, student, 10)  # 50 %
    _grade(db, exam.id, student, 70)  # 70 %
    _grade(db, later.id, student, 0)
    for day, status in [
        (date(2025, 9, 8), AttendanceStatus.ABSENT),
        (date(2025, 9, 9), AttendanceStatus.ABSENT),
        (date(2025, 9, 10), AttendanceStatus.EXCUSED),
    ]:
        db.add(
            AttendanceRecord(
                student_id=student.id, class_id=school.class_b.id, date=day, status=status
            )
        )
    db.flush()

    feats = risk.compute_features(db, [student, school.student_a], year)
    b = feats[student.id]
    assert b.g1 == pytest.approx((0.5 * 1 + 0.7 * 3) / 4 * 100 / 5)  # 13.0
    assert b.assessments_term1 == 2
    assert b.failures == 2
    # Attendance is recorded but is not a model input (UCI absences are whole-year; T-R2).
    assert set(b.as_row()) == {"g1", "failures"}
    assert feats[school.student_a.id].g1 is None
    assert not feats[school.student_a.id].complete


def _seed_scores(db: Session, school: School) -> None:
    assignment = _assignment(db, school)
    quiz = f.make_assessment(db, assignment, assignment.class_group.academic_year.terms[0])
    _grade(db, quiz.id, school.student_b, 6)
    extra = f.make_student(db, first_name="Ana", last_name="Zeta")
    f.enrol(db, extra, school.class_b)
    _grade(db, quiz.id, extra, 18)
    unscored = f.make_student(db, first_name="Bea", last_name="Alpha")
    f.enrol(db, unscored, school.class_b)
    db.commit()


def test_class_risk_endpoint(client: TestClient, db: Session, school: School) -> None:
    _seed_scores(db, school)
    url = f"/api/v1/risk/classes/{school.class_b.id}"
    body = client.get(url, headers=school.headers(school.teacher_b)).json()
    assert body["class_name"] == school.class_b.name
    assert body["as_of"] == "2025-12-19"
    assert body["model"]["data_notice"].startswith("Demo")
    assert "never use this score as an automatic sanction" in body["model"]["disclaimer"]
    statuses = [r["status"] for r in body["students"]]
    assert statuses == ["scored", "scored", "insufficient_data"]  # unscored last
    first, second = body["students"][:2]
    assert first["probability"] > second["probability"]
    assert first["band"] in {"high", "medium", "low"}
    assert first["top_factor"]
    assert first["inputs"]["g1"] == pytest.approx(6.0)

    asc = client.get(url, params={"order": "asc"}, headers=school.headers(school.admin)).json()
    assert asc["students"][0]["probability"] < asc["students"][1]["probability"]
    assert asc["students"][-1]["status"] == "insufficient_data"
    by_name = client.get(
        url, params={"sort": "name", "order": "asc"}, headers=school.headers(school.admin)
    )
    assert by_name.json()["students"][0]["last_name"] == "Alpha"


def test_risk_scoping_and_errors(client: TestClient, db: Session, school: School) -> None:
    _seed_scores(db, school)
    teacher_a = school.headers(school.teacher_a)
    assert (
        client.get(f"/api/v1/risk/classes/{school.class_b.id}", headers=teacher_a).status_code
        == 403
    )
    assert (
        client.get(f"/api/v1/risk/students/{school.student_b.id}", headers=teacher_a).status_code
        == 403
    )
    admin = school.headers(school.admin)
    assert client.get("/api/v1/risk/classes/999", headers=admin).status_code == 404
    assert client.get("/api/v1/risk/students/999", headers=admin).status_code == 404
    assert client.get("/api/v1/risk/model").status_code == 401
    bad_sort = client.get(
        f"/api/v1/risk/classes/{school.class_b.id}", params={"sort": "x"}, headers=admin
    )
    assert bad_sort.status_code == 422


def test_student_risk_endpoint(client: TestClient, db: Session, school: School) -> None:
    _seed_scores(db, school)
    body = client.get(
        f"/api/v1/risk/students/{school.student_b.id}", headers=school.headers(school.teacher_b)
    ).json()
    assert body["status"] == "scored"
    assert body["class_name"] == school.class_b.name
    assert body["factors"][0]["feature"] == "g1"
    assert {fac["label"] for fac in body["factors"]} == {
        "Term 1 average",
        "Previous failures",
    }
    assert body["inputs"]["assessments_term1"] == 1

    # Enrolled but without Term 1 grades: listed, not scored.
    no_grades = client.get(
        f"/api/v1/risk/students/{school.student_a.id}", headers=school.headers(school.admin)
    ).json()
    assert no_grades["status"] == "insufficient_data"
    assert no_grades["probability"] is None


def test_student_without_class_is_not_scored(
    client: TestClient, db: Session, school: School
) -> None:
    loner = f.make_student(db)
    db.commit()
    body = client.get(
        f"/api/v1/risk/students/{loner.id}", headers=school.headers(school.admin)
    ).json()
    assert body["status"] == "insufficient_data"
    assert body["class_id"] is None
    assert body["inputs"] is None


def test_model_info_and_demo_notice(client: TestClient, school: School, settings: Settings) -> None:
    info = client.get("/api/v1/risk/model", headers=school.headers(school.teacher_a)).json()
    assert (
        info["evaluation"]["average_precision"]["ci_low"]
        < info["evaluation"]["average_precision"]["ci_high"]
    )
    assert "re-validated" in info["training_data"]
    settings.demo_mode = False
    assert (
        client.get("/api/v1/risk/model", headers=school.headers(school.admin)).json()["data_notice"]
        is None
    )


def test_model_unavailable_returns_503(
    client: TestClient, school: School, settings: Settings, tmp_path: Path
) -> None:
    settings.model_dir = tmp_path
    response = client.get("/api/v1/risk/model", headers=school.headers(school.admin))
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "model_unavailable"


def test_probabilities_frame_order(model: risk.RiskModel) -> None:
    frame = pd.DataFrame([{"failures": 0.0, "g1": 12.0, "extra": 1.0}])  # columns shuffled
    assert 0 < model.probabilities(frame)[0] < 1
