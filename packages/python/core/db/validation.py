"""Input validation utilities for CRUD operations."""

import uuid
from typing import Optional, Dict, Any

from core.config import (
    MAX_CHECK_NAME_LENGTH,
    MAX_CHECK_STATUS_LENGTH,
    MAX_EXTERNAL_ID_LENGTH,
    MAX_FILE_PATH_LENGTH,
    MAX_CURRENT_PHASE_LENGTH,
)
from core.schemas.enums import JobSourceEnum, JobStatusEnum, CheckStatusEnum


class ValidationError(Exception):
    """Custom validation error for CRUD operations."""

    pass


def validate_job_identifier(identifier: Optional[str]) -> None:
    """Validate job identifier."""
    if identifier is not None and len(identifier.strip()) == 0:
        raise ValidationError("Job identifier cannot be empty string")


def validate_job_source(source: JobSourceEnum) -> None:
    """Validate job source enum."""
    if not isinstance(source, JobSourceEnum):
        raise ValidationError(f"Invalid job source: {source}")


def validate_job_status(status: JobStatusEnum) -> None:
    """Validate job status enum."""
    if not isinstance(status, JobStatusEnum):
        raise ValidationError(f"Invalid job status: {status}")


def validate_external_id(external_id: Optional[str]) -> None:
    """Validate external ID length."""
    if external_id is not None and len(external_id) > MAX_EXTERNAL_ID_LENGTH:
        raise ValidationError(
            f"External ID too long: {len(external_id)} > {MAX_EXTERNAL_ID_LENGTH}"
        )


def validate_file_path(file_path: Optional[str]) -> None:
    """Validate file path length."""
    if file_path is not None and len(file_path) > MAX_FILE_PATH_LENGTH:
        raise ValidationError(
            f"File path too long: {len(file_path)} > {MAX_FILE_PATH_LENGTH}"
        )


def validate_check_name(check_name: str) -> None:
    """Validate check name."""
    if not check_name or len(check_name.strip()) == 0:
        raise ValidationError("Check name cannot be empty")
    if len(check_name) > MAX_CHECK_NAME_LENGTH:
        raise ValidationError(
            f"Check name too long: {len(check_name)} > {MAX_CHECK_NAME_LENGTH}"
        )


def validate_check_status(status: str) -> None:
    """Validate check status."""
    if not status or len(status.strip()) == 0:
        raise ValidationError("Check status cannot be empty")
    if len(status) > MAX_CHECK_STATUS_LENGTH:
        raise ValidationError(
            f"Check status too long: {len(status)} > {MAX_CHECK_STATUS_LENGTH}"
        )

    valid_statuses = {status.value for status in CheckStatusEnum}
    if status not in valid_statuses:
        raise ValidationError(
            f"Invalid check status: {status}. Must be one of {valid_statuses}"
        )


def validate_current_phase(current_phase: Optional[str]) -> None:
    """Validate current phase length."""
    if current_phase is not None and len(current_phase) > MAX_CURRENT_PHASE_LENGTH:
        raise ValidationError(
            f"Current phase too long: {len(current_phase)} > {MAX_CURRENT_PHASE_LENGTH}"
        )


def validate_progress_values(checks_completed: int, total_checks: int) -> None:
    """Validate progress values."""
    if checks_completed < 0:
        raise ValidationError(
            f"Checks completed cannot be negative: {checks_completed}"
        )
    if total_checks <= 0:
        raise ValidationError(f"Total checks must be positive: {total_checks}")
    if checks_completed > total_checks:
        raise ValidationError(
            f"Checks completed ({checks_completed}) cannot exceed total ({total_checks})"
        )


def validate_uuid(value: uuid.UUID) -> None:
    """Validate UUID format."""
    if not isinstance(value, uuid.UUID):
        raise ValidationError(f"Invalid UUID format: {value}")


def validate_results_data(results: Optional[Dict[str, Any]]) -> None:
    """Validate results data structure."""
    if results is not None and not isinstance(results, dict):
        raise ValidationError("Results must be a dictionary")
