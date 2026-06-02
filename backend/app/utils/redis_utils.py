"""Shared Redis utilities for batch task progress tracking."""
import json
import redis as _redis_lib
from backend.app.config import settings

_redis_client = None


def _get_redis():
    global _redis_client
    if _redis_client is None:
        _redis_client = _redis_lib.from_url(settings.REDIS_URL)
    return _redis_client


def redis_set(key: str, value: dict, ttl: int = 7 * 86400):
    r = _get_redis()
    r.set(key, json.dumps(value), ex=ttl)


def redis_get(key: str) -> dict | None:
    r = _get_redis()
    raw = r.get(key)
    if raw is None:
        return None
    return json.loads(raw)
