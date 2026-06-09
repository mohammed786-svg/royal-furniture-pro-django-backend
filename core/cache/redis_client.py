"""Redis client singleton."""
from __future__ import annotations

import logging
from typing import Optional

import redis
from django.conf import settings

logger = logging.getLogger("cache")

_client: Optional[redis.Redis] = None


def get_redis_client() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.Redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
            health_check_interval=30,
        )
        logger.info("Redis client initialized")
    return _client


def redis_health_check() -> bool:
    try:
        return bool(get_redis_client().ping())
    except Exception:
        logger.exception("Redis health check failed")
        return False
