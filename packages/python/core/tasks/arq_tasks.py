# Helpers and fan-out infra
from arq.connections import ArqRedis

import asyncio
import logging
import uuid
from typing import Any, Awaitable, Dict, List, Optional, Set, Tuple, cast

import logfire
from logfire.propagate import attach_context
from sqlalchemy.ext.asyncio import AsyncSession

from core.checks import (
    grobid_metadata_extraction,
    prospective_registration,
    pubpeer_signal_analysis,
    registry_crosscheck,
    retraction_detection,
    eoc_correction_detection,
    author_retraction_history,
    timeline_consistency,
    trial_llm_extraction,
)
from core.services.llm_service import cleanup_job_files
from core.db.crud import job as crud_job
from core.db.models.job import JobStatusEnum
from core.db.session import AsyncSessionFactory
from core.schemas.prospective_registration_results import (
    ProspectiveRegistrationAnalysisOutput,
)
from core.schemas.registry_outputs import Check2RegistryLookupOutput
from core.results.normalize_checks import normalize_job_results
from core.config.check_registry import CheckConfig, get_registry

# No runtime import of worker settings types to avoid circular deps and typing issues

logger = logging.getLogger(__name__)


async def _merge_results_top(
    db: AsyncSession, job_id: uuid.UUID, patch: Dict[str, Any]
) -> None:
    """Atomically merge top-level keys of results JSON (no clobbering)."""
    if not isinstance(patch, dict) or not patch:
        return
    await crud_job.upsert_job_results_merge(db=db, job_id=job_id, patch=patch)
    await db.commit()


async def _update_step_status(
    db: AsyncSession,
    job_id: uuid.UUID,
    step: str,
    status: str,
    error: Optional[str] = None,
) -> None:
    entry: Dict[str, Any] = {"status": status}
    if error is not None:
        entry["error"] = error
    await crud_job.upsert_job_results_step(db=db, job_id=job_id, step=step, entry=entry)
    await db.commit()


async def _write_step_final(
    db: AsyncSession,
    job_id: uuid.UUID,
    step: str,
    payload_patch: Dict[str, Any],
    final_status: str,
    error: Optional[str] = None,
) -> None:
    """Atomically merge payload and set final step status (no timestamps)."""
    logger.info(f"_write_step_final: job_id={job_id}, step={step}, payload_patch keys={list(payload_patch.keys()) if payload_patch else []}, final_status={final_status}")
    if payload_patch:
        try:
            result = await crud_job.upsert_job_results_merge(
                db=db, job_id=job_id, patch=payload_patch
            )
            logger.info(f"_write_step_final: upsert_job_results_merge succeeded for job {job_id}, step {step}, result={result is not None}")
        except Exception as e:
            logger.error(f"_write_step_final: upsert_job_results_merge FAILED for job {job_id}, step {step}: {e}", exc_info=True)
            raise
    else:
        logger.warning(f"_write_step_final: No payload_patch to write for job {job_id}, step {step}")
    entry: Dict[str, Any] = {"status": final_status}
    if error is not None:
        entry["error"] = error
    await crud_job.upsert_job_results_step(db=db, job_id=job_id, step=step, entry=entry)
    try:
        await db.commit()
        logger.info(f"_write_step_final: db.commit() succeeded for job {job_id}, step {step}")
    except Exception as e:
        logger.error(f"_write_step_final: db.commit() FAILED for job {job_id}, step {step}: {e}", exc_info=True)
        raise


# Fan-out sub-task wrappers
async def task_trial_llm_extraction(
    ctx: Dict[str, Any], job_id: uuid.UUID, job_identifier: str, pdf_file_path: str
) -> str:
    async with AsyncSessionFactory() as db:
        step = "trial_llm_extraction"
        redis = cast(Any, ctx.get("redis"))
        try:
            await _update_step_status(db, job_id, step, "RUNNING")
            payload = await trial_llm_extraction.execute_llm_extraction_check(
                job_id=job_id,
                job_identifier=job_identifier,
                pdf_file_path=pdf_file_path,
                db=db,
                redis_client=redis,
            )
            logger.info(f"[DEBUG] task_trial_llm_extraction for job {job_id} received payload: {payload}")
            await _write_step_final(
                db,
                job_id,
                step,
                payload or {},
                "COMPLETED",
            )
            logger.info(f"[DEBUG] task_trial_llm_extraction for job {job_id} _write_step_final completed")
            return "ok"
        except Exception as e:
            logger.error(
                f"task_trial_llm_extraction failed for job {job_id}: {e}", exc_info=True
            )
            await _write_step_final(db, job_id, step, {}, "FAILED", error=str(e))
            return "error"


async def task_timeline_consistency(
    ctx: Dict[str, Any], job_id: uuid.UUID, job_identifier: str, pdf_file_path: str
) -> str:
    async with AsyncSessionFactory() as db:
        step = "timeline_consistency"
        redis = cast(Any, ctx.get("redis"))
        try:
            await _update_step_status(db, job_id, step, "RUNNING")
            payload = await timeline_consistency.execute_study_timeline_dates_check(
                job_id=job_id,
                job_identifier=job_identifier,
                pdf_file_path=pdf_file_path,
                db=db,
                redis_client=redis,
            )
            await _write_step_final(
                db,
                job_id,
                step,
                payload or {},
                "COMPLETED",
            )
            return "ok"
        except Exception as e:
            logger.error(
                f"task_timeline_consistency failed for job {job_id}: {e}", exc_info=True
            )
            await _write_step_final(db, job_id, step, {}, "FAILED", error=str(e))
            return "error"


async def task_grobid_metadata(
    ctx: Dict[str, Any], job_id: uuid.UUID, pdf_file_path: str
) -> str:
    async with AsyncSessionFactory() as db:
        step = "grobid_metadata_processing"
        try:
            await _update_step_status(db, job_id, step, "RUNNING")
            payload = await grobid_metadata_extraction.execute_grobid_extraction_check(
                job_id=job_id, pdf_file_path=pdf_file_path
            )
            await _write_step_final(
                db,
                job_id,
                step,
                payload or {},
                "COMPLETED",
            )
            return "ok"
        except Exception as e:
            logger.error(
                f"task_grobid_metadata failed for job {job_id}: {e}", exc_info=True
            )
            await _write_step_final(db, job_id, step, {}, "FAILED", error=str(e))
            return "error"


async def _run_task_logic(
    job_id: uuid.UUID,
    job_identifier: str,
    pdf_file_path: str,
    db: AsyncSession,
    redis: ArqRedis,
) -> None:
    import time
    processing_start_time = time.time()

    logfire.info(
        "Job processing started", job_id=str(job_id), identifier=job_identifier
    )
    await crud_job.update_job_status(db, job_id, JobStatusEnum.RUNNING)
    await db.commit()

    # This will hold all results from checks to be saved once at the end (or after a group of checks)
    aggregated_results_payload = {}
    current_job_status = JobStatusEnum.RUNNING  # Track overall status
    error_messages_for_job: List[str] = []
    enabled_check_ids: Set[str] = set()

    with logfire.span("arq_task_logic:run_evidence_synthesis", job_id=str(job_id)):
        try:
            registry = get_registry()
            enabled_checks = registry.get_enabled_checks()
            enabled_check_ids = set(enabled_checks.keys())

            checks_by_phase: Dict[int, List[CheckConfig]] = {}
            for check_cfg in enabled_checks.values():
                checks_by_phase.setdefault(check_cfg.phase, []).append(check_cfg)
            for phase_checks in checks_by_phase.values():
                phase_checks.sort(key=lambda cfg: cfg.id)

            def _arq_queue_name(queue_key: str) -> str:
                return "arq:queue" if queue_key == "default" else f"arq:queue:{queue_key}"

            async def _refresh_results_payload() -> Dict[str, Any]:
                snapshot = await crud_job.get_job(db, job_id)
                if snapshot and isinstance(snapshot.results, dict):
                    return snapshot.results
                return aggregated_results_payload

            async def _enqueue_arq_job_for_phase(
                check_cfg: CheckConfig,
            ) -> Optional[Any]:
                if str(check_cfg.executor).lower() != "arq":
                    return None

                queue_name = _arq_queue_name(check_cfg.queue)
                enqueue_kwargs: Dict[str, Any] = {
                    "_job_id": f"{job_id}:{check_cfg.id}",
                    "_queue_name": queue_name,
                }

                if check_cfg.id == "trial_llm_extraction":
                    args: Tuple[Any, ...] = (job_id, job_identifier, pdf_file_path)
                elif check_cfg.id == "timeline_consistency":
                    args = (job_id, job_identifier, pdf_file_path)
                elif check_cfg.id == "grobid_metadata":
                    args = (job_id, pdf_file_path)
                else:
                    logger.warning(
                        "No ARQ dispatcher configured for check '%s'", check_cfg.id
                    )
                    return None

                return await redis.enqueue_job(
                    check_cfg.task_name,
                    *args,
                    **enqueue_kwargs,
                )

            async def _await_phase_jobs(
                pending_jobs: List[Tuple[CheckConfig, Any]],
            ) -> None:
                if not pending_jobs:
                    return
                results = await asyncio.gather(
                    *[
                        job.result(timeout=check_cfg.timeout or 60)
                        for check_cfg, job in pending_jobs
                    ],
                    return_exceptions=True,
                )
                for (check_cfg, _), result in zip(pending_jobs, results):
                    if isinstance(result, Exception):
                        logger.error(
                            "Check %s failed during ARQ execution: %s",
                            check_cfg.id,
                            result,
                            exc_info=not isinstance(result, asyncio.CancelledError),
                        )
                        error_messages_for_job.append(
                            f"{check_cfg.id} Error: {str(result)[:200]}"
                        )
                    else:
                        logfire.info(
                            "Phase job completed",
                            job_id=str(job_id),
                            check_id=check_cfg.id,
                            queue=check_cfg.queue,
                            arq_result=str(result),
                        )

            # Phase 1: enqueue and await ARQ checks
            phase_one_checks = checks_by_phase.get(1, [])
            if phase_one_checks:
                logfire.info(
                    "Phase 1 dispatch",
                    job_id=str(job_id),
                    checks=[cfg.id for cfg in phase_one_checks],
                )
                phase_jobs: List[Tuple[CheckConfig, Any]] = []
                for check_cfg in phase_one_checks:
                    job_handle = await _enqueue_arq_job_for_phase(check_cfg)
                    if job_handle is not None:
                        phase_jobs.append((check_cfg, job_handle))
                await _await_phase_jobs(phase_jobs)

            aggregated_results_payload = await _refresh_results_payload()

            # Extract per-check payloads directly from DB results
            if "trial_llm_extraction" in enabled_check_ids:
                check_1_payload_or_exc = aggregated_results_payload.get(
                    "trial_llm_extraction"
                )
                # Process result of Check 1
                if isinstance(check_1_payload_or_exc, Exception):
                    exc = check_1_payload_or_exc
                    logger.error(
                        f"Check 1 (Trial ID) failed for job {job_id} with exception: {exc}",
                        exc_info=exc,
                    )
                    error_messages_for_job.append(f"Check 1 Error: {str(exc)}")
                    if "trial_llm_extraction" not in aggregated_results_payload:
                        aggregated_results_payload["trial_llm_extraction"] = {
                            "status": "FAILED_CRITICAL",
                            "error": str(exc),
                        }
                    current_job_status = JobStatusEnum.FAILED
                elif check_1_payload_or_exc:
                    check_1_internal_status = (check_1_payload_or_exc.get("status") or "").upper()
                    check_1_internal_error = check_1_payload_or_exc.get("error")
                    if check_1_internal_error and str(check_1_internal_error) not in error_messages_for_job:
                        error_messages_for_job.append(f"Check 1 Info/Error: {check_1_internal_error}")

                    if "FAILED" in check_1_internal_status:
                        current_job_status = JobStatusEnum.FAILED
                        logger.error(
                            f"Job {job_id}: Check 1 reported failure status: {check_1_internal_status}"
                        )
                    elif "NOT_FOUND" in check_1_internal_status:
                        logger.warning(
                            f"Job {job_id}: Check 1 reported NOT_FOUND status: {check_1_internal_status}"
                        )
                    else:
                        logger.info(
                            f"Job {job_id}: Check 1 completed. Status: {check_1_internal_status}"
                        )
                else:
                    logger.warning(
                        f"Check 1 (Trial ID) for job {job_id} returned no payload and no exception. This is unexpected."
                    )
                    aggregated_results_payload["trial_llm_extraction"] = {
                        "status": "UNKNOWN_FAILURE",
                        "error": "Check 1 returned no data.",
                    }
                    error_messages_for_job.append("Check 1 Error: Returned no data.")
                    current_job_status = JobStatusEnum.FAILED

            # Process result of Check 3 (Dates)
            if "timeline_consistency" in enabled_check_ids:
                check_3_dates_payload_or_exc = aggregated_results_payload.get(
                    "timeline_consistency"
                )
                if isinstance(check_3_dates_payload_or_exc, Exception):
                    exc = check_3_dates_payload_or_exc
                    logger.error(
                        f"Check 3 (Dates) failed for job {job_id} with exception: {exc}",
                        exc_info=exc,
                    )
                    error_messages_for_job.append(f"Check 3 (Dates) Error: {str(exc)}")
                    if "timeline_consistency" not in aggregated_results_payload:
                        aggregated_results_payload["timeline_consistency"] = {
                            "status": "FAILED_CRITICAL",
                            "error": str(exc),
                        }
                    current_job_status = JobStatusEnum.FAILED
                elif check_3_dates_payload_or_exc:
                    check_3_dates_internal_status = check_3_dates_payload_or_exc.get(
                        "status"
                    )
                    # TODO: Check 3 dates might have partial success, usually won't set job to FAILED unless it's a critical error from the check itself.
                    if "FAIL" in str(check_3_dates_internal_status):
                        current_job_status = (
                            JobStatusEnum.FAILED
                        )  # Only if the check itself flags a critical failure
                        logger.error(
                            f"Job {job_id}: Check 3 (Dates) reported critical failure. Status: {check_3_dates_internal_status}"
                        )
                    else:
                        logger.info(
                            f"Job {job_id}: Check 3 (Dates) completed. Status: {check_3_dates_internal_status}"
                        )
                else:
                    logger.warning(
                        f"Check 3 (Dates) for job {job_id} returned no payload and no exception. This is unexpected."
                    )
                    aggregated_results_payload["timeline_consistency"] = {
                        "status": "UNKNOWN_FAILURE",
                        "error": "Check 3 (Dates) returned no data.",
                    }
                    error_messages_for_job.append(
                        "Check 3 (Dates) Error: Returned no data."
                    )
                    current_job_status = JobStatusEnum.FAILED

            if "grobid_metadata" in enabled_check_ids:
                # Process result of GROBID extraction - handles both Check 4 and Check 5
                c4 = aggregated_results_payload.get("grobid_primary_metadata") or {}
                c5 = aggregated_results_payload.get("grobid_reference_metadata") or {}
                check_4_doi_internal_status = c4.get("status")
                check_5_ref_internal_status = c5.get("status")
                # Only fail on actual failures, not NOT_FOUND statuses TODO VERIFY THIS
                # Allow graceful degradation - only fail if both header AND references completely failed TODO VERIFY THIS
                check_4_failed = check_4_doi_internal_status == "FAILED"
                check_5_hard_failed = (
                    check_5_ref_internal_status == "FAILED"
                )  # Don't count graceful degradation as hard failure

                if check_4_failed and check_5_hard_failed:
                    current_job_status = JobStatusEnum.FAILED
                    logger.error(
                        f"Job {job_id}: GROBID extraction reported critical failure. Check 4 status: {check_4_doi_internal_status}, Check 5 status: {check_5_ref_internal_status}"
                    )
                elif (
                    check_5_ref_internal_status
                    == "FAILED_TIMEOUT_GRACEFUL_DEGRADATION"
                ):
                    # This is acceptable - continue with header-only processing
                    logger.warning(
                        f"Job {job_id}: GROBID references timed out but header succeeded. Continuing with graceful degradation. Check 4 status: {check_4_doi_internal_status}, Check 5 status: {check_5_ref_internal_status}"
                    )
                else:
                    logger.info(
                        f"Job {job_id}: GROBID extraction completed. Check 4 status: {check_4_doi_internal_status}, Check 5 status: {check_5_ref_internal_status}"
                    )

            # PHASE 2: Execute independent dependency chains in parallel
            logfire.info(
                f"Job {job_id}: Starting Phase 2 - Independent dependency chains"
            )

            chain_results = await asyncio.gather(
                _execute_registry_chain(
                    job_id,
                    aggregated_results_payload,
                    error_messages_for_job,
                    enabled_check_ids,
                ),
                _execute_post_publication_chain(
                    job_id,
                    aggregated_results_payload,
                    error_messages_for_job,
                    enabled_check_ids,
                ),
                return_exceptions=True,
            )

            # Process chain results and update aggregated payload
            chain_names = [
                "registry_chain",
                "post_publication_chain",
            ]
            for i, chain_result in enumerate(chain_results):
                if isinstance(chain_result, Exception):
                    logger.error(
                        f"Job {job_id}: {chain_names[i]} failed with exception: {chain_result}",
                        exc_info=chain_result,
                    )
                    error_messages_for_job.append(
                        f"{chain_names[i]} Error: {str(chain_result)}"
                    )
                    current_job_status = JobStatusEnum.FAILED
                elif isinstance(chain_result, dict):
                    # Merge chain results into aggregated payload
                    aggregated_results_payload.update(chain_result)
                    logger.info(
                        f"Job {job_id}: {chain_names[i]} completed successfully"
                    )

            # Determine final status if not already set to FAILED by a check
            if current_job_status == JobStatusEnum.RUNNING:
                current_job_status = JobStatusEnum.COMPLETED

        except trial_llm_extraction.LLMExtractionCheckError as c1_exc:
            logger.error(
                f"Caught specific Check 1 error in outer block for job {job_id}: {c1_exc}",
                exc_info=True,
            )
            current_job_status = JobStatusEnum.FAILED
            error_messages_for_job.append(f"Check 1 Orchestration Error: {str(c1_exc)}")
            if "trial_llm_extraction" not in aggregated_results_payload:
                aggregated_results_payload["trial_llm_extraction"] = {
                    "status": "FAILED_CRITICAL",
                    "error": str(c1_exc),
                }

        except timeline_consistency.StudyTimelineDatesCheckError as c3_dates_exc:
            logger.error(
                f"Caught specific Check 3 (Dates) error in outer block for job {job_id}: {c3_dates_exc}",
                exc_info=True,
            )
            current_job_status = JobStatusEnum.FAILED
            error_messages_for_job.append(
                f"Check 3 (Dates) Orchestration Error: {str(c3_dates_exc)}"
            )
            if "timeline_consistency" not in aggregated_results_payload:
                aggregated_results_payload["timeline_consistency"] = {
                    "status": "FAILED_CRITICAL",
                    "error": str(c3_dates_exc),
                }

        except grobid_metadata_extraction.GrobidExtractionCheckError as grobid_exc:
            logger.error(
                f"Caught specific GROBID extraction error in outer block for job {job_id}: {grobid_exc}",
                exc_info=True,
            )
            current_job_status = JobStatusEnum.FAILED
            error_messages_for_job.append(
                f"GROBID Extraction Orchestration Error: {str(grobid_exc)}"
            )
            # Only set if not already set by inner exception handling
            if "grobid_primary_metadata" not in aggregated_results_payload:
                aggregated_results_payload["grobid_primary_metadata"] = {
                    "status": "FAILED_CRITICAL",
                    "error": str(grobid_exc),
                }
            if "grobid_reference_metadata" not in aggregated_results_payload:
                aggregated_results_payload["grobid_reference_metadata"] = {
                    "status": "FAILED_CRITICAL",
                    "error": str(grobid_exc),
                }

        except Exception as task_logic_exc:
            # This catches any unhandled exceptions in task orchestration
            logger.error(
                f"Unhandled exception in ARQ task logic orchestration for job {job_id}: {task_logic_exc}",
                exc_info=True,
            )
            current_job_status = JobStatusEnum.FAILED
            error_messages_for_job.append(
                f"Task Orchestration Error: {str(task_logic_exc)}"
            )

        finally:
            final_error_message = (
                "; ".join(error_messages_for_job)
                if current_job_status == JobStatusEnum.FAILED and error_messages_for_job
                else None
            )
            logger.info(
                f"Normalizing results for job {job_id} with final status: {current_job_status.name}."
            )

            job_snapshot = await crud_job.get_job(db, job_id)
            raw_results = {}
            if job_snapshot and isinstance(job_snapshot.results, dict):
                raw_results.update(job_snapshot.results)
            if aggregated_results_payload:
                raw_results.update(aggregated_results_payload)
            normalized_results = normalize_job_results(raw_results)

            processing_end_time = time.time()
            processing_duration = processing_end_time - processing_start_time

            await crud_job.update_job_results(db, job_id, normalized_results)
            await crud_job.update_job_status(
                db=db,
                job_id=job_id,
                status=current_job_status,
                error_message=final_error_message,
                processing_time_seconds=round(processing_duration, 2),
            )
            await db.commit()
            logfire.info(
                "Job processing completed",
                job_id=str(job_id),
                status=current_job_status.name,
                processing_time_seconds=round(processing_duration, 2),
                has_errors=bool(error_messages_for_job),
            )

            # Clean up LLM files uploaded to Google for this job
            try:
                await cleanup_job_files(str(job_id), redis)
                logger.info(f"✅ LLM file cleanup completed for job {job_id}")
            except Exception as cleanup_error:
                logger.error(
                    f"Failed to clean up LLM files for job {job_id}: {cleanup_error}",
                    exc_info=True
                )


async def run_evidence_synthesis_arq_task(
    ctx: Dict[str, Any],
    job_id: uuid.UUID,
    job_identifier: str,
    pdf_file_path: str,
    otel_context: Optional[Dict[str, Any]] = None,
) -> None:
    """ARQ task for evidence synthesis, enqueued by the API."""
    effective_otel_context = otel_context or {}
    with attach_context(effective_otel_context):
        # Reduced verbosity for development - no need to log every task receipt
        async with AsyncSessionFactory() as db:
            try:
                redis = cast(ArqRedis, ctx["redis"])
                await _run_task_logic(
                    job_id,
                    job_identifier,
                    pdf_file_path,
                    db,
                    redis,
                )
            except Exception as e:
                # This outer catch is a final safeguard. _run_task_logic should ideally handle its errors
                # and set the job status appropriately. If an error escapes _run_task_logic entirely,
                # it implies a more fundamental issue in the task orchestration itself.
                logger.error(
                    f"Outer ARQ task execution wrapped an unhandled exception from _run_task_logic for job {job_id}: {e}",
                    exc_info=True,
                )
                try:
                    await db.rollback()
                    current_job = await crud_job.get_job(db, job_id)
                    if current_job and current_job.status not in [
                        JobStatusEnum.COMPLETED,
                        JobStatusEnum.FAILED,
                    ]:
                        await crud_job.update_job_status(
                            db,
                            job_id,
                            JobStatusEnum.FAILED,
                            error_message=f"Critical ARQ task failure: {str(e)[:200]}",
                        )
                        await db.commit()
                    elif not current_job:
                        logger.error(
                            f"Job {job_id} not found when attempting to mark as FAILED post-outer-exception."
                        )
                except Exception as db_error_after_main_exc:
                    logger.error(
                        f"Failed to update job {job_id} to FAILED after outer ARQ exception: {db_error_after_main_exc}",
                        exc_info=True,
                    )
                    await db.rollback()
            finally:
                # Keep PDF files for frontend serving - do not delete
                # if os.path.exists(pdf_file_path):
                #     try:
                #         os.remove(pdf_file_path)
                #         logger.info(f"Deleted temporary PDF: {pdf_file_path} for job {job_id}")
                #     except OSError as e_remove:
                #         logger.error(f"Error deleting temporary PDF {pdf_file_path} for job {job_id}: {e_remove}", exc_info=True)
                logger.info(
                    f"Keeping PDF file for serving: {pdf_file_path} for job {job_id}"
                )


# Helper Functions for Parallel Dependency Chains


async def _execute_registry_chain(
    job_id: uuid.UUID,
    aggregated_results_payload: Dict[str, Any],
    error_messages_for_job: List[str],
    enabled_check_ids: Set[str],
) -> Dict[str, Any]:
    """
    Execute Chain A: Check 1 → Check 2 → Check 6 (+ Check 3)
    Registry lookup and prospective registration analysis chain.
    """
    chain_results = {}
    registry_active = "registry_crosscheck" in enabled_check_ids
    prospective_active = "prospective_registration" in enabled_check_ids

    with logfire.span("registry_chain", job_id=str(job_id)):
        if registry_active:
            # Execute Check 2 (Registry Lookup)
            # Depends on successful Check 1 output
            check_1_results_data = aggregated_results_payload.get(
                "trial_llm_extraction", {}
            )
            trial_id_for_check2 = check_1_results_data.get("trial_id")
            registry_type_for_check2 = check_1_results_data.get("registry_type")
            check_1_status_for_check2 = check_1_results_data.get("status")

            if (
                trial_id_for_check2
                and registry_type_for_check2
                and check_1_status_for_check2 == "COMPLETED_SUCCESS"
            ):
                logfire.info(
                    f"Job {job_id}: Prerequisites met. Proceeding with Check 2 (Registry Lookup) for Trial ID: {trial_id_for_check2}."
                )
                try:
                    check_2_result_obj: Check2RegistryLookupOutput = (
                        await registry_crosscheck.execute_registry_lookup_check(
                            job_id=job_id,
                            trial_id=trial_id_for_check2,
                            registry_type=registry_type_for_check2,
                        )
                    )

                    if check_2_result_obj:
                        # Convert the main Check2RegistryLookupOutput to a dict
                        check_2_dict = check_2_result_obj.model_dump()
                        # If lookup_results exists, re-serialize it with exclude_defaults=True
                        if check_2_result_obj.lookup_results:
                            check_2_dict["lookup_results"] = (
                                check_2_result_obj.lookup_results.model_dump(
                                    exclude_defaults=True
                                )
                            )

                        chain_results[check_2_result_obj.check_name] = check_2_dict

                        if check_2_result_obj.error_message:
                            logger.error(
                                f"Job {job_id}: Check 2 (Registry Lookup) completed with an error: {check_2_result_obj.error_message}"
                            )
                            error_messages_for_job.append(
                                f"Check 2 Error: {check_2_result_obj.error_message}"
                            )
                        elif (
                            check_2_result_obj.lookup_results
                            and check_2_result_obj.lookup_results.lookup_successful
                        ):
                            logger.info(
                                f"Job {job_id}: Check 2 (Registry Lookup) completed successfully for {trial_id_for_check2}."
                            )
                        else:
                            lookup_error = (
                                check_2_result_obj.lookup_results.error_message
                                if (
                                    check_2_result_obj.lookup_results
                                    and check_2_result_obj.lookup_results.error_message
                                )
                                else "Lookup was not successful for unknown reasons."
                            )
                            logger.warning(
                                f"Job {job_id}: Check 2 (Registry Lookup) for {trial_id_for_check2} did not succeed: {lookup_error}"
                            )
                            error_messages_for_job.append(
                                f"Check 2 Warning: {lookup_error}"
                            )
                    else:
                        logger.error(
                            f"Job {job_id}: Check 2 (Registry Lookup) returned no result object. This is unexpected."
                        )
                        chain_results["registry_crosscheck"] = {
                            "status": "FAILED_UNEXPECTED",
                            "error": "Check 2 returned no result object.",
                        }
                        error_messages_for_job.append(
                            "Check 2 Error: Returned no result object."
                        )

                except registry_crosscheck.RegistryLookupCheckError as c2_exc:
                    logger.error(
                        f"Job {job_id}: Check 2 (Registry Lookup) failed with RegistryLookupCheckError: {c2_exc}",
                        exc_info=True,
                    )
                    chain_results["registry_crosscheck"] = {
                        "status": "FAILED_CRITICAL",
                        "error": str(c2_exc),
                    }
                    error_messages_for_job.append(f"Check 2 Error: {str(c2_exc)}")
                except Exception as e_check2:
                    logger.error(
                        f"Job {job_id}: An unexpected exception occurred during Check 2 (Registry Lookup): {e_check2}",
                        exc_info=True,
                    )
                    chain_results["registry_crosscheck"] = {
                        "status": "FAILED_UNEXPECTED",
                        "error": str(e_check2),
                    }
                    error_messages_for_job.append(
                        f"Check 2 Error: Unexpected - {str(e_check2)}"
                    )
            else:
                skip_reason = "Prerequisites from Check 1 not met or Check 1 failed/yielded no valid Trial ID/Registry Type."
                if not trial_id_for_check2:
                    skip_reason = "Check 1 did not yield a Trial ID."
                elif not registry_type_for_check2:
                    skip_reason = "Check 1 did not yield a Registry Type."
                elif check_1_status_for_check2 != "COMPLETED_SUCCESS":
                    skip_reason = f"Check 1 status was {check_1_status_for_check2}."

                logger.info(
                    f"Job {job_id}: Skipping Check 2 (Registry Lookup). Reason: {skip_reason}"
                )
                chain_results["registry_crosscheck"] = {
                    "trial_id": trial_id_for_check2 or "N/A",
                    "registry_type": registry_type_for_check2 or "N/A",
                    "status": "SKIPPED",
                    "message": skip_reason,
                    "lookup_results": None,
                }
        else:
            logger.info(f"Job {job_id}: Check 2 (Registry Lookup) disabled for profile.")

        # Execute Check 6 (Prospective Registration Analysis)
        # Depends on outputs from Check 2 (for registry date and type) and Check 3 (for LLM recruitment start date)
        if prospective_active:
            logfire.info(
                f"Job {job_id}: Preparing for Check 6 (Prospective Registration Analysis)."
            )
            check_3_timeline_payload = aggregated_results_payload.get(
                "timeline_consistency"
            )
            check_2_lookup_payload = chain_results.get("registry_crosscheck")

            try:
                check_6_output: ProspectiveRegistrationAnalysisOutput = (
                    await prospective_registration.execute_prospective_registration_check(
                        job_id=job_id,
                        llm_timeline_dates_payload=check_3_timeline_payload,
                        registry_lookup_payload=check_2_lookup_payload,
                    )
                )
                if check_6_output:
                    chain_results[check_6_output.check_name] = (
                        check_6_output.model_dump()
                    )
                    logger.info(
                        f"Job {job_id}: Check 6 (Prospective Registration) completed. Status: {check_6_output.status.value}, Message: {check_6_output.message}"
                    )
                else:
                    logger.error(
                        f"Job {job_id}: Check 6 returned no output object, which is unexpected."
                    )
                    chain_results["prospective_registration_analysis"] = {
                        "status": "ERROR_UNEXPECTED_NULL_OUTPUT",
                        "message": "Check 6 execution returned no output object.",
                    }
            except prospective_registration.ProspectiveRegistrationCheckError as c6_exc:
                logger.error(
                    f"Job {job_id}: Check 6 (Prospective Registration) failed with a critical error: {c6_exc}",
                    exc_info=True,
                )
                error_messages_for_job.append(f"Check 6 Error: {str(c6_exc)}")
                chain_results["prospective_registration_analysis"] = {
                    "status": "ERROR_CRITICAL_CHECK_FAILURE",
                    "message": f"Check 6 failed: {str(c6_exc)}",
                }
            except Exception as e_check6:
                logger.error(
                    f"Job {job_id}: An unexpected exception occurred during Check 6 (Prospective Registration): {e_check6}",
                    exc_info=True,
                )
                error_messages_for_job.append(
                    f"Check 6 Error: Unexpected - {str(e_check6)}"
                )
                chain_results["prospective_registration_analysis"] = {
                    "status": "ERROR_UNEXPECTED",
                    "message": f"Check 6 encountered an unexpected error: {str(e_check6)}",
                }
        else:
            logger.info(
                f"Job {job_id}: Check 6 (Prospective Registration) disabled for profile."
            )

    return chain_results


async def _execute_post_publication_chain(
    job_id: uuid.UUID,
    aggregated_results_payload: Dict[str, Any],
    error_messages_for_job: List[str],
    enabled_check_ids: Set[str],
) -> Dict[str, Any]:
    """
    Execute Chain B: Check 4 + Check 5 → Check 7 + Check 8 + Check 9 + Check 13
    Post-publication analysis chain: Retraction detection, EOC/Correction detection,
    Author retraction history, and PubPeer comments
    """
    chain_results = {}
    retraction_detection_enabled = "retraction_detection" in enabled_check_ids
    eoc_correction_enabled = "eoc_correction_detection" in enabled_check_ids
    author_history_enabled = "author_retraction_history" in enabled_check_ids
    pubpeer_enabled = "pubpeer_signal_analysis" in enabled_check_ids

    if not any([retraction_detection_enabled, eoc_correction_enabled, author_history_enabled, pubpeer_enabled]):
        logger.info(
            f"Job {job_id}: Post-publication checks disabled for active profile."
        )
        return chain_results

    with logfire.span("post_publication_chain", job_id=str(job_id)):
        # Get payloads from GROBID extraction (Check 4 & 5)
        main_doi_payload = aggregated_results_payload.get("grobid_primary_metadata")
        ref_dois_payload = aggregated_results_payload.get("grobid_reference_metadata")

        check_tasks: List[Tuple[str, Awaitable[Any]]] = []
        logger.info(f"Starting post-publication analysis for job {job_id}")

        # INSPECT-SR 1.1: Retraction Detection (main + refs)
        if retraction_detection_enabled:
            check_tasks.append(
                (
                    "retraction_detection",
                    retraction_detection.execute_retraction_detection_check(
                        job_id,
                        main_doi_payload=main_doi_payload,
                        reference_dois_payload=ref_dois_payload,
                    ),
                )
            )

        # INSPECT-SR 1.2: EOC/Correction Detection (main only)
        if eoc_correction_enabled:
            check_tasks.append(
                (
                    "eoc_correction_detection",
                    eoc_correction_detection.execute_eoc_correction_detection_check(
                        job_id,
                        main_doi_payload=main_doi_payload,
                        reference_dois_payload=None,  # Not used for 1.2
                    ),
                )
            )

        # INSPECT-SR 1.3: Author Retraction History
        if author_history_enabled:
            check_tasks.append(
                (
                    "author_retraction_history",
                    author_retraction_history.execute_author_retraction_history_check(
                        job_id,
                        main_doi_payload=main_doi_payload,
                        reference_dois_payload=None,  # Not used for 1.3
                    ),
                )
            )

        # PubPeer Signal Analysis
        if pubpeer_enabled:
            check_tasks.append(
                (
                    "pubpeer_signal_analysis",
                    pubpeer_signal_analysis.execute_pubpeer_analysis_check(
                        job_id,
                        main_doi_payload=main_doi_payload,
                    ),
                )
            )

        if check_tasks:
            results = await asyncio.gather(
                *(future for _, future in check_tasks), return_exceptions=True
            )

            for (check_id, _), result in zip(check_tasks, results):
                if isinstance(result, Exception):
                    logger.error(
                        f"{check_id} failed for job {job_id}: {result}", exc_info=True
                    )
                    chain_results[check_id] = {
                        "status": "FAILED",
                        "error": str(result),
                    }
                    error_messages_for_job.append(
                        f"{check_id} Error: {str(result)[:200]}"
                    )
                    continue

                if result:
                    # For dict results, store directly; for Pydantic models, dump to dict
                    if isinstance(result, dict):
                        chain_results[check_id] = result
                    else:
                        output = cast(Any, result)
                        chain_results[check_id] = output.model_dump(exclude_none=True)
                    logger.info(f"{check_id} completed for job {job_id}")
                else:
                    logger.error(f"{check_id} returned None for job {job_id}")
                    chain_results[check_id] = {
                        "status": "FAILED",
                        "error": "Check returned no output.",
                    }

    return chain_results
