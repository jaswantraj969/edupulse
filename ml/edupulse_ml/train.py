"""Train and evaluate the early-warning model, then write the artefacts and the run record.

Protocol (fixed before looking at test results):

1. Stratified, student-grouped holdout (20 %) created once with a fixed seed. A student's maths
   and Portuguese rows always land on the same side.
2. Repeated stratified grouped 5-fold CV (3 repeats) on the remaining 80 %; every candidate,
   including the baselines, is scored on identical folds. Primary metric: average precision.
3. Model selection: best mean CV average precision; a simpler model within 0.01 wins.
4. Operating threshold ("high" risk band) = highest threshold reaching 80 % recall on the
   out-of-fold predictions; "medium" band = 95 % recall. The test set is not used.
5. The chosen model is refit on the full 80 % and the test set is scored once, with 95 %
   cluster-bootstrap confidence intervals. Subgroup recall/precision by sex is reported.

Usage::

    python -m edupulse_ml.train            # writes ml/artifacts and ml/reports
"""

from __future__ import annotations

import json
import platform
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.base import ClassifierMixin, clone
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import Pipeline, make_pipeline
from sklearn.preprocessing import StandardScaler

from edupulse_ml import data, evaluate, explain, features
from edupulse_ml.evaluate import FloatArray, IntArray

SEED = 20251025
HOLDOUT_SPLITS = 5  # one fold of five = 20 % holdout
CV_SPLITS = 5
CV_REPEATS = 3
TARGET_RECALL_HIGH = 0.80
TARGET_RECALL_MEDIUM = 0.95
SELECTION_TOLERANCE = 0.01
BOOTSTRAP_RESAMPLES = 2000
MODEL_VERSION = "1.0.0"

ML_DIR = Path(__file__).resolve().parents[1]
ARTIFACT_DIR = ML_DIR / "artifacts"
REPORT_DIR = ML_DIR / "reports"

NDArrayStr = np.ndarray  # object array of "F"/"M" labels

# Simplest first: the selection rule prefers earlier entries when scores are close.
CANDIDATE_ORDER = ["dummy_prior", "logistic_regression", "gradient_boosting"]


def make_model(name: str) -> ClassifierMixin | Pipeline:
    if name == "dummy_prior":
        return DummyClassifier(strategy="prior")
    if name == "logistic_regression":
        return make_pipeline(StandardScaler(), LogisticRegression(C=1.0, max_iter=1000))
    if name == "gradient_boosting":
        # Fixed, conservative settings: no hyper-parameter search on ~800 rows.
        return HistGradientBoostingClassifier(
            max_depth=3, learning_rate=0.05, max_iter=200, l2_regularization=1.0, random_state=SEED
        )
    raise ValueError(name)


@dataclass
class Split:
    train: IntArray
    test: IntArray
    folds: list[tuple[IntArray, IntArray]]  # indices into ``train``


def make_split(y: IntArray, groups: IntArray) -> Split:
    outer = StratifiedGroupKFold(n_splits=HOLDOUT_SPLITS, shuffle=True, random_state=SEED)
    train, test = next(outer.split(np.zeros(len(y)), y, groups))
    folds = []
    for repeat in range(CV_REPEATS):
        inner = StratifiedGroupKFold(
            n_splits=CV_SPLITS, shuffle=True, random_state=SEED + 1 + repeat
        )
        folds.extend(inner.split(np.zeros(len(train)), y[train], groups[train]))
    return Split(
        np.asarray(train), np.asarray(test), [(np.asarray(a), np.asarray(b)) for a, b in folds]
    )


def cross_validate(
    name: str, X: pd.DataFrame, y: IntArray, split: Split
) -> tuple[list[dict[str, float]], FloatArray]:
    """Per-fold metrics and out-of-fold probabilities averaged over the repeats."""
    Xt, yt = X.iloc[split.train], y[split.train]
    oof_sum = np.zeros(len(split.train))
    oof_count = np.zeros(len(split.train))
    scores = []
    for fit_idx, val_idx in split.folds:
        model = clone(make_model(name)).fit(Xt.iloc[fit_idx], yt[fit_idx])
        p = model.predict_proba(Xt.iloc[val_idx])[:, 1]
        scores.append(evaluate.ranking_metrics(yt[val_idx], p))
        oof_sum[val_idx] += p
        oof_count[val_idx] += 1
    return scores, oof_sum / oof_count


def summarise(scores: list[dict[str, float]]) -> dict[str, dict[str, float]]:
    return {
        key: {
            "mean": float(np.mean([s[key] for s in scores])),
            "sd": float(np.std([s[key] for s in scores], ddof=1)),
        }
        for key in scores[0]
    }


def subgroup_report(
    y: IntArray, p: FloatArray, groups: IntArray, sex: NDArrayStr, threshold: float, seed: int
) -> dict[str, Any]:
    def stat(yy: IntArray, pp: FloatArray) -> dict[str, float]:
        m = evaluate.threshold_metrics(yy, pp, threshold)
        return {"recall": m["recall"], "precision": m["precision"], "flag_rate": m["flag_rate"]}

    report: dict[str, Any] = {}
    for value in ("F", "M"):
        mask = sex == value
        report[value] = {
            "n": int(mask.sum()),
            "positives": int(y[mask].sum()),
            "prevalence": float(y[mask].mean()),
            **evaluate.cluster_bootstrap(
                y[mask], p[mask], groups[mask], stat, BOOTSTRAP_RESAMPLES, seed
            ),
        }
    report["gap_F_minus_M"] = {
        k: report["F"][k]["estimate"] - report["M"][k]["estimate"]
        for k in ("recall", "precision", "flag_rate")
    }
    return report


def run(raw_dir: Path = data.RAW_DIR) -> dict[str, Any]:
    df = data.load(raw_dir)
    X = features.design_matrix(df)
    y = features.target(df).to_numpy()
    groups = df["student_group"].to_numpy()
    sex = df["sex"].to_numpy()
    split = make_split(y, groups)
    if set(groups[split.train]) & set(groups[split.test]):
        raise RuntimeError("A student appears in both the training and the test split")

    # --- repeated CV on identical folds ---------------------------------------------------
    cv: dict[str, Any] = {}
    oof: dict[str, FloatArray] = {}
    for name in CANDIDATE_ORDER:
        scores, oof[name] = cross_validate(name, X, y, split)
        cv[name] = {"folds": scores, "summary": summarise(scores)}
    chosen = evaluate.select_model(
        {n: [s["average_precision"] for s in cv[n]["folds"]] for n in CANDIDATE_ORDER},
        CANDIDATE_ORDER,
        SELECTION_TOLERANCE,
    )

    # --- thresholds from out-of-fold predictions only ---------------------------------------
    y_train = y[split.train]
    t_high = evaluate.threshold_for_recall(y_train, oof[chosen], TARGET_RECALL_HIGH)
    t_medium = evaluate.threshold_for_recall(y_train, oof[chosen], TARGET_RECALL_MEDIUM)
    oof_at_threshold = evaluate.threshold_metrics(y_train, oof[chosen], t_high)

    # --- ablations (CV only, chosen model family) --------------------------------------------
    ablation_sets = {
        "primary (g1, absences, failures)": features.FEATURE_NAMES,
        "+ age": [*features.FEATURE_NAMES, "age"],
        "- absences": ["g1", "failures"],
        "- g1 (start-of-year, no grades)": ["absences", "failures"],
    }
    ablations = {}
    for label, names in ablation_sets.items():
        scores, _ = cross_validate(chosen, features.design_matrix(df, names), y, split)
        ablations[label] = summarise(scores)["average_precision"]

    # --- final fit and the single test evaluation ---------------------------------------------
    X_train, X_test = X.iloc[split.train], X.iloc[split.test]
    y_test, g_test = y[split.test], groups[split.test]
    test: dict[str, Any] = {}
    final_models = {}
    for name in CANDIDATE_ORDER:
        final_models[name] = clone(make_model(name)).fit(X_train, y_train)
        p_test = final_models[name].predict_proba(X_test)[:, 1]

        def stat(yy: IntArray, pp: FloatArray) -> dict[str, float]:
            return evaluate.ranking_metrics(yy, pp) | evaluate.threshold_metrics(yy, pp, t_high)

        test[name] = evaluate.cluster_bootstrap(
            y_test, p_test, g_test, stat, BOOTSTRAP_RESAMPLES, SEED
        )
    model = final_models[chosen]
    p_chosen = model.predict_proba(X_test)[:, 1]
    fairness = {
        "test": subgroup_report(y_test, p_chosen, g_test, sex[split.test], t_high, SEED),
        "out_of_fold": subgroup_report(
            y_train, oof[chosen], groups[split.train], sex[split.train], t_high, SEED
        ),
    }

    reference = {name: float(X_train[name].median()) for name in features.FEATURE_NAMES}
    coefficients = None
    if chosen == "logistic_regression":
        scaler, lr = model.named_steps["standardscaler"], model.named_steps["logisticregression"]
        coefficients = {
            name: {"coef_per_sd": float(c), "mean": float(m), "sd": float(s)}
            for name, c, m, s in zip(
                features.FEATURE_NAMES, lr.coef_[0], scaler.mean_, scaler.scale_, strict=True
            )
        }
    examples = X_test.head(3)
    example_rows = [
        {
            "features": examples.iloc[i].to_dict(),
            "probability": float(model.predict_proba(examples.iloc[[i]])[0, 1]),
            "contributions": explain.contributions(model, examples.iloc[[i]], reference)
            .iloc[0]
            .to_dict(),
        }
        for i in range(len(examples))
    ]

    return {
        "protocol": {
            "seed": SEED,
            "holdout_fraction": 1 / HOLDOUT_SPLITS,
            "cv": f"{CV_REPEATS}x repeated stratified group {CV_SPLITS}-fold",
            "primary_metric": "average_precision",
            "selection_rule": (
                f"best mean CV AP; simpler model preferred within {SELECTION_TOLERANCE}"
            ),
            "threshold_rule": f"highest threshold with out-of-fold recall >= {TARGET_RECALL_HIGH}",
            "bootstrap": f"{BOOTSTRAP_RESAMPLES} cluster (student) resamples, percentile 95% CI",
            "prediction_moment": "end of the first grading period (G1 known; G2, G3 unknown)",
            "target": f"final grade G3 < {features.PASS_MARK} (fail)",
        },
        "data": {
            "source": data.SOURCE_URL,
            "doi": data.DOI,
            "licence": data.LICENCE,
            "sha256": data.FILE_SHA256,
            "rows": len(df),
            "students_groups": int(df["student_group"].nunique()),
            "positives": int(y.sum()),
            "prevalence": float(y.mean()),
            "train_rows": len(split.train),
            "test_rows": len(split.test),
            "test_positives": int(y_test.sum()),
            "features": [f.__dict__ for f in features.FEATURES],
            "excluded_leakage": features.LEAKAGE,
            "excluded_sensitive": features.EXCLUDED_SENSITIVE,
        },
        "cv": {name: cv[name]["summary"] for name in CANDIDATE_ORDER},
        "cv_folds": {name: cv[name]["folds"] for name in CANDIDATE_ORDER},
        "chosen_model": chosen,
        "thresholds": {"high": t_high, "medium": t_medium, "out_of_fold_at_high": oof_at_threshold},
        "ablations_cv_average_precision": ablations,
        "test": test,
        "fairness_by_sex": fairness,
        "reference_values": reference,
        "coefficients": coefficients,
        "explanation_examples": example_rows,
        "environment": {
            "python": platform.python_version(),
            "scikit_learn": sklearn.__version__,
            "numpy": np.__version__,
            "pandas": pd.__version__,
        },
        "_model": model,
    }


def write_outputs(
    result: dict[str, Any], artifact_dir: Path = ARTIFACT_DIR, report_dir: Path = REPORT_DIR
) -> None:
    from edupulse_ml.report import render_run_record  # local import keeps the CLI light

    artifact_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)
    model = result.pop("_model")
    model_path = artifact_dir / "model.joblib"
    joblib.dump(model, model_path)
    meta = {
        "model_version": MODEL_VERSION,
        "trained_at": datetime.now(UTC).date().isoformat(),
        "model_type": result["chosen_model"],
        "model_sha256": data.sha256(model_path.read_bytes()),
        "scikit_learn": sklearn.__version__,
        "features": [f.__dict__ for f in features.FEATURES],
        "pass_mark": features.PASS_MARK,
        "thresholds": {
            "high": result["thresholds"]["high"],
            "medium": result["thresholds"]["medium"],
        },
        "reference_values": result["reference_values"],
        "explanation_examples": result["explanation_examples"],
        "training_data": {"doi": data.DOI, "licence": data.LICENCE, "sha256": data.FILE_SHA256},
        "evaluation": {
            "dataset": "UCI Student Performance held-out test set (Portuguese schools, 2005-06)",
            "test_rows": result["data"]["test_rows"],
            **{
                key: result["test"][result["chosen_model"]][key]
                for key in ("average_precision", "roc_auc", "precision", "recall")
            },
        },
        "prediction_moment": result["protocol"]["prediction_moment"],
        "intended_use": "Decision support for school staff; never an automatic sanction.",
    }
    (artifact_dir / "model_meta.json").write_text(
        json.dumps(meta, indent=2) + "\n", encoding="utf-8"
    )
    (report_dir / "metrics.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    (report_dir / "run_record.md").write_text(render_run_record(result, meta), encoding="utf-8")


if __name__ == "__main__":  # pragma: no cover - thin CLI
    data.fetch()
    outcome = run()
    write_outputs(outcome)
    print(f"chosen model: {outcome['chosen_model']}; see {REPORT_DIR / 'run_record.md'}")
