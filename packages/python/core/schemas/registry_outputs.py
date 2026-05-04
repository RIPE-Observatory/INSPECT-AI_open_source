from pydantic import BaseModel
from typing import Optional


class RegistryLookupDetail(BaseModel):
    """Information retrieved from a clinical trial registry for a specific trial ID,
    focusing on QC date for ClinicalTrials.gov.
    """

    trial_id_original: str
    registry_name: str
    study_first_submit_qc_date: Optional[str] = ""
    url: Optional[str] = None
    lookup_successful: bool = False
    error_message: Optional[str] = ""


class Check2RegistryLookupOutput(BaseModel):
    """Output schema for Check 2: Registry Lookup & Verification."""

    check_name: str = "registry_crosscheck"
    trial_id: str
    registry_type: str
    lookup_results: Optional[RegistryLookupDetail] = None
    error_message: Optional[str] = None

    class Config:
        from_attributes = True
