from django.urls import path

from apps.orders.views import (
    OrderDetailView,
    OrderInvoiceView,
    OrderListCreateView,
    OrderOptionsView,
    OrderStatusDetailView,
    OrderStatusListCreateView,
    OrderTrackingListCreateView,
    ReturnListCreateView,
)

urlpatterns = [
    path("options/", OrderOptionsView.as_view(), name="order-options"),
    path("orders/", OrderListCreateView.as_view(), name="order-list"),
    path("orders/<int:order_id>/", OrderDetailView.as_view(), name="order-detail"),
    path("orders/<int:order_id>/invoice/", OrderInvoiceView.as_view(), name="order-invoice"),
    path("status/", OrderStatusListCreateView.as_view(), name="order-status-list"),
    path("status/<int:order_status_id>/", OrderStatusDetailView.as_view(), name="order-status-detail"),
    path("tracking/", OrderTrackingListCreateView.as_view(), name="order-tracking-list"),
    path("returns/", ReturnListCreateView.as_view(), name="order-returns"),
]
