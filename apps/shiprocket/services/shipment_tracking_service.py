from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from apps.orders.repositories.order_repository import order_repository
from apps.shiprocket.repositories.shipment_repository import shipment_repository
from apps.shiprocket.repositories.shipment_tracking_repository import (
    shipment_tracking_repository,
)
from core.exceptions.base import NotFoundException, ValidationException
from core.helpers.text import from_db_text, to_db_text


def _format_dt(value: Any) -> Optional[str]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _optional_int(value: Any) -> Optional[int]:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _base_list_params(kwargs: dict[str, Any]) -> dict[str, Any]:
    return {
        "page": kwargs.get("page", 1),
        "page_size": kwargs.get("page_size", 20),
        "search": kwargs.get("search", ""),
        "sort_by": kwargs.get("sort_by", "tracked_at"),
        "sort_dir": kwargs.get("sort_dir", "desc"),
    }


class ShipmentTrackingService:
    def _serialize(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": str(row["shipment_tracking_id"]),
            "shipmentId": str(row["shipment_id"]),
            "orderId": str(row["order_id"]),
            "orderNumber": from_db_text(row.get("order_number")) or "",
            "customerName": from_db_text(row.get("customer_name")) or "",
            "awbNumber": from_db_text(row.get("awb_number")),
            "statusCode": from_db_text(row.get("status_code")) or "",
            "statusMessage": from_db_text(row.get("status_message")) or "",
            "location": from_db_text(row.get("location")),
            "trackedAt": _format_dt(row.get("tracked_at")),
            "source": from_db_text(row.get("source")) or "SHIPROCKET",
            "rawPayload": row.get("raw_payload") or {},
            "createdAt": _format_dt(row.get("created_at")),
            "updatedAt": _format_dt(row.get("updated_at")),
        }

    def list_tracking(self, **kwargs) -> dict[str, Any]:
        params = _base_list_params(kwargs)
        if kwargs.get("shipment_id") is not None:
            params["shipment_id"] = kwargs["shipment_id"]
        if kwargs.get("order_id") is not None:
            params["order_id"] = kwargs["order_id"]
        rows, total = shipment_tracking_repository.list_paginated(**params)
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

    def get_tracking(self, tracking_id: int) -> dict[str, Any]:
        row = shipment_tracking_repository.fetch_by_id(tracking_id)
        if not row:
            raise NotFoundException("Shipment tracking record not found")
        return self._serialize(row)

    def create_tracking(self, payload: dict[str, Any]) -> dict[str, Any]:
        shipment_id = _optional_int(payload.get("shipmentId"))
        order_id = _optional_int(payload.get("orderId"))
        if not shipment_id:
            raise ValidationException(
                details=[{"field": "shipmentId", "message": "Shipment is required"}]
            )

        shipment = shipment_repository.fetch_by_id(shipment_id)
        if not shipment:
            raise NotFoundException("Shipment not found")

        if not order_id:
            order_id = int(shipment["order_id"])
        elif order_id != int(shipment["order_id"]):
            raise ValidationException(
                details=[{"field": "orderId", "message": "Order does not match shipment"}]
            )

        if not order_repository.fetch_by_id(order_id):
            raise NotFoundException("Order not found")

        row = shipment_tracking_repository.create({
            "shipment_id": shipment_id,
            "order_id": order_id,
            "status_code": to_db_text(payload.get("statusCode")),
            "status_message": to_db_text(payload.get("statusMessage")),
            "location": to_db_text(payload.get("location")),
            "tracked_at": payload.get("trackedAt") or datetime.now(),
            "source": to_db_text(payload.get("source") or "SHIPROCKET"),
            "raw_payload": payload.get("rawPayload") or {},
        })
        return self._serialize(row)

    def update_tracking(self, tracking_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        if not shipment_tracking_repository.fetch_by_id(tracking_id):
            raise NotFoundException("Shipment tracking record not found")

        field_map = {
            "statusCode": "status_code",
            "statusMessage": "status_message",
            "location": "location",
            "trackedAt": "tracked_at",
            "source": "source",
            "rawPayload": "raw_payload",
        }
        text_fields = {"statusCode", "statusMessage", "location", "source"}

        updates: dict[str, Any] = {}
        for api_key, db_key in field_map.items():
            if api_key in payload:
                value = payload.get(api_key)
                if api_key in text_fields:
                    updates[db_key] = to_db_text(value)
                else:
                    updates[db_key] = value

        row = shipment_tracking_repository.update(tracking_id, updates)
        if not row:
            raise NotFoundException("Shipment tracking record not found")
        return self._serialize(row)

    def delete_tracking(self, tracking_id: int) -> None:
        if not shipment_tracking_repository.soft_delete(tracking_id):
            raise NotFoundException("Shipment tracking record not found")


shipment_tracking_service = ShipmentTrackingService()
