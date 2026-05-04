import re
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from core.config import (
    MAX_REVIEWER_AFFILIATION_LENGTH,
    MAX_REVIEWER_COUNTRY_LENGTH,
    MAX_REVIEWER_NAME_LENGTH,
    MAX_REVIEWER_ORCID_LENGTH,
    MAX_REVIEWER_ROLE_LENGTH,
    MAX_REVIEWER_USERNAME_LENGTH,
)
from core.schemas.enums import KGVisibilityEnum


class ReviewerProfileUpdate(BaseModel):
    given_name: Optional[str] = Field(
        default=None, max_length=MAX_REVIEWER_NAME_LENGTH
    )
    family_name: Optional[str] = Field(
        default=None, max_length=MAX_REVIEWER_NAME_LENGTH
    )
    username: Optional[str] = Field(
        default=None, max_length=MAX_REVIEWER_USERNAME_LENGTH
    )
    email: Optional[str] = Field(
        default=None, max_length=255
    )
    affiliation_institution: Optional[str] = Field(
        default=None, max_length=MAX_REVIEWER_AFFILIATION_LENGTH
    )
    affiliation_department: Optional[str] = Field(
        default=None, max_length=MAX_REVIEWER_AFFILIATION_LENGTH
    )
    role: Optional[str] = Field(
        default=None, max_length=MAX_REVIEWER_ROLE_LENGTH
    )
    country: Optional[str] = Field(
        default=None, max_length=MAX_REVIEWER_COUNTRY_LENGTH
    )
    orcid: Optional[str] = Field(
        default=None, max_length=MAX_REVIEWER_ORCID_LENGTH
    )
    onboarding_complete: bool = Field(default=False)
    kg_visibility: Optional[KGVisibilityEnum] = Field(default=None)

    @field_validator(
        "given_name",
        "family_name",
        "username",
        "email",
        "affiliation_institution",
        "affiliation_department",
        "role",
        "country",
        "orcid",
        mode="before",
    )
    @classmethod
    def strip_blank(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    @field_validator("orcid")
    @classmethod
    def validate_orcid(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        if not re.match(r"^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$", value):
            raise ValueError("Invalid ORCID format")
        return value

    @model_validator(mode="after")
    def validate_onboarding_requirements(self) -> "ReviewerProfileUpdate":
        """Enforce that institution and role are required when marking onboarding complete."""
        if self.onboarding_complete:
            if not self.affiliation_institution or not self.affiliation_institution.strip():
                raise ValueError("Institution is required to complete onboarding")
            if not self.role or not self.role.strip():
                raise ValueError("Role is required to complete onboarding")
        return self


class ReviewerProfileResponse(BaseModel):
    id: uuid.UUID
    clerk_user_id: str
    given_name: Optional[str]
    family_name: Optional[str]
    username: Optional[str]
    email: Optional[str]
    affiliation_institution: Optional[str]
    affiliation_department: Optional[str]
    role: Optional[str]
    country: Optional[str]
    orcid: Optional[str]
    onboarding_complete: bool
    kg_visibility: KGVisibilityEnum
    kg_visibility_updated_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
