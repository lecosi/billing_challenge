from fastapi import Security, HTTPException, status, Request
from fastapi.security.api_key import APIKeyHeader
from typing import Optional
import os
import logging
import redis

logger = logging.getLogger(__name__)

RATE_LIMIT = 10  # max requests per IP per 60-second window
API_KEY_NAME = "X-API-Key"
API_KEY_SECRET = os.getenv("API_KEY_SECRET", "api-key-secret")
REDIS_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")

# auto_error=False so we can raise 401 ourselves instead of Starlette's default 403
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

# Single shared Redis connection — same instance used by Celery.
redis_client = redis.from_url(REDIS_URL, decode_responses=True)


def get_api_key(api_key: Optional[str] = Security(api_key_header)) -> str:
    """Validates the X-API-Key header. Returns 401 (not 403) on failure."""
    if api_key == API_KEY_SECRET:
        return api_key

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="API Key inválida o faltante",
    )


def rate_limiter(request: Request) -> None:
    """Sliding-window rate limiter backed by Redis.

    Allows RATE_LIMIT requests per IP per 60-second window.
    Uses a fallback key when request.client is None (e.g. ASGI test transport)
    so the limiter always executes and mocks work correctly in tests.
    Degrades gracefully when Redis is unavailable (fail-open).
    """
    client_ip = request.client.host if request.client else "testclient"
    redis_key = f"rate_limit:{client_ip}"

    try:
        count = redis_client.incr(redis_key)
        # Set TTL only on the first request to start the window.
        if count == 1:
            redis_client.expire(redis_key, 60)

        if count > RATE_LIMIT:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Try again later.",
            )
    except HTTPException:
        raise
    except redis.RedisError as exc:
        # Redis is down — degrade gracefully rather than blocking all traffic.
        logger.warning("Rate limiter unavailable (Redis error): %s", exc)