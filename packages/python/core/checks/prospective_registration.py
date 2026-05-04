import logging
import uuid
from typing import Optional, Dict, Any
from datetime import datetime
import logfire

from core.schemas.prospective_registration_results import (
    ProspectiveRegistrationAnalysisOutput,
    ProspectiveRegistrationStatusEnum,
)
from core.utils.date_parser import parse_date_to_components, get_comparison_string

logger = logging.getLogger(__name__)


class ProspectiveRegistrationCheckError(Exception):
    """Custom exception for critical failures during the prospective registration check."""

    pass


async def execute_prospective_registration_check(
    job_id: uuid.UUID,
    llm_timeline_dates_payload: Optional[Dict[str, Any]],
    registry_lookup_payload: Optional[Dict[str, Any]],
) -> ProspectiveRegistrationAnalysisOutput:
    """
    Perform the prospective registration analysis.
    Compares LLM-extracted recruitment start date with registry-obtained registration date.
    """
    with logfire.span("prospective_registration_check", job_id=str(job_id)):
        logfire.info("Starting prospective registration check", job_id=str(job_id))

        output = ProspectiveRegistrationAnalysisOutput(
            status=ProspectiveRegistrationStatusEnum.INDETERMINATE_MISSING_DATA,
            message="Analysis not yet performed.",
        )

        # --- 1. Extract necessary data from input payloads ---
        llm_recruitment_start_raw: Optional[str] = None
        if llm_timeline_dates_payload and isinstance(
            llm_timeline_dates_payload.get("recruitment_start"), dict
        ):
            llm_recruitment_start_raw = llm_timeline_dates_payload["recruitment_start"].get(
                "normalized_date"
            )
        output.llm_recruitment_start_raw = llm_recruitment_start_raw

        registry_name_from_check2: Optional[str] = None
        registry_registration_date_raw: Optional[str] = None
        if registry_lookup_payload:
            registry_name_from_check2 = registry_lookup_payload.get("registry_type")
            if isinstance(registry_lookup_payload.get("lookup_results"), dict):
                registry_registration_date_raw = registry_lookup_payload[
                    "lookup_results"
                ].get("study_first_submit_qc_date")
        output.registry_name_from_check2 = registry_name_from_check2
        output.registry_registration_date_raw = registry_registration_date_raw

        # --- 2. Validate critical inputs ---
        if not llm_recruitment_start_raw:
            output.status = ProspectiveRegistrationStatusEnum.INDETERMINATE_MISSING_DATA
            output.message = "LLM-extracted recruitment start date (normalized_date) is missing or empty."
            logger.warning(f"Job {job_id} (Prospective registration): {output.message}")
            return output

        if not registry_registration_date_raw:
            output.status = ProspectiveRegistrationStatusEnum.INDETERMINATE_MISSING_DATA
            output.message = "Registry registration date (study_first_submit_qc_date) is missing or empty."
            logger.warning(f"Job {job_id} (Prospective registration): {output.message}")
            return output

        if not registry_name_from_check2:
            output.status = ProspectiveRegistrationStatusEnum.INDETERMINATE_MISSING_DATA
            output.message = "Registry name/type from Check 2 is missing, cannot determine date parsing format for registry date."
            logger.warning(f"Job {job_id} (Prospective registration): {output.message}")
            return output

        # --- 3. Parse Dates ---
        llm_date_components = parse_date_to_components(
        llm_recruitment_start_raw, job_id=str(job_id)
    )
    if not llm_date_components:
        output.llm_recruitment_start_parsed_for_comparison = None
    else:
        output.llm_recruitment_start_parsed_for_comparison = get_comparison_string(
            llm_date_components
        )
    if not llm_date_components:
        output.status = (
            ProspectiveRegistrationStatusEnum.INDETERMINATE_DATE_PARSING_ERROR
        )
        output.message = f"Failed to parse LLM recruitment start date: '{llm_recruitment_start_raw}'."
        logger.error(f"Job {job_id} (Prospective registration): {output.message}")
        return output

    registry_date_components = parse_date_to_components(
        registry_registration_date_raw,
        registry_name_hint=registry_name_from_check2,
        job_id=str(job_id),
    )
    if not registry_date_components:
        output.registry_registration_date_parsed_for_comparison = None
    else:
        output.registry_registration_date_parsed_for_comparison = get_comparison_string(
            registry_date_components
        )
    if not registry_date_components:
        output.status = (
            ProspectiveRegistrationStatusEnum.INDETERMINATE_DATE_PARSING_ERROR
        )
        output.message = f"Failed to parse registry registration date: '{registry_registration_date_raw}' with hint '{registry_name_from_check2}'."
        logger.error(f"Job {job_id} (Prospective registration): {output.message}")
        return output

    # --- 4. Perform Comparison Logic ---
    try:
        llm_year = llm_date_components.get("year")
        llm_month = llm_date_components.get("month")
        llm_day = llm_date_components.get("day")

        reg_year = registry_date_components.get("year")
        reg_month = registry_date_components.get("month")
        reg_day = registry_date_components.get("day")

        # Ensure required components are ints before comparison
        if not (
            isinstance(llm_year, int)
            and isinstance(llm_month, int)
            and isinstance(reg_year, int)
            and isinstance(reg_month, int)
        ):
            output.status = (
                ProspectiveRegistrationStatusEnum.INDETERMINATE_DATE_PARSING_ERROR
            )
            output.message = (
                "Parsed year/month components are missing or invalid for comparison."
            )
            logger.error(f"Job {job_id} (Prospective registration): {output.message}")
            return output

        llm_year_i = llm_year
        llm_month_i = llm_month
        reg_year_i = reg_year
        reg_month_i = reg_month

        # Determine comparison level
        if isinstance(llm_day, int) and isinstance(reg_day, int):
            output.comparison_level = "day"
            # Full date comparison
            llm_dt = datetime(llm_year_i, llm_month_i, llm_day)
            reg_dt = datetime(reg_year_i, reg_month_i, reg_day)
            if reg_dt <= llm_dt:
                output.status = ProspectiveRegistrationStatusEnum.PROSPECTIVE
                output.is_prospective = True
                output.message = (
                    "Registration date is on or before LLM recruitment start date."
                )
            else:
                output.status = ProspectiveRegistrationStatusEnum.RETROSPECTIVE
                output.is_prospective = False
                output.message = (
                    "Registration date is after LLM recruitment start date."
                )
                logfire.warn("RETROSPECTIVE REGISTRATION detected", job_id=str(job_id))
        else:
            output.comparison_level = "month"
            if reg_year_i < llm_year_i:
                output.status = ProspectiveRegistrationStatusEnum.PROSPECTIVE
                output.is_prospective = True
            elif reg_year_i > llm_year_i:
                output.status = ProspectiveRegistrationStatusEnum.RETROSPECTIVE
                output.is_prospective = False
            else:
                if reg_month_i <= llm_month_i:
                    output.status = ProspectiveRegistrationStatusEnum.PROSPECTIVE
                    output.is_prospective = True
                else:
                    output.status = ProspectiveRegistrationStatusEnum.RETROSPECTIVE
                    output.is_prospective = False
                    logfire.warn("RETROSPECTIVE REGISTRATION detected (month level)", job_id=str(job_id))

            output.message = f"Comparison performed at month level. Registration: {reg_year_i}-{reg_month_i:02d}, LLM Recruitment Start: {llm_year_i}-{llm_month_i:02d}."
            if output.is_prospective is True:
                output.message += " Deemed prospective at month level."
            elif output.is_prospective is False:
                output.message += " Deemed retrospective at month level."

        logger.info(
            f"Job {job_id} (Prospective registration): Status: {output.status}, Message: {output.message}"
        )

    except KeyError as ke:
        output.status = (
            ProspectiveRegistrationStatusEnum.INDETERMINATE_DATE_PARSING_ERROR
        )
        output.message = f"Internal error: Missing expected year/month from parsed date components. {ke}"
        logger.error(
            f"Job {job_id} (Prospective registration): {output.message}", exc_info=True
        )
    except Exception as e:
        output.status = ProspectiveRegistrationStatusEnum.INDETERMINATE_MISSING_DATA
        output.message = (
            f"An unexpected error occurred during date comparison: {str(e)}"
        )
        logger.error(
            f"Job {job_id} (Prospective registration): Unexpected error in comparison logic: {e}",
            exc_info=True,
        )
        logfire.error("Prospective registration check failed", exc_info=True, job_id=str(job_id))

    return output
