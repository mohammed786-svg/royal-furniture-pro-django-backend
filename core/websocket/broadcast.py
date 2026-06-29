"""Broadcast real-time events to admin WebSocket clients."""
from __future__ import annotations

import json
import logging
from typing import Any

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

logger = logging.getLogger("websocket")

ADMIN_ORDERS_GROUP = "admin_orders"


def broadcast_admin_order_event(payload: dict[str, Any]) -> None:
    layer = get_channel_layer()
    if layer is None:
        logger.warning("Channel layer unavailable — order event not broadcast")
        return
    try:
        async_to_sync(layer.group_send)(
            ADMIN_ORDERS_GROUP,
            {
                "type": "order_event",
                "payload": payload,
            },
        )
    except Exception:
        logger.exception("Failed to broadcast admin order event")
