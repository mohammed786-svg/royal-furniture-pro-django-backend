from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from apps.orders.repositories.order_history_repository import order_history_repository
from apps.orders.repositories.order_repository import order_repository
from apps.orders.repositories.order_status_repository import order_status_repository
from apps.orders.services.order_service import order_service
from core.database.transaction import atomic
from core.exceptions.base import NotFoundException, ValidationException
from core.helpers.text import from_db_text, to_db_text


RETURN_STATUSES = ("RETURNED", "REFUNDED")


class ReturnService:
    def list_returns(self, **kwargs) -> dict[str, Any]:
        params = {
            "page": kwargs.get("page", 1),
            "page_size": kwargs.get("page_size", 20),
            "search": kwargs.get("search", ""),
            "sort_by": kwargs.get("sort_by", "created_at"),
            "sort_dir": kwargs.get("sort_dir", "desc"),
            "status_codes": list(RETURN_STATUSES),
        }
        if kwargs.get("customer_id") is not None:
            params["customer_id"] = kwargs["customer_id"]
        rows, total = order_repository.list_paginated(**params)
        page = params["page"]
        page_size = params["page_size"]
        return {
            "items": [order_service._serialize_summary(r) for r in rows],
            "pagination": {
                "page": page,
                "pageSize": page_size,
                "total": total,
                "totalPages": max(1, (total + page_size - 1) // page_size),
            },
        }

    def initiate_return(
        self,
        payload: dict[str, Any],
        *,
        changed_by: Optional[int] = None,
    ) -> dict[str, Any]:
        order_id = payload.get("orderId")
        if not order_id:
            raise ValidationException(
                details=[{"field": "orderId", "message": "Order is required"}]
            )
        order_id = int(order_id)
        order = order_repository.fetch_by_id(order_id)
        if not order:
            raise NotFoundException("Order not found")

        target_status = (payload.get("statusCode") or "RETURNED").strip().upper()
        if target_status not in RETURN_STATUSES:
            raise ValidationException(
                details=[{
                    "field": "statusCode",
                    "message": f"Status must be one of: {', '.join(RETURN_STATUSES)}",
                }]
            )

        status_row = order_status_repository.fetch_by_code(target_status)
        if not status_row:
            raise ValidationException(
                details=[{"field": "statusCode", "message": "Return status not configured"}]
            )

        from_status = from_db_text(order.get("current_status")) or "NA"
        change_reason = to_db_text(payload.get("reason") or payload.get("changeReason"))

        with atomic() as conn:
            order_repository.update(
                order_id,
                {
                    "order_status_id": int(status_row["order_status_id"]),
                    "current_status": target_status,
                },
                conn=conn,
            )
            order_history_repository.create({
                "order_id": order_id,
                "from_status": from_status,
                "to_status": target_status,
                "changed_by": changed_by,
                "change_reason": change_reason,
                "metadata": payload.get("metadata") or {},
                "changed_at": datetime.now(),
            }, conn=conn)

        return order_service.get_order(order_id)


return_service = ReturnService()
