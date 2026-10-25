"""Re-run training in a temporary directory and compare with the committed run.

Exits non-zero if the chosen model differs, or thresholds or headline metrics differ by more
than half of the last published digit (5e-4). Used by CI to show the published numbers are
reproducible.

Usage::

    python -m edupulse_ml.reproduce
"""

from __future__ import annotations

import json
import sys
from typing import Any

from edupulse_ml import data, train

# Published figures carry three decimals; agreement within half of the last reported digit
# means every published number reproduces. (Different OS/BLAS builds differ around 1e-5.)
TOLERANCE = 5e-4


def compare(committed: dict[str, Any], fresh: dict[str, Any]) -> list[str]:
    problems = []
    if committed["chosen_model"] != fresh["chosen_model"]:
        problems.append(f"chosen model {committed['chosen_model']} != {fresh['chosen_model']}")
    pairs = [
        (f"thresholds.{k}", committed["thresholds"][k], fresh["thresholds"][k])
        for k in ("high", "medium")
    ]
    for name, metrics in committed["cv"].items():
        for key, value in metrics.items():
            pairs.append((f"cv.{name}.{key}.mean", value["mean"], fresh["cv"][name][key]["mean"]))
    chosen = committed["chosen_model"]
    for key, value in committed["test"][chosen].items():
        pairs.append(
            (f"test.{chosen}.{key}", value["estimate"], fresh["test"][chosen][key]["estimate"])
        )
    for label, a, b in pairs:
        if abs(a - b) > TOLERANCE:
            problems.append(f"{label}: committed {a:.6f} != reproduced {b:.6f}")
    return problems


def main() -> int:
    committed = json.loads((train.REPORT_DIR / "metrics.json").read_text(encoding="utf-8"))
    data.fetch()
    fresh = train.run()
    fresh.pop("_model")
    problems = compare(committed, fresh)
    for line in problems:
        print("MISMATCH", line)
    print("reproduced" if not problems else f"{len(problems)} mismatch(es)")
    return 1 if problems else 0


if __name__ == "__main__":  # pragma: no cover - thin CLI
    sys.exit(main())
