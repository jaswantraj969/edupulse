"""Model inputs, target and the prediction moment.

Prediction moment: the end of the FIRST grading period (term) of the school year. At that point
the first-period grade (G1) is known; the second-period grade (G2) and the final grade (G3)
are not, so G2 and G3 are never inputs. G3 only defines the target.

Only features that EduPulse itself records are used, so the deployed model can be fed from the
app's own data. Protected and socioeconomic attributes are excluded on purpose (see
EXCLUDED_SENSITIVE); `sex` is kept in the evaluation frame solely for the fairness check.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

PASS_MARK = 10  # Portuguese 0-20 scale: a final grade below 10 is a fail


@dataclass(frozen=True)
class Feature:
    name: str
    source: str  # column in the UCI data
    description: str
    app_mapping: str
    app_computable: bool = True
    justification: str = ""


FEATURES = [
    Feature(
        "g1",
        "G1",
        "First-period grade (0-20)",
        "Weighted mean percentage of the student's Term 1 assessments across subjects / 5",
        justification="School record; the strongest signal and what teachers already act on.",
    ),
    Feature(
        "absences",
        "absences",
        "Number of school absences (0-93)",
        "Term 1 'absent' days extrapolated to the full year (x school days / Term 1 days)",
        justification="School attendance record; something the school can act on.",
    ),
    Feature(
        "failures",
        "failures",
        "Number of past class failures (0-3)",
        "students.prior_failures",
        justification="School record of past academic outcomes (years repeated).",
    ),
]
FEATURE_NAMES = [f.name for f in FEATURES]

# Never model inputs. Grades after the prediction moment (leakage):
LEAKAGE = ["G2", "G3"]
# Protected attributes and family/socioeconomic proxies judged sensitive:
EXCLUDED_SENSITIVE = [
    "sex",
    "age",
    "address",
    "famsize",
    "Pstatus",
    "Medu",
    "Fedu",
    "Mjob",
    "Fjob",
    "guardian",
    "famsup",
    "paid",
    "internet",
    "romantic",
    "Dalc",
    "Walc",
    "health",
    "reason",
    "traveltime",
]

# Optional extra inputs used only in the ablation study (never in the deployed model).
ABLATION_EXTRA = {"age": "age"}


def target(df: pd.DataFrame) -> pd.Series:
    """1 = final grade below the pass mark (the outcome the early warning tries to anticipate)."""
    return (df["G3"] < PASS_MARK).astype(int)


def design_matrix(df: pd.DataFrame, names: list[str] | None = None) -> pd.DataFrame:
    names = names or FEATURE_NAMES
    sources = {f.name: f.source for f in FEATURES} | ABLATION_EXTRA
    return pd.DataFrame({name: df[sources[name]].astype(float) for name in names}, index=df.index)
