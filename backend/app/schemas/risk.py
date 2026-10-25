"""Early-warning risk schemas."""

from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, Field

Band = Literal["high", "medium", "low"]
Status = Literal["scored", "insufficient_data"]


class RiskModelInfo(BaseModel):
    version: str
    model_type: str
    trained_at: str
    prediction_moment: str
    thresholds: dict[str, float] = Field(description="Probability cut-offs for the bands")
    evaluation: dict[str, Any] = Field(description="Held-out test metrics with 95 % CIs")
    training_data: str
    disclaimer: str
    data_notice: str | None = Field(
        description="Set when the installation holds synthetic demo data (label the scores)"
    )


class RiskFactor(BaseModel):
    feature: str
    label: str
    value: float
    contribution: float = Field(description="Change in log-odds versus a typical value")
    direction: Literal["raises", "lowers"]
    text: str


class RiskInputs(BaseModel):
    g1: float | None = Field(description="Term 1 average in this subject on the 0-20 scale")
    failures: int
    assessments_term1: int = Field(description="Graded Term 1 assessments in this subject")


class SubjectRisk(BaseModel):
    """The score for one (student, subject) pair; the model's training unit is one course."""

    subject_id: int
    subject_name: str
    status: Status
    probability: float | None
    band: Band | None
    factors: list[RiskFactor]
    inputs: RiskInputs


class StudentRiskRow(BaseModel):
    student_id: int
    student_no: str
    first_name: str
    last_name: str
    status: Status = Field(description="scored when at least one subject has Term 1 grades")
    probability: float | None = Field(description="Of the highest-risk subject")
    band: Band | None = Field(description="Of the highest-risk subject")
    top_subject_id: int | None
    top_subject: str | None = Field(description="Name of the highest-risk subject")
    top_factor: str | None
    inputs: RiskInputs | None = Field(description="Inputs of the highest-risk subject")
    subjects_scored: int
    subjects_insufficient: int


class ClassRisk(BaseModel):
    class_id: int
    class_name: str
    as_of: date = Field(description="Prediction moment: after first-period (Term 1) grades")
    model: RiskModelInfo
    students: list[StudentRiskRow]


class StudentRisk(BaseModel):
    student_id: int
    student_no: str
    first_name: str
    last_name: str
    class_id: int | None
    class_name: str | None
    as_of: date | None
    status: Status
    probability: float | None = Field(description="Of the highest-risk subject")
    band: Band | None = Field(description="Of the highest-risk subject")
    top_subject: str | None
    subjects: list[SubjectRisk] = Field(description="Every subject, highest risk first")
    model: RiskModelInfo
