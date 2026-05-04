import uuid
from datetime import datetime
from typing import Optional, TYPE_CHECKING, Dict, Any

from sqlalchemy import String, DateTime, Text, func, Integer, Float, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Enum as SQLAlchemyEnum

from core.db.base import Base
from core.schemas.enums import JobSourceEnum, JobStatusEnum
from core.config import (
    DEFAULT_TOTAL_CHECKS,
    DEFAULT_CHECKS_COMPLETED,
    DEFAULT_CURRENT_PHASE,
    MAX_EXTERNAL_ID_LENGTH,
    MAX_FILE_PATH_LENGTH,
    MAX_CURRENT_PHASE_LENGTH,
)


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    status: Mapped[JobStatusEnum] = mapped_column(
        SQLAlchemyEnum(JobStatusEnum, name="job_status_enum", create_constraint=True),
        nullable=False,
        default=JobStatusEnum.PENDING,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    identifier: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    results: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB, nullable=True, default=lambda: {}
    )

    # New fields for job source and external identifier
    source: Mapped[JobSourceEnum] = mapped_column(
        SQLAlchemyEnum(JobSourceEnum, name="jobsourceenum", create_constraint=True),
        nullable=False,
        server_default=JobSourceEnum.USER.value,
    )
    external_id: Mapped[Optional[str]] = mapped_column(
        String(MAX_EXTERNAL_ID_LENGTH), nullable=True
    )

    # PDF file path for serving to frontend
    file_path: Mapped[Optional[str]] = mapped_column(
        String(MAX_FILE_PATH_LENGTH), nullable=True
    )

    # Processing time tracking
    processing_time_seconds: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True
    )

    # Streaming progress fields
    checks_completed: Mapped[int] = mapped_column(
        Integer, default=DEFAULT_CHECKS_COMPLETED, nullable=False
    )
    total_checks: Mapped[int] = mapped_column(
        Integer, default=DEFAULT_TOTAL_CHECKS, nullable=False
    )
    current_phase: Mapped[Optional[str]] = mapped_column(
        String(MAX_CURRENT_PHASE_LENGTH), default=DEFAULT_CURRENT_PHASE, nullable=True
    )

    reviewer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("reviewers.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    reviewer = relationship("Reviewer", back_populates="jobs")

    # Relationship to check results
    check_results = relationship(
        "CheckResult", back_populates="job", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Job(id={self.id}, status='{self.status}', identifier='{self.identifier}')>"

    if TYPE_CHECKING:
        pass
