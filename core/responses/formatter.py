"""Standard API response formatter."""
from __future__ import annotations

from typing import Any, Optional

from rest_framework.response import Response

from core.responses.error_normalizer import normalize_errors


class APIResponse:
    @staticmethod
    def _build(
        *,
        success: bool,
        status_code: int,
        message: str,
        data: Any = None,
        errors: Any = None,
        endpoint: str = "",
    ) -> dict[str, Any]:
        return {
            "success": success,
            "statusCode": status_code,
            "message": message,
            "data": data,
            "errors": normalize_errors(errors) if not success else None,
            "endpoint": endpoint,
        }

    @staticmethod
    def success(
        data: Any = None,
        message: str = "Success",
        status_code: int = 200,
        meta: Optional[dict[str, Any]] = None,
        endpoint: str = "",
    ) -> Response:
        body = APIResponse._build(
            success=True,
            status_code=status_code,
            message=message,
            data=data,
            endpoint=endpoint,
        )
        if meta:
            body["meta"] = meta
        return Response(body, status=status_code)

    @staticmethod
    def error(
        message: str = "Error",
        status_code: int = 400,
        errors: Any = None,
        endpoint: str = "",
    ) -> Response:
        body = APIResponse._build(
            success=False,
            status_code=status_code,
            message=message,
            data=None,
            errors=errors,
            endpoint=endpoint,
        )
        return Response(body, status=status_code)
