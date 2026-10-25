"""Makes "the test set is scored once, after every decision" a property of the code."""

from __future__ import annotations

from typing import Any

import numpy as np
from numpy.typing import NDArray


class HoldoutGuard:
    def __init__(self, test_indices: NDArray[np.int64]) -> None:
        self._indices = test_indices
        self._frozen: dict[str, Any] | None = None
        self._predictions: dict[str, NDArray[np.float64]] = {}
        self.log: list[str] = []

    def freeze(self, **decisions: Any) -> None:
        """Record the decisions (model choice, thresholds) before the holdout is touched."""
        if self._frozen is not None:
            raise RuntimeError("Decisions are already frozen")
        self._frozen = dict(decisions)
        self.log.append("freeze: " + ", ".join(sorted(decisions)))

    def indices(self) -> NDArray[np.int64]:
        if self._frozen is None:
            raise RuntimeError("Freeze all decisions before reading the holdout")
        return self._indices

    def score(self, name: str, model: Any, X: Any) -> NDArray[np.float64]:
        """Predict on the holdout. Each model may be scored exactly once."""
        if self._frozen is None:
            raise RuntimeError("Freeze all decisions before scoring the holdout")
        if name in self._predictions:
            raise RuntimeError(f"The holdout was already scored for {name!r}")
        predictions = np.asarray(model.predict_proba(X)[:, 1], dtype=float)
        self._predictions[name] = predictions
        self.log.append(f"score: {name}")
        return predictions

    def predictions(self, name: str) -> NDArray[np.float64]:
        """Re-use stored predictions instead of scoring again."""
        return self._predictions[name]

    @property
    def decisions(self) -> dict[str, Any]:
        return dict(self._frozen or {})
