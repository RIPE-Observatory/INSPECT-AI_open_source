"""
SQLAlchemy models for Retraction Watch database.

These models represent retraction notices and their associated authors,
loaded from the Retraction Watch CSV dataset.
"""

from datetime import datetime
from typing import List, TYPE_CHECKING

from sqlalchemy import String, DateTime, Text, Date, Integer, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.db.base import Base


class Retraction(Base):
    """
    Retraction Watch entry - represents a retraction notice.

    Note: Same paper DOI can have multiple entries (retraction + EOC + correction).
    Data stored exactly as provided by Retraction Watch.
    """

    __tablename__ = "retractions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Unique record ID from Retraction Watch CSV
    record_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)

    # Paper identification
    title: Mapped[str] = mapped_column(Text, nullable=False)
    original_paper_doi: Mapped[str | None] = mapped_column(String(255), nullable=True)
    original_paper_pubmed_id: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Retraction notice details
    retraction_doi: Mapped[str | None] = mapped_column(String(255), nullable=True)
    retraction_pubmed_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    retraction_nature: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    retraction_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    original_paper_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)

    # Metadata
    journal: Mapped[str | None] = mapped_column(String(500), nullable=True)
    publisher: Mapped[str | None] = mapped_column(String(500), nullable=True)
    country: Mapped[str | None] = mapped_column(String(255), nullable=True)
    institution: Mapped[Text | None] = mapped_column(Text, nullable=True)
    subject: Mapped[Text | None] = mapped_column(Text, nullable=True)
    article_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reason: Mapped[Text | None] = mapped_column(Text, nullable=True)
    notes: Mapped[Text | None] = mapped_column(Text, nullable=True)
    urls: Mapped[Text | None] = mapped_column(Text, nullable=True)
    paywalled: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Denormalized author list for fast searching (semicolon-separated)
    authors_fulltext: Mapped[Text | None] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()", onupdate=datetime.now
    )

    # Relationship to normalized authors
    authors: Mapped[List["RetractionAuthor"]] = relationship(
        "RetractionAuthor",
        back_populates="retraction",
        cascade="all, delete-orphan"
    )

    # Indexes defined as table args for composite/partial indexes
    __table_args__ = (
        # Partial index for DOI lookups - excludes placeholder values
        Index(
            'idx_retractions_original_doi',
            original_paper_doi,
            postgresql_where=(
                (original_paper_doi.isnot(None)) &
                (~original_paper_doi.in_(['Unavailable', 'unavailable', '0']))
            )
        ),
        # Full-text search index on title
        Index(
            'idx_retractions_title_gin',
            'title',
            postgresql_using='gin',
            postgresql_ops={'title': 'gin_trgm_ops'}
        ),
        # Composite index for nature + date queries (for "20 most recent")
        Index('idx_retractions_nature_date', 'retraction_nature', retraction_date.desc()),
        # Date-only index for ordering
        Index('idx_retractions_date', retraction_date.desc()),
    )

    def __repr__(self):
        return f"<Retraction(id={self.id}, record_id='{self.record_id}', nature='{self.retraction_nature}')>"

    if TYPE_CHECKING:
        pass


class RetractionAuthor(Base):
    """
    Normalized author table for exact name matching.
    One row per author per retraction.
    """

    __tablename__ = "retraction_authors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Foreign key to retraction
    retraction_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("retractions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Author name exactly as appears in Retraction Watch
    author_name: Mapped[str] = mapped_column(String(500), nullable=False)

    # Position in author list (1 = first author, 2 = second, etc.)
    author_position: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )

    # Relationship back to retraction
    retraction: Mapped["Retraction"] = relationship("Retraction", back_populates="authors")

    # Table constraints and indexes
    __table_args__ = (
        # Prevent duplicate author names for same retraction
        Index('idx_unique_retraction_author', 'retraction_id', 'author_name', unique=True),
        # Case-insensitive exact match index for author searches
        Index('idx_authors_name_lower', 'author_name', postgresql_ops={'author_name': 'text_pattern_ops'}),
    )

    def __repr__(self):
        return f"<RetractionAuthor(id={self.id}, name='{self.author_name}', pos={self.author_position})>"

    if TYPE_CHECKING:
        pass
