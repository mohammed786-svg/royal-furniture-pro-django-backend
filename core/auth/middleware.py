"""JWT authentication middleware shell."""
from __future__ import annotations

from typing import Callable

from django.http import HttpRequest, HttpResponse

from core.auth.jwt_handler import jwt_handler


class JWTAuthenticationMiddleware:
    """
    Attach authenticated user context from Bearer token.
    Implement user resolution via raw SQL when auth APIs are built.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        request.user_id = None
        request.user_role = None
        request.customer_id = None
        request.jwt_payload = None

        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()
            payload = jwt_handler.verify(token, token_type="access")
            if payload:
                request.jwt_payload = payload
                request.user_id = payload.get("user_id")
                request.user_role = payload.get("role")
                request.customer_id = payload.get("customer_id")

        return self.get_response(request)
