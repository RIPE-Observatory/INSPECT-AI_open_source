import logging
import uuid
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from opentelemetry import trace
import logfire
from typing import Optional, Dict, Any

from core.schemas.llm_outputs import StudyTimelineDates
from core.services import llm_service
from core.prompts.llm_prompts import (
    DEFAULT_SYSTEM_PROMPT,
    STUDY_TIMELINE_DATES_USER_PROMPT,
)


logger = logging.getLogger(__name__)


class StudyTimelineDatesCheckError(Exception):
    """Custom exception for failures during the study timeline dates extraction check."""

    pass


async def execute_study_timeline_dates_check(
    job_id: uuid.UUID, job_identifier: str, pdf_file_path: str, db: AsyncSession, redis_client=None
) -> Optional[Dict[str, Any]]:
    """
    Performs Check #3 Part A: Uses the LLM service to extract study timeline dates.
    Returns a dictionary payload for database update.
    Raises:
        StudyTimelineDatesCheckError: If a critical error occurs.
    """
    logfire.info(
        f"Preparing Check #3 (Timeline Dates) for job {job_id}, PDF: {pdf_file_path}"
    )

    path_obj = Path(pdf_file_path)
    if not path_obj.is_file():
        logger.error(
            f"PDF file not found at path for job {job_id} (Timeline Dates): {pdf_file_path}"
        )
        raise StudyTimelineDatesCheckError(
            f"PDF file not found for Timeline Dates check: {pdf_file_path}"
        )

    with logfire.span(
        "timeline_consistency_execution job_id={job_id}", job_id=str(job_id)
    ):
        logfire.info(
            f"Starting execution of Check #3 (Timeline Dates) for job {job_id}"
        )
        results_payload_for_check: Optional[Dict[str, Any]] = None
        try:
            llm_response_dict = await llm_service.get_structured_llm_response(
                system_prompt=DEFAULT_SYSTEM_PROMPT,
                user_prompt_template=STUDY_TIMELINE_DATES_USER_PROMPT,
                response_model=StudyTimelineDates,
                pdf_file_path=pdf_file_path,
                original_filename_for_logging=job_identifier,
                job_id=str(job_id),
                redis_client=redis_client,
            )

            parsed_timeline_info: Optional[StudyTimelineDates] = None
            token_usage_data: Optional[Dict[str, Any]] = None
            cost_info: Optional[Dict[str, Any]] = None
            model_used: Optional[str] = None

            if llm_response_dict:
                if isinstance(llm_response_dict.get("parsed_info"), StudyTimelineDates):
                    parsed_timeline_info = llm_response_dict["parsed_info"]
                token_usage_data = llm_response_dict.get("token_usage")
                cost_info = llm_response_dict.get("cost_info")
                model_used = llm_response_dict.get("model_used")

            if token_usage_data:
                current_span = trace.get_current_span()
                if current_span.is_recording():
                    attributes_to_set = {
                        f"timeline_consistency.token_usage.{key}": value
                        for key, value in token_usage_data.items()
                    }
                    current_span.set_attributes(attributes_to_set)
                    logfire.debug(
                        f"Set token usage attributes for job {job_id} on 'timeline_consistency_execution' span."
                    )

                # Log cost and model information
                if cost_info:
                    logger.info(f"Check 3 LLM costs for job {job_id}: {cost_info}")
                if model_used:
                    logger.info(
                        f"Check 3 LLM model used for job {job_id}: {model_used}"
                    )

            if parsed_timeline_info:
                logger.info(
                    f"LLM timeline dates extraction successful for job {job_id}."
                )
                results_payload_for_check = {
                    "timeline_consistency": {
                        "recruitment_start": parsed_timeline_info.recruitment_start.model_dump(),
                        "recruitment_finish": parsed_timeline_info.recruitment_finish.model_dump(),
                        "study_end_date": parsed_timeline_info.study_end_date.model_dump(),
                        "status": "COMPLETED_SUCCESS",
                    }
                }
            else:
                logger.error(
                    f"LLM timeline dates extraction failed to produce any response or parsed info for job {job_id}."
                )
                # This check won't directly mark the main job as FAILED here.
                # It will return a payload indicating its own failure, or raise an exception.
                # The orchestrator (arq_tasks) will make the final decision on job status.
                raise StudyTimelineDatesCheckError(
                    "Check 3 (Timeline Dates): LLM service returned no data or failed internally."
                )

            if results_payload_for_check:
                if token_usage_data:
                    results_payload_for_check["timeline_consistency"]["token_usage"] = (
                        token_usage_data
                    )
                if cost_info:
                    results_payload_for_check["timeline_consistency"]["cost_info"] = (
                        cost_info
                    )
                if model_used:
                    results_payload_for_check["timeline_consistency"]["model_used"] = (
                        model_used
                    )

            return results_payload_for_check

        except StudyTimelineDatesCheckError:
            raise
        except Exception as e:
            logger.error(
                f"Error during Check #3 (Timeline Dates) for job {job_id}: {e}",
                exc_info=True,
            )
            # No direct DB update here; let the orchestrator handle overall job status based on this exception.
            raise StudyTimelineDatesCheckError(
                f"Check 3 (Timeline Dates) failed for job {job_id}: {str(e)}"
            ) from e
