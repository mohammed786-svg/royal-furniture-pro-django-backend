"""Cache manager — get/set/delete/invalidate patterns."""
from __future__ import annotations

import json
import logging
from typing import Any, Callable, Optional

from core.cache.redis_client import get_redis_client

logger = logging.getLogger("cache")


class CacheManager:
    def __init__(self, default_ttl: int = 3600) -> None:
        self.default_ttl = default_ttl
        self.client = get_redis_client()

    def get(self, key: str) -> Any:
        raw = self.client.get(key)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return raw

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        payload = json.dumps(value) if not isinstance(value, (str, bytes)) else value
        return bool(self.client.setex(key, ttl or self.default_ttl, payload))

    def delete(self, key: str) -> int:
        return int(self.client.delete(key))

    def delete_pattern(self, pattern: str) -> int:
        keys = list(self.client.scan_iter(match=pattern, count=500))
        if not keys:
            return 0
        return int(self.client.delete(*keys))

    def get_or_set(
        self,
        key: str,
        factory: Callable[[], Any],
        ttl: Optional[int] = None,
    ) -> Any:
        cached = self.get(key)
        if cached is not None:
            return cached
        value = factory()
        self.set(key, value, ttl=ttl)
        return value


cache_manager = CacheManager()
