"""Rate limiting middleware using SlowAPI."""
import logging
from slowapi import Limiter
from slowapi.util import get_remote_address

from core.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

# Initialize rate limiter with Redis backend
# Falls back to in-memory storage if Redis is unavailable
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=str(settings.REDIS_URL) if settings.REDIS_URL else None,
    default_limits=["60/minute"],  # 60 requests per minute per IP by default
    enabled=True,  # Can be toggled via environment variable if needed
)

logger.info(
    f"Rate limiter initialized with storage: "
    f"{'Redis' if settings.REDIS_URL else 'In-Memory'}"
)
