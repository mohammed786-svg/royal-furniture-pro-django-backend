"""Global DRF exception handler."""
from __future__ import annotations

import logging

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import DatabaseError
from rest_framework import status
from rest_framework.views import exception_handler as drf_exception_handler

from core.exceptions.base import RoyalFurnitureException, ValidationException
from core.responses.formatter import APIResponse

logger = logging.getLogger("api")


def _endpoint_from_context(context: dict) -> str:
    request = context.get("request")
    return request.path if request else ""


def custom_exception_handler(exc, context):
    endpoint = _endpoint_from_context(context)

    if isinstance(exc, RoyalFurnitureException):
        return APIResponse.error(
            message=exc.message,
            status_code=exc.status_code,
            errors=exc.details,
            endpoint=endpoint,
        )

    if isinstance(exc, DjangoValidationError):
        return APIResponse.error(
            message="Validation failed",
            status_code=status.HTTP_400_BAD_REQUEST,
            errors=exc.message_dict if hasattr(exc, "message_dict") else exc.messages,
            endpoint=endpoint,
        )

    if isinstance(exc, DatabaseError):
        logger.exception("Database error")
        return APIResponse.error(
            message="Database error",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            endpoint=endpoint,
        )

    response = drf_exception_handler(exc, context)
    if response is not None:
        return APIResponse.error(
            message=str(exc),
            status_code=response.status_code,
            errors=response.data,
            endpoint=endpoint,
        )

    logger.exception("Unhandled exception")
    return APIResponse.error(
        message="Internal server error",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        endpoint=endpoint,
    )
