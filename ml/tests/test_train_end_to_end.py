"""Run the full training pipeline on a synthetic UCI-shaped dataset and check its outputs."""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import pytest

from edupulse_ml import data, train


def _write_fake_dataset(raw_dir: Path) -> dict[str, str]:
    rng = np.random.default_rng(7)
    hashes = {}
    shared: pd.DataFrame | None = None
    for name, n in (("student-mat.csv", 300), ("student-por.csv", 360)):
        g1 = rng.integers(3, 20, n)
        failures = rng.choice([0, 0, 0, 0, 1, 2, 3], n)
        frame = pd.DataFrame(
            {
                "school": rng.choice(["GP", "MS"], n),
                "sex": rng.choice(["F", "M"], n),
                "age": rng.integers(15, 20, n),
                "address": rng.choice(["U", "R"], n),
                "famsize": rng.choice(["GT3", "LE3"], n),
                "Pstatus": rng.choice(["T", "A"], n),
                "Medu": rng.integers(0, 5, n),
                "Fedu": rng.integers(0, 5, n),
                "Mjob": rng.choice(["teacher", "other", "services"], n),
                "Fjob": rng.choice(["teacher", "other", "services"], n),
                "reason": rng.choice(["course", "home"], n),
                "nursery": rng.choice(["yes", "no"], n),
                "internet": rng.choice(["yes", "no"], n),
                "G1": g1,
                "G2": g1,
                "G3": np.clip(g1 + rng.normal(0, 2, n) - failures, 0, 20).round().astype(int),
                "absences": rng.poisson(4, n),
                "failures": failures,
            }
        )
        # The first 200 students take both courses, as in the real data.
        if shared is None:
            shared = frame.loc[:199, data.IDENTITY_COLUMNS].copy()
        else:
            frame.loc[:199, data.IDENTITY_COLUMNS] = shared.to_numpy()
        content = frame.to_csv(sep=";", index=False).encode()
        (raw_dir / name).write_bytes(content)
        hashes[name] = data.sha256(content)
    return hashes


@pytest.fixture
def result(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, object]:
    raw = tmp_path / "raw"
    raw.mkdir()
    monkeypatch.setattr(data, "FILE_SHA256", _write_fake_dataset(raw))
    monkeypatch.setattr(train, "BOOTSTRAP_RESAMPLES", 50)
    return train.run(raw)


def test_run_follows_protocol(result: dict[str, object]) -> None:
    assert result["chosen_model"] in train.CANDIDATE_ORDER
    cv = result["cv"]
    assert isinstance(cv, dict)
    assert set(cv) == set(train.CANDIDATE_ORDER)
    thresholds = result["thresholds"]
    assert isinstance(thresholds, dict)
    assert 0 < thresholds["medium"] <= thresholds["high"] < 1
    assert thresholds["out_of_fold_at_high"]["recall"] >= train.TARGET_RECALL_HIGH
    fairness = result["fairness_by_sex"]
    assert isinstance(fairness, dict)
    assert {"F", "M", "gap_F_minus_M"} <= set(fairness["test"])
    ablations = result["ablations_cv_average_precision"]
    assert isinstance(ablations, dict)
    assert len(ablations) == 4


def test_split_is_disjoint_and_holdout_scored_once(result: dict[str, object]) -> None:
    audit = result["split_audit"]
    assert isinstance(audit, dict)
    assert audit["groups_crossing_holdout"] == 0
    assert audit["groups_crossing_cv_folds"] == [0] * (train.CV_SPLITS * train.CV_REPEATS)
    assert audit["groups_in_both_files"] > 0  # the fake data has shared identities too
    log = result["test_scoring_log"]
    assert isinstance(log, list)
    assert log[0].startswith("freeze:")  # every decision fixed before the holdout is read
    scored = [entry for entry in log if entry.startswith("score:")]
    assert sorted(scored) == sorted({*scored})  # no model scored twice
    assert len(scored) == len(train.CANDIDATE_ORDER) + 1  # + pre-term variant


def test_pre_term_variant_and_importance(result: dict[str, object]) -> None:
    pre = result["pre_term_variant"]
    assert isinstance(pre, dict)
    assert pre["features"] == ["absences", "failures"]
    assert set(pre["test"]) >= {"average_precision", "recall", "precision"}
    importance = result["permutation_importance_test"]
    assert isinstance(importance, dict)
    assert set(importance) == {"g1", "absences", "failures"}
    assert all(v["app_computable"] for v in importance.values())
    assert abs(sum(v["share"] for v in importance.values()) - 1) < 1e-9


def test_write_outputs(result: dict[str, object], tmp_path: Path) -> None:
    train.write_outputs(result, tmp_path / "artifacts", tmp_path / "reports")
    meta = json.loads((tmp_path / "artifacts" / "model_meta.json").read_text())
    model_bytes = (tmp_path / "artifacts" / "model.joblib").read_bytes()
    assert meta["model_sha256"] == data.sha256(model_bytes)
    assert [f["name"] for f in meta["features"]] == ["g1", "absences", "failures"]
    assert "never an automatic sanction" in meta["intended_use"]
    model = joblib.load(tmp_path / "artifacts" / "model.joblib")
    proba = model.predict_proba(pd.DataFrame([{"g1": 6.0, "absences": 10.0, "failures": 2.0}]))
    assert proba.shape == (1, 2)
    metrics = json.loads((tmp_path / "reports" / "metrics.json").read_text())
    assert "_model" not in metrics
    assert (tmp_path / "reports" / "run_record.md").read_text().startswith("# Early-warning model")
