from __future__ import annotations

from typing import Any, Optional

from apps.orders.repositories.order_repository import order_repository
from apps.orders.services.order_lifecycle_service import order_lifecycle_service
from core.exceptions.base import NotFoundException, ValidationException
from core.helpers.text import from_db_text


class StorefrontOrderActionsService:
    def _resolve_owned_order(
        self,
        *,
        customer_id: int,
        order_number: Optional[str] = None,
        order_id: Optional[Any] = None,
    ) -> tuple[int, dict[str, Any]]:
        parsed_id: Optional[int] = None
        if order_id not in (None, ""):
            try:
                parsed_id = int(order_id)
            except (TypeError, ValueError):
                raise ValidationException(
                    details=[{"field": "orderId", "message": "Invalid order id"}]
                )
        if parsed_id is not None:
            order = order_repository.fetch_by_id(parsed_id)
        else:
            order_number = (order_number or "").strip().upper()
            if not order_number:
                raise ValidationException(
                    details=[{"field": "orderNumber", "message": "Order ID is required"}]
                )
            order = order_repository.fetch_by_order_number(order_number)
        if not order or int(order["customer_id"]) != customer_id:
            raise NotFoundException("Order not found")
        return int(order["order_id"]), order

    def get_actions(
        self,
        customer_id: int,
        *,
        order_number: Optional[str] = None,
        order_id: Optional[int] = None,
    ) -> dict[str, Any]:
        oid, _ = self._resolve_owned_order(
            customer_id=customer_id,
            order_number=order_number,
            order_id=order_id,
        )
        return order_lifecycle_service.get_order_actions(oid, customer_id=customer_id)

    def cancel_order(
        self,
        customer_id: int,
        *,
        order_number: Optional[str] = None,
        order_id: Optional[int] = None,
        reason_code: str,
        reason_text: str = "",
    ) -> dict[str, Any]:
        oid, order = self._resolve_owned_order(
            customer_id=customer_id,
            order_number=order_number,
            order_id=order_id,
        )
        result = order_lifecycle_service.cancel_order(
            oid,
            reason_code=reason_code,
            reason_text=reason_text,
            customer_id=customer_id,
        )
        return {
            "order": {
                "orderId": str(oid),
                "orderNumber": from_db_text(order.get("order_number")) or "",
                "status": result.get("currentStatus") or "CANCELLED",
                "statusName": result.get("statusName") or "Cancelled",
            }
        }

    def return_or_exchange(
        self,
        customer_id: int,
        *,
        order_number: Optional[str] = None,
        order_id: Optional[int] = None,
        request_type: str,
        reason_code: str,
        reason_text: str = "",
    ) -> dict[str, Any]:
        oid, order = self._resolve_owned_order(
            customer_id=customer_id,
            order_number=order_number,
            order_id=order_id,
        )
        result = order_lifecycle_service.request_return_or_exchange(
            oid,
            request_type=request_type,
            reason_code=reason_code,
            reason_text=reason_text,
            customer_id=customer_id,
        )
        return {
            "order": {
                "orderId": str(oid),
                "orderNumber": from_db_text(order.get("order_number")) or "",
                "status": result.get("currentStatus") or "RETURNED",
                "statusName": result.get("statusName") or "Returned",
            }
        }


storefront_order_actions_service = StorefrontOrderActionsService()
