"""
Base pytest configuration and fixtures for all tests.
"""

import asyncio
import os
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text
from dotenv import load_dotenv
from pathlib import Path
import time

from core.db.base import Base

# Load test environment from repo root to ensure correct path when running from src/
root_env = Path(__file__).resolve().parents[2] / ".env.test"
load_dotenv(root_env)

# Make unit fixtures available globally
pytest_plugins = [
    "tests.unit.fixtures.http_fixtures",
    "tests.unit.fixtures.service_fixtures",
    "tests.unit.fixtures.data_fixtures",
]


# ============= Event Loop Configuration =============
@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


# ============= Database Fixtures =============
@pytest_asyncio.fixture(scope="function")
async def test_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Create a test database session with automatic cleanup.
    Each test gets a fresh database state.
    """
    # Get test database URL from environment
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://test_user:test_password@localhost:5433/test_inspect_ai",
    )

    # Create engine
    engine = create_async_engine(
        database_url,
        echo=False,  # Set to True for SQL debugging
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
        # Drop all tables first for clean state
        await conn.run_sync(Base.metadata.drop_all)
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)

    # Create session factory
    async_session = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    # Provide session to test
    async with async_session() as session:
        yield session
        # Rollback any uncommitted changes
        await session.rollback()

    # Cleanup
    await engine.dispose()


# ============= Timing Fixture =============
class _TestTimer:
    def __init__(self):
        self._start = time.perf_counter()

    def assert_under_ms(self, max_ms: int, label: str = ""):
        elapsed_ms = (time.perf_counter() - self._start) * 1000.0
        assert (
            elapsed_ms <= max_ms
        ), f"{label or 'Operation'} took {elapsed_ms:.2f}ms which exceeds {max_ms}ms"


@pytest.fixture
def test_timer() -> _TestTimer:
    return _TestTimer()
