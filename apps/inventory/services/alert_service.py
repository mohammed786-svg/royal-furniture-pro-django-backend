from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from apps.inventory.repositories.inventory_repository import inventory_repository
from core.helpers.text import from_db_text


def _format_dt(value: Any) -> Optional[str]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


class AlertService:
    def _serialize(self, row: dict[str, Any]) -> dict[str, Any]:
        variant_id = row.get("product_variant_id")
        return {
            "id": str(row["inventory_id"]),
            "productId": str(row["product_id"]),
            "productName": from_db_text(row.get("product_name")) or "",
            "productSku": from_db_text(row.get("product_sku")) or "",
            "productVariantId": str(variant_id) if variant_id else None,
            "variantName": from_db_text(row.get("variant_name")),
            "variantSku": from_db_text(row.get("variant_sku")),
            "warehouseId": str(row["warehouse_id"]),
            "warehouseCode": from_db_text(row.get("warehouse_code")) or "",
            "warehouseName": from_db_text(row.get("warehouse_name")) or "",
            "availableStock": int(row.get("available_stock") or 0),
            "reorderLevel": int(row.get("reorder_level") or 0),
            "shortage": int(row.get("shortage") or 0),
        }

    def list_alerts(self, **kwargs) -> dict[str, Any]:
        page = kwargs.get("page", 1)
        page_size = kwargs.get("page_size", 20)
        warehouse_id = kwargs.get("warehouse_id")
        rows, total = inventory_repository.list_low_stock(
            page=page,
            page_size=page_size,
            warehouse_id=warehouse_id,
        )
        return {
            "items": [self._serialize(r) for r in rows],
            "pagination": {
                "page": page,
                "pageSize": page_size,
                "total": total,
                "totalPages": max(1, (total + page_size - 1) // page_size),
            },
        }


alert_service = AlertService()
