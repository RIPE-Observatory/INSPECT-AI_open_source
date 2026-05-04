import asyncio
import logging
import os
from core.config.arq_config import ArqWorkerSettings

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """
    Run the ARQ worker using the Worker class directly to avoid asyncio.run conflicts.
    """
    try:
        from arq.worker import Worker

        queue_env = os.environ.get("WORKER_QUEUE_NAME")
        queue_name = queue_env or "arq:queue"

        logger.info("Starting ARQ worker process...")
        # Allow per-container override of max_jobs via env
        env_max_jobs = os.environ.get("WORKER_MAX_JOBS")
        max_jobs_cfg = (
            int(env_max_jobs) if env_max_jobs and env_max_jobs.isdigit() else ArqWorkerSettings.max_jobs
        )

        worker = Worker(
            functions=ArqWorkerSettings.functions,
            redis_settings=ArqWorkerSettings.redis_settings,
            on_startup=ArqWorkerSettings.on_startup, # type: ignore[reportOptionalMemberAccess]
            job_timeout=ArqWorkerSettings.job_timeout,
            max_tries=ArqWorkerSettings.max_tries,
            max_jobs=max_jobs_cfg,
            health_check_interval=ArqWorkerSettings.health_check_interval,
            queue_name=queue_name,
        )
        worker.run()

    except KeyboardInterrupt:
        logger.info("ARQ worker process interrupted by user.")
    except Exception as e:
        logger.error(f"ARQ worker process failed to start or run: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    if os.name == "nt":
        # Windows-specific event loop policy
        if hasattr(asyncio, "WindowsSelectorEventLoopPolicy"):
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    main()
