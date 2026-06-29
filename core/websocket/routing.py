from django.urls import path

from core.websocket.consumers.admin_orders import AdminOrderConsumer
from core.websocket.consumers.base import BaseConsumer

websocket_urlpatterns = [
    path("ws/", BaseConsumer.as_asgi()),
    path("ws/admin/", AdminOrderConsumer.as_asgi()),
]
