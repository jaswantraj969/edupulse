"""Per-student explanations by reference substitution.

For each feature, the contribution is the change in log-odds when that feature is replaced by a
reference value (the training median), all other features held fixed:

    contribution_i = logit f(x) - logit f(x with x_i := reference_i)

For a logistic regression this equals coef_i * (x_i - reference_i) / scale_i exactly; for other
models it is a one-at-a-time local attribution. Positive values raise the risk estimate.
The backend implements the same formula (backend/app/services/risk.py); a test there checks
that it reproduces the values written here into the model metadata examples.
"""

from __future__ import annotations

from typing import Any, Protocol

import numpy as np
import pandas as pd

EPS = 1e-6


class ProbabilisticModel(Protocol):
    def predict_proba(self, X: Any) -> Any: ...


def logit(p: np.ndarray) -> np.ndarray:
    p = np.clip(p, EPS, 1 - EPS)
    return np.asarray(np.log(p / (1 - p)), dtype=float)


def contributions(
    model: ProbabilisticModel, X: pd.DataFrame, reference: dict[str, float]
) -> pd.DataFrame:
    base = logit(model.predict_proba(X)[:, 1])
    out = {}
    for name in X.columns:
        swapped = X.copy()
        swapped[name] = reference[name]
        out[name] = base - logit(model.predict_proba(swapped)[:, 1])
    return pd.DataFrame(out, index=X.index)
