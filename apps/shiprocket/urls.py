from django.urls import path

from apps.shiprocket.views import (
    ShipmentDetailView,
    ShipmentListCreateView,
    ShipmentTrackingDetailView,
    ShipmentTrackingListCreateView,
    ShippingOptionsView,
)

urlpatterns = [
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
