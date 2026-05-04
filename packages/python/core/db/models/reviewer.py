import uuid
from datetime import datetime
from typing import Optional, TYPE_CHECKING, List

from sqlalchemy import (
    String,
    DateTime,
    Boolean,
    func,
    Enum as SQLAlchemyEnum,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.config import (
    DEFAULT_KG_VISIBILITY,
    MAX_REVIEWER_AFFILIATION_LENGTH,
    MAX_REVIEWER_COUNTRY_LENGTH,
    MAX_REVIEWER_NAME_LENGTH,
    MAX_REVIEWER_ORCID_LENGTH,
    MAX_REVIEWER_ROLE_LENGTH,
    MAX_REVIEWER_USERNAME_LENGTH,
)
from core.db.base import Base
from core.schemas.enums import KGVisibilityEnum


class Reviewer(Base):
    __tablename__ = "reviewers"
    __table_args__ = (
        UniqueConstraint("clerk_user_id", name="uq_reviewers_clerk_user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    clerk_user_id: Mapped[str] = mapped_column(
        String(MAX_REVIEWER_USERNAME_LENGTH),
        nullable=False,
        index=True,
    )
    given_name: Mapped[Optional[str]] = mapped_column(
        String(MAX_REVIEWER_NAME_LENGTH), nullable=True
    )
    family_name: Mapped[Optional[str]] = mapped_column(
        String(MAX_REVIEWER_NAME_LENGTH), nullable=True
    )
    username: Mapped[Optional[str]] = mapped_column(
        String(MAX_REVIEWER_USERNAME_LENGTH), nullable=True
    )
    email: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, index=True
    )
    affiliation_institution: Mapped[Optional[str]] = mapped_column(
        String(MAX_REVIEWER_AFFILIATION_LENGTH), nullable=True
    )
    affiliation_department: Mapped[Optional[str]] = mapped_column(
        String(MAX_REVIEWER_AFFILIATION_LENGTH), nullable=True
    )
    role: Mapped[Optional[str]] = mapped_column(
        String(MAX_REVIEWER_ROLE_LENGTH), nullable=True
    )
    country: Mapped[Optional[str]] = mapped_column(
        String(MAX_REVIEWER_COUNTRY_LENGTH), nullable=True
    )
    orcid: Mapped[Optional[str]] = mapped_column(
        String(MAX_REVIEWER_ORCID_LENGTH), nullable=True
    )
    onboarding_complete: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    kg_visibility: Mapped[KGVisibilityEnum] = mapped_column(
        SQLAlchemyEnum(KGVisibilityEnum, name="kg_visibility_enum", create_constraint=True, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        server_default=DEFAULT_KG_VISIBILITY,
    )
    kg_visibility_updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    jobs: Mapped[List["Job"]] = relationship(
        "Job", back_populates="reviewer"
    )

    def __repr__(self) -> str:
        return f"<Reviewer id={self.id} clerk_user_id={self.clerk_user_id}>"

    if TYPE_CHECKING:
        from .job import Job  # pragma: no cover
