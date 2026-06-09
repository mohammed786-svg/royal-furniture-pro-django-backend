"""Base WebSocket consumer — no business logic yet."""
import logging

from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger("websocket")


class BaseConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        logger.info("WebSocket connected: %s", self.channel_name)

    async def disconnect(self, close_code):
        logger.info("WebSocket disconnected: %s code=%s", self.channel_name, close_code)

    async def receive(self, text_data=None, bytes_data=None):
        pass
