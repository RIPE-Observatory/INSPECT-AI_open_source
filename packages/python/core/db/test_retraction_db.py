"""
Test script to verify Retraction Watch database setup and CRUD operations.
"""

import asyncio
import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

from core.db.crud.retraction import (
    find_retractions_by_doi,
    find_retractions_by_title,
    find_eoc_corrections_by_doi,
    find_retractions_by_author,
    get_retraction_by_record_id,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_URL = "postgresql+asyncpg://inspect_user:password@localhost:5432/inspect_ai"


async def test_database_setup(engine):
    """Test basic database setup and data counts."""
    logger.info("\n" + "="*60)
    logger.info("TEST 1: Database Setup Verification")
    logger.info("="*60)

    async with engine.begin() as conn:
        # Count retractions
        result = await conn.execute(text("SELECT COUNT(*) FROM retractions"))
        retraction_count = result.scalar()
        logger.info(f"✓ Retractions count: {retraction_count:,}")
        assert retraction_count == 67020, f"Expected 67020 retractions, got {retraction_count}"

        # Count authors
        result = await conn.execute(text("SELECT COUNT(*) FROM retraction_authors"))
        author_count = result.scalar()
        logger.info(f"✓ Author entries count: {author_count:,}")

        # Check retraction nature distribution
        result = await conn.execute(text("""
            SELECT retraction_nature, COUNT(*)
            FROM retractions
            GROUP BY retraction_nature
            ORDER BY COUNT(*) DESC
        """))
        logger.info("\nRetraction nature distribution:")
        for row in result.fetchall():
            logger.info(f"  {row[0]}: {row[1]:,}")

        # Verify indexes exist
        result = await conn.execute(text("""
            SELECT indexname
            FROM pg_indexes
            WHERE tablename IN ('retractions', 'retraction_authors')
            ORDER BY indexname
        """))
        indexes = [row[0] for row in result.fetchall()]
        logger.info(f"\n✓ Found {len(indexes)} indexes")
        for idx in indexes:
            logger.info(f"  - {idx}")


async def test_retraction_by_doi(session):
    """Test INSPECT-SR 1.1: Find retractions by DOI."""
    logger.info("\n" + "="*60)
    logger.info("TEST 2: Find Retractions by DOI (INSPECT-SR 1.1)")
    logger.info("="*60)

    # Get a DOI from the database for testing
    result_check = await session.execute(text("""
        SELECT original_paper_doi FROM retractions
        WHERE retraction_nature = 'Retraction'
        AND original_paper_doi IS NOT NULL
        AND original_paper_doi NOT IN ('Unavailable', 'unavailable', '0')
        LIMIT 1
    """))
    test_doi = result_check.scalar()

    if not test_doi:
        logger.info("No retraction DOI found in database")
        return

    logger.info(f"Testing DOI: {test_doi}")

    results = await find_retractions_by_doi(session, test_doi)
    logger.info(f"✓ Found {len(results)} retraction(s)")

    for retraction in results:
        logger.info(f"\n  Record ID: {retraction.record_id}")
        logger.info(f"  Title: {retraction.title[:80]}...")
        logger.info(f"  Nature: {retraction.retraction_nature}")
        logger.info(f"  Retraction Date: {retraction.retraction_date}")
        logger.info(f"  Journal: {retraction.journal}")
        logger.info(f"  Authors: {len(retraction.authors)} authors")
        assert retraction.retraction_nature == "Retraction", "Should only return Retractions"


async def test_eoc_by_doi(session):
    """Test INSPECT-SR 1.2: Find EOC/Corrections by DOI."""
    logger.info("\n" + "="*60)
    logger.info("TEST 3: Find EOC/Corrections by DOI (INSPECT-SR 1.2)")
    logger.info("="*60)

    # First, find a DOI that has EOC or Correction
    result = await session.execute(text("""
        SELECT original_paper_doi, retraction_nature, title
        FROM retractions
        WHERE retraction_nature IN ('Expression of concern', 'Correction')
        AND original_paper_doi IS NOT NULL
        AND original_paper_doi NOT IN ('Unavailable', 'unavailable', '0')
        LIMIT 1
    """))
    row = result.fetchone()

    if row:
        test_doi = row[0]
        logger.info(f"Testing DOI: {test_doi}")
        logger.info(f"Expected nature: {row[1]}")

        results = await find_eoc_corrections_by_doi(session, test_doi)
        logger.info(f"✓ Found {len(results)} EOC/Correction(s)")

        for retraction in results:
            logger.info(f"\n  Title: {retraction.title[:80]}...")
            logger.info(f"  Nature: {retraction.retraction_nature}")
            assert retraction.retraction_nature in ['Expression of concern', 'Correction']
    else:
        logger.info("No EOC/Correction with valid DOI found for testing")


async def test_author_search(session):
    """Test INSPECT-SR 1.3: Find retractions by author."""
    logger.info("\n" + "="*60)
    logger.info("TEST 4: Find Retractions by Author (INSPECT-SR 1.3)")
    logger.info("="*60)

    # Find an author with multiple retractions
    result = await session.execute(text("""
        SELECT author_name, COUNT(*) as count
        FROM retraction_authors
        GROUP BY author_name
        HAVING COUNT(*) >= 3
        ORDER BY COUNT(*) DESC
        LIMIT 1
    """))
    row = result.fetchone()

    if row:
        test_author = row[0]
        expected_count = row[1]
        logger.info(f"Testing author: {test_author}")
        logger.info(f"Expected at least: {expected_count} retractions")

        results = await find_retractions_by_author(session, test_author, limit=20)
        logger.info(f"✓ Found {len(results)} retraction(s) (limited to 20)")

        if results:
            logger.info("\n  Most recent retraction:")
            logger.info(f"  Title: {results[0].title[:80]}...")
            logger.info(f"  Date: {results[0].retraction_date}")
            logger.info(f"  Nature: {results[0].retraction_nature}")

            # Verify author appears in the retraction
            author_found = any(
                a.author_name.lower() == test_author.lower()
                for a in results[0].authors
            )
            assert author_found, "Author should appear in the retraction"
            logger.info("  ✓ Author verified in author list")
    else:
        logger.info("No author with 3+ retractions found for testing")


async def test_title_search(session):
    """Test fuzzy title search."""
    logger.info("\n" + "="*60)
    logger.info("TEST 5: Fuzzy Title Search")
    logger.info("="*60)

    # Get a title from database and search with a partial match
    result = await session.execute(text("""
        SELECT title, retraction_nature
        FROM retractions
        WHERE retraction_nature = 'Retraction'
        AND LENGTH(title) > 50
        LIMIT 1
    """))
    row = result.fetchone()

    if row:
        full_title = row[0]
        # Use first 30 characters for fuzzy search
        partial_title = full_title[:30]
        logger.info(f"Full title: {full_title[:80]}...")
        logger.info(f"Searching with: {partial_title}")

        results = await find_retractions_by_title(session, partial_title, similarity_threshold=0.3)
        logger.info(f"✓ Found {len(results)} match(es)")

        if results:
            logger.info("\n  Top match:")
            logger.info(f"  Title: {results[0].title[:80]}...")
            logger.info(f"  Nature: {results[0].retraction_nature}")


async def test_record_id_lookup(session):
    """Test lookup by Retraction Watch record ID."""
    logger.info("\n" + "="*60)
    logger.info("TEST 6: Lookup by Record ID")
    logger.info("="*60)

    # Get a random record ID
    result = await session.execute(text("SELECT record_id FROM retractions LIMIT 1"))
    test_record_id = result.scalar()

    logger.info(f"Testing record ID: {test_record_id}")

    result = await get_retraction_by_record_id(session, test_record_id)
    assert result is not None, "Should find retraction by record ID"
    logger.info(f"✓ Found retraction: {result.title[:80]}...")
    logger.info(f"  DOI: {result.original_paper_doi}")
    logger.info(f"  Nature: {result.retraction_nature}")


async def test_query_performance(engine):
    """Test query performance with EXPLAIN ANALYZE."""
    logger.info("\n" + "="*60)
    logger.info("TEST 7: Query Performance")
    logger.info("="*60)

    async with engine.begin() as conn:
        # Test DOI index usage
        logger.info("\n1. DOI lookup performance:")
        result = await conn.execute(text("""
            EXPLAIN ANALYZE
            SELECT * FROM retractions
            WHERE original_paper_doi = '10.1016/j.jacl.2015.12.017'
            AND retraction_nature = 'Retraction'
        """))
        for row in result.fetchall():
            logger.info(f"  {row[0]}")

        # Test author index usage
        logger.info("\n2. Author lookup performance:")
        result = await conn.execute(text("""
            EXPLAIN ANALYZE
            SELECT r.* FROM retractions r
            JOIN retraction_authors ra ON r.id = ra.retraction_id
            WHERE LOWER(ra.author_name) = LOWER('John Smith')
            ORDER BY r.retraction_date DESC NULLS LAST
            LIMIT 20
        """))
        for row in result.fetchall():
            logger.info(f"  {row[0]}")


async def main():
    """Run all tests."""
    logger.info("Starting Retraction Watch Database Tests...")

    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        # Test 1: Database setup
        await test_database_setup(engine)

        # Create session for CRUD tests
        async with async_session() as session:
            # Test 2: DOI lookup for retractions
            await test_retraction_by_doi(session)

            # Test 3: DOI lookup for EOC/corrections
            await test_eoc_by_doi(session)

            # Test 4: Author search
            await test_author_search(session)

            # Test 5: Title search
            await test_title_search(session)

            # Test 6: Record ID lookup
            await test_record_id_lookup(session)

        # Test 7: Query performance
        await test_query_performance(engine)

        logger.info("\n" + "="*60)
        logger.info("✓ ALL TESTS PASSED!")
        logger.info("="*60)

    except Exception as e:
        logger.error(f"\n✗ TEST FAILED: {e}", exc_info=True)
        raise
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
