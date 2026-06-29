"""Admin dashboard WebSocket — order create/update notifications."""
from __future__ import annotations

import json
import logging

from channels.generic.websocket import AsyncWebsocketConsumer

from core.websocket.broadcast import ADMIN_ORDERS_GROUP

logger = logging.getLogger("websocket")


class AdminOrderConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.channel_layer.group_add(ADMIN_ORDERS_GROUP, self.channel_name)
        await self.accept()
        logger.info("Admin order WebSocket connected: %s", self.channel_name)

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(ADMIN_ORDERS_GROUP, self.channel_name)
        logger.info(
            "Admin order WebSocket disconnected: %s code=%s",
            self.channel_name,
            close_code,
        )

    async def order_event(self, event: dict):
        payload = event.get("payload") or {}
        await self.send(text_data=json.dumps({"event": "order.notification", "payload": payload}))
