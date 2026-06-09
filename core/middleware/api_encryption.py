"""Encrypt API responses and decrypt API requests."""
from __future__ import annotations

import json
import logging
from typing import Callable

from django.conf import settings
from django.http import HttpRequest, HttpResponse, JsonResponse

from core.crypto.payload_crypto import decrypt_payload, encrypt_payload, get_crypto_key
from core.debug.api_logger import log_api_request, log_api_response

logger = logging.getLogger("api")

EXEMPT_PREFIXES = (
    "/admin/",
    "/static/",
    "/media/",
    "/health/",
)


class ApiEncryptionMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        should_process = self._should_process(request)

        if should_process:
            self._decrypt_request(request)

        response = self.get_response(request)

        if should_process:
            response = self._encrypt_response(request, response)

        return response

    def _should_process(self, request: HttpRequest) -> bool:
        if not getattr(settings, "API_ENCRYPTION_ENABLED", True):
            return False
        if get_crypto_key() is None:
            return False
        path = request.path
        if not path.startswith("/api/"):
            return False
        return not any(path.startswith(prefix) for prefix in EXEMPT_PREFIXES)

    def _decrypt_request(self, request: HttpRequest) -> None:
        if request.method not in ("POST", "PUT", "PATCH", "DELETE"):
            return
        if not request.body:
            return

        try:
            envelope = json.loads(request.body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return

        payload = envelope.get("payload") if isinstance(envelope, dict) else None
        if not payload:
            return

        try:
            decrypted = decrypt_payload(payload)
        except Exception:
            logger.warning("Failed to decrypt request payload for %s", request.path)
            return

        log_api_request(request.method, request.path, decrypted)

        new_body = json.dumps(decrypted).encode("utf-8")
        request._body = new_body
        request._stream = None
        request.META["CONTENT_LENGTH"] = str(len(new_body))

    def _encrypt_response(self, request: HttpRequest, response: HttpResponse) -> HttpResponse:
        content_type = response.get("Content-Type", "")
        if "application/json" not in content_type:
            return response

        try:
            body = json.loads(response.content.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError, AttributeError):
            return response

        if isinstance(body, dict) and "payload" in body and len(body) == 1:
            return response

        log_api_response(request.path, response.status_code, body)

        try:
            encrypted_payload = encrypt_payload(body)
        except Exception:
            logger.exception("Failed to encrypt response for %s", request.path)
            return response

        encrypted_body = {"payload": encrypted_payload}
        encrypted_response = JsonResponse(encrypted_body, status=response.status_code)

        for header, value in response.items():
            if header.lower() not in ("content-type", "content-length"):
                encrypted_response[header] = value

        encrypted_response["X-Payload-Encrypted"] = "1"
        return encrypted_response
