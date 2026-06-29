from django.urls import path

from apps.shiprocket.views import (
    ShipmentDetailView,
    ShipmentListCreateView,
    ShipmentTrackingDetailView,
    ShipmentTrackingListCreateView,
    ShiprocketOrderDetailView,
    ShiprocketOrdersListView,
    ShiprocketServiceabilityView,
    ShiprocketTrackView,
    ShiprocketWebhookView,
    ShippingOptionsView,
)

urlpatterns = [
    path("webhook/shiprocket/", ShiprocketWebhookView.as_view(), name="shiprocket-webhook"),
    path("shiprocket/orders/", ShiprocketOrdersListView.as_view(), name="shiprocket-orders"),
    path(
        "shiprocket/orders/<str:shiprocket_order_id>/",
        ShiprocketOrderDetailView.as_view(),
        name="shiprocket-order-detail",
    ),
    path("shiprocket/track/", ShiprocketTrackView.as_view(), name="shiprocket-track"),
    path(
        "shiprocket/serviceability/",
        ShiprocketServiceabilityView.as_view(),
        name="shiprocket-serviceability",
    ),
    path("meta-options/", ShippingOptionsView.as_view(), name="shipping-meta-options"),
    path("shipments/", ShipmentListCreateView.as_view(), name="shipment-list"),
    path("shipments/<int:shipment_id>/", ShipmentDetailView.as_view(), name="shipment-detail"),
    path("tracking/", ShipmentTrackingListCreateView.as_view(), name="shipment-tracking-list"),
    path(
        "tracking/<int:tracking_id>/",
        ShipmentTrackingDetailView.as_view(),
        name="shipment-tracking-detail",
    ),
]
