"""API request logging with IP tracking."""
from __future__ import annotations

import logging
import time
import uuid
from typing import Callable

from django.http import HttpRequest, HttpResponse

api_logger = logging.getLogger("api")


class RequestLoggingMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        request.request_id = str(uuid.uuid4())
        from core.helpers.ip import get_client_ip

        request.client_ip = get_client_ip(request)
        start = time.perf_counter()
        response = self.get_response(request)
        duration_ms = (time.perf_counter() - start) * 1000
        api_logger.info(
            "request_id=%s method=%s path=%s status=%s duration_ms=%.2f ip=%s",
            request.request_id,
            request.method,
            request.path,
            response.status_code,
            duration_ms,
            request.client_ip,
        )
        response["X-Request-ID"] = request.request_id
        return response

