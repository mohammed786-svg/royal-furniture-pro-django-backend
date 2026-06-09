"""Custom application exceptions."""
from __future__ import annotations

from typing import Any, Optional


class RoyalFurnitureException(Exception):
    status_code: int = 500
    default_message: str = "An unexpected error occurred"

    def __init__(self, message: Optional[str] = None, *, details: Any = None) -> None:
        self.message = message or self.default_message
        self.details = details
        super().__init__(self.message)


class ValidationException(RoyalFurnitureException):
    status_code = 400
    default_message = "Validation failed"


class AuthenticationException(RoyalFurnitureException):
    status_code = 401
    default_message = "Authentication required"


class AuthorizationException(RoyalFurnitureException):
    status_code = 403
    default_message = "Permission denied"


class NotFoundException(RoyalFurnitureException):
    status_code = 404
    default_message = "Resource not found"


class ConflictException(RoyalFurnitureException):
    status_code = 409
    default_message = "Resource conflict"


class DatabaseException(RoyalFurnitureException):
    status_code = 500
    default_message = "Database operation failed"


class RateLimitException(RoyalFurnitureException):
    status_code = 429
    default_message = "Too many requests"
