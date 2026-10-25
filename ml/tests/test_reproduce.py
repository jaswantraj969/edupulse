import copy
from typing import Any

from edupulse_ml.reproduce import compare


def _run() -> dict[str, Any]:
    ci = {"estimate": 0.8, "ci_low": 0.7, "ci_high": 0.9, "n": 100}
    return {
        "chosen_model": "logistic_regression",
        "thresholds": {"high": 0.3, "medium": 0.1},
        "cv": {"logistic_regression": {"average_precision": {"mean": 0.8, "sd": 0.05}}},
        "test": {"logistic_regression": {"average_precision": ci}},
    }


def test_identical_runs_match() -> None:
    assert compare(_run(), _run()) == []


def test_differences_are_reported() -> None:
    fresh = copy.deepcopy(_run())
    fresh["chosen_model"] = "gradient_boosting"
    fresh["thresholds"]["high"] = 0.31
    fresh["test"] = {"logistic_regression": {"average_precision": {"estimate": 0.79}}}
    # Cross-platform floating-point noise is tolerated.
    fresh["cv"]["logistic_regression"]["average_precision"]["mean"] = 0.8 + 2e-5
    problems = compare(_run(), fresh)
    assert any("chosen model" in p for p in problems)
    assert any("thresholds.high" in p for p in problems)
    assert any("test.logistic_regression.average_precision" in p for p in problems)
    assert not any("cv." in p for p in problems)
