from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .enums import CheckOutcomeStatus, CheckFindingCode, SectionFindingCode


class CheckResultEnvelope(BaseModel):
    """Normalized representation of an automated check outcome."""

    check_id: str = Field(..., description="Unique identifier for the check (e.g. 'trial_llm_extraction')")
    status: CheckOutcomeStatus = Field(..., description="UI-ready status token for this check")
    finding_code: Optional[CheckFindingCode] = Field(
        default=None, description="Structured classification of the finding"
    )
    summary: str = Field(..., description="Human-readable headline")
    detail: Optional[str] = Field(
        default=None, description="Additional context or provenance for the finding"
    )
    payload: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Raw structured data produced by the check (tables, tokens, etc.)",
    )
    dependencies: List[str] = Field(
        default_factory=list,
        description="Other check_ids this outcome depends on (useful for UI grouping)",
    )
    provider_messages: List[str] = Field(
        default_factory=list,
        description="Underlying provider or service messages surfaced for support",
    )


class SectionSummaryEnvelope(BaseModel):
    """Derived summary that aggregates one or more checks for UI presentation."""

    section_id: str = Field(..., description="Identifier for the UI section (e.g. 'registration')")
    status: CheckOutcomeStatus = Field(..., description="UI-ready status token for the section")
    finding_code: Optional[SectionFindingCode] = Field(
        default=None, description="Structured classification of the section-level finding"
    )
    summary: str = Field(..., description="Headline describing the overall outcome")
    detail: Optional[str] = Field(
        default=None, description="Supporting detail or provenance for the section summary"
    )
    contributing_checks: List[str] = Field(
        default_factory=list,
        description="Check IDs that fed into this section summary",
    )
