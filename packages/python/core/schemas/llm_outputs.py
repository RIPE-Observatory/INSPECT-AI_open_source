from typing import Optional, List
from datetime import datetime
import re

from pydantic import BaseModel, Field, field_validator


class LLMTokenUsage(BaseModel):
    """Model to store token usage details from LLM responses."""

    prompt_token_count: int
    candidates_token_count: int
    total_token_count: int


class TrialRegistrationInfo(BaseModel):
    """Pydantic model for expected JSON output from Trial ID extraction."""

    trial_id: str = Field(
        default="",
        description="The primary registration ID found (e.g., NCT12345678, CTRI/2018/07/015678). Return an empty string if not found.",
    )
    registry_type: str = Field(
        default="",
        description="The type of registry (e.g., 'ClinicalTrials.gov', 'CTRI', 'EU CTR', 'ANZCTR', 'ChiCTR', 'Other'). Return an empty string if not found or if the type is not in the provided list and cannot be reasonably inferred as 'Other'.",
    )
    comment: str = Field(
        default="",
        description="Any comments or notes regarding the extraction process, such as ambiguities or confidence level. Return an empty string if no comments.",
    )


class LLMDOIExtractionOutput(BaseModel):
    """Pydantic model for dedicated DOI extraction from an LLM."""

    doi_value: str = Field(
        default="",
        description="The extracted DOI string, or an empty string if not found.",
        examples=["10.1000/xyz123", ""],
    )
    comment: str = Field(
        default="",
        description="Explanation of where the DOI was found or why it's empty/not found. This field is mandatory and should be populated even if no DOI is found (e.g., 'DOI not found in document.').",
    )


class DateExtractionDetail(BaseModel):
    normalized_date: str = Field(
        default="",
        description="Normalized date in DD-MM-YYYY or MM-YYYY format (e.g., '15-03-2021', '02-2020'), or an empty string if not found/applicable.",
        examples=["15-03-2021", "02-2020", ""],
    )
    interpretation_comment: str = Field(
        description="Explanation of how the date was derived or why it's empty/null. Should not be empty if a date is provided or explicitly not found."
    )

    @field_validator("normalized_date", mode="before")
    @classmethod
    def normalize_date_string(cls, value: Optional[str]) -> str:
        if not value or not isinstance(value, str):
            return ""

        candidate = value.strip()
        if not candidate:
            return ""

        # Remove trailing commentary/time segments (e.g., "0:00", timezone, etc.)
        candidate = candidate.split("T")[0].strip()
        if " " in candidate:
            candidate = candidate.split()[0]

        # Extract the first plausible date-like segment (allowing '-', '/').
        patterns = [
            r"\d{1,4}[/-]\d{1,2}[/-]\d{2,4}",  # full date
            r"\d{1,2}[/-]\d{4}",  # month-year variant (requires 4-digit year)
            r"\d{4}[/-]\d{1,2}",  # year-month
        ]
        for pattern in patterns:
            match = re.search(pattern, candidate)
            if match:
                candidate = match.group(0)
                break

        candidate = candidate.strip(" ,.;")
        normalized_for_parse = candidate.replace("/", "-")

        parts = normalized_for_parse.split("-")
        if len(parts) >= 2:
            year_token = parts[-1]
            if len(year_token) != 4 or not year_token.isdigit():
                return ""

        # Try to coerce into DD-MM-YYYY or MM-YYYY consistently.
        for fmt in ("%d-%m-%Y", "%Y-%m-%d", "%m-%d-%Y"):
            try:
                dt = datetime.strptime(normalized_for_parse, fmt)
                return dt.strftime("%d-%m-%Y")
            except ValueError:
                continue

        for fmt in ("%m-%Y", "%Y-%m"):
            try:
                dt = datetime.strptime(normalized_for_parse, fmt)
                return dt.strftime("%m-%Y")
            except ValueError:
                continue

        return ""


class DOIExtractionDetail(BaseModel):
    value: str = Field(
        default="",
        description="The extracted DOI string, or an empty string if not found.",
        examples=["10.1000/xyz123", ""],
    )
    interpretation_comment: str = Field(
        description="Explanation of where the DOI was found or why it's empty. Should not be empty if a DOI is provided or explicitly not found."
    )


class StudyTimelineDates(BaseModel):
    """Pydantic model for study timeline dates."""

    recruitment_start: DateExtractionDetail
    recruitment_finish: DateExtractionDetail
    study_end_date: DateExtractionDetail


class LLMReferenceDOIsOutput(BaseModel):
    """Pydantic model for extracting a list of DOIs from the references section."""

    reference_dois: List[str] = Field(
        default_factory=list,
        description="A list of unique DOI strings found in the references section. Only valid DOI strings starting with '10.' should be included. Exclude any DOIs that are clearly the main article's DOI if it happens to appear in the reference list (e.g. self-citation).",
    )
    comment: str = Field(
        default="",
        description="A mandatory comment about the reference DOI extraction process. E.g., 'Extracted X DOIs from references section.', 'No DOIs found in references.', 'Difficulty parsing references section format.'",
    )


