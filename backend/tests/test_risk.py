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
    Teacher,
    TeachingAssignment,
)
from app.models.academic import Subject
from app.services import risk
from tests import factories as f
from tests.conftest import School

MODEL_DIR = Settings().model_dir


@pytest.fixture
def model() -> risk.RiskModel:
    return risk.load_model(MODEL_DIR)


def pair(
    g1: float | None, failures: int = 0, student_id: int = 1, subject: str = "Maths"
) -> risk.SubjectFeatures:
    n = 0 if g1 is None else 2
    return risk.SubjectFeatures(student_id, sum(map(ord, subject)), subject, g1, failures, n)


def score_one(model: risk.RiskModel, feats: risk.SubjectFeatures) -> risk.RiskResult:
    return risk.score_pairs(model, [feats])[0]


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
        result = score_one(model, pair(x["g1"], int(x["failures"])))
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
    results = risk.score_pairs(model, [pair(g1) for g1 in [16.0, 11.0, 7.0, 4.0]])
    probs = [r.probability for r in results]
    assert probs == sorted(probs)  # type: ignore[type-var]
    assert results[3].band == "high"
    assert results[0].band == "low"


def test_factor_text_compares_at_the_displayed_precision(model: risk.RiskModel) -> None:
    """10.96 is shown as 11.0, so it must not read "below" a typical 11.0 (review T-FINAL)."""
    assert model.reference["g1"] == pytest.approx(11.0)
    text = risk._describe("g1", pair(10.96, subject="History"), 11.0, raises=True)
    assert text.startswith("Term 1 History average of 11.0/20 (55%) is at or above")
    assert "the typical 11.0/20;" in text
    assert "below" not in text
    lower = risk._describe("g1", pair(10.94, subject="History"), 11.0, raises=True)
    assert "average of 10.9/20 (55%) is below the typical 11.0/20;" in lower
    scored = {f.feature: f.text for f in score_one(model, pair(10.96)).factors}
    assert "11.0/20 (55%) is at or above the typical 11.0/20" in scored["g1"]


def test_factors_are_sorted_and_described(model: risk.RiskModel) -> None:
    result = score_one(model, pair(6.5, 2, subject="Mathematics"))
    assert result.status == "scored"
    magnitudes = [abs(fac.contribution) for fac in result.factors]
    assert magnitudes == sorted(magnitudes, reverse=True)
    texts = {fac.feature: fac.text for fac in result.factors}
    assert texts["g1"].startswith("Term 1 Mathematics average of 6.5/20 (32%) is below")
    assert texts["g1"].endswith("raises the estimate.")
    assert set(texts) == {"g1", "failures"}  # absences are not a model input
    assert "Failed 2 previous school years" in texts["failures"]
    good = score_one(model, pair(17.0))
    good_texts = {fac.feature: fac.text for fac in good.factors}
    assert "at or above" in good_texts["g1"]
    assert "No previous school-year failures" in good_texts["failures"]
    one = score_one(model, pair(9.0, 1))
    assert any("Failed 1 previous school year;" in fac.text for fac in one.factors)


def test_insufficient_data_without_term1_grades(model: risk.RiskModel) -> None:
    result = score_one(model, pair(None))
    assert result.status == "insufficient_data"
    assert result.probability is None
    assert result.factors == []
    assert risk.score_pairs(model, []) == []
    assert risk.score_students(model, {}) == {}
    assert risk.score_students(model, {1: [pair(None)]})[1].top is None


def test_student_band_is_the_highest_risk_subject(model: risk.RiskModel) -> None:
    """35 % in one subject and 80 % in all others: flagged on that subject (review T-R3)."""
    others = ["Biology", "English", "History", "Physics"]
    feats = {1: [pair(16.0, subject=name) for name in others] + [pair(7.0, subject="Chemistry")]}
    result = risk.score_students(model, feats)[1]
    top = result.top
    assert top is not None
    assert top.features.subject_name == "Chemistry"
    assert top.band == "high"
    assert next(r.features.subject_name for r in result.subjects) == "Chemistry"
    assert all(r.band == "low" for r in result.subjects[1:])
    assert "Term 1 Chemistry average of 7.0/20 (35%)" in top.factors[0].text
    # The average across subjects (15.2/20) would have scored low.
    averaged = score_one(model, pair((16.0 * 4 + 7.0) / 5))
    assert averaged.band == "low"


def test_subject_without_term1_grades_is_insufficient_on_its_own(model: risk.RiskModel) -> None:
    feats = {1: [pair(None, subject="Art"), pair(9.0, subject="Maths")]}
    result = risk.score_students(model, feats)[1]
    by_name = {r.features.subject_name: r for r in result.subjects}
    assert by_name["Art"].status == "insufficient_data"
    assert by_name["Art"].probability is None
    assert by_name["Maths"].status == "scored"
    assert result.top is by_name["Maths"]
    assert result.subjects[-1] is by_name["Art"]  # unscored subjects last


def _teacher_b(school: School) -> Teacher:
    teacher = school.class_b.homeroom_teacher
    assert teacher is not None
    return teacher


def _assignment(db: Session, school: School) -> TeachingAssignment:
    return db.scalars(
        select(TeachingAssignment)
        .where(TeachingAssignment.class_id == school.class_b.id)
        .order_by(TeachingAssignment.id)
        .limit(1)
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

    feats = risk.compute_features(db, [student, school.student_a], school.class_b)
    [b] = feats[student.id]
    assert b.subject_id == assignment.subject_id
    assert b.g1 == pytest.approx((0.5 * 1 + 0.7 * 3) / 4 * 100 / 5)  # 13.0
    assert b.assessments_term1 == 2
    assert b.failures == 2
    # Attendance is recorded but is not a model input (UCI absences are whole-year; T-R2).
    assert set(b.as_row()) == {"g1", "failures"}
    # student_a is not graded: one entry per subject taught in the class, without g1.
    [a] = feats[school.student_a.id]
    assert a.g1 is None
    assert not a.complete


def test_compute_features_per_subject(db: Session, school: School) -> None:
    """g1 is computed per subject, never averaged across subjects (review T-R3)."""
    maths = _assignment(db, school)
    term1 = maths.class_group.academic_year.terms[0]
    science = f.assign(db, school.class_b, _teacher_b(school))
    art = f.assign(db, school.class_b, _teacher_b(school))  # taught, but nothing graded yet
    student = school.student_b
    _grade(db, f.make_assessment(db, maths, term1).id, student, 7)  # 35 %
    _grade(db, f.make_assessment(db, science, term1).id, student, 16)  # 80 %
    db.flush()

    feats = {
        x.subject_id: x for x in risk.compute_features(db, [student], school.class_b)[student.id]
    }
    assert set(feats) == {maths.subject_id, science.subject_id, art.subject_id}
    assert feats[maths.subject_id].g1 == pytest.approx(7.0)
    assert feats[science.subject_id].g1 == pytest.approx(16.0)
    assert feats[art.subject_id].g1 is None
    assert feats[art.subject_id].assessments_term1 == 0
    assert feats[maths.subject_id].subject_name == db.get(Subject, maths.subject_id).name  # type: ignore[union-attr]


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
    assert first["top_subject"] == _assignment(db, school).subject.name
    assert first["top_factor"].startswith(f"Term 1 {first['top_subject']} average")
    assert first["inputs"]["g1"] == pytest.approx(6.0)
    assert (first["subjects_scored"], first["subjects_insufficient"]) == (1, 0)
    assert body["students"][2]["top_subject"] is None

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
    [subject] = body["subjects"]
    assert body["top_subject"] == subject["subject_name"]
    assert body["band"] == subject["band"]
    assert subject["factors"][0]["feature"] == "g1"
    assert {fac["label"] for fac in subject["factors"]} == {
        "Term 1 subject average",
        "Previous failures",
    }
    assert subject["inputs"]["assessments_term1"] == 1

    # Enrolled but without Term 1 grades: listed, not scored.
    no_grades = client.get(
        f"/api/v1/risk/students/{school.student_a.id}", headers=school.headers(school.admin)
    ).json()
    assert no_grades["status"] == "insufficient_data"
    assert no_grades["probability"] is None
    assert no_grades["subjects"] == []  # class_a_homeroom has no teaching assignments


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
    assert body["subjects"] == []


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


def test_per_subject_output_endpoints(client: TestClient, db: Session, school: School) -> None:
    """35 % in one subject, 80 % in all others: the class list and the student panel flag the
    weak subject; an ungraded subject is insufficient_data on its own (review T-R3)."""
    maths = _assignment(db, school)
    term1 = maths.class_group.academic_year.terms[0]
    strong = [f.assign(db, school.class_b, _teacher_b(school)) for _ in range(3)]
    ungraded = f.assign(db, school.class_b, _teacher_b(school))
    student = school.student_b
    _grade(db, f.make_assessment(db, maths, term1).id, student, 7)  # 35 %
    for assignment in strong:
        _grade(db, f.make_assessment(db, assignment, term1).id, student, 16)  # 80 %
    db.commit()
    weak_name = maths.subject.name

    teacher_b = school.headers(school.teacher_b)
    row = client.get(f"/api/v1/risk/classes/{school.class_b.id}", headers=teacher_b).json()[
        "students"
    ][0]
    assert (row["top_subject"], row["band"]) == (weak_name, "high")
    assert row["inputs"]["g1"] == pytest.approx(7.0)
    assert (row["subjects_scored"], row["subjects_insufficient"]) == (3 + 1, 1)

    panel = client.get(f"/api/v1/risk/students/{student.id}", headers=teacher_b).json()
    assert panel["band"] == "high"
    assert panel["top_subject"] == weak_name
    subjects = panel["subjects"]
    assert next(x["subject_name"] for x in subjects) == weak_name
    assert len(subjects) == 5
    assert all(len(x["factors"]) == 2 for x in subjects if x["status"] == "scored")
    assert [x["band"] for x in subjects[1:4]] == ["low", "low", "low"]
    assert subjects[-1]["subject_name"] == ungraded.subject.name
    assert subjects[-1]["status"] == "insufficient_data"
    assert subjects[-1]["factors"] == []

    # Teacher scoping still applies to the per-subject output.
    teacher_a = school.headers(school.teacher_a)
    for url in (
        f"/api/v1/risk/classes/{school.class_b.id}",
        f"/api/v1/risk/classes/{school.class_b.id}/export",
        f"/api/v1/risk/students/{student.id}",
    ):
        assert client.get(url, headers=teacher_a).status_code == 403
