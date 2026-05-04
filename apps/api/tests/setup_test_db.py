#!/usr/bin/env python
"""
Test database setup script.
Initializes the test database with proper schema and extensions.
"""

import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from core.db.base import Base

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load test environment
test_env_path = Path(__file__).parent.parent.parent / ".env.test"
if test_env_path.exists():
    load_dotenv(test_env_path, override=True)


async def setup_test_database():
    """Setup test database with all tables and extensions."""
    database_url = os.getenv(
        "TEST_DATABASE_URL",
        "postgresql+asyncpg://test_user:test_password@localhost:5433/test_inspect_ai",
    )

    print(f"Setting up test database: {database_url}")

    # Create engine
    engine = create_async_engine(database_url, echo=False)

    try:
        async with engine.begin() as conn:
            print("Ensuring pg_trgm extension...")
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))

            # Drop all existing tables
            print("Dropping existing tables...")
            await conn.run_sync(Base.metadata.drop_all)

            # Create all tables
            print("Creating tables...")
            await conn.run_sync(Base.metadata.create_all)

            # Verify tables were created
            result = await conn.execute(
                text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)
            )
            tables = result.fetchall()

            print(f"\nCreated {len(tables)} tables:")
            for table in tables:
                print(f"  - {table[0]}")

            print("\nTest database setup complete!")

    except Exception as e:
        print(f"Error setting up test database: {e}")
        raise
    finally:
        await engine.dispose()


async def verify_database_connection():
    """Verify the database connection and configuration."""
    database_url = os.getenv(
        "TEST_DATABASE_URL",
        "postgresql+asyncpg://test_user:test_password@localhost:5433/test_inspect_ai",
    )

    print(f"Verifying connection to: {database_url}")

    engine = create_async_engine(database_url, echo=False)

    try:
        async with engine.begin() as conn:
            # Test basic connection
            result = await conn.execute(text("SELECT 1"))
            result.fetchone()
            print("Database connection successful")

    except Exception as e:
        print(f"Database connection failed: {e}")
        raise
    finally:
        await engine.dispose()


async def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Test database setup utility")
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Only verify connection without creating tables",
    )
    parser.add_argument(
        "--drop-only", action="store_true", help="Only drop tables without recreating"
    )

    args = parser.parse_args()

    if args.verify_only:
        await verify_database_connection()
    elif args.drop_only:
        database_url = os.getenv(
            "TEST_DATABASE_URL",
            "postgresql+asyncpg://test_user:test_password@localhost:5433/test_inspect_ai",
        )
        engine = create_async_engine(database_url, echo=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            print("All tables dropped")
        await engine.dispose()
    else:
        await verify_database_connection()
        await setup_test_database()


if __name__ == "__main__":
    asyncio.run(main())
