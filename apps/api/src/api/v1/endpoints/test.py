"""
Test API endpoints - NO AUTHENTICATION REQUIRED
For local development and testing only.
WARNING: Do not use in production!
"""
import os
import uuid
import logging
import logfire
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.schemas.job import JobCreateResponse, JobStatusResponse
from core.schemas.enums import JobSourceEnum
from core.db.crud import job as crud_job
from core.db.crud import reviewer as reviewer_crud
from core.db.session import get_db_session
from core.config import settings
from core.db.models.reviewer import Reviewer

from arq import ArqRedis, create_pool
from arq.connections import RedisSettings

from logfire.propagate import get_context
from core.db.session import get_redis_settings

router = APIRouter()
logger = logging.getLogger(__name__)

# Test reviewer ID - we'll create/use a test reviewer
TEST_REVIEWER_CLERK_ID = "test_reviewer_local"
TEST_REVIEWER_EMAIL = "test@localhost.dev"


async def get_or_create_test_reviewer(db: AsyncSession) -> Reviewer:
    """Get or create a test reviewer for local testing."""
    reviewer = await reviewer_crud.get_reviewer_by_clerk_user_id(db, TEST_REVIEWER_CLERK_ID)
    if not reviewer:
        logger.info("Creating test reviewer for local testing")
        reviewer = await reviewer_crud.ensure_reviewer(db, TEST_REVIEWER_CLERK_ID)
        # Mark onboarding as complete
        reviewer.email = TEST_REVIEWER_EMAIL
        reviewer.onboarding_complete = True
        await db.commit()
        await db.refresh(reviewer)
    return reviewer


@router.post(
    "/test/analyze-existing-pdf",
    response_model=JobCreateResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def test_analyze_existing_pdf(
    pdf_filename: str,
    identifier: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session),
    redis_settings: RedisSettings = Depends(get_redis_settings),
):
    """
    Test endpoint: Submit a job using an existing PDF from the storage directory.
    NO AUTHENTICATION REQUIRED - for local testing only.

    Args:
        pdf_filename: Name of PDF file in /app/pdf_storage (e.g., "1. Peter H. Gorman.pdf")
        identifier: Optional job identifier (defaults to filename)
    """
    # Get or create test reviewer
    reviewer = await get_or_create_test_reviewer(db)

    # Construct full path
    file_path = os.path.join(settings.PDF_STORAGE_PATH, pdf_filename)

    # Verify file exists
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"PDF file '{pdf_filename}' not found in storage. Available files: {os.listdir(settings.PDF_STORAGE_PATH)[:10]}",
        )

    job_identifier = identifier if identifier else pdf_filename

    arq_pool: Optional[ArqRedis] = None
    try:
        with logfire.span(
            "test.job.create",
            identifier=job_identifier,
            source=JobSourceEnum.USER.value,
            filename=pdf_filename,
        ):
            otel_context_dict = get_context()
            db_job = await crud_job.create_job(
                db=db,
                identifier=job_identifier,
                source=JobSourceEnum.USER,
                reviewer_id=reviewer.id,
                external_id=None,
                file_path=file_path,
            )
            if not db_job:
                logger.error(
                    f"Failed to create test job in database for identifier: {job_identifier}"
                )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Could not create job in database.",
                )

            # Commit the transaction to persist the job
            await db.commit()

            arq_pool = await create_pool(redis_settings)
            await arq_pool.enqueue_job(
                "run_evidence_synthesis_arq_task",
                db_job.id,
                job_identifier,
                file_path,
                _queue_name="arq:queue:orchestrator",
                _job_id=f"{db_job.id}:orchestrator",
                otel_context=otel_context_dict,
            )

            logfire.info(
                "Test job created and enqueued",
                job_id=str(db_job.id),
                identifier=job_identifier,
                source=JobSourceEnum.USER.value,
            )

            return JobCreateResponse(job_id=db_job.id, filename=pdf_filename)

    except Exception as e:
        logger.error(
            f"Error in /test/analyze-existing-pdf for file '{pdf_filename}': {e}",
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}",
        )
    finally:
        if arq_pool:
            await arq_pool.close()


@router.get("/test/jobs/{job_id}/status", response_model=JobStatusResponse)
async def test_get_job_status(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Test endpoint: Get job status without authentication.
    NO AUTHENTICATION REQUIRED - for local testing only.
    """
    db_job = await crud_job.get_job(db=db, job_id=job_id)
    if db_job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID {job_id} not found.",
        )
    return db_job


@router.get("/test/list-pdfs")
async def test_list_pdfs():
    """
    Test endpoint: List available PDFs in storage.
    NO AUTHENTICATION REQUIRED - for local testing only.
    """
    try:
        pdf_files = [
            f for f in os.listdir(settings.PDF_STORAGE_PATH) if f.endswith(".pdf")
        ]
        return {
            "storage_path": settings.PDF_STORAGE_PATH,
            "pdf_count": len(pdf_files),
            "pdfs": sorted(pdf_files)[:50],  # Return max 50 files
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing PDFs: {str(e)}",
        )
