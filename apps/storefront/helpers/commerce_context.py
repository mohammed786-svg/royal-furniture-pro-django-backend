"""Resolve guest session + authenticated customer from storefront requests."""
from __future__ import annotations

import re
import uuid

from django.http import HttpRequest

from core.helpers.text import from_db_text

GUEST_SESSION_HEADER = "HTTP_X_GUEST_SESSION"
GUEST_SESSION_COOKIE = "royal_guest_session"


def normalize_phone(phone: str) -> str:
    digits = re.sub(r"\D", "", phone or "")
    return digits[-10:] if len(digits) >= 10 else digits


def resolve_guest_session(request: HttpRequest) -> str:
    header = request.META.get(GUEST_SESSION_HEADER, "").strip()
    if header:
        return header[:128]
    cookie = request.COOKIES.get(GUEST_SESSION_COOKIE, "").strip()
    if cookie:
        return cookie[:128]
    return ""


def ensure_guest_session(request: HttpRequest) -> str:
    session = resolve_guest_session(request)
    if session:
        return session
    return str(uuid.uuid4())


def resolve_customer_id(request: HttpRequest) -> int | None:
    customer_id = getattr(request, "customer_id", None)
    if customer_id:
        try:
            return int(customer_id)
        except (TypeError, ValueError):
            return None
    payload = getattr(request, "jwt_payload", None) or {}
    raw = payload.get("customer_id")
    if raw in (None, ""):
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def require_customer_id(request: HttpRequest) -> int:
    from core.exceptions.base import AuthenticationException

    customer_id = resolve_customer_id(request)
    if not customer_id:
        raise AuthenticationException("Please sign in to continue")
    return customer_id


def require_customer_mobile(request: HttpRequest) -> int:
    from apps.customers.repositories.customer_repository import customer_repository
    from core.exceptions.base import ValidationException

    customer_id = require_customer_id(request)
    customer = customer_repository.fetch_by_id(customer_id)
    phone = from_db_text(customer.get("phone")) if customer else ""
    if len(normalize_phone(phone)) != 10:
        raise ValidationException(
            details=[
                {
                    "field": "mobile",
                    "message": "Add your mobile number in profile to continue shopping",
                }
            ]
        )
    return customer_id
