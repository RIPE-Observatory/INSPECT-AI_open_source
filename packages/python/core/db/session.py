import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from typing import AsyncGenerator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from core.config import settings
from arq.connections import RedisSettings

# Determine application name for connection tracking
_app_name = os.environ.get("WORKER_QUEUE_NAME", "api").replace("arq:queue:", "")
_app_name = f"inspect-ai-{_app_name}" if _app_name else "inspect-ai-api"

# Asynchronous Database Setup
async_engine = create_async_engine(
    str(settings.DATABASE_URL),
    pool_pre_ping=True,
    echo=False,
    # Connection pool sizing: Increased for better concurrency
    # Formula: 4 services × (5 base + 5 overflow) = 40 max connections
    # Still under PostgreSQL max_connections=100
    pool_size=5,              # Base connections per service (orchestrator, default, grobid, api)
    max_overflow=5,           # Additional connections during burst load
    pool_recycle=1800,        # Recycle connections after 30 min to prevent stale connections
    pool_timeout=10,          # Fail fast (10s) instead of waiting full timeout
    pool_reset_on_return='rollback',  # Clean state on connection return
    connect_args={
        "server_settings": {
            "application_name": _app_name,  # Track connections by service in pg_stat_activity
            "statement_timeout": "25000",   # 25s query timeout (less than client 30s)
        }
    }
)
"""Async SQLAlchemy engine with optimized connection pooling."""

AsyncSessionFactory = async_sessionmaker(
    bind=async_engine, autoflush=False, expire_on_commit=False, class_=AsyncSession
)
"""Async SQLAlchemy session factory."""

# Synchronous Database Setup
sync_db_url = str(settings.DATABASE_URL).replace(
    "postgresql+asyncpg", "postgresql+psycopg"
)

sync_engine = create_engine(
    sync_db_url,
    pool_pre_ping=True,
    echo=False,
    pool_size=5,
    max_overflow=5,
    pool_recycle=1800,
    pool_timeout=10,
)
"""Sync SQLAlchemy engine."""

SyncSessionFactory = sessionmaker(
    bind=sync_engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)
"""Sync SQLAlchemy session factory."""


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency to provide an async database session."""
    async with AsyncSessionFactory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def get_redis_settings() -> RedisSettings:
    """FastAPI dependency to provide ARQ Redis settings."""
    if not settings.REDIS_URL:
        raise RuntimeError("REDIS_URL not configured in settings.")
    return RedisSettings.from_dsn(str(settings.REDIS_URL))
