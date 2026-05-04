import os
import uuid
import aiofiles
import logging
import logfire
from typing import Optional, Dict
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Form, Request
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from core.schemas.job import JobCreateResponse, JobStatusResponse
from core.schemas.enums import JobSourceEnum
from core.db.crud import job as crud_job
from core.db.session import get_db_session
from core.config import settings
from core.db.models.job import Job
from core.db.models.reviewer import Reviewer
from core.middleware.rate_limit import limiter

from arq import ArqRedis, create_pool
from arq.connections import RedisSettings

from logfire.propagate import get_context
from core.db.session import get_redis_settings
from core.schemas.inspect_sr import (
    AnswerRecord,
    InspectSRGetResponse,
    InspectSRPutRequest,
    InspectSRPutResponse,
    InspectSRProgressResponse,
    QUESTION_TYPES,
    get_active_question_types,
    compute_progress_from_records,
)
from api.dependencies.reviewer import require_complete_reviewer

router = APIRouter()
logger = logging.getLogger(__name__)


async def _get_job_for_reviewer_or_404(
    db: AsyncSession, job_id: uuid.UUID, reviewer: Reviewer
) -> Job:
    db_job = await crud_job.get_job_for_reviewer(
        db=db, job_id=job_id, reviewer_id=reviewer.id
    )
    if db_job is None:
        logger.warning(
            "Job %s not found for reviewer %s", job_id, reviewer.clerk_user_id
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID {job_id} not found.",
        )
    return db_job


@router.post(
    "/analyze", response_model=JobCreateResponse, status_code=status.HTTP_202_ACCEPTED
)
@limiter.limit("5/minute")
async def analyze_document(
    request: Request,
    file: UploadFile = File(...),
    identifier: Optional[str] = Form(None),
    source: JobSourceEnum = Form(JobSourceEnum.USER),
    external_id: Optional[str] = Form(None),
    reviewer: Reviewer = Depends(require_complete_reviewer),
    db: AsyncSession = Depends(get_db_session),
    redis_settings: RedisSettings = Depends(get_redis_settings),
):
    """
    Accepts a PDF, creates a job, saves the PDF to shared storage, and enqueues the analysis task with the file path.
    Identifier is the original filename if not provided, otherwise the provided identifier.
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No filename provided."
        )
    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Only PDF is accepted.",
        )

    job_identifier = identifier if identifier else file.filename
    original_filename = file.filename

    base_name_for_file = (
        job_identifier
        if len(job_identifier) > 5 and job_identifier != original_filename
        else original_filename
    )
    safe_base_name = "".join(
        c if c.isalnum() or c in (".", "-", "_") else "_"
        for c in base_name_for_file.rsplit(".", 1)[0]
    )
    unique_filename = f"{safe_base_name[:50]}_{uuid.uuid4()}.pdf"
    file_save_path = os.path.join(settings.PDF_STORAGE_PATH, unique_filename)

    try:
        os.makedirs(settings.PDF_STORAGE_PATH, exist_ok=True)
        logger.info(
            f"Ensured PDF storage directory exists: {settings.PDF_STORAGE_PATH}"
        )
    except OSError as e_dir:
        logger.error(
            f"Could not create PDF storage directory {settings.PDF_STORAGE_PATH}: {e_dir}",
            exc_info=True,
        )
        # Depending on severity, you might re-raise or raise HTTPException here
        # TODO For now, proceeding, assuming it might exist or subsequent file open will fail clearly.

    try:
        # Stream file to disk instead of loading entirely into memory
        async with aiofiles.open(file_save_path, "wb") as out_file:
            file_size = 0
            chunk_size = 8192  # 8KB chunks

            while chunk := await file.read(chunk_size):
                file_size += len(chunk)
                await out_file.write(chunk)

            if file_size == 0:
                await file.close()
                # Remove empty file
                if os.path.exists(file_save_path):
                    os.remove(file_save_path)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Uploaded file is empty.",
                )
        await file.close()
        logger.info(f"File {original_filename} saved as {file_save_path}")
    except Exception as e:
        logger.error(
            f"Failed to save uploaded file {original_filename} to {file_save_path}: {e}",
            exc_info=True,
        )
        await file.close()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not save uploaded file.",
        )

    arq_pool: Optional[ArqRedis] = None
    try:
        with logfire.span(
            "job.create",
            identifier=job_identifier,
            source=source.value,
            filename=original_filename,
        ):
            otel_context_dict = get_context()
            db_job = await crud_job.create_job(
                db=db,
                identifier=job_identifier,
                source=source,
                reviewer_id=reviewer.id,
                external_id=external_id,
                file_path=file_save_path,
            )
            if not db_job:
                logger.error(
                    f"Failed to create job in database for identifier: {job_identifier}"
                )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Could not create job in database.",
                )

            # Commit the transaction to persist the job
            await db.commit()

            arq_pool = await create_pool(redis_settings)
            try:
                await arq_pool.enqueue_job(
                    "run_evidence_synthesis_arq_task",
                    db_job.id,
                    job_identifier,
                    file_save_path,
                    _queue_name="arq:queue:orchestrator",
                    _job_id=f"{db_job.id}:orchestrator",
                    otel_context=otel_context_dict,
                )
            finally:
                await arq_pool.close()

            logfire.info(
                "Job created and enqueued",
                job_id=str(db_job.id),
                identifier=job_identifier,
                source=source.value,
            )

            return JobCreateResponse(job_id=db_job.id, filename=original_filename)

    except Exception as e:
        logger.error(
            f"Error in /analyze for file '{original_filename}': {e}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred processing the file.",
        )

@router.get("/jobs/{job_id}/status", response_model=JobStatusResponse)
async def get_job_status(
    job_id: uuid.UUID,
    reviewer: Reviewer = Depends(require_complete_reviewer),
    db: AsyncSession = Depends(get_db_session),
):
    """Retrieves the status and results for a specific job by its UUID."""
    db_job = await _get_job_for_reviewer_or_404(db, job_id, reviewer)
    return db_job


@router.get("/jobs/{job_id}/pdf")
async def get_job_pdf(
    job_id: uuid.UUID,
    reviewer: Reviewer = Depends(require_complete_reviewer),
    db: AsyncSession = Depends(get_db_session),
):
    """Serves the PDF file associated with a specific job."""
    db_job = await _get_job_for_reviewer_or_404(db, job_id, reviewer)

    if not db_job.file_path or not os.path.exists(db_job.file_path):
        logger.warning(
            "PDF file not found for Job ID: %s, file_path: %s",
            job_id,
            db_job.file_path,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="PDF file not found."
        )

    filename = os.path.basename(db_job.file_path)

    return FileResponse(
        path=db_job.file_path, media_type="application/pdf", filename=filename
    )


@router.get("/jobs/{job_id}/inspect-sr", response_model=InspectSRGetResponse)
async def get_job_inspect_sr(
    job_id: uuid.UUID,
    reviewer: Reviewer = Depends(require_complete_reviewer),
    db: AsyncSession = Depends(get_db_session),
):
    """Retrieve stored INSPECT-SR data for a job.

    INSPECT-SR data is automatically created during job processing,
    so this endpoint simply returns what already exists.
    """
    db_job = await _get_job_for_reviewer_or_404(db, job_id, reviewer)

    results = db_job.results if isinstance(db_job.results, dict) else {}
    sr = results.get("inspect_sr")

    if not sr or not isinstance(sr, dict):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="INSPECT-SR data not found for this job. Job may not be completed yet.",
        )

    # Extract data
    version = int(sr.get("version", 1))
    updated_at = sr.get("updated_at") or datetime.now(timezone.utc).isoformat()
    data = sr.get("data") or []

    # Validate and convert to AnswerRecord objects
    try:
        records = [AnswerRecord.model_validate(r) for r in data]
    except Exception as e:
        logger.error(f"Invalid INSPECT-SR records for job {job_id}: {e}")
        records = []

    # Compute progress
    progress = compute_progress_from_records(records)

    return InspectSRGetResponse(
        job_id=db_job.id,
        version=version,
        updated_at=updated_at,
        progress=progress,
        data=records,
    )


@router.put("/jobs/{job_id}/inspect-sr", response_model=InspectSRPutResponse)
@limiter.limit("30/minute")
async def put_job_inspect_sr(
    request: Request,
    job_id: uuid.UUID,
    payload: InspectSRPutRequest,
    reviewer: Reviewer = Depends(require_complete_reviewer),
    db: AsyncSession = Depends(get_db_session),
):
    """Create or update INSPECT-SR checklist data for a job (stored under results.inspect_sr)."""
    db_job = await _get_job_for_reviewer_or_404(db, job_id, reviewer)

    # Validate flat records
    if payload.data is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Missing data"
        )
    try:
        incoming_records = [AnswerRecord.model_validate(r) for r in payload.data]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid records: {e}"
        )

    # Get active beta question set.
    active_question_types = get_active_question_types()

    # Validate question ids and answers; collect ids
    incoming_ids: Dict[str, int] = {}
    for r in incoming_records:
        qtype = QUESTION_TYPES.get(r.question_id)
        if not qtype:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown question_id: {r.question_id}",
            )
        # Uniqueness check
        if r.question_id in incoming_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Duplicate question_id: {r.question_id}",
            )
        incoming_ids[r.question_id] = 1
        # Validate automated_judgement if present
        if r.automated_judgement is not None:
            if qtype == "check" and r.automated_judgement not in ("yes", "no", "unclear", "na"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid automated_judgement for {r.question_id}",
                )
            if qtype == "judgement" and r.automated_judgement not in (
                "no-concerns",
                "some-concerns",
                "serious-concerns",
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid automated_judgement for {r.question_id}",
                )
        # Validate reviewed_judgement if present
        if r.reviewed_judgement is not None:
            if qtype == "check" and r.reviewed_judgement not in ("yes", "no", "unclear", "na"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid reviewed_judgement for {r.question_id}",
                )
            if qtype == "judgement" and r.reviewed_judgement not in (
                "no-concerns",
                "some-concerns",
                "serious-concerns",
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid reviewed_judgement for {r.question_id}",
                )

    # Require the complete active beta set.
    expected_ids = set(active_question_types.keys())
    provided_ids = set(incoming_ids.keys())
    missing = sorted(expected_ids - provided_ids)
    extra = sorted(provided_ids - expected_ids)
    if missing or extra:
        details = {}
        if missing:
            details["missing"] = missing
        if extra:
            details["extra"] = extra
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "invalid_question_set", **details},
        )

    results = db_job.results if isinstance(db_job.results, dict) else {}
    current_sr = results.get("inspect_sr") if isinstance(results, dict) else None

    prev_version = 0
    if isinstance(current_sr, dict):
        try:
            prev_version = int(current_sr.get("version") or 0)
        except Exception:
            prev_version = 0

    # Optimistic concurrency
    if payload.version is not None and prev_version != payload.version:
        server_copy = current_sr if isinstance(current_sr, dict) else None
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "version_conflict", "server": server_copy},
        )

    # Simple merge: just save what the frontend sends
    merged_map: Dict[str, Dict] = {}
    for r in incoming_records:
        # Convert to dict and save directly
        merged_map[r.question_id] = r.model_dump()

    # Persist container
    now_iso = datetime.now(timezone.utc).isoformat()
    new_version = prev_version + 1
    new_records = list(merged_map.values())
    progress = compute_progress_from_records(
        [AnswerRecord.model_validate(x) for x in new_records]
    )
    sr_container = {
        "version": new_version,
        "updated_at": now_iso,
        "progress": progress,
        "data": new_records,
    }

    # Use atomic JSONB merge for better performance and to prevent race conditions
    # This only writes the inspect_sr key, preserving all other keys (grobid_metadata, checks, etc.)
    await crud_job.upsert_job_results_merge(
        db=db, job_id=job_id, patch={"inspect_sr": sr_container}
    )
    await db.commit()

    return InspectSRPutResponse(
        job_id=db_job.id, updated_at=now_iso, version=new_version
    )


@router.get(
    "/jobs/{job_id}/inspect-sr/progress", response_model=InspectSRProgressResponse
)
async def get_job_inspect_sr_progress(
    job_id: uuid.UUID,
    reviewer: Reviewer = Depends(require_complete_reviewer),
    db: AsyncSession = Depends(get_db_session),
):
    db_job = await _get_job_for_reviewer_or_404(db, job_id, reviewer)
    results = db_job.results if isinstance(db_job.results, dict) else {}
    sr = results.get("inspect_sr") if isinstance(results, dict) else None
    if not isinstance(sr, dict):
        return InspectSRProgressResponse(job_id=db_job.id, completed=0, percent=0, total=0)
    data = sr.get("data") or []
    try:
        records = [AnswerRecord.model_validate(x) for x in data]
    except Exception:
        records = []
    prog = compute_progress_from_records(records)
    return InspectSRProgressResponse(
        job_id=db_job.id,
        completed=prog["completed"],
        percent=prog["percent"],
        total=prog.get("total", 26),
    )


