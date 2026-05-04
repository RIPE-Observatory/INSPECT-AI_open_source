import uuid
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

from core.db.models.job import JobStatusEnum
from core.schemas.enums import JobSourceEnum


# Schema for data required to create a job
class JobCreate(BaseModel):
    """Schema for creating a job. Identifier is typically the main subject of the job, like a DOI or filename."""

    pass  # No explicit fields needed from user for PDF upload scenario beyond the file itself.


# Schema for the response after creating a job
class JobCreateResponse(BaseModel):
    job_id: uuid.UUID = Field(
        ..., description="The unique ID assigned to the created job."
    )
    filename: str = Field(..., description="The name of the file being processed.")


# Schema for representing job status and results
class JobStatusResponse(BaseModel):
    id: uuid.UUID
    status: JobStatusEnum
    identifier: str  # This will store the filename
    results: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    processing_time_seconds: Optional[float] = None
    source: JobSourceEnum
    external_id: Optional[str] = None
    file_path: Optional[str] = None  # PDF file path for serving
    reviewer_id: Optional[uuid.UUID] = None

    class Config:
        from_attributes = True
