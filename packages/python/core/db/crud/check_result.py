import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from core.db.models.check_result import CheckResult
from core.db.validation import (
    validate_check_name,
    validate_check_status,
    validate_results_data,
    validate_uuid,
)
from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def create_or_update_check_result(
    db: AsyncSession,
    job_id: uuid.UUID,
    check_name: str,
    status: str,
    result_data: Optional[Dict[str, Any]] = None,
    error_message: Optional[str] = None,
    started_at: Optional[datetime] = None,
    completed_at: Optional[datetime] = None,
    execution_time_ms: Optional[int] = None,
) -> CheckResult:
    """Create or update a check result record."""
    # Validate inputs
    validate_uuid(job_id)
    validate_check_name(check_name)
    validate_check_status(status)
    validate_results_data(result_data)

    if execution_time_ms is not None and execution_time_ms < 0:
        raise ValueError("Execution time cannot be negative")

    # Check if record exists
    stmt = select(CheckResult).where(
        and_(CheckResult.job_id == job_id, CheckResult.check_name == check_name)
    )
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        # Update existing record
        update_stmt = (
            update(CheckResult)
            .where(
                and_(CheckResult.job_id == job_id, CheckResult.check_name == check_name)
            )
            .values(
                status=status,
                result_data=result_data,
                error_message=error_message,
                completed_at=completed_at,
                execution_time_ms=execution_time_ms,
            )
        )
        await db.execute(update_stmt)
        await db.refresh(existing)
        return existing
    else:
        # Create new record
        check_result = CheckResult(
            job_id=job_id,
            check_name=check_name,
            status=status,
            result_data=result_data or {},
            error_message=error_message,
            started_at=started_at,
            completed_at=completed_at,
            execution_time_ms=execution_time_ms,
        )
        db.add(check_result)
        await db.flush()
        return check_result


async def mark_check_started(
    db: AsyncSession, job_id: uuid.UUID, check_name: str, started_at: datetime
) -> CheckResult:
    """Mark a check as started."""
    return await create_or_update_check_result(
        db=db,
        job_id=job_id,
        check_name=check_name,
        status="RUNNING",
        started_at=started_at,
    )


async def mark_check_completed(
    db: AsyncSession,
    job_id: uuid.UUID,
    check_name: str,
    result_data: Dict[str, Any],
    execution_time_ms: int,
) -> CheckResult:
    """Mark a check as completed with results."""
    return await create_or_update_check_result(
        db=db,
        job_id=job_id,
        check_name=check_name,
        status="COMPLETED",
        result_data=result_data,
        completed_at=datetime.now(timezone.utc),
        execution_time_ms=execution_time_ms,
    )


async def mark_check_failed(
    db: AsyncSession,
    job_id: uuid.UUID,
    check_name: str,
    error_message: str,
    execution_time_ms: Optional[int] = None,
) -> CheckResult:
    """Mark a check as failed."""
    return await create_or_update_check_result(
        db=db,
        job_id=job_id,
        check_name=check_name,
        status="FAILED",
        error_message=error_message,
        completed_at=datetime.now(timezone.utc),
        execution_time_ms=execution_time_ms,
    )


async def get_job_check_results(
    db: AsyncSession, job_id: uuid.UUID
) -> List[CheckResult]:
    """Get all check results for a job."""
    stmt = (
        select(CheckResult)
        .where(CheckResult.job_id == job_id)
        .order_by(CheckResult.started_at)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_check_result(
    db: AsyncSession, job_id: uuid.UUID, check_name: str
) -> Optional[CheckResult]:
    """Get a specific check result."""
    stmt = select(CheckResult).where(
        and_(CheckResult.job_id == job_id, CheckResult.check_name == check_name)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_completed_checks_count(db: AsyncSession, job_id: uuid.UUID) -> int:
    """Get count of completed checks for a job."""
    stmt = select(CheckResult).where(
        and_(
            CheckResult.job_id == job_id,
            CheckResult.status.in_(["COMPLETED", "FAILED"]),
        )
    )
    result = await db.execute(stmt)
    return len(list(result.scalars().all()))
