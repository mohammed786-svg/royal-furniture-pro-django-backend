from django.urls import path

from apps.orders.views import (
    OrderActionsView,
    OrderAssignAwbView,
    OrderCancelView,
    OrderDetailView,
    OrderInvoiceView,
    OrderListCreateView,
    OrderOptionsView,
    OrderReasonOptionsView,
    OrderReturnExchangeView,
    OrderStatusDetailView,
    OrderStatusListCreateView,
    OrderTrackingListCreateView,
    ReturnListCreateView,
)

urlpatterns = [
    path("options/", OrderOptionsView.as_view(), name="order-options"),
    path("reason-options/", OrderReasonOptionsView.as_view(), name="order-reason-options"),
    path("orders/", OrderListCreateView.as_view(), name="order-list"),
    path("orders/<int:order_id>/", OrderDetailView.as_view(), name="order-detail"),
    path("orders/<int:order_id>/actions/", OrderActionsView.as_view(), name="order-actions"),
    path("orders/<int:order_id>/cancel/", OrderCancelView.as_view(), name="order-cancel"),
    path("orders/<int:order_id>/assign-awb/", OrderAssignAwbView.as_view(), name="order-assign-awb"),
    path(
        "orders/<int:order_id>/return-exchange/",
        OrderReturnExchangeView.as_view(),
        name="order-return-exchange",
    ),
    path("orders/<int:order_id>/invoice/", OrderInvoiceView.as_view(), name="order-invoice"),
    path("status/", OrderStatusListCreateView.as_view(), name="order-status-list"),
    path("status/<int:order_status_id>/", OrderStatusDetailView.as_view(), name="order-status-detail"),
    path("tracking/", OrderTrackingListCreateView.as_view(), name="order-tracking-list"),
    path("returns/", ReturnListCreateView.as_view(), name="order-returns"),
]
