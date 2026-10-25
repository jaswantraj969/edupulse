"""Metrics, operating-threshold selection, model selection and bootstrap confidence intervals."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence

import numpy as np
from numpy.typing import NDArray
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    precision_score,
    recall_score,
    roc_auc_score,
)

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]


def ranking_metrics(y: IntArray, p: FloatArray) -> dict[str, float]:
    return {
        "average_precision": float(average_precision_score(y, p)),
        "roc_auc": float(roc_auc_score(y, p)),
        "brier": float(brier_score_loss(y, p)),
    }


def threshold_metrics(y: IntArray, p: FloatArray, threshold: float) -> dict[str, float]:
    flagged = (p >= threshold).astype(int)
    precision = float(precision_score(y, flagged, zero_division=0))
    recall = float(recall_score(y, flagged, zero_division=0))
    f1 = 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)
    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "flag_rate": float(flagged.mean()),
    }


def threshold_for_recall(y: IntArray, p: FloatArray, target_recall: float) -> float:
    """Highest threshold whose recall on (y, p) is at least ``target_recall``.

    Applied to out-of-fold predictions only, so the test set never influences it.
    """
    positives = np.sort(p[y == 1])[::-1]
    if positives.size == 0:
        raise ValueError("No positive examples")
    needed = int(np.ceil(target_recall * positives.size))
    return float(positives[max(needed, 1) - 1])


def select_model(
    cv_ap: Mapping[str, Sequence[float]], order: Sequence[str], tolerance: float
) -> str:
    """Best mean CV average precision; a simpler model (earlier in ``order``) within
    ``tolerance`` of the best is preferred."""
    means = {name: float(np.mean(cv_ap[name])) for name in order}
    best = max(means.values())
    for name in order:
        if means[name] >= best - tolerance:
            return name
    raise AssertionError("unreachable")  # pragma: no cover


def cluster_bootstrap(
    y: IntArray,
    p: FloatArray,
    groups: IntArray,
    statistic: Callable[[IntArray, FloatArray], dict[str, float]],
    n_resamples: int = 2000,
    seed: int = 0,
    alpha: float = 0.05,
) -> dict[str, dict[str, float]]:
    """Percentile CIs, resampling whole groups (a student's maths and Portuguese rows together).

    Resamples without both classes are skipped (they make AP/AUC undefined); the number used is
    reported as ``n``.
    """
    rng = np.random.default_rng(seed)
    unique = np.unique(groups)
    index_by_group = {g: np.flatnonzero(groups == g) for g in unique}
    point = statistic(y, p)
    samples: dict[str, list[float]] = {k: [] for k in point}
    for _ in range(n_resamples):
        chosen = rng.choice(unique, size=unique.size, replace=True)
        idx = np.concatenate([index_by_group[g] for g in chosen])
        if y[idx].min() == y[idx].max():
            continue
        for key, value in statistic(y[idx], p[idx]).items():
            samples[key].append(value)
    out = {}
    for key, value in point.items():
        values = np.asarray(samples[key])
        out[key] = {
            "estimate": value,
            "ci_low": float(np.quantile(values, alpha / 2)),
            "ci_high": float(np.quantile(values, 1 - alpha / 2)),
            "n": int(values.size),
        }
    return out
