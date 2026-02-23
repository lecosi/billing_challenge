from fastapi import Security, HTTPException, status, Request
from fastapi.security.api_key import APIKeyHeader
import os
import logging
import redis

logger = logging.getLogger(__name__)

RATE_LIMIT = 10
API_KEY_NAME = "X-API-Key"
API_KEY_SECRET = os.getenv("API_KEY_SECRET", "api-key-secret")
REDIS_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")

api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=True)

redis_client = redis.from_url(REDIS_URL, decode_responses=True)


def get_api_key(api_key: str = Security(api_key_header)) -> str:
    if api_key == API_KEY_SECRET:
        return api_key

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="API Key inválida o faltante",
    )


def rate_limiter(request: Request) -> None:
    """Sliding-window rate limiter backed by Redis.

    Allows RATE_LIMIT requests per IP per 60-second window.
    If Redis is unavailable the limiter degrades gracefully
    (logs a warning, lets the request through) so a Redis outage
    doesn't take the whole API down.
    """
    client_ip = request.client.host
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