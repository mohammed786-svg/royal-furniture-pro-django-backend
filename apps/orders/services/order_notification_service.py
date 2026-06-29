from __future__ import annotations

import time
from datetime import datetime
from typing import Any, Optional

from apps.orders.repositories.order_repository import order_repository
from core.helpers.text import from_db_text
from core.websocket.broadcast import broadcast_admin_order_event

_DEDUPE_SECONDS = 3.0
_recent_broadcasts: dict[str, float] = {}


class OrderNotificationService:
    def notify(self, *, action: str, order_id: int, extra: Optional[dict[str, Any]] = None) -> None:
        dedupe_key = f"{order_id}:{action}"
        now = time.monotonic()
        last = _recent_broadcasts.get(dedupe_key)
        if last is not None and now - last < _DEDUPE_SECONDS:
            return
        _recent_broadcasts[dedupe_key] = now
        if len(_recent_broadcasts) > 500:
            cutoff = now - _DEDUPE_SECONDS
            stale = [k for k, ts in _recent_broadcasts.items() if ts < cutoff]
            for k in stale:
                del _recent_broadcasts[k]

        order = order_repository.fetch_by_id(order_id)
        if not order:
            return
        payload: dict[str, Any] = {
            "action": action,
            "orderId": str(order_id),
            "orderNumber": from_db_text(order.get("order_number")) or "",
            "status": from_db_text(order.get("current_status")) or "",
            "statusName": from_db_text(order.get("status_name")) or "",
            "totalAmount": float(order.get("total_amount") or 0),
            "customerName": from_db_text(order.get("customer_name")) or "",
            "timestamp": datetime.now().isoformat(),
        }
        if extra:
            payload.update(extra)
        broadcast_admin_order_event(payload)

    def notify_created(self, order_id: int) -> None:
        self.notify(action="created", order_id=order_id)

    def notify_updated(self, order_id: int, *, from_status: str = "", to_status: str = "") -> None:
        self.notify(
            action="updated",
            order_id=order_id,
            extra={"fromStatus": from_status, "toStatus": to_status},
        )

    def notify_cancelled(self, order_id: int) -> None:
        self.notify(action="cancelled", order_id=order_id)

    def notify_return(self, order_id: int, *, request_type: str = "RETURN") -> None:
        self.notify(action="return", order_id=order_id, extra={"requestType": request_type})

    def notify_awb_generated(self, order_id: int) -> None:
        self.notify(action="awb_generated", order_id=order_id)


order_notification_service = OrderNotificationService()
