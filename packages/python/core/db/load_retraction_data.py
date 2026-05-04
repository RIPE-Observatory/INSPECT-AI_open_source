"""
Retraction Watch CSV to PostgreSQL Data Loader

This script loads the Retraction Watch CSV data into the normalized PostgreSQL database
tables created by the Alembic migration.

Usage:
    python -m core.db.load_retraction_data

Environment Variables:
    DATABASE_URL - PostgreSQL connection string (default: from .env)
    RETRACTION_CSV_PATH - Path to CSV file (default: var/data/retraction_watch.csv)
"""

import csv
import asyncio
import logging
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
from dotenv import load_dotenv

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://inspect_user:password@localhost:5432/inspect_ai")
CSV_PATH = os.getenv("RETRACTION_CSV_PATH", "var/data/retraction_watch.csv")
BATCH_SIZE = 1000


def str_or_none(value: str) -> Optional[str]:
    """Convert empty string to None, otherwise return stripped value."""
    if not value or not value.strip():
        return None
    return value.strip()


def parse_date(date_str: str) -> Optional[datetime]:
    """
    Parse date from CSV format: M/D/YYYY H:MM (e.g., '1/6/2025 0:00')

    Args:
        date_str: Date string from CSV

    Returns:
        datetime object or None if empty
    """
    if not date_str or not date_str.strip():
        return None

    try:
        return datetime.strptime(date_str.strip(), "%m/%d/%Y %H:%M")
    except ValueError as e:
        logger.error(f"Unexpected date format: '{date_str}' - {e}")
        return None


def parse_authors(author_string: str) -> List[tuple[str, int]]:
    """
    Parse semicolon-separated authors.

    Args:
        author_string: Raw author string from CSV (e.g., "John Smith;Jane Doe;...")

    Returns:
        List of (author_name, position) tuples
    """
    if not author_string or not author_string.strip():
        return []

    authors = [a.strip() for a in author_string.split(';') if a.strip()]
    return [(name, idx + 1) for idx, name in enumerate(authors)]


def parse_csv_row(row: Dict[str, str]) -> Dict[str, Any]:
    """
    Parse a single CSV row into database format.
    Store data EXACTLY as Retraction Watch provides it.
    Only conversions: dates (string→datetime), empty→NULL

    Args:
        row: Dictionary from csv.DictReader

    Returns:
        Dictionary ready for database insertion
    """
    return {
        'record_id': row['Record ID'].strip(),
        'title': row['Title'].strip(),
        'original_paper_doi': str_or_none(row.get('OriginalPaperDOI', '')),
        'original_paper_pubmed_id': str_or_none(row.get('OriginalPaperPubMedID', '')),
        'retraction_doi': str_or_none(row.get('RetractionDOI', '')),
        'retraction_pubmed_id': str_or_none(row.get('RetractionPubMedID', '')),
        'retraction_nature': str_or_none(row.get('RetractionNature', '')) or 'Unknown',
        'retraction_date': parse_date(row.get('RetractionDate', '')),
        'original_paper_date': parse_date(row.get('OriginalPaperDate', '')),
        'journal': str_or_none(row.get('Journal', '')),
        'publisher': str_or_none(row.get('Publisher', '')),
        'country': str_or_none(row.get('Country', '')),
        'institution': str_or_none(row.get('Institution', '')),
        'subject': str_or_none(row.get('Subject', '')),
        'article_type': str_or_none(row.get('ArticleType', '')),
        'reason': str_or_none(row.get('Reason', '')),
        'notes': str_or_none(row.get('Notes', '')),
        'urls': str_or_none(row.get('URLS', '')),
        'paywalled': str_or_none(row.get('Paywalled', '')),
        'authors_fulltext': str_or_none(row.get('Author', '')),
    }


async def truncate_tables(engine):
    """Truncate existing tables to start fresh."""
    logger.info("Truncating existing tables...")

    async with engine.begin() as conn:
        await conn.execute(text("TRUNCATE TABLE retraction_authors CASCADE"))
        await conn.execute(text("TRUNCATE TABLE retractions CASCADE"))

    logger.info("✓ Tables truncated")


async def bulk_insert_batch(
    session: AsyncSession,
    retraction_batch: List[Dict[str, Any]],
    author_batch: List[Dict[str, Any]]
):
    """
    Bulk insert a batch of retractions and authors.

    Args:
        session: Database session
        retraction_batch: List of retraction records
        author_batch: List of author records
    """
    if not retraction_batch:
        return

    # Insert retractions one by one to get IDs
    insert_retractions_sql = """
        INSERT INTO retractions (
            record_id, title, original_paper_doi, original_paper_pubmed_id,
            retraction_doi, retraction_pubmed_id, retraction_nature,
            retraction_date, original_paper_date, journal, publisher,
            country, institution, subject, article_type, reason, notes,
            urls, paywalled, authors_fulltext
        ) VALUES (
            :record_id, :title, :original_paper_doi, :original_paper_pubmed_id,
            :retraction_doi, :retraction_pubmed_id, :retraction_nature,
            :retraction_date, :original_paper_date, :journal, :publisher,
            :country, :institution, :subject, :article_type, :reason, :notes,
            :urls, :paywalled, :authors_fulltext
        )
        RETURNING id
    """

    # Execute inserts individually and collect IDs
    retraction_ids = []
    for retraction_record in retraction_batch:
        result = await session.execute(text(insert_retractions_sql), retraction_record)
        retraction_id = result.scalar_one()
        retraction_ids.append(retraction_id)

    # Map author records to retraction IDs
    if author_batch:
        # Update author records with actual retraction IDs
        for author_record in author_batch:
            batch_idx = author_record['retraction_batch_idx']
            author_record['retraction_id'] = retraction_ids[batch_idx]
            del author_record['retraction_batch_idx']

        # Insert authors
        insert_authors_sql = """
            INSERT INTO retraction_authors (retraction_id, author_name, author_position)
            VALUES (:retraction_id, :author_name, :author_position)
            ON CONFLICT (retraction_id, author_name) DO NOTHING
        """

        await session.execute(text(insert_authors_sql), author_batch)

    await session.commit()


async def load_csv_data(engine):
    """Load CSV data into database with batching."""
    logger.info(f"Loading CSV data from: {CSV_PATH}")

    if not os.path.exists(CSV_PATH):
        raise FileNotFoundError(f"CSV file not found: {CSV_PATH}")

    async_session = async_sessionmaker(engine, expire_on_commit=False)

    retraction_batch = []
    author_batch = []
    total_rows = 0
    total_authors = 0

    with open(CSV_PATH, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)

        async with async_session() as session:
            for row in reader:
                try:
                    # Parse retraction record
                    retraction_record = parse_csv_row(row)
                    retraction_batch.append(retraction_record)
                    batch_idx = len(retraction_batch) - 1

                    # Parse authors for this retraction
                    authors = parse_authors(row.get('Author', ''))
                    for author_name, position in authors:
                        author_batch.append({
                            'retraction_batch_idx': batch_idx,  # Temporary reference
                            'author_name': author_name,
                            'author_position': position
                        })
                        total_authors += 1

                    total_rows += 1

                    # Bulk insert in batches
                    if len(retraction_batch) >= BATCH_SIZE:
                        await bulk_insert_batch(session, retraction_batch, author_batch)
                        logger.info(f"Inserted batch: {total_rows} retractions, {total_authors} authors")
                        retraction_batch = []
                        author_batch = []

                except Exception as e:
                    logger.error(f"Error processing row {total_rows + 1}: {e}")
                    logger.error(f"Row data: {row}")
                    # Continue processing other rows
                    continue

            # Insert remaining records
            if retraction_batch:
                await bulk_insert_batch(session, retraction_batch, author_batch)

    logger.info(f"✓ Loaded {total_rows:,} retractions with {total_authors:,} author entries")


async def validate_migration(engine):
    """Validate the data load and report statistics."""
    logger.info("\n" + "="*60)
    logger.info("DATA LOAD VALIDATION")
    logger.info("="*60)

    async with engine.begin() as conn:
        # Count retractions
        result = await conn.execute(text("SELECT COUNT(*) FROM retractions"))
        retraction_count = result.scalar()
        logger.info(f"Total retractions: {retraction_count:,}")

        # Count authors
        result = await conn.execute(text("SELECT COUNT(*) FROM retraction_authors"))
        author_count = result.scalar()
        logger.info(f"Total author entries: {author_count:,}")

        # Count unique authors
        result = await conn.execute(text("SELECT COUNT(DISTINCT LOWER(author_name)) FROM retraction_authors"))
        unique_authors = result.scalar()
        logger.info(f"Unique authors (case-insensitive): {unique_authors:,}")

        # Retraction nature distribution
        logger.info("\nRetraction Nature Distribution:")
        result = await conn.execute(text("""
            SELECT retraction_nature, COUNT(*) as count
            FROM retractions
            GROUP BY retraction_nature
            ORDER BY count DESC
        """))
        for row in result.fetchall():
            logger.info(f"  {row[0]}: {row[1]:,}")

        # DOI coverage
        result = await conn.execute(text("""
            SELECT
                COUNT(*) as total,
                COUNT(original_paper_doi) as with_doi,
                COUNT(*) - COUNT(original_paper_doi) as without_doi
            FROM retractions
        """))
        row = result.fetchone()
        logger.info("\nDOI Coverage:")
        logger.info(f"  With DOI: {row[1]:,} ({row[1]/row[0]*100:.1f}%)")
        logger.info(f"  Without DOI: {row[2]:,} ({row[2]/row[0]*100:.1f}%)")

    logger.info("\n" + "="*60)
    logger.info("✓ DATA LOAD COMPLETED SUCCESSFULLY")
    logger.info("="*60)


async def main():
    """Main data loading function."""
    logger.info("Starting Retraction Watch data load...")
    logger.info(f"Database: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else DATABASE_URL}")
    logger.info(f"CSV file: {CSV_PATH}")

    # Create async engine
    engine = create_async_engine(DATABASE_URL, echo=False)

    try:
        # Step 1: Truncate existing data
        await truncate_tables(engine)

        # Step 2: Load CSV data
        await load_csv_data(engine)

        # Step 3: Validate data load
        await validate_migration(engine)

    except Exception as e:
        logger.error(f"Data load failed: {e}", exc_info=True)
        raise
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
