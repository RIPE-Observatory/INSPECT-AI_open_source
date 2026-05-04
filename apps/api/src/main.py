import os
import logfire
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from api.dependencies.auth import get_current_user, get_test_user
from api.v1.api import api_router as api_router_v1
from core.config import get_settings
from core.middleware.rate_limit import limiter

settings = get_settings()
logger = logging.getLogger(__name__)

logfire_token = os.getenv("LOGFIRE_TOKEN")
if logfire_token:
    logfire.configure(
        token=logfire_token,
        send_to_logfire=True,
        service_name=settings.PROJECT_NAME,
        console=logfire.ConsoleOptions(min_log_level="info"),
        # TODO: service_version="0.1.0"
    )
    logger.info("Logfire configured for FastAPI.")
else:
    logger.warning("LOGFIRE_TOKEN not found. Logfire will not be active for FastAPI.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    logger.info(f"Starting up {settings.PROJECT_NAME}")

    # Configure test authentication if enabled
    enable_test_auth = os.getenv("ENABLE_TEST_AUTH", "false").lower() == "true"
    if enable_test_auth:
        logger.warning("=" * 80)
        logger.warning("TEST AUTHENTICATION ENABLED - DO NOT USE IN PRODUCTION!")
        logger.warning("All API requests will bypass Clerk authentication")
        logger.warning("Set ENABLE_TEST_AUTH=false to disable")
        logger.warning("=" * 80)
        app.dependency_overrides[get_current_user] = get_test_user

    yield

    # Shutdown logic (if needed)
    logger.info(f"Shutting down {settings.PROJECT_NAME}")


app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)

# Configure rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]
logger.info("Rate limiting configured")

if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            str(origin).strip("/") for origin in settings.BACKEND_CORS_ORIGINS
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

if logfire_token:
    logger.info("Configuring selective Logfire instrumentations...")
    # NOTE: Database instrumentations (SQLAlchemy, psycopg) disabled to reduce query noise
    # Only instrumenting HTTP client and LLM calls for development

    # Keep HTTPX for external API debugging
    try:
        logfire.instrument_httpx(capture_headers=True)
    except Exception as e:
        logger.error(f"Failed to instrument HTTPX: {e}")

    logger.info("Logfire selective instrumentation completed (HTTP client only).")

app.include_router(api_router_v1, prefix=settings.API_V1_STR)


@app.get("/")
async def read_root():
    return {"message": f"Welcome to {settings.PROJECT_NAME}"}
