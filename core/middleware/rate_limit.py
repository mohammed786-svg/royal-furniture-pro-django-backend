"""Simple Redis-backed rate limiting middleware."""
from __future__ import annotations

import time
from typing import Callable

from django.http import HttpRequest, HttpResponse, JsonResponse

from core.cache.redis_client import get_redis_client
from core.helpers.ip import get_client_ip


class RateLimitMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response
        self.limit = 120
        self.window = 60

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if request.path.startswith("/api/"):
            ip = get_client_ip(request)
            key = f"royal:ratelimit:ip:{ip}"
            client = get_redis_client()
            current = client.incr(key)
            if current == 1:
                client.expire(key, self.window)
            if current > self.limit:
                return JsonResponse(
                    {"success": False, "message": "Too many requests"},
                    status=429,
                )
        return self.get_response(request)
