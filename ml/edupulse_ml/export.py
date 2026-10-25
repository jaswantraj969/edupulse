"""Copy the trained model and its metadata into the backend (``backend/model/``).

Usage::

    python -m edupulse_ml.export
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from edupulse_ml import data
from edupulse_ml.train import ARTIFACT_DIR, ML_DIR

BACKEND_MODEL_DIR = ML_DIR.parent / "backend" / "model"
FILES = ("model.joblib", "model_meta.json")


def export(source: Path = ARTIFACT_DIR, target: Path = BACKEND_MODEL_DIR) -> list[Path]:
    meta = json.loads((source / "model_meta.json").read_text(encoding="utf-8"))
    if data.sha256((source / "model.joblib").read_bytes()) != meta["model_sha256"]:
        raise data.IntegrityError("model.joblib does not match the SHA-256 in model_meta.json")
    target.mkdir(parents=True, exist_ok=True)
    return [Path(shutil.copy2(source / name, target / name)) for name in FILES]


if __name__ == "__main__":  # pragma: no cover - thin CLI
    for path in export():
        print(f"exported {path.relative_to(ML_DIR.parent)}")
