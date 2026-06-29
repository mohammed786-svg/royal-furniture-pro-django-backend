from __future__ import annotations

from typing import Any, Optional

from apps.customers.repositories.customer_repository import customer_repository
from apps.orders.repositories.order_item_repository import order_item_repository
from apps.orders.repositories.order_repository import order_repository
from apps.orders.services.invoice_service import invoice_service
from apps.orders.services.order_lifecycle_service import order_lifecycle_service
from apps.payments.repositories.payment_repository import payment_repository
from apps.shiprocket.services.shiprocket_integration_service import shiprocket_integration_service
from apps.storefront.helpers.commerce_context import normalize_phone
from core.exceptions.base import NotFoundException, ValidationException
from core.helpers.datetime_format import serialize_datetime as _format_dt
from core.helpers.text import from_db_text


def _phone_matches(order_phone: str, input_phone: str) -> bool:
    a = normalize_phone(order_phone or "")
    b = normalize_phone(input_phone or "")
    if not a or not b:
        return False
    return a == b


_PAID_PAYMENT_STATUSES = {"PAID", "VERIFIED"}
_PAID_ORDER_STATUSES = {
    "PAYMENT_VERIFIED",
    "CONFIRMED",
    "PROCESSING",
    "PACKED",
    "SHIPPED",
    "DELIVERED",
}
_INVOICE_BLOCKED_STATUSES = {"CANCELLED", "RETURNED", "REFUNDED"}


class StorefrontOrderTrackingService:
    def _order_status_code(self, order: dict[str, Any]) -> str:
        code = (
            from_db_text(order.get("status_code"))
            or from_db_text(order.get("current_status"))
            or ""
        ).strip().upper()
        if code:
            return code
        name = (from_db_text(order.get("status_name")) or "").strip().upper()
        return name.replace(" ", "_")

    def _invoice_available(self, order: dict[str, Any]) -> bool:
        status_code = self._order_status_code(order)
        if status_code in _INVOICE_BLOCKED_STATUSES:
            return False
        if status_code == "DELIVERED":
            return True

        order_id = int(order["order_id"])
        for payment in payment_repository.list_by_order(order_id):
            payment_status = (from_db_text(payment.get("payment_status")) or "").upper()
            if payment_status in _PAID_PAYMENT_STATUSES:
                return True

        return status_code in _PAID_ORDER_STATUSES

    def get_invoice(self, *, order_number: str, customer_id: int) -> dict[str, Any]:
        order_number = (order_number or "").strip().upper()
        if not order_number:
            raise ValidationException(
                details=[{"field": "orderNumber", "message": "Order ID is required"}]
            )

        order = order_repository.fetch_by_order_number(order_number)
        if not order or int(order["customer_id"]) != customer_id:
            raise NotFoundException("Order not found")

        if not self._invoice_available(order):
            raise ValidationException(
                details=[{
                    "field": "order",
                    "message": "Invoice is available after payment is verified or once the order is delivered",
                }]
            )

        return invoice_service.build_invoice(int(order["order_id"]))

    def list_customer_orders(self, customer_id: int, *, page: int = 1, page_size: int = 20) -> dict[str, Any]:
        rows, total = order_repository.list_paginated(
            page=page,
            page_size=page_size,
            customer_id=customer_id,
            sort_by="created_at",
            sort_dir="desc",
        )
        items = [self._serialize_order_summary(row) for row in rows]
        return {
            "items": items,
            "pagination": {
                "page": page,
                "pageSize": page_size,
                "total": total,
                "totalPages": max(1, (total + page_size - 1) // page_size),
            },
        }

    def track_order(
        self,
        *,
        order_number: str,
        mobile: str = "",
        customer_id: int | None = None,
    ) -> dict[str, Any]:
        order_number = (order_number or "").strip().upper()
        if not order_number:
            raise ValidationException(
                details=[{"field": "orderNumber", "message": "Order ID is required"}]
            )

        order = order_repository.fetch_by_order_number(order_number)
        if not order:
            raise NotFoundException("Order not found")

        if customer_id is not None:
            if int(order["customer_id"]) != customer_id:
                raise NotFoundException("Order not found")
        else:
            mobile_digits = normalize_phone(mobile or "")
            if len(mobile_digits) != 10:
                raise ValidationException(
                    details=[{"field": "mobile", "message": "Enter a valid 10-digit mobile number"}]
                )

            customer = customer_repository.fetch_by_id(int(order["customer_id"]))
            customer_phone = from_db_text((customer or {}).get("phone")) or ""
            shipping_phone = from_db_text(order.get("shipping_phone")) or ""
            if not (
                _phone_matches(customer_phone, mobile_digits)
                or _phone_matches(shipping_phone, mobile_digits)
            ):
                raise NotFoundException("Order not found")

        order_id = int(order["order_id"])
        live_tracking = shiprocket_integration_service.get_live_tracking_for_order(order_id)
        shipment = live_tracking.get("shipment")
        tracking_rows = live_tracking.get("events") or []

        items = order_item_repository.list_by_order(order_id)
        actions = None
        if customer_id is not None:
            actions = order_lifecycle_service.get_order_actions(order_id, customer_id=customer_id)

        return {
            "order": self._serialize_order_summary(order),
            "invoiceAvailable": self._invoice_available(order),
            "items": [
                {
                    "id": str(item["order_item_id"]),
                    "name": from_db_text(item.get("product_name")) or "",
                    "quantity": int(item.get("quantity") or 1),
                    "unitPrice": float(item.get("unit_price") or 0),
                    "lineTotal": float(item.get("line_total") or 0),
                    "sku": from_db_text(item.get("sku")) or "",
                }
                for item in items
            ],
            "shipment": shipment,
            "tracking": tracking_rows,
            "actions": actions,
        }

    def _serialize_order_summary(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "orderId": str(row["order_id"]),
            "orderNumber": from_db_text(row.get("order_number")) or "",
            "status": from_db_text(row.get("current_status")) or "",
            "statusName": from_db_text(row.get("status_name")) or "",
            "totalAmount": float(row.get("total_amount") or 0),
            "createdAt": _format_dt(row.get("created_at")),
            "paymentMethod": from_db_text(row.get("payment_method")) or "",
        }

    def _serialize_shipment(self, row: dict[str, Any]) -> dict[str, Any]:
        awb = from_db_text(row.get("awb_number")) or ""
        return {
            "id": str(row["shiprocket_order_id"]) if row.get("shiprocket_order_id") else None,
            "shiprocketOrderId": from_db_text(row.get("shiprocket_order_id")),
            "awbNumber": awb if awb.upper() != "NA" else "",
            "courierName": from_db_text(row.get("courier_name")) or "",
            "deliveryStatus": from_db_text(row.get("delivery_status")) or "",
            "trackingNumber": from_db_text(row.get("tracking_number")) or "",
            "estimatedDeliveryDate": _format_dt(row.get("estimated_delivery_date")),
        }

    def _serialize_tracking(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "statusCode": from_db_text(row.get("status_code")) or "",
            "statusMessage": from_db_text(row.get("status_message")) or "",
            "location": from_db_text(row.get("location")) or "",
            "trackedAt": _format_dt(row.get("tracked_at")),
            "source": from_db_text(row.get("source")) or "SHIPROCKET",
        }


storefront_order_tracking_service = StorefrontOrderTrackingService()
