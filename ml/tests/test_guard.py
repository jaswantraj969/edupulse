"""The holdout can be read only after decisions are frozen, and each model is scored once."""

import numpy as np
import pandas as pd
import pytest
from sklearn.dummy import DummyClassifier

from edupulse_ml.guard import HoldoutGuard


def _model() -> DummyClassifier:
    return DummyClassifier(strategy="prior").fit(pd.DataFrame({"x": [0, 1, 2, 3]}), [0, 0, 1, 1])


def test_holdout_is_locked_until_decisions_are_frozen() -> None:
    guard = HoldoutGuard(np.array([2, 3]))
    with pytest.raises(RuntimeError, match="Freeze"):
        guard.indices()
    with pytest.raises(RuntimeError, match="Freeze"):
        guard.score("m", _model(), pd.DataFrame({"x": [1]}))
    guard.freeze(chosen="m", threshold=0.3)
    assert guard.indices().tolist() == [2, 3]
    assert guard.decisions == {"chosen": "m", "threshold": 0.3}
    with pytest.raises(RuntimeError, match="already frozen"):
        guard.freeze(chosen="other")


def test_each_model_is_scored_once() -> None:
    guard = HoldoutGuard(np.array([0]))
    guard.freeze(chosen="m")
    first = guard.score("m", _model(), pd.DataFrame({"x": [1, 2]}))
    assert first.tolist() == [0.5, 0.5]
    with pytest.raises(RuntimeError, match="already scored"):
        guard.score("m", _model(), pd.DataFrame({"x": [1, 2]}))
    assert guard.predictions("m") is first
    guard.score("other", _model(), pd.DataFrame({"x": [1]}))
    assert guard.log == ["freeze: chosen", "score: m", "score: other"]
