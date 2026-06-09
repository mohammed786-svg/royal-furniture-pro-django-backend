from django.urls import path

from apps.inventory.views import (
    AdjustmentDetailView,
    AdjustmentListCreateView,
    AlertListView,
    InventoryOptionsView,
    StockDetailView,
    StockListCreateView,
    TransferDetailView,
    TransferListCreateView,
    WarehouseDetailView,
    WarehouseListCreateView,
)

urlpatterns = [
    path("options/", InventoryOptionsView.as_view(), name="inventory-options"),
    path("warehouses/", WarehouseListCreateView.as_view(), name="warehouse-list"),
    path("warehouses/<int:warehouse_id>/", WarehouseDetailView.as_view(), name="warehouse-detail"),
    path("stock/", StockListCreateView.as_view(), name="stock-list"),
    path("stock/<int:inventory_id>/", StockDetailView.as_view(), name="stock-detail"),
    path("adjustments/", AdjustmentListCreateView.as_view(), name="adjustment-list"),
    path(
        "adjustments/<int:adjustment_id>/",
        AdjustmentDetailView.as_view(),
        name="adjustment-detail",
    ),
    path("transfers/", TransferListCreateView.as_view(), name="transfer-list"),
    path("transfers/<int:transfer_id>/", TransferDetailView.as_view(), name="transfer-detail"),
    path("alerts/", AlertListView.as_view(), name="inventory-alerts"),
]
