"""
CRUD operations for Retraction Watch database queries.

Implements specific query patterns for INSPECT-SR checks 1.1, 1.2, and 1.3:
- 1.1: Retraction detection (main article + references)
- 1.2: Expression of Concern / Correction detection (main article only)
- 1.3: Author retraction history (exact name match, 20 most recent)
"""

import logging
from typing import List, Optional

from sqlalchemy import select, func, or_, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.db.models.retraction import Retraction, RetractionAuthor

logger = logging.getLogger(__name__)


# INSPECT-SR 1.1: Retraction detection (main article + references)
async def find_retractions_by_doi(
    db: AsyncSession,
    doi: str
) -> List[Retraction]:
    """
    Find retractions by DOI.

    Used for INSPECT-SR 1.1 - checks if a paper (or its references) has been retracted.
    Only returns records with retraction_nature='Retraction'.

    Args:
        db: Database session
        doi: Digital Object Identifier (exact match, case-sensitive as stored)

    Returns:
        List of Retraction objects with retraction_nature='Retraction'
    """
    if not doi or not doi.strip():
        return []

    doi = doi.strip()

    stmt = (
        select(Retraction)
        .where(
            Retraction.original_paper_doi == doi,
            Retraction.retraction_nature == 'Retraction'
        )
        .options(selectinload(Retraction.authors))
        .order_by(Retraction.retraction_date.desc().nulls_last())
    )

    result = await db.execute(stmt)
    return list(result.scalars().all())


async def find_retractions_by_title(
    db: AsyncSession,
    title: str,
    similarity_threshold: float = 0.9
) -> List[Retraction]:
    """
    Find retractions by title using fuzzy text search.

    Used for INSPECT-SR 1.1 - fallback when DOI is not available for main article.
    Uses PostgreSQL's pg_trgm for trigram similarity matching with optimized GIN index usage.
    Only returns records with retraction_nature='Retraction'.

    Performance optimization:
    - set_limit(0.85) reduces GIN index candidates from ~10k to ~1-10 rows
    - Then filter by similarity >= threshold (default 0.9) for high accuracy
    - Result: 200x faster (1400ms → 7ms per query)

    Args:
        db: Database session
        title: Paper title for fuzzy matching
        similarity_threshold: Minimum similarity score (0.0 to 1.0, default 0.9)

    Returns:
        List of Retraction objects with retraction_nature='Retraction', ordered by similarity
    """
    if not title or not title.strip():
        return []

    title = title.strip()

    # Set GIN index threshold to 0.85 for broader candidate matching (performance optimization)
    # This dramatically reduces GIN index scan time while still catching valid fuzzy matches
    await db.execute(text("SELECT set_limit(0.85)"))

    # Use % operator (trigram matching) + strict similarity filter
    # GIN index returns ~1-10 candidates at 0.85, then we filter to >=0.9 for accuracy
    stmt = (
        select(Retraction)
        .where(
            Retraction.title.op('%')(title),  # GIN index operator (fast)
            Retraction.retraction_nature == 'Retraction',
            func.similarity(Retraction.title, title) >= similarity_threshold  # Accuracy filter
        )
        .options(selectinload(Retraction.authors))
        .order_by(func.similarity(Retraction.title, title).desc())
        .limit(1)  # Return only top match
    )

    result = await db.execute(stmt)
    return list(result.scalars().all())


# INSPECT-SR 1.2: Expression of Concern / Correction detection (main article only)
async def find_eoc_corrections_by_doi(
    db: AsyncSession,
    doi: str
) -> List[Retraction]:
    """
    Find Expressions of Concern and Corrections by DOI.

    Used for INSPECT-SR 1.2 - checks if main article has EOC or correction notices.
    Returns records with retraction_nature in ['Expression of concern', 'Correction'].

    Args:
        db: Database session
        doi: Digital Object Identifier (exact match, case-sensitive as stored)

    Returns:
        List of Retraction objects with retraction_nature in EOC/Correction
    """
    if not doi or not doi.strip():
        return []

    doi = doi.strip()

    stmt = (
        select(Retraction)
        .where(
            Retraction.original_paper_doi == doi,
            or_(
                Retraction.retraction_nature == 'Expression of concern',
                Retraction.retraction_nature == 'Correction'
            )
        )
        .options(selectinload(Retraction.authors))
        .order_by(Retraction.retraction_date.desc().nulls_last())
    )

    result = await db.execute(stmt)
    return list(result.scalars().all())


async def find_eoc_corrections_by_title(
    db: AsyncSession,
    title: str,
    similarity_threshold: float = 0.9
) -> List[Retraction]:
    """
    Find Expressions of Concern and Corrections by title using fuzzy text search.

    Used for INSPECT-SR 1.2 - fallback when DOI is not available for main article.
    Uses PostgreSQL's pg_trgm for trigram similarity matching with optimized GIN index usage.
    Returns records with retraction_nature in ['Expression of concern', 'Correction'].

    Performance optimization:
    - set_limit(0.85) reduces GIN index candidates from ~10k to ~1-10 rows
    - Then filter by similarity >= threshold (default 0.9) for high accuracy
    - Result: 200x faster (1400ms → 7ms per query)

    Args:
        db: Database session
        title: Paper title for fuzzy matching
        similarity_threshold: Minimum similarity score (0.0 to 1.0, default 0.9)

    Returns:
        List of Retraction objects with retraction_nature in EOC/Correction, ordered by similarity
    """
    if not title or not title.strip():
        return []

    title = title.strip()

    # Set GIN index threshold to 0.85 for broader candidate matching (performance optimization)
    await db.execute(text("SELECT set_limit(0.85)"))

    # Use % operator (trigram matching) + strict similarity filter
    stmt = (
        select(Retraction)
        .where(
            Retraction.title.op('%')(title),  # GIN index operator (fast)
            or_(
                Retraction.retraction_nature == 'Expression of concern',
                Retraction.retraction_nature == 'Correction'
            ),
            func.similarity(Retraction.title, title) >= similarity_threshold  # Accuracy filter
        )
        .options(selectinload(Retraction.authors))
        .order_by(func.similarity(Retraction.title, title).desc())
        .limit(1)  # Return only top match
    )

    result = await db.execute(stmt)
    return list(result.scalars().all())


# INSPECT-SR 1.3: Author retraction history (exact name match, 20 most recent)
async def find_retractions_by_author(
    db: AsyncSession,
    author_name: str,
    limit: int = 20
) -> List[Retraction]:
    """
    Find retractions by author name (exact match, case-insensitive).

    Used for INSPECT-SR 1.3 - checks an author's retraction history.
    Returns up to 'limit' most recent retractions where the author appears.

    Args:
        db: Database session
        author_name: Full author name (exact match, case-insensitive)
        limit: Maximum number of results (default: 20)

    Returns:
        List of Retraction objects where author appears, ordered by most recent retraction_date
    """
    if not author_name or not author_name.strip():
        return []

    author_name = author_name.strip()

    # Join with retraction_authors table and filter by exact name match (case-insensitive)
    stmt = (
        select(Retraction)
        .join(RetractionAuthor, Retraction.id == RetractionAuthor.retraction_id)
        .where(func.lower(RetractionAuthor.author_name) == func.lower(author_name))
        .options(selectinload(Retraction.authors))
        .order_by(Retraction.retraction_date.desc().nulls_last())
        .limit(limit)
    )

    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_retraction_by_record_id(
    db: AsyncSession,
    record_id: str
) -> Optional[Retraction]:
    """
    Get a single retraction by its Retraction Watch record ID.

    Args:
        db: Database session
        record_id: Retraction Watch record ID (unique)

    Returns:
        Retraction object or None if not found
    """
    if not record_id or not record_id.strip():
        return None

    record_id = record_id.strip()

    stmt = (
        select(Retraction)
        .where(Retraction.record_id == record_id)
        .options(selectinload(Retraction.authors))
    )

    result = await db.execute(stmt)
    return result.scalar_one_or_none()
