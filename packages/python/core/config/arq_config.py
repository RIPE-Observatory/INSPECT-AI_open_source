import logging
import warnings
import os
from arq.connections import RedisSettings
from sqlalchemy import text
import logfire

from core.config import settings
# NEW: Import check registry for dynamic task loading
from core.config.check_registry import registry

logger = logging.getLogger(__name__)

worker_queue_name = os.environ.get("WORKER_QUEUE_NAME", "arq:queue")


def _logical_queue_name(raw: str) -> str:
    if raw in {"arq:queue", "default"}:
        return "default"
    if raw.startswith("arq:queue:"):
        return raw.split("arq:queue:", 1)[1]
    return raw


arq_redis_settings = RedisSettings(
    host=settings.REDIS_URL.host or "localhost",
    port=settings.REDIS_URL.port or 6379,
    password=settings.REDIS_URL.password,
    database=int(settings.REDIS_URL.path.lstrip("/"))
    if settings.REDIS_URL.path and settings.REDIS_URL.path.lstrip("/")
    else 0,
)

logger.info(
    "Loading ARQ tasks for profile '%s' (queue=%s, %s checks enabled)",
    registry.profile,
    worker_queue_name,
    registry.get_total_checks(),
)

queue_key = (
    worker_queue_name
    if worker_queue_name == "arq:queue:orchestrator"
    else _logical_queue_name(worker_queue_name)
)

ARQ_TASK_FUNCTIONS = registry.get_arq_task_functions_for_queue(queue_key)

if not ARQ_TASK_FUNCTIONS:
    logger.warning(
        "No ARQ functions registered for queue '%s' (logical=%s). Worker will idle until tasks are available.",
        worker_queue_name,
        queue_key,
    )
else:
    logger.info(
        "Registered %s ARQ task functions for queue '%s' (logical=%s)",
        len(ARQ_TASK_FUNCTIONS),
        worker_queue_name,
        queue_key,
    )

# Global engine reference for proper cleanup
_worker_db_engine = None


async def on_startup(ctx: dict) -> None:
    """Initialize database engine and Logfire for each ARQ worker on startup."""
    global _worker_db_engine

    # Attach a readable worker id (container hostname or env)
    worker_id = os.environ.get("HOSTNAME") or ctx.get("worker_id", "unknown_worker")
    ctx["worker_id"] = worker_id
    logger.info(f"ARQ Worker [{worker_id}]: on_startup hook executing.")

    # Initialize database connection pool
    logger.info(f"ARQ Worker [{worker_id}]: Initializing database connection pool")

    # Import here to ensure engine is created with proper environment variables
    from core.db.session import async_engine, AsyncSessionFactory

    # Store engine reference for proper cleanup
    _worker_db_engine = async_engine
    ctx["db_engine"] = _worker_db_engine

    # Warm up connection pool with 1 connection to verify connectivity
    try:
        async with AsyncSessionFactory() as session:
            result = await session.execute(text("SELECT 1"))
            result.scalar()
        logger.info(f"ARQ Worker [{worker_id}]: Database pool warmed up successfully")
    except Exception as e:
        logger.error(f"ARQ Worker [{worker_id}]: Failed to warm up database pool: {e}", exc_info=True)

    # Silence noisy third-party deprecations (LangChain instrumentation warnings)
    try:
        warnings.filterwarnings(
            "ignore",
            message=r".*Importing chat models from langchain is deprecated.*",
            category=Warning,
        )
    except Exception:
        # Best-effort; do not fail startup on warning config
        pass

    logfire_token = settings.LOGFIRE_TOKEN
    if logfire_token:
        logger.info(
            f"ARQ Worker [{worker_id}]: LOGFIRE_TOKEN found: {logfire_token[:5]}... (partially shown)"
        )
        try:
            logfire.configure(
                token=logfire_token,
                service_name="inspect-ai-worker",
                send_to_logfire=True,
            )
            logfire.instrument_pydantic()
            # FastAPI instrumentation not needed for ARQ workers
            logfire.instrument_sqlalchemy()
            logfire.instrument_psycopg()
            # ARQ instrumentation enabled via on_startup function
            logger.info(
                "Logfire configured for ARQ worker.",
            )
        except Exception as e:
            logger.error(
                f"ARQ Worker [{worker_id}]: Error configuring Logfire in on_startup: {e}",
                exc_info=True,
            )
    else:
        logger.warning(
            f"ARQ Worker [{worker_id}]: LOGFIRE_TOKEN not found in settings. Logfire will not be initialized via on_startup."
        )


async def on_shutdown(ctx: dict) -> None:
    """Gracefully close database connections on worker shutdown."""
    worker_id = ctx.get("worker_id", "unknown_worker")
    logger.info(f"ARQ Worker [{worker_id}]: Shutting down, closing database connections")

    engine = ctx.get("db_engine")
    if engine:
        try:
            await engine.dispose()
            logger.info(f"ARQ Worker [{worker_id}]: Database engine disposed successfully")
        except Exception as e:
            logger.error(f"ARQ Worker [{worker_id}]: Error disposing database engine: {e}", exc_info=True)
    else:
        logger.warning(f"ARQ Worker [{worker_id}]: No database engine found in context during shutdown")


# Worker settings class that ARQ can load.
class ArqWorkerSettings:
    functions = ARQ_TASK_FUNCTIONS
    redis_settings = arq_redis_settings
    # ARQ settings.
    job_timeout = int(os.environ.get("ARQ_JOB_TIMEOUT", "600"))  # 10 minutes default
    max_tries = 3  # retry attempts
    max_jobs = 2  # conservative default concurrency per worker
    health_check_interval = 60  # Standard health check interval (seconds)
    on_startup = on_startup
    on_shutdown = on_shutdown
