import logging
import uuid
import logfire
from core.services.registry_service import RegistryService
from core.schemas.registry_outputs import (
    Check2RegistryLookupOutput,
    RegistryLookupDetail,
)

logger = logging.getLogger(__name__)


class RegistryLookupCheckError(Exception):
    """Custom exception for Check 2 errors."""

    pass


async def execute_registry_lookup_check(
    job_id: uuid.UUID,
    trial_id: str,
    registry_type: str,
) -> Check2RegistryLookupOutput:
    """
    Executes Check 2: Registry Lookup & Verification.

    This check takes a trial_id and registry_type (from Check 1 output),
    uses the RegistryService to look it up, and returns a structured output.
    """
    with logfire.span("registry_lookup_check", job_id=str(job_id), trial_id=trial_id):
        logger.info(
            f"[Job: {job_id}] Starting Check 2: Registry Lookup for Trial ID '{trial_id}' in registry '{registry_type}'."
        )
        logfire.info("Starting registry lookup check", job_id=str(job_id), trial_id=trial_id, registry_type=registry_type)

        if not trial_id or not registry_type:
            error_msg = f"[Job: {job_id}] Missing trial_id or registry_type for Check 2. Cannot proceed."
            logger.error(error_msg)
            logfire.error("Missing trial_id or registry_type", job_id=str(job_id))
            return Check2RegistryLookupOutput(
                trial_id=trial_id or "Unknown",
                registry_type=registry_type or "Unknown",
                error_message=error_msg,
            )

        try:
            registry_service = RegistryService()
            lookup_detail: RegistryLookupDetail = (
                await registry_service.lookup_trial_in_registry(
                    trial_id=trial_id, registry_type=registry_type
                )
            )

            logger.info(
                f"[Job: {job_id}] Check 2 completed for {trial_id}. Success: {lookup_detail.lookup_successful}"
            )

            if lookup_detail.lookup_successful:
                logfire.info("Registry lookup successful", job_id=str(job_id), trial_id=trial_id)
            else:
                logfire.warn("Registry lookup failed", job_id=str(job_id), trial_id=trial_id, error=lookup_detail.error_message)

            return Check2RegistryLookupOutput(
                trial_id=trial_id,
                registry_type=registry_type,
                lookup_results=lookup_detail,
                error_message=lookup_detail.error_message
                if not lookup_detail.lookup_successful
                else None,
            )

        except Exception as e:
            error_msg = f"[Job: {job_id}] An unexpected error occurred during Check 2 (Registry Lookup) for {trial_id}: {e}"
            logger.exception(error_msg)
            logfire.error("Registry lookup check failed", exc_info=True, job_id=str(job_id))
            # Raise a specific error that can be caught by the ARQ task runner if needed for specific handling
            # For now, we package it into the output directly.
            return Check2RegistryLookupOutput(
                trial_id=trial_id,
                registry_type=registry_type,
                error_message="Registry lookup failed due to an internal error",
            )
