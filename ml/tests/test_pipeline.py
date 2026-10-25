"""Unit tests for the ML pipeline building blocks (no network, no real dataset needed)."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from edupulse_ml import data, evaluate, explain, features, train
from edupulse_ml.report import render_run_record


def synthetic_frame(n: int = 240, seed: int = 0) -> pd.DataFrame:
    """A UCI-shaped frame with a learnable relationship (for tests only)."""
    rng = np.random.default_rng(seed)
    g1 = rng.integers(3, 20, n)
    absences = rng.poisson(4, n)
    failures = rng.choice([0, 0, 0, 1, 2, 3], n)
    g3 = np.clip(g1 + rng.normal(0, 1.5, n) - 0.5 * failures, 0, 20).round().astype(int)
    df = pd.DataFrame(
        {
            "G1": g1,
            "G2": g1,
            "G3": g3,
            "absences": absences,
            "failures": failures,
            "age": rng.integers(15, 20, n),
            "sex": rng.choice(["F", "M"], n),
        }
    )
    df["student_group"] = np.arange(n) // 2  # pairs of rows share a student
    return df


def test_target_and_design_matrix_exclude_leakage() -> None:
    df = synthetic_frame()
    X = features.design_matrix(df)
    assert list(X.columns) == ["g1", "absences", "failures"]
    assert not {"G2", "G3", "sex", "age"} & set(X.columns)
    assert features.target(df).tolist() == (df["G3"] < 10).astype(int).tolist()
    assert list(features.design_matrix(df, ["g1", "age"]).columns) == ["g1", "age"]


def test_sensitive_attributes_are_never_features() -> None:
    sources = {f.source for f in features.FEATURES}
    assert not sources & set(features.EXCLUDED_SENSITIVE)
    assert not sources & set(features.LEAKAGE)


def test_threshold_for_recall() -> None:
    y = np.array([1, 1, 1, 1, 0, 0])
    p = np.array([0.9, 0.8, 0.4, 0.2, 0.5, 0.1])
    assert evaluate.threshold_for_recall(y, p, 0.75) == 0.4  # 3 of 4 positives
    assert evaluate.threshold_for_recall(y, p, 1.0) == 0.2
    assert evaluate.threshold_for_recall(y, p, 0.01) == 0.9
    with pytest.raises(ValueError, match="No positive"):
        evaluate.threshold_for_recall(np.zeros(3, dtype=int), p[:3], 0.5)


def test_threshold_metrics() -> None:
    y = np.array([1, 1, 0, 0])
    p = np.array([0.9, 0.2, 0.8, 0.1])
    m = evaluate.threshold_metrics(y, p, 0.5)
    assert m == {"precision": 0.5, "recall": 0.5, "f1": 0.5, "flag_rate": 0.5}
    assert evaluate.threshold_metrics(y, p, 0.95)["f1"] == 0.0


def test_select_model_prefers_simpler_within_tolerance() -> None:
    order = ["dummy", "lr", "gb"]
    scores = {"dummy": [0.2, 0.2], "lr": [0.80, 0.80], "gb": [0.805, 0.805]}
    assert evaluate.select_model(scores, order, tolerance=0.01) == "lr"
    assert evaluate.select_model(scores, order, tolerance=0.0) == "gb"


def test_cluster_bootstrap_brackets_estimate_and_keeps_groups() -> None:
    rng = np.random.default_rng(1)
    y = rng.integers(0, 2, 200)
    p = np.clip(y * 0.6 + rng.normal(0.2, 0.2, 200), 0, 1)
    groups = np.arange(200) // 2
    out = evaluate.cluster_bootstrap(
        y, p, groups, evaluate.ranking_metrics, n_resamples=200, seed=3
    )
    ap = out["average_precision"]
    assert ap["ci_low"] <= ap["estimate"] <= ap["ci_high"]
    assert 0 < ap["n"] <= 200


def test_split_groups_never_cross_and_folds_are_shared() -> None:
    df = synthetic_frame(400)
    y = features.target(df).to_numpy()
    groups = df["student_group"].to_numpy()
    split = train.make_split(y, groups)
    assert not set(groups[split.train]) & set(groups[split.test])
    assert len(split.folds) == train.CV_SPLITS * train.CV_REPEATS
    assert 0.15 < len(split.test) / len(y) < 0.25
    for fit_idx, val_idx in split.folds:
        g = groups[split.train]
        assert not set(g[fit_idx]) & set(g[val_idx])


def test_cross_validate_returns_oof_for_every_training_row() -> None:
    df = synthetic_frame(300)
    X, y = features.design_matrix(df), features.target(df).to_numpy()
    split = train.make_split(y, df["student_group"].to_numpy())
    scores, oof = train.cross_validate("logistic_regression", X, y, split)
    assert len(scores) == len(split.folds)
    assert oof.shape == (len(split.train),)
    assert np.all((oof >= 0) & (oof <= 1))
    assert train.summarise(scores)["average_precision"]["mean"] > 0.5


def test_make_model_rejects_unknown() -> None:
    with pytest.raises(ValueError, match="nope"):
        train.make_model("nope")


def test_contributions_match_logistic_regression_formula() -> None:
    df = synthetic_frame()
    X, y = features.design_matrix(df), features.target(df)
    model = make_pipeline(StandardScaler(), LogisticRegression()).fit(X, y)
    reference = {c: float(X[c].median()) for c in X.columns}
    contrib = explain.contributions(model, X.head(5), reference)
    scaler, lr = model.named_steps["standardscaler"], model.named_steps["logisticregression"]
    expected = (X.head(5) - pd.Series(reference)) / scaler.scale_ * lr.coef_[0]
    np.testing.assert_allclose(contrib.to_numpy(), expected.to_numpy(), atol=1e-6)


def _fake_archive(files: dict[str, bytes]) -> bytes:
    inner_buf = io.BytesIO()
    with zipfile.ZipFile(inner_buf, "w") as inner:
        for name, content in files.items():
            inner.writestr(name, content)
    outer_buf = io.BytesIO()
    with zipfile.ZipFile(outer_buf, "w") as outer:
        outer.writestr("student.zip", inner_buf.getvalue())
    return outer_buf.getvalue()


def test_extract_rejects_tampered_archive(monkeypatch: pytest.MonkeyPatch) -> None:
    files = {"student-mat.csv": b"a;b\n1;2\n", "student-por.csv": b"a;b\n3;4\n"}
    archive = _fake_archive(files)
    with pytest.raises(data.IntegrityError, match="archive"):
        data.extract(archive)
    monkeypatch.setattr(data, "ARCHIVE_SHA256", data.sha256(archive))
    with pytest.raises(data.IntegrityError, match="student-"):
        data.extract(archive)
    monkeypatch.setattr(data, "FILE_SHA256", {k: data.sha256(v) for k, v in files.items()})
    assert data.extract(archive) == files


def test_load_combines_courses_and_groups_students(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    header = ";".join([*data.IDENTITY_COLUMNS, "G1", "G2", "G3", "absences", "failures"])
    row = ";".join(
        ['"GP"', '"F"', "16", '"U"', '"GT3"', '"T"', "4", "4", '"x"', '"y"', '"z"', '"yes"', '"no"']
    )
    mat = f'{header}\n{row};"5";"6";7;2;0\n'.encode()
    por = f"{header}\n{row};12;13;14;1;0\n".encode()
    (tmp_path / "student-mat.csv").write_bytes(mat)
    (tmp_path / "student-por.csv").write_bytes(por)
    monkeypatch.setattr(
        data,
        "FILE_SHA256",
        {"student-mat.csv": data.sha256(mat), "student-por.csv": data.sha256(por)},
    )
    df = data.load(tmp_path)
    assert list(df["course"]) == ["mat", "por"]
    assert df["G1"].tolist() == [5, 12]  # quoted numbers parsed
    assert df["student_group"].nunique() == 1  # same student in both courses
    (tmp_path / "student-mat.csv").write_bytes(mat + b"tampered")
    with pytest.raises(data.IntegrityError):
        data.load(tmp_path)


def test_fetch_uses_existing_verified_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    files = {"student-mat.csv": b"m", "student-por.csv": b"p"}
    for name, content in files.items():
        (tmp_path / name).write_bytes(content)
    monkeypatch.setattr(data, "FILE_SHA256", {k: data.sha256(v) for k, v in files.items()})
    assert [p.name for p in data.fetch(tmp_path, url="http://not-used")] == list(files)
    (tmp_path / "student-mat.csv").write_bytes(b"changed")
    with pytest.raises(ValueError, match="HTTPS"):
        data.fetch(tmp_path, url="http://insecure.example/x.zip")


def test_render_run_record_smoke() -> None:
    ci = {"estimate": 0.5, "ci_low": 0.4, "ci_high": 0.6, "n": 10}
    group = {"n": 10, "positives": 3, "recall": ci, "precision": ci, "flag_rate": ci}
    keys = ("average_precision", "roc_auc", "brier", "precision", "recall", "f1")
    summary = {k: {"mean": 0.5, "sd": 0.1} for k in ("average_precision", "roc_auc", "brier")}
    result = {
        "data": {
            "doi": "x",
            "licence": "CC BY 4.0",
            "rows": 10,
            "students_groups": 5,
            "positives": 3,
            "prevalence": 0.3,
            "train_rows": 8,
            "test_rows": 2,
            "test_positives": 1,
            "features": [{"name": "g1"}],
        },
        "protocol": {
            "prediction_moment": "pm",
            "target": "t",
            "selection_rule": "s",
            "cv": "cv",
            "threshold_rule": "r",
            "bootstrap": "b",
        },
        "chosen_model": "logistic_regression",
        "cv": {"logistic_regression": summary},
        "thresholds": {
            "high": 0.3,
            "medium": 0.1,
            "out_of_fold_at_high": {"precision": 0.5, "recall": 0.8, "flag_rate": 0.2},
        },
        "test": {"logistic_regression": dict.fromkeys(keys, ci)},
        "fairness_by_sex": {
            "test": {
                "F": group,
                "M": group,
                "gap_F_minus_M": {"recall": 0.0, "precision": 0.0, "flag_rate": 0.0},
            }
        },
        "ablations_cv_average_precision": {"primary": {"mean": 0.5, "sd": 0.1}},
        "coefficients": {"g1": {"coef_per_sd": -1.0, "mean": 10.0, "sd": 3.0}},
        "environment": {"python": "3.12", "scikit_learn": "1.9", "numpy": "2", "pandas": "3"},
    }
    meta = {
        "trained_at": "2026-01-01",
        "model_version": "1",
        "scikit_learn": "1.9",
        "model_sha256": "abc",
    }
    text = render_run_record(result, meta)
    assert "| Logistic regression | 0.500 ± 0.100" in text
    assert "0.500 [0.400, 0.600]" in text
    assert "gap F-M" in text
