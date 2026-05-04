import uuid
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from sqlalchemy import select, update, case, text, bindparam
from sqlalchemy import types as satypes
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session, selectinload

from core.db.models.job import Job
from core.schemas.enums import JobSourceEnum, JobStatusEnum
from core.config import DEFAULT_TOTAL_CHECKS
from core.db.validation import (
    validate_job_identifier,
    validate_job_source,
    validate_job_status,
    validate_external_id,
    validate_file_path,
    validate_current_phase,
    validate_progress_values,
    validate_uuid,
    validate_results_data,
)

logger = logging.getLogger(__name__)


# Async CRUD Operations
async def create_job(
    db: AsyncSession,
    identifier: str,
    source: JobSourceEnum,
    reviewer_id: uuid.UUID,
    external_id: Optional[str] = None,
    file_path: Optional[str] = None,
) -> Job:
    """Create a new job with a given identifier, source, optional external_id, file_path, and PENDING status."""
    # Validate inputs
    validate_job_identifier(identifier)
    validate_job_source(source)
    validate_external_id(external_id)
    validate_file_path(file_path)
    validate_uuid(reviewer_id)

    db_job = Job(
        identifier=identifier,
        status=JobStatusEnum.PENDING,
        source=source,
        external_id=external_id,
        file_path=file_path,
        reviewer_id=reviewer_id,
    )
    db.add(db_job)
    await db.flush()
    return db_job


async def get_job(db: AsyncSession, job_id: uuid.UUID) -> Optional[Job]:
    """Retrieve a job by its ID."""
    validate_uuid(job_id)
    result = await db.execute(select(Job).where(Job.id == job_id))
    return result.scalar_one_or_none()


async def get_job_for_reviewer(
    db: AsyncSession, job_id: uuid.UUID, reviewer_id: uuid.UUID
) -> Optional[Job]:
    """Retrieve a job by its ID scoped to a reviewer."""
    validate_uuid(job_id)
    validate_uuid(reviewer_id)
    stmt = (
        select(Job)
        .where(Job.id == job_id, Job.reviewer_id == reviewer_id)
        .execution_options(populate_existing=True)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def update_job_status(
    db: AsyncSession,
    job_id: uuid.UUID,
    status: JobStatusEnum,
    error_message: Optional[str] = None,
    processing_time_seconds: Optional[float] = None,
) -> Optional[Job]:
    """Update the status and optionally the error message and processing time of a job."""
    validate_uuid(job_id)
    validate_job_status(status)

    # Direct UPDATE query to avoid N+1 pattern
    update_values = {"status": status, "updated_at": datetime.now(timezone.utc)}

    if error_message is not None:
        update_values["error_message"] = error_message
    elif status != JobStatusEnum.FAILED:
        update_values["error_message"] = None

    if processing_time_seconds is not None:
        update_values["processing_time_seconds"] = processing_time_seconds

    stmt = update(Job).where(Job.id == job_id).values(**update_values).returning(Job)

    result = await db.execute(stmt)
    await db.flush()
    return result.scalar_one_or_none()


async def update_job_results(
    db: AsyncSession,
    job_id: uuid.UUID,
    results: Dict[str, Any],
    status: Optional[JobStatusEnum] = None,
) -> Optional[Job]:
    """Update the results of a job and optionally its status."""
    validate_uuid(job_id)
    validate_results_data(results)
    if status is not None:
        validate_job_status(status)

    # Direct UPDATE query to avoid N+1 pattern
    update_values = {"results": results, "updated_at": datetime.now(timezone.utc)}

    if status:
        update_values["status"] = status
    if status == JobStatusEnum.COMPLETED:
        update_values["error_message"] = None

    stmt = update(Job).where(Job.id == job_id).values(**update_values).returning(Job)

    result = await db.execute(stmt)
    await db.flush()
    return result.scalar_one_or_none()


# Atomic JSONB upserts to prevent lost updates during parallel tasks
async def upsert_job_results_merge(
    db: AsyncSession, job_id: uuid.UUID, patch: Dict[str, Any]
) -> Optional[Job]:
    """
    Atomically merge top-level keys into results JSONB using jsonb concatenation.

    Equivalent to: results = coalesce(results,'{}'::jsonb) || :patch::jsonb
    """
    validate_uuid(job_id)
    validate_results_data(patch)

    stmt = text(
        """
            UPDATE jobs
            SET results = COALESCE(results, '{}'::jsonb) || :patch,
                updated_at = now()
            WHERE id = :job_id
            RETURNING *
            """
    ).bindparams(bindparam("patch", type_=JSONB()))
    result = await db.execute(stmt, {"job_id": str(job_id), "patch": patch})
    await db.flush()
    row = result.first()
    return row[0] if row else None


def _sanitize_step_key(step: str) -> str:
    """Allow only simple step keys for jsonb_set path injection safety."""
    # Keep alphanumerics, underscore, hyphen.
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-.")
    filtered = "".join(ch for ch in (step or "") if ch in allowed)
    if not filtered:
        raise ValueError("Invalid step key")
    return filtered


async def upsert_job_results_step(
    db: AsyncSession, job_id: uuid.UUID, step: str, entry: Dict[str, Any]
) -> Optional[Job]:
    """
    Atomically set results.steps[step] = entry (jsonb_set with create_missing = true).
    """
    validate_uuid(job_id)
    validate_results_data(entry)

    step_key = _sanitize_step_key(step)
    path_elems = ["steps", step_key]

    stmt = (
        text(
            """
            UPDATE jobs
            SET results = jsonb_set(
                COALESCE(results, '{}'::jsonb),
                :path,
                :entry,
                true
            ),
                updated_at = now()
            WHERE id = :job_id
            RETURNING *
            """
        )
        .bindparams(bindparam("path", type_=ARRAY(satypes.TEXT())))
        .bindparams(bindparam("entry", type_=JSONB()))
    )
    params = {"job_id": str(job_id), "path": path_elems, "entry": entry}
    result = await db.execute(stmt, params)
    await db.flush()
    row = result.first()
    return row[0] if row else None


async def update_job_progress(
    db: AsyncSession,
    job_id: uuid.UUID,
    checks_completed: int,
    total_checks: int = DEFAULT_TOTAL_CHECKS,
    current_phase: str = "processing",
) -> Optional[Job]:
    """Update job progress information for streaming."""
    validate_uuid(job_id)
    validate_progress_values(checks_completed, total_checks)
    validate_current_phase(current_phase)

    stmt = (
        update(Job)
        .where(Job.id == job_id)
        .values(
            checks_completed=checks_completed,
            total_checks=total_checks,
            current_phase=current_phase,
            updated_at=datetime.now(timezone.utc),
        )
        .returning(Job)
    )

    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_job_with_check_results(
    db: AsyncSession, job_id: uuid.UUID
) -> Optional[Job]:
    """Get job with all its check results."""
    stmt = select(Job).where(Job.id == job_id).options(selectinload(Job.check_results))
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def increment_job_checks_completed(
    db: AsyncSession, job_id: uuid.UUID
) -> Optional[Job]:
    """Increment the completed checks count for a job."""
    validate_uuid(job_id)

    # Use a single UPDATE with SQL increment to avoid N+1 pattern
    stmt = (
        update(Job)
        .where(Job.id == job_id)
        .values(
            checks_completed=Job.checks_completed + 1,
            current_phase=case(
                (Job.checks_completed + 1 >= Job.total_checks, "completed"),
                else_="processing",
            ),
            updated_at=datetime.now(timezone.utc),
        )
        .returning(Job)
    )

    result = await db.execute(stmt)
    await db.flush()
    return result.scalar_one_or_none()


# Synchronous CRUD Operations


def update_job_status_sync(
    db: Session,
    job_id: uuid.UUID,
    status: JobStatusEnum,
    error_message: Optional[str] = None,
) -> Optional[Job]:
    """(Sync) Updates the status and optionally error message of a job using a direct UPDATE statement."""
    values_to_update: Dict[str, Any] = {
        "status": status,
        "updated_at": datetime.now(timezone.utc),
    }
    if error_message is not None:
        values_to_update["error_message"] = error_message
    elif status != JobStatusEnum.FAILED:
        values_to_update["error_message"] = None

    stmt = update(Job).where(Job.id == job_id).values(**values_to_update).returning(Job)
    updated_job: Optional[Job] = None
    try:
        result = db.execute(stmt)
        updated_job = result.scalar_one_or_none()
        db.commit()
        if updated_job:
            logger.info(f"[SYNC] Updated job {job_id} status to {status.name}")
        else:
            logger.warning(
                f"[SYNC] Job {job_id} not found for status update or update returned no rows."
            )
    except Exception as e:
        logger.error(
            f"[SYNC] update_job_status_sync failed for job {job_id}: {e}", exc_info=True
        )
        db.rollback()
    return updated_job


def update_job_results_sync(
    db: Session,
    job_id: uuid.UUID,
    new_results: Dict[str, Any],
    final_status: JobStatusEnum,
    error_message: Optional[str] = None,
    clear_error_on_success: bool = False,
) -> Optional[Job]:
    """(Sync) Updates results and status/error message. Merges with existing results."""

    job = db.execute(select(Job).where(Job.id == job_id)).scalar_one_or_none()
    if not job:
        logger.warning(
            f"[SYNC] Attempted to update results for non-existent job: {job_id}"
        )
        return None

    current_results = job.results if isinstance(job.results, dict) else {}
    current_results.update(new_results)

    final_error_message: Optional[str] = None
    if error_message is not None:
        final_error_message = error_message
    elif clear_error_on_success and final_status == JobStatusEnum.COMPLETED:
        final_error_message = None
    elif final_status == JobStatusEnum.FAILED:
        final_error_message = (
            job.error_message if error_message is None else error_message
        )

    values_to_update: Dict[str, Any] = {
        "results": current_results,
        "status": final_status,
        "updated_at": datetime.now(timezone.utc),
        "error_message": final_error_message,
    }

    stmt = update(Job).where(Job.id == job_id).values(**values_to_update).returning(Job)
    updated_job: Optional[Job] = None
    try:
        result = db.execute(stmt)
        updated_job = result.scalar_one_or_none()
        db.commit()
        if updated_job:
            logger.info(
                f"[SYNC] Updated results for job {job_id}. Final status: {final_status.name}"
            )
        else:
            logger.warning(
                f"[SYNC] Job {job_id} not found for results update or update returned no rows."
            )
    except Exception as e:
        logger.error(
            f"[SYNC] update_job_results_sync failed for job {job_id}: {e}",
            exc_info=True,
        )
        db.rollback()
    return updated_job
