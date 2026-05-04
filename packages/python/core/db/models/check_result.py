import uuid
from datetime import datetime
from typing import Optional, Dict, Any

from sqlalchemy import String, DateTime, Integer, Text, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, Mapped, mapped_column

from core.db.base import Base
from core.config import MAX_CHECK_NAME_LENGTH, MAX_CHECK_STATUS_LENGTH


class CheckResult(Base):
    """Individual check result for streaming progress tracking."""

    __tablename__ = "check_results"
    __table_args__ = (Index("ix_check_results_job_status", "job_id", "status"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("jobs.id"), nullable=False, index=True
    )
    check_name: Mapped[str] = mapped_column(
        String(MAX_CHECK_NAME_LENGTH), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String(MAX_CHECK_STATUS_LENGTH), nullable=False, index=True
    )
    result_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    execution_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Relationship back to job
    job = relationship("Job", back_populates="check_results")

    def __repr__(self):
        return f"<CheckResult(job_id={self.job_id}, check_name='{self.check_name}', status='{self.status}')>"
