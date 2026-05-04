import logging
import uuid
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from opentelemetry import trace
import logfire
from typing import Optional, Dict, Any

from core.schemas.llm_outputs import TrialRegistrationInfo
from core.services import llm_service
from core.prompts.llm_prompts import (
    DEFAULT_SYSTEM_PROMPT,
    TRIAL_ID_EXTRACTION_USER_PROMPT,
)

from core.db.crud import job as crud_job
from core.db.models.job import JobStatusEnum

logger = logging.getLogger(__name__)


class LLMExtractionCheckError(Exception):
    """Custom exception for failures during the LLM extraction check."""

    pass


async def execute_llm_extraction_check(
    job_id: uuid.UUID, job_identifier: str, pdf_file_path: str, db: AsyncSession, redis_client=None
) -> Optional[Dict[str, Any]]:
    """
    Performs Check #1: Uses the LLM service to extract trial registration ID
    from a PDF, processes the results.
    Returns a dictionary payload for database update or None if critical internal check failure.
    Args:
        job_id: The UUID of the job.
        job_identifier: The original identifier for the job (e.g., filename).
        pdf_file_path: The absolute path to the saved PDF file.
        db: The SQLAlchemy AsyncSession for database operations (for critical failure updates).

    Returns:
        Optional[Dict[str, Any]]: A dictionary containing the check results,
                                   or None if the check itself failed critically
                                   (after attempting to mark job as FAILED).
    Raises:
        LLMExtractionCheckError: If a critical error occurs that should lead to task failure.
    """
    logfire.info(
        f"Preparing Check #1: LLM Extraction for job {job_id}, PDF: {pdf_file_path}"
    )

    path_obj = Path(pdf_file_path)
    if not path_obj.is_file():
        logger.error(f"PDF file not found at path for job {job_id}: {pdf_file_path}")
        await crud_job.update_job_status(
            db,
            job_id,
            JobStatusEnum.FAILED,
            error_message=f"Check 1: PDF file not found: {pdf_file_path}",
        )
        await db.commit()
        raise LLMExtractionCheckError(f"PDF file not found: {pdf_file_path}")

    with logfire.span(
        "trial_llm_extraction_execution job_id={job_id}", job_id=str(job_id)
    ):
        logfire.info(f"Starting execution of Check #1: LLM Extraction for job {job_id}")
        results_payload_for_check: Optional[Dict[str, Any]] = None
        try:
            llm_response_dict = await llm_service.get_structured_llm_response(
                system_prompt=DEFAULT_SYSTEM_PROMPT,
                user_prompt_template=TRIAL_ID_EXTRACTION_USER_PROMPT,
                response_model=TrialRegistrationInfo,
                pdf_file_path=pdf_file_path,
                original_filename_for_logging=job_identifier,
                job_id=str(job_id),
                redis_client=redis_client,
            )

            parsed_document_info: Optional[TrialRegistrationInfo] = None
            token_usage_data: Optional[Dict[str, Any]] = None
            cost_info: Optional[Dict[str, Any]] = None
            model_used: Optional[str] = None

            if llm_response_dict:
                if isinstance(
                    llm_response_dict.get("parsed_info"), TrialRegistrationInfo
                ):
                    parsed_document_info = llm_response_dict["parsed_info"]
                token_usage_data = llm_response_dict.get("token_usage")
                cost_info = llm_response_dict.get("cost_info")
                model_used = llm_response_dict.get("model_used")

            if token_usage_data:
                current_span = trace.get_current_span()
                if current_span.is_recording():
                    attributes_to_set = {
                        f"trial_llm_extraction.token_usage.{key}": value
                        for key, value in token_usage_data.items()
                    }
                    current_span.set_attributes(attributes_to_set)
                    logfire.debug(
                        f"Set token usage attributes for job {job_id} on 'trial_llm_extraction_execution' span."
                    )

                # Log cost and model information
                if cost_info:
                    logger.info(f"Check 1 LLM costs for job {job_id}: {cost_info}")
                if model_used:
                    logger.info(
                        f"Check 1 LLM model used for job {job_id}: {model_used}"
                    )

            if parsed_document_info and parsed_document_info.trial_id:
                logger.info(
                    f"LLM extraction successful for job {job_id}. Trial ID: {parsed_document_info.trial_id}"
                )
                results_payload_for_check = {
                    "trial_llm_extraction": {
                        "trial_id": parsed_document_info.trial_id,
                        "registry_type": parsed_document_info.registry_type,
                        "comment": parsed_document_info.comment,
                        "status": "COMPLETED_SUCCESS",
                    }
                }
            elif parsed_document_info:
                logger.warning(
                    f"LLM extraction completed for job {job_id}, but no Trial ID was found."
                )
                results_payload_for_check = {
                    "trial_llm_extraction": {
                        "trial_id": parsed_document_info.trial_id,
                        "registry_type": parsed_document_info.registry_type,
                        "comment": parsed_document_info.comment,
                        "status": "COMPLETED_NOT_FOUND",
                        "message": "LLM could not identify a trial registration ID.",
                    }
                }
            else:
                logger.error(
                    f"LLM extraction failed to produce any response or parsed info for job {job_id}. Marking job FAILED."
                )
                await crud_job.update_job_status(
                    db=db,
                    job_id=job_id,
                    status=JobStatusEnum.FAILED,
                    error_message="Check 1: LLM extraction service returned no data or failed internally.",
                )
                await db.commit()
                raise LLMExtractionCheckError(
                    "Check 1: LLM extraction service returned no data or failed internally."
                )

            if results_payload_for_check:
                if token_usage_data:
                    results_payload_for_check["trial_llm_extraction"]["token_usage"] = (
                        token_usage_data
                    )
                if cost_info:
                    results_payload_for_check["trial_llm_extraction"]["cost_info"] = (
                        cost_info
                    )
                if model_used:
                    results_payload_for_check["trial_llm_extraction"]["model_used"] = (
                        model_used
                    )

            logger.info(f"[DEBUG] execute_llm_extraction_check for job {job_id} returning payload: {results_payload_for_check}")
            return results_payload_for_check

        except LLMExtractionCheckError:
            raise
        except Exception as e:
            logger.error(
                f"Error during Check #1 (LLM Extraction) for job {job_id}: {e}",
                exc_info=True,
            )
            try:
                current_job_status_obj = await crud_job.get_job(db, job_id)
                if current_job_status_obj and current_job_status_obj.status not in [
                    JobStatusEnum.FAILED,
                    JobStatusEnum.COMPLETED,
                ]:
                    await crud_job.update_job_status(
                        db=db,
                        job_id=job_id,
                        status=JobStatusEnum.FAILED,
                        error_message=f"Check 1 (LLM Extraction) encountered an unhandled error: {str(e)[:250]}",
                    )
                    await db.commit()
            except Exception as db_error:
                logger.error(
                    f"Failed to update job {job_id} status to FAILED after check error: {db_error}",
                    exc_info=True,
                )
            raise LLMExtractionCheckError(
                f"Check 1 (LLM Extraction) failed for job {job_id}: {str(e)}"
            ) from e
