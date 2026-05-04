from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional

from core.schemas.check_results import CheckResultEnvelope, SectionSummaryEnvelope
from core.schemas.enums import (
    CheckFindingCode,
    CheckOutcomeStatus,
    SectionFindingCode,
)

SeverityOrder = {
    CheckOutcomeStatus.CONCERN: 4,
    CheckOutcomeStatus.WARNING: 3,
    CheckOutcomeStatus.PENDING: 2,
    CheckOutcomeStatus.UNKNOWN: 1,
    CheckOutcomeStatus.OK: 0,
}


def _collect_provider_messages(*messages: Optional[str]) -> List[str]:
    return [msg for msg in messages if msg]


# --- Individual check normalisers -------------------------------------------------


def _normalize_trial(check: Optional[Mapping[str, Any]], step: Mapping[str, Any]) -> CheckResultEnvelope:
    payload = dict(check or {}) or None
    status_raw = (payload or {}).get("status", "")
    trial_id = (payload or {}).get("trial_id", "") or ""
    comment = (payload or {}).get("comment")
    error = (payload or {}).get("error")
    step_status = (step or {}).get("status")
    step_error = (step or {}).get("error")

    provider_messages = _collect_provider_messages(comment, error, step_error)

    if payload:
        status_upper = str(status_raw).upper()
        if status_upper == "SKIPPED_DISABLED":
            summary = "Trial ID extraction disabled for active profile."
            return CheckResultEnvelope(
                check_id="trial_llm_extraction",
                status=CheckOutcomeStatus.UNKNOWN,
                finding_code=CheckFindingCode.TRIAL_ID_CHECK_FAILED,
                summary=summary,
                detail=(payload or {}).get("message") or comment,
                payload=payload,
                provider_messages=provider_messages,
            )
        if "COMPLETED_SUCCESS" in status_upper and trial_id:
            summary = f"Trial ID extracted ({trial_id})"
            return CheckResultEnvelope(
                check_id="trial_llm_extraction",
                status=CheckOutcomeStatus.OK,
                finding_code=CheckFindingCode.TRIAL_ID_FOUND,
                summary=summary,
                detail=comment,
                payload=payload,
                provider_messages=provider_messages,
            )
        if "COMPLETED_NOT_FOUND" in status_upper or not trial_id:
            summary = "Trial registration ID was not found."
            return CheckResultEnvelope(
                check_id="trial_llm_extraction",
                status=CheckOutcomeStatus.CONCERN,
                finding_code=CheckFindingCode.TRIAL_ID_NOT_FOUND,
                summary=summary,
                detail=comment,
                payload=payload,
                provider_messages=provider_messages,
            )
        if "FAILED" in status_upper:
            summary = "Trial ID extraction failed."
            return CheckResultEnvelope(
                check_id="trial_llm_extraction",
                status=CheckOutcomeStatus.WARNING,
                finding_code=CheckFindingCode.TRIAL_ID_CHECK_FAILED,
                summary=summary,
                detail=comment or error,
                payload=payload,
                provider_messages=provider_messages,
            )

    if step_status in {"RUNNING", "PENDING"}:
        return CheckResultEnvelope(
            check_id="trial_llm_extraction",
            status=CheckOutcomeStatus.PENDING,
            finding_code=CheckFindingCode.TRIAL_ID_CHECK_FAILED,
            summary="Trial ID extraction is still running.",
            detail=step_error,
            payload=payload,
            provider_messages=provider_messages,
        )

    if step_status == "FAILED":
        return CheckResultEnvelope(
            check_id="trial_llm_extraction",
            status=CheckOutcomeStatus.WARNING,
            finding_code=CheckFindingCode.TRIAL_ID_CHECK_FAILED,
            summary="Trial ID extraction failed.",
            detail=step_error,
            payload=payload,
            provider_messages=provider_messages,
        )

    return CheckResultEnvelope(
        check_id="trial_llm_extraction",
        status=CheckOutcomeStatus.UNKNOWN,
        finding_code=CheckFindingCode.TRIAL_ID_CHECK_FAILED,
        summary="Trial ID extraction outcome is unavailable.",
        detail=step_error,
        payload=payload,
        provider_messages=provider_messages,
    )


def _normalize_registry(check: Optional[Mapping[str, Any]], step: Mapping[str, Any]) -> CheckResultEnvelope:
    payload = dict(check or {}) or None
    status_raw = (payload or {}).get("status", "")
    error = (payload or {}).get("error_message")
    lookup = (payload or {}).get("lookup_results") or {}
    lookup_success = lookup.get("lookup_successful")
    registry_name = lookup.get("registry_name")
    step_error = (step or {}).get("error")
    step_status = (step or {}).get("status")

    provider_messages = _collect_provider_messages(error, lookup.get("error_message"), step_error)

    if payload:
        if str(status_raw).upper() == "SKIPPED_DISABLED":
            return CheckResultEnvelope(
                check_id="registry_crosscheck",
                status=CheckOutcomeStatus.UNKNOWN,
                finding_code=CheckFindingCode.REGISTRY_LOOKUP_FAILED,
                summary="Registry lookup disabled for active profile.",
                detail=(payload or {}).get("message") or error,
                payload=payload,
                provider_messages=provider_messages,
            )
        if error:
            return CheckResultEnvelope(
                check_id="registry_crosscheck",
                status=CheckOutcomeStatus.WARNING,
                finding_code=CheckFindingCode.REGISTRY_LOOKUP_FAILED,
                summary="Registry lookup failed.",
                detail=error,
                payload=payload,
                provider_messages=provider_messages,
            )
        if lookup_success:
            summary = "Registry record confirmed."
            detail = lookup.get("study_first_submit_qc_date")
            if registry_name and detail:
                detail = f"{registry_name}: QC date {detail}"
            elif registry_name:
                detail = f"Registry: {registry_name}"
            return CheckResultEnvelope(
                check_id="registry_crosscheck",
                status=CheckOutcomeStatus.OK,
                finding_code=CheckFindingCode.REGISTRY_CONFIRMED,
                summary=summary,
                detail=detail,
                payload=payload,
                provider_messages=provider_messages,
            )
        return CheckResultEnvelope(
            check_id="registry_crosscheck",
            status=CheckOutcomeStatus.CONCERN,
            finding_code=CheckFindingCode.REGISTRY_NOT_FOUND,
            summary="Registry record could not be confirmed.",
            detail=lookup.get("error_message") or lookup.get("registry_name"),
            payload=payload,
            provider_messages=provider_messages,
        )

    if step_status in {"RUNNING", "PENDING"}:
        return CheckResultEnvelope(
            check_id="registry_crosscheck",
            status=CheckOutcomeStatus.PENDING,
            finding_code=CheckFindingCode.REGISTRY_LOOKUP_FAILED,
            summary="Registry lookup is still running.",
            detail=step_error,
            payload=payload,
            provider_messages=provider_messages,
        )

    if step_status == "FAILED":
        return CheckResultEnvelope(
            check_id="registry_crosscheck",
            status=CheckOutcomeStatus.WARNING,
            finding_code=CheckFindingCode.REGISTRY_LOOKUP_FAILED,
            summary="Registry lookup failed.",
            detail=step_error,
            payload=payload,
            provider_messages=provider_messages,
        )

    return CheckResultEnvelope(
        check_id="registry_crosscheck",
        status=CheckOutcomeStatus.UNKNOWN,
        finding_code=CheckFindingCode.REGISTRY_LOOKUP_FAILED,
        summary="Registry lookup outcome is unavailable.",
        detail=step_error,
        payload=payload,
        provider_messages=provider_messages,
    )


def _normalize_timeline(check: Optional[Mapping[str, Any]], step: Mapping[str, Any]) -> CheckResultEnvelope:
    payload = dict(check or {}) or None
    status_raw = (payload or {}).get("status", "")
    step_status = (step or {}).get("status")
    step_error = (step or {}).get("error")

    provider_messages = _collect_provider_messages(step_error)

    if payload:
        status_upper = str(status_raw).upper()
        if status_upper == "SKIPPED_DISABLED":
            return CheckResultEnvelope(
                check_id="timeline_consistency",
                status=CheckOutcomeStatus.UNKNOWN,
                finding_code=CheckFindingCode.TIMELINE_NOT_AVAILABLE,
                summary="Timeline extraction disabled for active profile.",
                detail=(payload or {}).get("message"),
                payload=payload,
                provider_messages=provider_messages,
            )
        meaningful_dates = []
        for key in ("recruitment_start", "recruitment_finish", "study_end_date"):
            date_info = (payload or {}).get(key, {})
            if isinstance(date_info, dict) and date_info.get("normalized_date"):
                meaningful_dates.append(date_info["normalized_date"])
        if "COMPLETED_SUCCESS" in status_upper and meaningful_dates:
            detail = ", ".join(meaningful_dates)
            return CheckResultEnvelope(
                check_id="timeline_consistency",
                status=CheckOutcomeStatus.OK,
                finding_code=CheckFindingCode.TIMELINE_EXTRACTED,
                summary="Timeline dates extracted.",
                detail=detail,
                payload=payload,
                provider_messages=provider_messages,
            )
        if "COMPLETED_SUCCESS" in status_upper and not meaningful_dates:
            return CheckResultEnvelope(
                check_id="timeline_consistency",
                status=CheckOutcomeStatus.WARNING,
                finding_code=CheckFindingCode.TIMELINE_NOT_AVAILABLE,
                summary="Timeline dates not identified in the document.",
                detail=None,
                payload=payload,
                provider_messages=provider_messages,
            )
        if "FAILED" in status_upper:
            return CheckResultEnvelope(
                check_id="timeline_consistency",
                status=CheckOutcomeStatus.WARNING,
                finding_code=CheckFindingCode.TIMELINE_EXTRACTION_FAILED,
                summary="Timeline extraction failed.",
                detail=step_error,
                payload=payload,
                provider_messages=provider_messages,
            )

    if step_status in {"RUNNING", "PENDING"}:
        return CheckResultEnvelope(
            check_id="timeline_consistency",
            status=CheckOutcomeStatus.PENDING,
            finding_code=CheckFindingCode.TIMELINE_EXTRACTION_FAILED,
            summary="Timeline extraction is still running.",
            detail=step_error,
            payload=payload,
            provider_messages=provider_messages,
        )

    if step_status == "FAILED":
        return CheckResultEnvelope(
            check_id="timeline_consistency",
            status=CheckOutcomeStatus.WARNING,
            finding_code=CheckFindingCode.TIMELINE_EXTRACTION_FAILED,
            summary="Timeline extraction failed.",
            detail=step_error,
            payload=payload,
            provider_messages=provider_messages,
        )

    return CheckResultEnvelope(
        check_id="timeline_consistency",
        status=CheckOutcomeStatus.UNKNOWN,
        finding_code=CheckFindingCode.TIMELINE_EXTRACTION_FAILED,
        summary="Timeline extraction outcome is unavailable.",
        detail=step_error,
        payload=payload,
        provider_messages=provider_messages,
    )


def _normalize_prospective(
    check: Optional[Mapping[str, Any]], step: Mapping[str, Any]
) -> CheckResultEnvelope:
    payload = dict(check or {}) or None
    raw_status_value = (payload or {}).get("status", "")
    if isinstance(raw_status_value, str):
        status_raw = raw_status_value
    else:
        status_raw = str(raw_status_value)
    # Handle Enum-like strings e.g. "ProspectiveRegistrationStatusEnum.PROSPECTIVE"
    status_normalized = status_raw.upper().split(".")[-1]
    message = (payload or {}).get("message")
    step_status = (step or {}).get("status")
    step_error = (step or {}).get("error")

    provider_messages = _collect_provider_messages(message, step_error)

    status_upper = status_normalized
    if payload and status_upper == "SKIPPED_DISABLED":
        return CheckResultEnvelope(
            check_id="prospective_registration_analysis",
            status=CheckOutcomeStatus.UNKNOWN,
            finding_code=CheckFindingCode.PROSPECTIVE_ANALYSIS_FAILED,
            summary="Prospective registration analysis disabled for active profile.",
            detail=(payload or {}).get("message"),
            payload=payload,
            provider_messages=provider_messages,
        )
    if status_upper == "PROSPECTIVE":
        return CheckResultEnvelope(
            check_id="prospective_registration_analysis",
            status=CheckOutcomeStatus.OK,
            finding_code=CheckFindingCode.PROSPECTIVE_CONFIRMED,
            summary="Registration assessed as prospective.",
            detail=message,
            payload=payload,
            provider_messages=provider_messages,
        )
    if status_upper == "RETROSPECTIVE":
        return CheckResultEnvelope(
            check_id="prospective_registration_analysis",
            status=CheckOutcomeStatus.CONCERN,
            finding_code=CheckFindingCode.RETROSPECTIVE_IDENTIFIED,
            summary="Registration assessed as retrospective.",
            detail=message,
            payload=payload,
            provider_messages=provider_messages,
        )
    if status_upper.startswith("INDETERMINATE"):
        return CheckResultEnvelope(
            check_id="prospective_registration_analysis",
            status=CheckOutcomeStatus.WARNING,
            finding_code=CheckFindingCode.PROSPECTIVE_INDETERMINATE,
            summary="Registration timing could not be determined.",
            detail=message,
            payload=payload,
            provider_messages=provider_messages,
        )
    if status_upper:
        return CheckResultEnvelope(
            check_id="prospective_registration_analysis",
            status=CheckOutcomeStatus.WARNING,
            finding_code=CheckFindingCode.PROSPECTIVE_ANALYSIS_FAILED,
            summary="Prospective registration analysis failed.",
            detail=message,
            payload=payload,
            provider_messages=provider_messages,
        )

    if step_status in {"RUNNING", "PENDING"}:
        return CheckResultEnvelope(
            check_id="prospective_registration_analysis",
            status=CheckOutcomeStatus.PENDING,
            finding_code=CheckFindingCode.PROSPECTIVE_ANALYSIS_FAILED,
            summary="Prospective registration analysis is still running.",
            detail=step_error,
            payload=payload,
            provider_messages=provider_messages,
        )

    if step_status == "FAILED":
        return CheckResultEnvelope(
            check_id="prospective_registration_analysis",
            status=CheckOutcomeStatus.WARNING,
            finding_code=CheckFindingCode.PROSPECTIVE_ANALYSIS_FAILED,
            summary="Prospective registration analysis failed.",
            detail=step_error,
            payload=payload,
            provider_messages=provider_messages,
        )

    return CheckResultEnvelope(
        check_id="prospective_registration_analysis",
        status=CheckOutcomeStatus.UNKNOWN,
        finding_code=CheckFindingCode.PROSPECTIVE_ANALYSIS_FAILED,
        summary="Prospective registration analysis outcome is unavailable.",
        detail=step_error,
        payload=payload,
        provider_messages=provider_messages,
    )


def _normalize_grobid_primary(
    check: Optional[Mapping[str, Any]], step: Mapping[str, Any]
) -> CheckResultEnvelope:
    payload = dict(check or {}) or None
    status_raw = str((payload or {}).get("status", ""))
    comment = (payload or {}).get("comment")
    doi_value = (payload or {}).get("doi_value") or (payload or {}).get("doi")
    step_status = (step or {}).get("status")
    step_error = (step or {}).get("error")

    provider_messages = _collect_provider_messages(comment, step_error)

    status_upper = status_raw.upper()
    if "COMPLETED_SUCCESS" in status_upper and doi_value:
        summary = "Primary DOI extracted."
        detail = f"DOI: {doi_value}"
        return CheckResultEnvelope(
            check_id="grobid_primary_metadata",
            status=CheckOutcomeStatus.OK,
            finding_code=CheckFindingCode.DOI_IDENTIFIED,
            summary=summary,
            detail=detail,
            payload=payload,
            provider_messages=provider_messages,
        )
    if "COMPLETED_NOT_FOUND" in status_upper:
        return CheckResultEnvelope(
            check_id="grobid_primary_metadata",
            status=CheckOutcomeStatus.WARNING,
            finding_code=CheckFindingCode.DOI_NOT_FOUND,
            summary="Primary DOI was not found in the document.",
            detail=comment,
            payload=payload,
            provider_messages=provider_messages,
        )
    if "FAILED" in status_upper:
        return CheckResultEnvelope(
            check_id="grobid_primary_metadata",
            status=CheckOutcomeStatus.WARNING,
            finding_code=CheckFindingCode.DOI_EXTRACTION_FAILED,
            summary="Primary DOI extraction failed.",
            detail=comment or step_error,
            payload=payload,
            provider_messages=provider_messages,
        )

    if step_status in {"RUNNING", "PENDING"}:
        return CheckResultEnvelope(
            check_id="grobid_primary_metadata",
            status=CheckOutcomeStatus.PENDING,
            finding_code=CheckFindingCode.DOI_EXTRACTION_FAILED,
            summary="Primary DOI extraction is still running.",
            detail=step_error,
            payload=payload,
            provider_messages=provider_messages,
        )

    if step_status == "FAILED":
        return CheckResultEnvelope(
            check_id="grobid_primary_metadata",
            status=CheckOutcomeStatus.WARNING,
            finding_code=CheckFindingCode.DOI_EXTRACTION_FAILED,
            summary="Primary DOI extraction failed.",
            detail=step_error,
            payload=payload,
            provider_messages=provider_messages,
        )

    return CheckResultEnvelope(
        check_id="grobid_primary_metadata",
        status=CheckOutcomeStatus.UNKNOWN,
        finding_code=CheckFindingCode.DOI_EXTRACTION_FAILED,
        summary="Primary DOI extraction outcome is unavailable.",
        detail=step_error,
        payload=payload,
        provider_messages=provider_messages,
    )


def _normalize_grobid_references(
    check: Optional[Mapping[str, Any]], step: Mapping[str, Any]
) -> CheckResultEnvelope:
    payload = dict(check or {}) or None
    status_raw = str((payload or {}).get("status", ""))
    step_status = (step or {}).get("status")
    step_error = (step or {}).get("error")

    provider_messages = _collect_provider_messages(payload.get("comment") if payload else None, step_error)

    status_upper = status_raw.upper()
    if "COMPLETED_SUCCESS" in status_upper:
        doi_count = len((payload or {}).get("reference_dois", []) or [])
        summary = "Reference metadata extracted."
        detail = f"DOIs captured: {doi_count}" if doi_count else None
        return CheckResultEnvelope(
            check_id="grobid_reference_metadata",
            status=CheckOutcomeStatus.OK,
            finding_code=CheckFindingCode.REFERENCE_METADATA_CAPTURED,
            summary=summary,
            detail=detail,
            payload=payload,
            provider_messages=provider_messages,
        )
    if "FAILED_TIMEOUT_GRACEFUL_DEGRADATION" in status_upper or "COMPLETED_NOT_FOUND" in status_upper:
        summary = "Reference metadata partially available."
        return CheckResultEnvelope(
            check_id="grobid_reference_metadata",
            status=CheckOutcomeStatus.WARNING,
            finding_code=CheckFindingCode.REFERENCE_METADATA_PARTIAL,
            summary=summary,
            detail=payload.get("comment") if payload else None,
            payload=payload,
            provider_messages=provider_messages,
        )
    if "FAILED" in status_upper:
        summary = "Reference metadata extraction failed."
        return CheckResultEnvelope(
            check_id="grobid_reference_metadata",
            status=CheckOutcomeStatus.WARNING,
            finding_code=CheckFindingCode.REFERENCE_METADATA_FAILED,
            summary=summary,
            detail=payload.get("comment") if payload else step_error,
            payload=payload,
            provider_messages=provider_messages,
        )

    if step_status in {"RUNNING", "PENDING"}:
        return CheckResultEnvelope(
            check_id="grobid_reference_metadata",
            status=CheckOutcomeStatus.PENDING,
            finding_code=CheckFindingCode.REFERENCE_METADATA_FAILED,
            summary="Reference metadata extraction is still running.",
            detail=step_error,
            payload=payload,
            provider_messages=provider_messages,
        )

    if step_status == "FAILED":
        return CheckResultEnvelope(
            check_id="grobid_reference_metadata",
            status=CheckOutcomeStatus.WARNING,
            finding_code=CheckFindingCode.REFERENCE_METADATA_FAILED,
            summary="Reference metadata extraction failed.",
            detail=step_error,
            payload=payload,
            provider_messages=provider_messages,
        )

    return CheckResultEnvelope(
        check_id="grobid_reference_metadata",
        status=CheckOutcomeStatus.UNKNOWN,
        finding_code=CheckFindingCode.REFERENCE_METADATA_FAILED,
        summary="Reference metadata extraction outcome is unavailable.",
        detail=step_error,
        payload=payload,
        provider_messages=provider_messages,
    )


def _normalize_retraction_detection(check: Optional[Mapping[str, Any]], step: Mapping[str, Any]) -> CheckResultEnvelope:
    """Normalize INSPECT-SR 1.1: Retraction Detection (main article + references)."""
    payload = dict(check or {}) or None
    error_message = (payload or {}).get("error_message")
    summary = (payload or {}).get("summary", {})
    main_retracted = summary.get("main_article_retracted", False)
    refs_retracted = summary.get("references_retracted", 0)
    refs_checked = summary.get("references_checked", 0)
    summary_message = summary.get("message", "")
    step_status = (step or {}).get("status")
    step_error = (step or {}).get("error")

    provider_messages = _collect_provider_messages(error_message, step_error)

    if error_message:
        return CheckResultEnvelope(
            check_id="retraction_detection",
            status=CheckOutcomeStatus.WARNING,
            finding_code=CheckFindingCode.RETRACTION_LOOKUP_FAILED,
            summary="Retraction detection lookup failed.",
            detail=error_message,
            payload=payload,
            provider_messages=provider_messages,
        )

    if main_retracted:
        return CheckResultEnvelope(
            check_id="retraction_detection",
            status=CheckOutcomeStatus.CONCERN,
            finding_code=CheckFindingCode.RETRACTION_MAIN_MATCH,
            summary="Main article appears in Retraction Watch.",
            detail=summary_message,
            payload=payload,
            provider_messages=provider_messages,
        )

    if refs_retracted > 0:
        detail = f"{refs_retracted}/{refs_checked} references retracted"
        return CheckResultEnvelope(
            check_id="retraction_detection",
            status=CheckOutcomeStatus.CONCERN,
            finding_code=CheckFindingCode.RETRACTION_REFERENCE_MATCH,
            summary="Reference publications listed in Retraction Watch.",
            detail=detail,
            payload=payload,
            provider_messages=provider_messages,
        )

    if payload:
        detail = f"Main article: clean. References: {refs_checked} checked, none retracted."
        return CheckResultEnvelope(
            check_id="retraction_detection",
            status=CheckOutcomeStatus.OK,
            finding_code=CheckFindingCode.RETRACTION_NO_MATCH,
            summary="No retractions detected.",
            detail=detail,
            payload=payload,
            provider_messages=provider_messages,
        )

    if step_status in {"RUNNING", "PENDING"}:
        return CheckResultEnvelope(
            check_id="retraction_detection",
            status=CheckOutcomeStatus.PENDING,
            finding_code=CheckFindingCode.RETRACTION_LOOKUP_FAILED,
            summary="Retraction detection is still running.",
            detail=step_error,
            payload=payload,
            provider_messages=provider_messages,
        )

    if step_status == "FAILED":
        return CheckResultEnvelope(
            check_id="retraction_detection",
            status=CheckOutcomeStatus.WARNING,
            finding_code=CheckFindingCode.RETRACTION_LOOKUP_FAILED,
            summary="Retraction detection failed.",
            detail=step_error,
            payload=payload,
            provider_messages=provider_messages,
        )

    return CheckResultEnvelope(
        check_id="retraction_detection",
        status=CheckOutcomeStatus.UNKNOWN,
        finding_code=CheckFindingCode.RETRACTION_LOOKUP_FAILED,
        summary="Retraction detection outcome is unavailable.",
        detail=step_error,
        payload=payload,
        provider_messages=provider_messages,
    )


def _normalize_eoc_correction_detection(check: Optional[Mapping[str, Any]], step: Mapping[str, Any]) -> CheckResultEnvelope:
    """Normalize INSPECT-SR 1.2: EOC/Correction Detection (main article only)."""
    payload = dict(check or {}) or None
    error_message = (payload or {}).get("error_message")
    summary = (payload or {}).get("summary", {})
    has_notices = summary.get("main_article_has_eoc_or_correction", False)
    total_notices = summary.get("total_notices", 0)
    summary_message = summary.get("message", "")
    step_status = (step or {}).get("status")
    step_error = (step or {}).get("error")

    provider_messages = _collect_provider_messages(error_message, step_error)

    if error_message:
        return CheckResultEnvelope(
            check_id="eoc_correction_detection",
            status=CheckOutcomeStatus.WARNING,
            finding_code=CheckFindingCode.EOC_CORRECTION_LOOKUP_FAILED,
            summary="EOC/correction detection lookup failed.",
            detail=error_message,
            payload=payload,
            provider_messages=provider_messages,
        )

    if has_notices:
        detail = f"{total_notices} EOC/correction notice(s) found"
        return CheckResultEnvelope(
            check_id="eoc_correction_detection",
            status=CheckOutcomeStatus.CONCERN,
            finding_code=CheckFindingCode.EOC_CORRECTION_FOUND,
            summary="Main article has EOC or correction notices.",
            detail=detail,
            payload=payload,
            provider_messages=provider_messages,
        )

    if payload:
        return CheckResultEnvelope(
            check_id="eoc_correction_detection",
            status=CheckOutcomeStatus.OK,
            finding_code=CheckFindingCode.EOC_CORRECTION_CLEAR,
            summary="No EOC/correction notices found.",
            detail=summary_message,
            payload=payload,
            provider_messages=provider_messages,
        )

    if step_status in {"RUNNING", "PENDING"}:
        return CheckResultEnvelope(
            check_id="eoc_correction_detection",
            status=CheckOutcomeStatus.PENDING,
            finding_code=CheckFindingCode.EOC_CORRECTION_LOOKUP_FAILED,
            summary="EOC/correction detection is still running.",
            detail=step_error,
            payload=payload,
            provider_messages=provider_messages,
        )

    if step_status == "FAILED":
        return CheckResultEnvelope(
            check_id="eoc_correction_detection",
            status=CheckOutcomeStatus.WARNING,
            finding_code=CheckFindingCode.EOC_CORRECTION_LOOKUP_FAILED,
            summary="EOC/correction detection failed.",
            detail=step_error,
            payload=payload,
            provider_messages=provider_messages,
        )

    return CheckResultEnvelope(
        check_id="eoc_correction_detection",
        status=CheckOutcomeStatus.UNKNOWN,
        finding_code=CheckFindingCode.EOC_CORRECTION_LOOKUP_FAILED,
        summary="EOC/correction detection outcome is unavailable.",
        detail=step_error,
        payload=payload,
        provider_messages=provider_messages,
    )


def _normalize_author_retraction_history(check: Optional[Mapping[str, Any]], step: Mapping[str, Any]) -> CheckResultEnvelope:
    """Normalize INSPECT-SR 1.3: Author Retraction History."""
    payload = dict(check or {}) or None
    error_message = (payload or {}).get("error_message")
    summary = (payload or {}).get("summary", {})
    authors_with_retractions = summary.get("authors_with_retractions", 0)
    total_authors = summary.get("total_authors_checked", 0)
    total_retractions = summary.get("total_retractions_found", 0)
    step_status = (step or {}).get("status")
    step_error = (step or {}).get("error")

    provider_messages = _collect_provider_messages(error_message, step_error)

    if error_message:
        return CheckResultEnvelope(
            check_id="author_retraction_history",
            status=CheckOutcomeStatus.WARNING,
            finding_code=CheckFindingCode.AUTHOR_HISTORY_LOOKUP_FAILED,
            summary="Author retraction history lookup failed.",
            detail=error_message,
            payload=payload,
            provider_messages=provider_messages,
        )

    if authors_with_retractions > 0:
        detail = f"{authors_with_retractions}/{total_authors} author(s) with {total_retractions} total retraction(s)"
        return CheckResultEnvelope(
            check_id="author_retraction_history",
            status=CheckOutcomeStatus.CONCERN,
            finding_code=CheckFindingCode.AUTHOR_HISTORY_FOUND,
            summary="Author(s) have prior retractions.",
            detail=detail,
            payload=payload,
            provider_messages=provider_messages,
        )

    if payload:
        detail = f"{total_authors} author(s) checked, no retraction history"
        return CheckResultEnvelope(
            check_id="author_retraction_history",
            status=CheckOutcomeStatus.OK,
            finding_code=CheckFindingCode.AUTHOR_HISTORY_CLEAR,
            summary="No author retraction history found.",
            detail=detail,
            payload=payload,
            provider_messages=provider_messages,
        )

    if step_status in {"RUNNING", "PENDING"}:
        return CheckResultEnvelope(
            check_id="author_retraction_history",
            status=CheckOutcomeStatus.PENDING,
            finding_code=CheckFindingCode.AUTHOR_HISTORY_LOOKUP_FAILED,
            summary="Author retraction history check is still running.",
            detail=step_error,
            payload=payload,
            provider_messages=provider_messages,
        )

    if step_status == "FAILED":
        return CheckResultEnvelope(
            check_id="author_retraction_history",
            status=CheckOutcomeStatus.WARNING,
            finding_code=CheckFindingCode.AUTHOR_HISTORY_LOOKUP_FAILED,
            summary="Author retraction history check failed.",
            detail=step_error,
            payload=payload,
            provider_messages=provider_messages,
        )

    return CheckResultEnvelope(
        check_id="author_retraction_history",
        status=CheckOutcomeStatus.UNKNOWN,
        finding_code=CheckFindingCode.AUTHOR_HISTORY_LOOKUP_FAILED,
        summary="Author retraction history outcome is unavailable.",
        detail=step_error,
        payload=payload,
        provider_messages=provider_messages,
    )


def _normalize_pubpeer(check: Optional[Mapping[str, Any]], step: Mapping[str, Any]) -> CheckResultEnvelope:
    payload = dict(check or {}) or None
    status_raw = str((payload or {}).get("status", ""))
    error_message = (payload or {}).get("error_message")
    main_result = (payload or {}).get("main_paper_result") or {}
    scraped = main_result.get("scraped_comments") or {}
    comments = scraped.get("comments") or []
    api_error = main_result.get("error")
    step_status = (step or {}).get("status")
    step_error = (step or {}).get("error")

    provider_messages = _collect_provider_messages(error_message, api_error, step_error)

    status_upper = status_raw.upper()
    if payload and status_upper == "SKIPPED_DISABLED":
        return CheckResultEnvelope(
            check_id="pubpeer_signal_analysis",
            status=CheckOutcomeStatus.UNKNOWN,
            finding_code=CheckFindingCode.PUBPEER_LOOKUP_FAILED,
            summary="PubPeer analysis disabled for active profile.",
            detail=(payload or {}).get("message"),
            payload=payload,
            provider_messages=provider_messages,
        )
    if error_message or api_error or status_upper == "FAILED":
        return CheckResultEnvelope(
            check_id="pubpeer_signal_analysis",
            status=CheckOutcomeStatus.WARNING,
            finding_code=CheckFindingCode.PUBPEER_LOOKUP_FAILED,
            summary="PubPeer analysis failed.",
            detail=error_message or api_error,
            payload=payload,
            provider_messages=provider_messages,
        )
    if comments:
        detail = f"Comments: {len(comments)}"
        return CheckResultEnvelope(
            check_id="pubpeer_signal_analysis",
            status=CheckOutcomeStatus.CONCERN,
            finding_code=CheckFindingCode.PUBPEER_COMMENTS_FOUND,
            summary="PubPeer comments detected.",
            detail=detail,
            payload=payload,
            provider_messages=provider_messages,
        )
    if status_upper == "COMPLETED_NOT_FOUND":
        return CheckResultEnvelope(
            check_id="pubpeer_signal_analysis",
            status=CheckOutcomeStatus.OK,
            finding_code=CheckFindingCode.PUBPEER_NOT_FOUND,
            summary="No PubPeer entry found for this DOI.",
            detail=None,
            payload=payload,
            provider_messages=provider_messages,
        )
    if status_upper == "COMPLETED_SUCCESS":
        return CheckResultEnvelope(
            check_id="pubpeer_signal_analysis",
            status=CheckOutcomeStatus.OK,
            finding_code=CheckFindingCode.PUBPEER_NONE,
            summary="No PubPeer comments found.",
            detail=None,
            payload=payload,
            provider_messages=provider_messages,
        )

    if step_status in {"RUNNING", "PENDING"}:
        return CheckResultEnvelope(
            check_id="pubpeer_signal_analysis",
            status=CheckOutcomeStatus.PENDING,
            finding_code=CheckFindingCode.PUBPEER_LOOKUP_FAILED,
            summary="PubPeer analysis is still running.",
            detail=step_error,
            payload=payload,
            provider_messages=provider_messages,
        )

    if step_status == "FAILED":
        return CheckResultEnvelope(
            check_id="pubpeer_signal_analysis",
            status=CheckOutcomeStatus.WARNING,
            finding_code=CheckFindingCode.PUBPEER_LOOKUP_FAILED,
            summary="PubPeer analysis failed.",
            detail=step_error,
            payload=payload,
            provider_messages=provider_messages,
        )

    return CheckResultEnvelope(
        check_id="pubpeer_signal_analysis",
        status=CheckOutcomeStatus.UNKNOWN,
        finding_code=CheckFindingCode.PUBPEER_LOOKUP_FAILED,
        summary="PubPeer analysis outcome is unavailable.",
        detail=step_error,
        payload=payload,
        provider_messages=provider_messages,
    )


CHECK_NORMALIZERS = {
    "trial_llm_extraction": _normalize_trial,
    "registry_crosscheck": _normalize_registry,
    "timeline_consistency": _normalize_timeline,
    "prospective_registration_analysis": _normalize_prospective,
    "grobid_primary_metadata": _normalize_grobid_primary,
    "grobid_reference_metadata": _normalize_grobid_references,
    "retraction_detection": _normalize_retraction_detection,
    "eoc_correction_detection": _normalize_eoc_correction_detection,
    "author_retraction_history": _normalize_author_retraction_history,
    "pubpeer_signal_analysis": _normalize_pubpeer,
}


SECTION_DEFINITIONS = {
    "registration": {
        "checks": [
            "trial_llm_extraction",
            "registry_crosscheck",
            "timeline_consistency",
            "prospective_registration_analysis",
        ],
    },
    "retraction": {
        "checks": [
            "retraction_detection",
            "eoc_correction_detection",
            "author_retraction_history",
            "grobid_primary_metadata",
            "grobid_reference_metadata",
        ],
    },
    "pubpeer": {
        "checks": ["pubpeer_signal_analysis"],
    },
}


# --- Section aggregation ---------------------------------------------------------


def _worst_status(statuses: List[CheckOutcomeStatus]) -> CheckOutcomeStatus:
    return max(statuses or [CheckOutcomeStatus.UNKNOWN], key=lambda s: SeverityOrder.get(s, -1))


def _build_section_summary(section_id: str, checks: List[CheckResultEnvelope]) -> SectionSummaryEnvelope:
    statuses = [check.status for check in checks]
    worst = _worst_status(statuses)

    if section_id == "registration":
        return _registration_section_summary(checks, worst)
    if section_id == "retraction":
        return _retraction_section_summary(checks, worst)
    if section_id == "pubpeer":
        return _pubpeer_section_summary(checks, worst)

    return SectionSummaryEnvelope(
        section_id=section_id,
        status=worst,
        finding_code=None,
        summary="Outcome unavailable.",
        detail=None,
        contributing_checks=[check.check_id for check in checks],
    )


def _registration_section_summary(
    checks: List[CheckResultEnvelope], worst: CheckOutcomeStatus
) -> SectionSummaryEnvelope:
    by_id = {check.check_id: check for check in checks}
    prospective = by_id.get("prospective_registration_analysis")
    registry = by_id.get("registry_crosscheck")
    trial = by_id.get("trial_llm_extraction")

    if prospective and prospective.finding_code == CheckFindingCode.RETROSPECTIVE_IDENTIFIED:
        return SectionSummaryEnvelope(
            section_id="registration",
            status=CheckOutcomeStatus.CONCERN,
            finding_code=SectionFindingCode.REGISTRATION_RETROSPECTIVE,
            summary="Registration assessed as retrospective.",
            detail=prospective.detail,
            contributing_checks=[check.check_id for check in checks],
        )

    if any(check.status == CheckOutcomeStatus.WARNING for check in checks):
        detail = registry.detail if registry and registry.status == CheckOutcomeStatus.WARNING else None
        detail = detail or (trial.detail if trial and trial.status == CheckOutcomeStatus.WARNING else None)
        return SectionSummaryEnvelope(
            section_id="registration",
            status=CheckOutcomeStatus.WARNING,
            finding_code=SectionFindingCode.REGISTRATION_FAILED,
            summary="Registration checks were blocked or incomplete.",
            detail=detail,
            contributing_checks=[check.check_id for check in checks],
        )

    if trial and trial.status == CheckOutcomeStatus.CONCERN:
        return SectionSummaryEnvelope(
            section_id="registration",
            status=CheckOutcomeStatus.CONCERN,
            finding_code=SectionFindingCode.REGISTRATION_INDETERMINATE,
            summary="Trial registration ID was not located.",
            detail=trial.detail,
            contributing_checks=[check.check_id for check in checks],
        )

    if prospective and prospective.status == CheckOutcomeStatus.OK:
        return SectionSummaryEnvelope(
            section_id="registration",
            status=CheckOutcomeStatus.OK,
            finding_code=SectionFindingCode.REGISTRATION_PROSPECTIVE,
            summary="Registration assessed as prospective.",
            detail=prospective.detail,
            contributing_checks=[check.check_id for check in checks],
        )

    return SectionSummaryEnvelope(
        section_id="registration",
        status=worst,
        finding_code=SectionFindingCode.REGISTRATION_INDETERMINATE,
        summary="Registration outcome is indeterminate.",
        detail=None,
        contributing_checks=[check.check_id for check in checks],
    )


def _retraction_section_summary(
    checks: List[CheckResultEnvelope], worst: CheckOutcomeStatus
) -> SectionSummaryEnvelope:
    by_id = {check.check_id: check for check in checks}
    retraction_det = by_id.get("retraction_detection")
    eoc_correction = by_id.get("eoc_correction_detection")
    author_history = by_id.get("author_retraction_history")

    # Collect all concerns
    concerns = []
    if retraction_det and retraction_det.status == CheckOutcomeStatus.CONCERN:
        concerns.append(retraction_det.summary)
    if eoc_correction and eoc_correction.status == CheckOutcomeStatus.CONCERN:
        concerns.append(eoc_correction.summary)
    if author_history and author_history.status == CheckOutcomeStatus.CONCERN:
        concerns.append(author_history.summary)

    if concerns:
        detail = "; ".join(concerns)
        return SectionSummaryEnvelope(
            section_id="retraction",
            status=CheckOutcomeStatus.CONCERN,
            finding_code=SectionFindingCode.RETRACTION_MATCH,
            summary="Retraction Watch identified potential issues.",
            detail=detail,
            contributing_checks=[check.check_id for check in checks],
        )

    # Check for warnings/failures
    if any(check.status == CheckOutcomeStatus.WARNING for check in checks):
        warning_details = [
            check.detail for check in checks
            if check.status == CheckOutcomeStatus.WARNING and check.detail
        ]
        detail = "; ".join(warning_details) if warning_details else None
        return SectionSummaryEnvelope(
            section_id="retraction",
            status=CheckOutcomeStatus.WARNING,
            finding_code=SectionFindingCode.RETRACTION_FAILED,
            summary="Retraction Watch lookup failed or incomplete.",
            detail=detail,
            contributing_checks=[check.check_id for check in checks],
        )

    return SectionSummaryEnvelope(
        section_id="retraction",
        status=worst,
        finding_code=SectionFindingCode.RETRACTION_CLEAR,
        summary="No Retraction Watch matches detected.",
        detail=None,
        contributing_checks=[check.check_id for check in checks],
    )


def _pubpeer_section_summary(
    checks: List[CheckResultEnvelope], worst: CheckOutcomeStatus
) -> SectionSummaryEnvelope:
    pubpeer = checks[0] if checks else None

    if pubpeer and pubpeer.status == CheckOutcomeStatus.CONCERN:
        return SectionSummaryEnvelope(
            section_id="pubpeer",
            status=CheckOutcomeStatus.CONCERN,
            finding_code=SectionFindingCode.PUBPEER_COMMENTS,
            summary="PubPeer comments detected.",
            detail=pubpeer.detail,
            contributing_checks=[check.check_id for check in checks],
        )

    if pubpeer and pubpeer.status == CheckOutcomeStatus.WARNING:
        return SectionSummaryEnvelope(
            section_id="pubpeer",
            status=CheckOutcomeStatus.WARNING,
            finding_code=SectionFindingCode.PUBPEER_FAILED,
            summary="PubPeer analysis failed or was incomplete.",
            detail=pubpeer.detail,
            contributing_checks=[check.check_id for check in checks],
        )

    return SectionSummaryEnvelope(
        section_id="pubpeer",
        status=worst,
        finding_code=SectionFindingCode.PUBPEER_CLEAR,
        summary="No PubPeer concerns detected.",
        detail=None,
        contributing_checks=[check.check_id for check in checks],
    )


# --- Public helpers --------------------------------------------------------------


def build_check_envelopes(raw_results: Mapping[str, Any]) -> Dict[str, CheckResultEnvelope]:
    steps = raw_results.get("steps", {}) if isinstance(raw_results, Mapping) else {}
    envelopes: Dict[str, CheckResultEnvelope] = {}

    for check_id, normalizer in CHECK_NORMALIZERS.items():
        payload = raw_results.get(check_id) if isinstance(raw_results, Mapping) else None
        step_info = steps.get(check_id, {}) if isinstance(steps, Mapping) else {}
        envelopes[check_id] = normalizer(payload, step_info)

    return envelopes


def build_section_envelopes(checks: Dict[str, CheckResultEnvelope]) -> Dict[str, SectionSummaryEnvelope]:
    sections: Dict[str, SectionSummaryEnvelope] = {}
    for section_id, config in SECTION_DEFINITIONS.items():
        section_checks = [checks[check_id] for check_id in config["checks"] if check_id in checks]
        sections[section_id] = _build_section_summary(section_id, section_checks)
    return sections


def normalize_job_results(raw_results: Mapping[str, Any]) -> Dict[str, Any]:
    from core.results.populate_inspect_sr import populate_inspect_sr_from_checks

    checks = build_check_envelopes(raw_results)
    sections = build_section_envelopes(checks)

    # Build normalized results
    normalized = {
        "checks": {key: envelope.model_dump() for key, envelope in checks.items()},
        "sections": {key: envelope.model_dump() for key, envelope in sections.items()},
        "meta": {
            "steps": raw_results.get("steps", {}) if isinstance(raw_results, Mapping) else {},
        },
    }

    # Auto-populate INSPECT-SR data from check results
    normalized["inspect_sr"] = populate_inspect_sr_from_checks(normalized)

    return normalized
