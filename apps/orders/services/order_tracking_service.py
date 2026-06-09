from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from apps.orders.repositories.order_repository import order_repository
from apps.orders.repositories.order_tracking_repository import order_tracking_repository
from core.exceptions.base import NotFoundException, ValidationException
from core.helpers.text import from_db_text, to_db_text


def _format_dt(value: Any) -> Optional[str]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _base_list_params(kwargs: dict[str, Any]) -> dict[str, Any]:
    return {
        "page": kwargs.get("page", 1),
        "page_size": kwargs.get("page_size", 20),
        "search": kwargs.get("search", ""),
        "sort_by": kwargs.get("sort_by", "tracked_at"),
        "sort_dir": kwargs.get("sort_dir", "desc"),
    }


class OrderTrackingService:
    def _serialize(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": str(row["order_tracking_id"]),
            "orderId": str(row["order_id"]),
            "orderNumber": from_db_text(row.get("order_number")),
            "customerName": from_db_text(row.get("customer_name")),
            "statusCode": from_db_text(row.get("status_code")) or "",
            "statusMessage": from_db_text(row.get("status_message")) or "",
            "location": from_db_text(row.get("location")),
            "trackedAt": _format_dt(row.get("tracked_at")),
            "isCustomerVisible": bool(row.get("is_customer_visible")),
            "createdAt": _format_dt(row.get("created_at")),
        }

    def list_tracking(self, **kwargs) -> dict[str, Any]:
        params = _base_list_params(kwargs)
        if kwargs.get("order_id") is not None:
            params["order_id"] = kwargs["order_id"]
        rows, total = order_tracking_repository.list_paginated(**params)
        page = params["page"]
        page_size = params["page_size"]
        return {
            "items": [self._serialize(r) for r in rows],
            "pagination": {
                "page": page,
                "pageSize": page_size,
                "total": total,
                "totalPages": max(1, (total + page_size - 1) // page_size),
            },
        }

    def add_tracking(self, payload: dict[str, Any]) -> dict[str, Any]:
        order_id = payload.get("orderId")
        if not order_id:
            raise ValidationException(
                details=[{"field": "orderId", "message": "Order is required"}]
            )
        order_id = int(order_id)
        if not order_repository.fetch_by_id(order_id):
            raise NotFoundException("Order not found")
        status_code = (payload.get("statusCode") or "").strip()
        if not status_code:
            raise ValidationException(
                details=[{"field": "statusCode", "message": "Status code is required"}]
            )
        row = order_tracking_repository.create({
            "order_id": order_id,
            "status_code": status_code,
            "status_message": to_db_text(payload.get("statusMessage") or status_code),
            "location": to_db_text(payload.get("location")),
            "tracked_at": payload.get("trackedAt") or datetime.now(),
            "is_customer_visible": bool(payload.get("isCustomerVisible", True)),
        })
        row["order_number"] = order_repository.fetch_by_id(order_id).get("order_number")
        return self._serialize(row)


order_tracking_service = OrderTrackingService()
