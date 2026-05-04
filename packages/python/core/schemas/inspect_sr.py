from __future__ import annotations

import uuid
from typing import List, Optional, Literal, Dict
from pydantic import BaseModel, Field

# Flat model enums
ResponseType = Optional[Literal["yes", "no", "unclear", "na"]]
JudgementType = Optional[Literal["no-concerns", "some-concerns", "serious-concerns"]]


class AnswerRecord(BaseModel):
    question_id: str
    label: str
    automated_judgement: Optional[str] = None  # AI suggestion (read-only)
    reviewed_judgement: Optional[str] = None   # User's final answer
    comment: str = ""


class InspectSRContainer(BaseModel):
    version: int = Field(default=1)
    updated_at: str = Field(description="ISO 8601 timestamp of last update")
    progress: Dict[str, int]  # { completed, percent }
    data: List[AnswerRecord]


class InspectSRGetResponse(BaseModel):
    job_id: uuid.UUID
    version: int
    updated_at: str
    progress: Dict[str, int]
    data: List[AnswerRecord]


class InspectSRPutRequest(BaseModel):
    data: List[AnswerRecord]
    version: Optional[int] = None


class InspectSRPutResponse(BaseModel):
    job_id: uuid.UUID
    updated_at: str
    version: int


class InspectSRProgressResponse(BaseModel):
    job_id: uuid.UUID
    completed: int
    percent: int
    total: int


# Canon of valid beta question IDs and their types
QUESTION_TYPES: Dict[str, str] = {
    "Q1.1": "check",
    "Q1.2": "check",
    "Q1.3": "check",
    "Q2.2": "check",
    "OVERALL": "judgement",
}

# Q1.1 - Retraction, Q1.2 - EOC, Q1.3 - Author history, Q2.2 - Registration timing, OVERALL
BETA_QUESTION_IDS: List[str] = ["Q1.1", "Q1.2", "Q1.3", "Q2.2", "OVERALL"]


def get_active_question_types() -> Dict[str, str]:
    """Return the active beta question types."""
    return {qid: QUESTION_TYPES[qid] for qid in BETA_QUESTION_IDS}


def compute_progress_from_records(records: List[AnswerRecord]) -> Dict[str, int]:
    """
    Compute progress against the active question set.

    For beta profile (5 questions):
    - 4 individual checks (Q1.1, Q1.2, Q1.3, Q2.2) contribute to progress
    - OVERALL is tracked separately (when answered, indicates completion)

    Returns:
        Dict with completed, percent, total keys
    """
    active_types = get_active_question_types()

    # For progress calculation, exclude OVERALL from the denominator
    # (OVERALL indicates "complete" status, not a countable check)
    check_ids = {k for k, v in active_types.items() if k != "OVERALL"}
    total = len(check_ids)

    completed = sum(
        1 for r in records if r.question_id in check_ids and r.reviewed_judgement is not None
    )
    percent = round((completed / total) * 100) if total else 0
    return {"completed": completed, "percent": percent, "total": total}
