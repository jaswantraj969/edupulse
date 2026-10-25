"""UCI Student Performance dataset: download, integrity check and loading.

Source: P. Cortez and A. Silva, "Using Data Mining to Predict Secondary School Student
Performance", 2008. UCI Machine Learning Repository, https://doi.org/10.24432/C5TG7T.
Licence: Creative Commons Attribution 4.0 International (CC BY 4.0).

Usage::

    python -m edupulse_ml.data          # download into ml/data/raw and verify SHA-256
"""

from __future__ import annotations

import hashlib
import io
import urllib.request
import zipfile
from pathlib import Path

import pandas as pd

ML_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = ML_DIR / "data" / "raw"

SOURCE_URL = "https://archive.ics.uci.edu/static/public/320/student+performance.zip"
DOI = "10.24432/C5TG7T"
LICENCE = "CC BY 4.0"

# SHA-256 of the files as published (recorded on first download, see ml/data/SOURCE.md).
ARCHIVE_SHA256 = "82ae9d66437b9808df42e8c89d2bb179c46e9cfbcf06f38abc1d20b3b747e177"
FILE_SHA256 = {
    "student-mat.csv": "e47f9ee225e1ee6e69b7564e6dac7123e80b8486677fe111f351964cef5dec80",
    "student-por.csv": "a7594a11d7771c0efe1a740824e0e833da9c4cad07c39a9766a874575563fb3f",
}
COURSES = {"student-mat.csv": "mat", "student-por.csv": "por"}

# Attributes the dataset authors use (student-merge.R) to identify the same student in both
# course files. Used only to keep a student's two rows in the same split, never as features.
IDENTITY_COLUMNS = [
    "school",
    "sex",
    "age",
    "address",
    "famsize",
    "Pstatus",
    "Medu",
    "Fedu",
    "Mjob",
    "Fjob",
    "reason",
    "nursery",
    "internet",
]


class IntegrityError(RuntimeError):
    pass


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def extract(archive: bytes) -> dict[str, bytes]:
    """Return the course CSVs from the published archive, verifying every checksum."""
    if sha256(archive) != ARCHIVE_SHA256:
        raise IntegrityError("Downloaded archive does not match the recorded SHA-256")
    outer = zipfile.ZipFile(io.BytesIO(archive))
    inner = zipfile.ZipFile(io.BytesIO(outer.read("student.zip")))
    files = {name: inner.read(name) for name in FILE_SHA256}
    for name, data in files.items():
        if sha256(data) != FILE_SHA256[name]:
            raise IntegrityError(f"{name} does not match the recorded SHA-256")
    return files


def fetch(raw_dir: Path = RAW_DIR, url: str = SOURCE_URL) -> list[Path]:
    """Download the dataset (if missing) and verify it. Returns the CSV paths."""
    raw_dir.mkdir(parents=True, exist_ok=True)
    paths = [raw_dir / name for name in FILE_SHA256]
    if all(p.exists() and sha256(p.read_bytes()) == FILE_SHA256[p.name] for p in paths):
        return paths
    if not url.startswith("https://"):
        raise ValueError("Only HTTPS sources are allowed")
    with urllib.request.urlopen(url, timeout=60) as response:  # noqa: S310 (https checked)
        archive = response.read()
    for name, data in extract(archive).items():
        (raw_dir / name).write_bytes(data)
    return paths


def load(raw_dir: Path = RAW_DIR) -> pd.DataFrame:
    """Both course files as one frame with ``course`` and ``student_group`` columns."""
    frames = []
    for name, course in COURSES.items():
        path = raw_dir / name
        if sha256(path.read_bytes()) != FILE_SHA256[name]:
            raise IntegrityError(f"{path.name} does not match the recorded SHA-256; re-fetch it")
        frame = pd.read_csv(path, sep=";")
        frame["course"] = course
        frames.append(frame)
    df = pd.concat(frames, ignore_index=True)
    for column in ("G1", "G2", "G3", "absences", "failures", "age"):
        df[column] = pd.to_numeric(df[column]).astype(int)
    key = df[IDENTITY_COLUMNS].astype(str).agg("|".join, axis=1)
    df["student_group"] = pd.factorize(key)[0]
    return df


if __name__ == "__main__":  # pragma: no cover - thin CLI
    for path in fetch():
        print(f"verified {path.relative_to(ML_DIR)}  sha256={FILE_SHA256[path.name]}")
