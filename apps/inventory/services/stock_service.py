from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from apps.inventory.repositories.inventory_repository import inventory_repository
from apps.inventory.repositories.warehouse_repository import warehouse_repository
from apps.products.repositories.product_repository import product_repository
from core.database import select_one
from core.exceptions.base import ConflictException, NotFoundException, ValidationException
from core.helpers.text import from_db_text


def _format_dt(value: Any) -> Optional[str]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _optional_int(value: Any) -> Optional[int]:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _base_list_params(kwargs: dict[str, Any]) -> dict[str, Any]:
    return {
        "page": kwargs.get("page", 1),
        "page_size": kwargs.get("page_size", 20),
        "search": kwargs.get("search", ""),
        "sort_by": kwargs.get("sort_by", "created_at"),
        "sort_dir": kwargs.get("sort_dir", "desc"),
    }


class StockService:
    schema = "royal"

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
            "reservedStock": int(row.get("reserved_stock") or 0),
            "soldStock": int(row.get("sold_stock") or 0),
            "damagedStock": int(row.get("damaged_stock") or 0),
            "returnedStock": int(row.get("returned_stock") or 0),
            "warehouseStock": int(row.get("warehouse_stock") or 0),
            "reorderLevel": int(row.get("reorder_level") or 0),
            "lastRestockedAt": _format_dt(row.get("last_restocked_at")),
            "isActive": bool(row.get("is_active")),
            "createdAt": _format_dt(row.get("created_at")),
            "updatedAt": _format_dt(row.get("updated_at")),
        }

    def _validate_variant(self, product_id: int, variant_id: Optional[int]) -> None:
        if variant_id is None:
            return
        sql = f"""
            SELECT product_variant_id
            FROM {self.schema}.product_varianttbl
            WHERE product_variant_id = %s
              AND product_id = %s
              AND is_deleted = FALSE
        """
        if not select_one(sql, [variant_id, product_id]):
            raise ValidationException(
                details=[{"field": "productVariantId", "message": "Product variant not found"}]
            )

    def list_stock(self, **kwargs) -> dict[str, Any]:
        params = _base_list_params(kwargs)
        if kwargs.get("warehouse_id") is not None:
            params["warehouse_id"] = kwargs["warehouse_id"]
        if kwargs.get("product_id") is not None:
            params["product_id"] = kwargs["product_id"]
        rows, total = inventory_repository.list_paginated(**params)
        page = params["page"]
        page_size = params["page_size"]
        return {
            "items": [self._serialize(r) for r in rows],
            "pagination": {
                "page": page,
                "pageSize": page_size,
                "total": total,
                "totalPages": max(1, (total + page_size - 1) // page_size),
            },
        }

    def get_stock(self, inventory_id: int) -> dict[str, Any]:
        row = inventory_repository.fetch_by_id(inventory_id)
        if not row:
            raise NotFoundException("Inventory record not found")
        return self._serialize(row)

    def create_stock(self, payload: dict[str, Any]) -> dict[str, Any]:
        product_id = _optional_int(payload.get("productId"))
        warehouse_id = _optional_int(payload.get("warehouseId"))
        variant_id = _optional_int(payload.get("productVariantId"))

        if not product_id:
            raise ValidationException(
                details=[{"field": "productId", "message": "Product is required"}]
            )
        if not warehouse_id:
            raise ValidationException(
                details=[{"field": "warehouseId", "message": "Warehouse is required"}]
            )
        if not product_repository.fetch_by_id(product_id):
            raise NotFoundException("Product not found")
        if not warehouse_repository.fetch_by_id(warehouse_id):
            raise NotFoundException("Warehouse not found")
        self._validate_variant(product_id, variant_id)

        if inventory_repository.combo_exists(
            product_id=product_id,
            warehouse_id=warehouse_id,
            product_variant_id=variant_id,
        ):
            raise ConflictException("Inventory record already exists for this product and warehouse")

        available = int(payload.get("availableStock") or 0)
        reserved = int(payload.get("reservedStock") or 0)
        sold = int(payload.get("soldStock") or 0)
        damaged = int(payload.get("damagedStock") or 0)
        returned = int(payload.get("returnedStock") or 0)
        warehouse_stock = int(payload.get("warehouseStock") or available)
        reorder_level = int(payload.get("reorderLevel") or 0)

        if available < 0 or warehouse_stock < 0:
            raise ValidationException(
                details=[{"field": "availableStock", "message": "Stock cannot be negative"}]
            )

        row = inventory_repository.create({
            "product_id": product_id,
            "product_variant_id": variant_id,
            "warehouse_id": warehouse_id,
            "available_stock": available,
            "reserved_stock": reserved,
            "sold_stock": sold,
            "damaged_stock": damaged,
            "returned_stock": returned,
            "warehouse_stock": warehouse_stock,
            "reorder_level": reorder_level,
            "is_active": bool(payload.get("isActive", True)),
        })
        from core.cache.product_cache import invalidate_product_cache_by_id

        invalidate_product_cache_by_id(product_id)
        return self._serialize(row)

    def update_stock(self, inventory_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        existing = inventory_repository.fetch_by_id(inventory_id)
        if not existing:
            raise NotFoundException("Inventory record not found")

        updates: dict[str, Any] = {}
        int_fields = (
            ("availableStock", "available_stock"),
            ("reservedStock", "reserved_stock"),
            ("soldStock", "sold_stock"),
            ("damagedStock", "damaged_stock"),
            ("returnedStock", "returned_stock"),
            ("warehouseStock", "warehouse_stock"),
            ("reorderLevel", "reorder_level"),
        )
        for api_key, db_key in int_fields:
            if api_key in payload:
                value = int(payload.get(api_key) or 0)
                if db_key in ("available_stock", "warehouse_stock") and value < 0:
                    raise ValidationException(
                        details=[{"field": api_key, "message": "Stock cannot be negative"}]
                    )
                updates[db_key] = value
        if "isActive" in payload:
            updates["is_active"] = bool(payload.get("isActive"))

        row = inventory_repository.update(inventory_id, updates)
        if not row:
            raise NotFoundException("Inventory record not found")
        from core.cache.product_cache import invalidate_product_cache_by_id

        invalidate_product_cache_by_id(int(existing["product_id"]))
        return self._serialize(row)

    def delete_stock(self, inventory_id: int) -> None:
        if not inventory_repository.soft_delete(inventory_id):
            raise NotFoundException("Inventory record not found")


stock_service = StockService()
