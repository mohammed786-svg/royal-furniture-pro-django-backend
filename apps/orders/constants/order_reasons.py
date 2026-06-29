"""Shared cancellation / return reason options for storefront and admin."""
from __future__ import annotations

ORDER_REASON_OPTIONS: list[dict[str, str]] = [
    {"code": "CHANGED_MIND", "label": "Changed my mind"},
    {"code": "ORDERED_MISTAKE", "label": "Ordered by mistake"},
    {"code": "BETTER_PRICE", "label": "Found a better price elsewhere"},
    {"code": "SLOW_DELIVERY", "label": "Delivery taking too long"},
    {"code": "OTHER", "label": "Other"},
]

NON_CANCELLABLE_STATUSES = frozenset(
    {
        "CANCELLED",
        "SHIPPED",
        "IN_TRANSIT",
        "OUT_FOR_DELIVERY",
        "DELIVERED",
        "RETURNED",
        "REFUNDED",
    }
)

AWB_ELIGIBLE_STATUSES = frozenset(
    {
        "PENDING",
        "PAYMENT_PENDING",
        "PAYMENT_VERIFIED",
        "CONFIRMED",
        "PROCESSING",
        "PACKED",
    }
)

RETURN_ELIGIBLE_STATUSES = frozenset({"DELIVERED"})


def resolve_reason_text(*, reason_code: str, reason_text: str = "") -> str:
    from core.exceptions.base import ValidationException

    code = (reason_code or "").strip().upper()
    custom = (reason_text or "").strip()
    if code == "OTHER":
        if not custom:
            raise ValidationException(
                details=[{"field": "reasonText", "message": "Please describe your reason"}]
            )
        return custom
    for option in ORDER_REASON_OPTIONS:
        if option["code"] == code:
            return option["label"]
    if custom:
        return custom
    raise ValidationException(
        details=[{"field": "reasonCode", "message": "Select a valid reason"}]
    )
