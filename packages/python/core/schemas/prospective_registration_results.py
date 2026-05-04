from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class ProspectiveRegistrationStatusEnum(str, Enum):
    """Status outcomes for the prospective registration analysis."""

    PROSPECTIVE = "PROSPECTIVE"
    RETROSPECTIVE = "RETROSPECTIVE"
    INDETERMINATE_MISSING_DATA = "INDETERMINATE_MISSING_DATA"
    INDETERMINATE_DATE_PARSING_ERROR = "INDETERMINATE_DATE_PARSING_ERROR"
    INDETERMINATE_UNSUPPORTED_REGISTRY_FORMAT = (
        "INDETERMINATE_UNSUPPORTED_REGISTRY_FORMAT"
    )


class ProspectiveRegistrationAnalysisOutput(BaseModel):
    """Structured output for the prospective registration analysis."""

    check_name: str = Field(
        default="prospective_registration_analysis",
        description="The name of the check.",
    )
    status: ProspectiveRegistrationStatusEnum = Field(
        description="The determined status of the prospective registration analysis."
    )

    llm_recruitment_start_raw: Optional[str] = Field(
        default=None,
        description="Raw recruitment start date string produced by the timeline extraction step (e.g., 'DD-MM-YYYY' or 'MM-YYYY').",
    )
    llm_recruitment_start_parsed_for_comparison: Optional[str] = Field(
        default=None,
        description="The LLM recruitment start date parsed into YYYY-MM-DD or YYYY-MM format for comparison.",
    )

    registry_name_from_check2: Optional[str] = Field(
        default=None,
        description="Registry name/type used to interpret registry-specific date formats (e.g., ClinicalTrials.gov).",
    )
    registry_registration_date_raw: Optional[str] = Field(
        default=None,
        description="Raw registration date string returned by the registry lookup step.",
    )
    registry_registration_date_parsed_for_comparison: Optional[str] = Field(
        default=None,
        description="The registry registration date parsed into YYYY-MM-DD or YYYY-MM format for comparison.",
    )

    comparison_level: Optional[str] = Field(
        default=None,
        description="The level at which the date comparison was made (e.g., 'day', 'month').",
    )
    is_prospective: Optional[bool] = Field(
        default=None,
        description="True if registration is deemed prospective, False if retrospective, None if indeterminate.",
    )

    message: Optional[str] = Field(
        default=None,
        description="A message providing context, details about partial comparisons, errors, or missing data.",
    )

    class Config:
        use_enum_values = True
