import asyncio
import logging
import os
from logging.config import fileConfig
from urllib.parse import urlparse

from alembic import context
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import AsyncEngine

from dotenv import load_dotenv

from core.db.base import Base

# Import all models to register them with metadata
import core.db.models  # noqa
from core.config import settings

DOTENV_PATH = os.path.join(os.path.dirname(__file__), "..", ".env")
ROOT_DOTENV_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", ".env"
)  # Path to root/.env

logger = logging.getLogger("alembic.env")

if os.path.exists(ROOT_DOTENV_PATH):
    load_dotenv(dotenv_path=ROOT_DOTENV_PATH, override=True)
    logger.info(f"Loaded .env from {ROOT_DOTENV_PATH}")
elif os.path.exists(DOTENV_PATH):
    load_dotenv(dotenv_path=DOTENV_PATH, override=True)
    logger.info(f"Loaded .env from {DOTENV_PATH}")
else:
    logger.warning(f".env file not found at {ROOT_DOTENV_PATH} or {DOTENV_PATH}")

config = context.config

db_url = str(settings.DATABASE_URL)
alembic_db_host = os.getenv("ALEMBIC_DB_HOST")
if alembic_db_host and "@postgres:" in db_url:
    parts = db_url.split("@postgres:")
    if len(parts) == 2:
        db_url = f"{parts[0]}@{alembic_db_host}:{parts[1]}"
        logger.info(f"Overriding DATABASE_URL host for Alembic. Using: {db_url}")

# Validate the database URL
try:
    parsed = urlparse(db_url)
    if not all([parsed.scheme, parsed.netloc]):
        raise ValueError(f"Invalid DATABASE_URL after override: {db_url}")
except Exception as e:
    logger.error(f"Invalid DATABASE_URL: {e}")
    raise

config.set_main_option("sqlalchemy.url", db_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL and not an Engine, though an Engine is acceptable here as well.
    By skipping the Engine creation we don't even need a DBAPI to be available.
    Calls to context.execute() here emit the given string to the script output.

    """
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode using async engine."""

    # Use configuration from alembic.ini (TODO:sqlalchemy.url should be set)
    connectable = AsyncEngine(
        engine_from_config(
            config.get_section(config.config_ini_section, {}),
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
            future=True,
        )
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
