from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from apps.orders.repositories.order_repository import order_repository
from apps.shiprocket.repositories.shipment_repository import shipment_repository
from core.exceptions.base import NotFoundException, ValidationException
from core.helpers.text import from_db_text, to_db_text


def _format_dt(value: Any) -> Optional[str]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    if hasattr(value, "isoformat"):
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
        "sort_by": kwargs.get("sort_by", "created_at"),
        "sort_dir": kwargs.get("sort_dir", "desc"),
    }


class ShipmentService:
    def _serialize(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": str(row["shipment_id"]),
            "orderId": str(row["order_id"]),
            "orderNumber": from_db_text(row.get("order_number")) or "",
            "customerName": from_db_text(row.get("customer_name")) or "",
            "shiprocketOrderId": from_db_text(row.get("shiprocket_order_id")),
            "shipmentIdExternal": from_db_text(row.get("shipment_id_external")),
            "awbNumber": from_db_text(row.get("awb_number")),
            "courierName": from_db_text(row.get("courier_name")),
            "trackingNumber": from_db_text(row.get("tracking_number")),
            "pickupStatus": from_db_text(row.get("pickup_status")),
            "deliveryStatus": from_db_text(row.get("delivery_status")),
            "shippingLabelUrl": from_db_text(row.get("shipping_label_url")),
            "estimatedDeliveryDate": _format_dt(row.get("estimated_delivery_date")),
            "shippedAt": _format_dt(row.get("shipped_at")),
            "deliveredAt": _format_dt(row.get("delivered_at")),
            "rawResponse": row.get("raw_response") or {},
            "createdAt": _format_dt(row.get("created_at")),
            "updatedAt": _format_dt(row.get("updated_at")),
        }

    def list_shipments(self, **kwargs) -> dict[str, Any]:
        params = _base_list_params(kwargs)
        if kwargs.get("order_id") is not None:
            params["order_id"] = kwargs["order_id"]
        if kwargs.get("delivery_status"):
            params["delivery_status"] = kwargs["delivery_status"]
        rows, total = shipment_repository.list_paginated(**params)
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

    def get_shipment(self, shipment_id: int) -> dict[str, Any]:
        row = shipment_repository.fetch_by_id(shipment_id)
        if not row:
            raise NotFoundException("Shipment not found")
        return self._serialize(row)

    def create_shipment(self, payload: dict[str, Any]) -> dict[str, Any]:
        order_id = _optional_int(payload.get("orderId"))
        if not order_id:
            raise ValidationException(
                details=[{"field": "orderId", "message": "Order is required"}]
            )
        if not order_repository.fetch_by_id(order_id):
            raise NotFoundException("Order not found")

        row = shipment_repository.create({
            "order_id": order_id,
            "shiprocket_order_id": to_db_text(payload.get("shiprocketOrderId")),
            "shipment_id_external": to_db_text(payload.get("shipmentIdExternal")),
            "awb_number": to_db_text(payload.get("awbNumber")),
            "courier_name": to_db_text(payload.get("courierName")),
            "tracking_number": to_db_text(payload.get("trackingNumber")),
            "pickup_status": to_db_text(payload.get("pickupStatus")),
            "delivery_status": to_db_text(payload.get("deliveryStatus")),
            "shipping_label_url": to_db_text(payload.get("shippingLabelUrl")),
            "estimated_delivery_date": payload.get("estimatedDeliveryDate"),
            "shipped_at": payload.get("shippedAt"),
            "delivered_at": payload.get("deliveredAt"),
            "raw_response": payload.get("rawResponse") or {},
        })
        return self._serialize(row)

    def update_shipment(self, shipment_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        if not shipment_repository.fetch_by_id(shipment_id):
            raise NotFoundException("Shipment not found")

        field_map = {
            "shiprocketOrderId": "shiprocket_order_id",
            "shipmentIdExternal": "shipment_id_external",
            "awbNumber": "awb_number",
            "courierName": "courier_name",
            "trackingNumber": "tracking_number",
            "pickupStatus": "pickup_status",
            "deliveryStatus": "delivery_status",
            "shippingLabelUrl": "shipping_label_url",
            "estimatedDeliveryDate": "estimated_delivery_date",
            "shippedAt": "shipped_at",
            "deliveredAt": "delivered_at",
            "rawResponse": "raw_response",
        }
        text_fields = {
            "shiprocketOrderId", "shipmentIdExternal", "awbNumber", "courierName",
            "trackingNumber", "pickupStatus", "deliveryStatus", "shippingLabelUrl",
        }

        updates: dict[str, Any] = {}
        for api_key, db_key in field_map.items():
            if api_key in payload:
                value = payload.get(api_key)
                if api_key in text_fields:
                    updates[db_key] = to_db_text(value)
                else:
                    updates[db_key] = value

        row = shipment_repository.update(shipment_id, updates)
        if not row:
            raise NotFoundException("Shipment not found")
        return self._serialize(row)

    def delete_shipment(self, shipment_id: int) -> None:
        if not shipment_repository.soft_delete(shipment_id):
            raise NotFoundException("Shipment not found")


shipment_service = ShipmentService()
