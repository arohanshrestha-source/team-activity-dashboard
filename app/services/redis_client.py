"""
Optional Redis client for persistent response cache and conversation memory.
When REDIS_URL is set, the app uses Redis; otherwise in-memory storage is used.
"""
from typing import Optional

_redis_client = None


def get_redis():
    """Return a Redis client if REDIS_URL is configured, else None."""
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    try:
        from app.config import get_settings
        url = get_settings().redis_url
        if not url or not url.strip():
            return None
        import redis
        _redis_client = redis.from_url(url, decode_responses=True)
        _redis_client.ping()
        return _redis_client
    except Exception:
        return None
