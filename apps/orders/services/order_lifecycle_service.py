from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from psycopg2.extras import Json

from apps.orders.constants.order_reasons import (
    AWB_ELIGIBLE_STATUSES,
    NON_CANCELLABLE_STATUSES,
    ORDER_REASON_OPTIONS,
    RETURN_ELIGIBLE_STATUSES,
    resolve_reason_text,
)
from apps.orders.repositories.order_repository import order_repository
from apps.orders.services.order_service import order_service
from apps.shiprocket.repositories.shipment_repository import shipment_repository
from apps.shiprocket.services.shiprocket_integration_service import shiprocket_integration_service
from core.exceptions.base import NotFoundException, ValidationException
from core.helpers.text import from_db_text, to_db_text
from core.integrations.shiprocket.client import ShiprocketError


def _status_code(order: dict[str, Any]) -> str:
    return (from_db_text(order.get("current_status")) or "").strip().upper()


def _has_valid_awb(shipment: Optional[dict[str, Any]]) -> bool:
    if not shipment:
        return False
    awb = from_db_text(shipment.get("awb_number")) or ""
    return bool(awb) and awb.upper() != "NA"


class OrderLifecycleService:
    def get_reason_options(self) -> dict[str, Any]:
        return {"reasons": ORDER_REASON_OPTIONS}

    def get_order_actions(self, order_id: int, *, customer_id: Optional[int] = None) -> dict[str, Any]:
        order = order_repository.fetch_by_id(order_id)
        if not order:
            raise NotFoundException("Order not found")
        if customer_id is not None and int(order["customer_id"]) != customer_id:
            raise NotFoundException("Order not found")

        status = _status_code(order)
        shipment = shipment_repository.fetch_by_order_id(order_id)
        has_awb = _has_valid_awb(shipment)
        has_shipment = shipment is not None

        return {
            "orderId": str(order_id),
            "orderNumber": from_db_text(order.get("order_number")) or "",
            "status": status,
            "canCancel": status not in NON_CANCELLABLE_STATUSES,
            "canGenerateAwb": status in AWB_ELIGIBLE_STATUSES and has_shipment and not has_awb,
            "canReturn": status in RETURN_ELIGIBLE_STATUSES,
            "canExchange": status in RETURN_ELIGIBLE_STATUSES,
            "hasAwb": has_awb,
            "reasons": ORDER_REASON_OPTIONS,
        }

    def _ensure_order_access(
        self,
        order_id: int,
        *,
        customer_id: Optional[int] = None,
    ) -> dict[str, Any]:
        order = order_repository.fetch_by_id(order_id)
        if not order:
            raise NotFoundException("Order not found")
        if customer_id is not None and int(order["customer_id"]) != customer_id:
            raise NotFoundException("Order not found")
        return order

    def cancel_order(
        self,
        order_id: int,
        *,
        reason_code: str,
        reason_text: str = "",
        customer_id: Optional[int] = None,
        changed_by: Optional[int] = None,
    ) -> dict[str, Any]:
        order = self._ensure_order_access(order_id, customer_id=customer_id)
        status = _status_code(order)
        if status in NON_CANCELLABLE_STATUSES:
            raise ValidationException(
                details=[{"field": "orderId", "message": "This order can no longer be cancelled"}]
            )

        reason = resolve_reason_text(reason_code=reason_code, reason_text=reason_text)

        try:
            shiprocket_integration_service.cancel_for_order(order_id)
        except ShiprocketError as exc:
            raise ValidationException(
                details=[{"field": "shiprocket", "message": str(exc)}]
            ) from exc

        return order_service.update_order(
            order_id,
            {
                "statusCode": "CANCELLED",
                "cancelReason": reason,
                "changeReason": reason,
                "metadata": {
                    "reasonCode": reason_code,
                    "source": "customer" if customer_id else "admin",
                },
            },
            changed_by=changed_by,
        )

    def generate_awb(
        self,
        order_id: int,
        *,
        courier_id: Optional[int] = None,
        customer_id: Optional[int] = None,
    ) -> dict[str, Any]:
        order = self._ensure_order_access(order_id, customer_id=customer_id)
        status = _status_code(order)
        if status not in AWB_ELIGIBLE_STATUSES:
            raise ValidationException(
                details=[{"field": "orderId", "message": "AWB cannot be generated for this order status"}]
            )

        shipment = shipment_repository.fetch_by_order_id(order_id)
        if not shipment:
            raise ValidationException(
                details=[{"field": "orderId", "message": "No Shiprocket shipment exists for this order"}]
            )
        if _has_valid_awb(shipment):
            raise ValidationException(
                details=[{"field": "orderId", "message": "AWB is already assigned"}]
            )

        try:
            shiprocket_integration_service.assign_awb_for_order(order_id, courier_id=courier_id)
        except ShiprocketError as exc:
            raise ValidationException(
                details=[{"field": "shiprocket", "message": str(exc)}]
            ) from exc

        from apps.orders.services.order_notification_service import order_notification_service

        order_notification_service.notify_awb_generated(order_id)
        return order_service.get_order(order_id)

    def request_return_or_exchange(
        self,
        order_id: int,
        *,
        request_type: str,
        reason_code: str,
        reason_text: str = "",
        customer_id: Optional[int] = None,
        changed_by: Optional[int] = None,
    ) -> dict[str, Any]:
        order = self._ensure_order_access(order_id, customer_id=customer_id)
        status = _status_code(order)
        if status not in RETURN_ELIGIBLE_STATUSES:
            raise ValidationException(
                details=[
                    {
                        "field": "orderId",
                        "message": "Return or exchange is only available after delivery",
                    }
                ]
            )

        normalized_type = (request_type or "RETURN").strip().upper()
        if normalized_type not in {"RETURN", "EXCHANGE"}:
            raise ValidationException(
                details=[{"field": "requestType", "message": "Request type must be RETURN or EXCHANGE"}]
            )

        reason = resolve_reason_text(reason_code=reason_code, reason_text=reason_text)
        shiprocket_meta: dict[str, Any] = {}
        try:
            shiprocket_meta = shiprocket_integration_service.create_return_for_order(
                order_id,
                request_type=normalized_type,
            )
        except ShiprocketError as exc:
            raise ValidationException(
                details=[{"field": "shiprocket", "message": str(exc)}]
            ) from exc

        from apps.orders.repositories.order_history_repository import order_history_repository
        from apps.orders.repositories.order_status_repository import order_status_repository
        from core.database.transaction import atomic

        status_row = order_status_repository.fetch_by_code("RETURNED")
        if not status_row:
            raise ValidationException(
                details=[{"field": "statusCode", "message": "Return status not configured"}]
            )

        from_status = status
        with atomic() as conn:
            order_repository.update(
                order_id,
                {
                    "order_status_id": int(status_row["order_status_id"]),
                    "current_status": "RETURNED",
                },
                conn=conn,
            )
            order_history_repository.create(
                {
                    "order_id": order_id,
                    "from_status": from_status,
                    "to_status": "RETURNED",
                    "changed_by": changed_by,
                    "change_reason": to_db_text(
                        f"{normalized_type.title()}: {reason}"
                    ),
                    "metadata": Json(
                        {
                            "requestType": normalized_type,
                            "reasonCode": reason_code,
                            "reason": reason,
                            "shiprocket": shiprocket_meta,
                            "source": "customer" if customer_id else "admin",
                        }
                    ),
                    "changed_at": datetime.now(),
                },
                conn=conn,
            )

        from apps.orders.services.order_notification_service import order_notification_service

        order_notification_service.notify_return(order_id, request_type=normalized_type)
        return order_service.get_order(order_id)


order_lifecycle_service = OrderLifecycleService()
