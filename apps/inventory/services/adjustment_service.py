from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from apps.inventory.repositories.inventory_log_repository import inventory_log_repository
from apps.inventory.repositories.inventory_repository import inventory_repository
from apps.inventory.repositories.stock_adjustment_repository import stock_adjustment_repository
from core.database.transaction import atomic
from core.exceptions.base import NotFoundException, ValidationException
from core.helpers.text import from_db_text, to_db_text


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


ADJUSTMENT_TYPES = {"INCREASE", "DECREASE", "DAMAGE", "RETURN", "CORRECTION"}
ADJUSTMENT_STATUSES = {"PENDING", "APPROVED", "REJECTED"}


class AdjustmentService:
    def _serialize(self, row: dict[str, Any]) -> dict[str, Any]:
        variant_id = row.get("product_variant_id")
        approved_by = row.get("approved_by")
        return {
            "id": str(row["stock_adjustment_id"]),
            "inventoryId": str(row["inventory_id"]),
            "warehouseId": str(row["warehouse_id"]),
            "warehouseCode": from_db_text(row.get("warehouse_code")) or "",
            "warehouseName": from_db_text(row.get("warehouse_name")) or "",
            "productId": str(row["product_id"]),
            "productName": from_db_text(row.get("product_name")) or "",
            "productSku": from_db_text(row.get("product_sku")) or "",
            "productVariantId": str(variant_id) if variant_id else None,
            "variantName": from_db_text(row.get("variant_name")),
            "variantSku": from_db_text(row.get("variant_sku")),
            "adjustmentType": from_db_text(row.get("adjustment_type")) or "",
            "quantity": int(row.get("quantity") or 0),
            "reason": from_db_text(row.get("reason")) or "",
            "approvedBy": str(approved_by) if approved_by else None,
            "status": from_db_text(row.get("status")) or "PENDING",
            "adjustedAt": _format_dt(row.get("adjusted_at")),
            "currentAvailableStock": int(row.get("available_stock") or 0),
            "createdAt": _format_dt(row.get("created_at")),
            "updatedAt": _format_dt(row.get("updated_at")),
        }

    def list_adjustments(self, **kwargs) -> dict[str, Any]:
        params = _base_list_params(kwargs)
        if kwargs.get("status"):
            params["status"] = kwargs["status"]
        if kwargs.get("warehouse_id") is not None:
            params["warehouse_id"] = kwargs["warehouse_id"]
        rows, total = stock_adjustment_repository.list_paginated(**params)
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

    def get_adjustment(self, adjustment_id: int) -> dict[str, Any]:
        row = stock_adjustment_repository.fetch_by_id(adjustment_id)
        if not row:
            raise NotFoundException("Stock adjustment not found")
        return self._serialize(row)

    def create_adjustment(self, payload: dict[str, Any]) -> dict[str, Any]:
        inventory_id = _optional_int(payload.get("inventoryId"))
        if not inventory_id:
            raise ValidationException(
                details=[{"field": "inventoryId", "message": "Inventory is required"}]
            )

        inventory = inventory_repository.fetch_by_id(inventory_id)
        if not inventory:
            raise NotFoundException("Inventory record not found")

        adjustment_type = (payload.get("adjustmentType") or "").strip().upper()
        if adjustment_type not in ADJUSTMENT_TYPES:
            raise ValidationException(
                details=[{
                    "field": "adjustmentType",
                    "message": f"Must be one of: {', '.join(sorted(ADJUSTMENT_TYPES))}",
                }]
            )

        quantity = int(payload.get("quantity") or 0)
        if quantity <= 0:
            raise ValidationException(
                details=[{"field": "quantity", "message": "Quantity must be greater than zero"}]
            )

        row = stock_adjustment_repository.create({
            "inventory_id": inventory_id,
            "warehouse_id": int(inventory["warehouse_id"]),
            "adjustment_type": adjustment_type,
            "quantity": quantity,
            "reason": to_db_text(payload.get("reason")),
            "status": "PENDING",
        })
        return self._serialize(row)

    def _apply_stock_change(
        self,
        inventory: dict[str, Any],
        adjustment_type: str,
        quantity: int,
    ) -> dict[str, int]:
        available = int(inventory.get("available_stock") or 0)
        warehouse_stock = int(inventory.get("warehouse_stock") or 0)
        damaged = int(inventory.get("damaged_stock") or 0)
        returned = int(inventory.get("returned_stock") or 0)

        if adjustment_type == "INCREASE":
            new_available = available + quantity
            new_warehouse = warehouse_stock + quantity
        elif adjustment_type == "DECREASE":
            new_available = available - quantity
            new_warehouse = warehouse_stock - quantity
            if new_available < 0:
                raise ValidationException(
                    details=[{"field": "quantity", "message": "Insufficient available stock"}]
                )
        elif adjustment_type == "DAMAGE":
            new_available = available - quantity
            new_warehouse = warehouse_stock
            new_damaged = damaged + quantity
            if new_available < 0:
                raise ValidationException(
                    details=[{"field": "quantity", "message": "Insufficient available stock"}]
                )
            return {
                "available_stock": new_available,
                "warehouse_stock": new_warehouse,
                "damaged_stock": new_damaged,
            }
        elif adjustment_type == "RETURN":
            new_available = available + quantity
            new_warehouse = warehouse_stock + quantity
            new_returned = returned + quantity
            return {
                "available_stock": new_available,
                "warehouse_stock": new_warehouse,
                "returned_stock": new_returned,
            }
        elif adjustment_type == "CORRECTION":
            new_available = quantity
            diff = quantity - available
            new_warehouse = warehouse_stock + diff
            if new_available < 0 or new_warehouse < 0:
                raise ValidationException(
                    details=[{"field": "quantity", "message": "Correction would result in negative stock"}]
                )
        else:
            raise ValidationException(
                details=[{"field": "adjustmentType", "message": "Unsupported adjustment type"}]
            )

        if new_available < 0 or new_warehouse < 0:
            raise ValidationException(
                details=[{"field": "quantity", "message": "Insufficient available stock"}]
            )

        return {
            "available_stock": new_available,
            "warehouse_stock": new_warehouse,
        }

    def _write_logs(
        self,
        *,
        inventory: dict[str, Any],
        adjustment_id: int,
        adjustment_type: str,
        quantity_before: int,
        quantity_after: int,
        quantity_changed: int,
        reason: str,
        performed_by: int,
        conn,
    ) -> None:
        inventory_id = int(inventory["inventory_id"])
        product_id = int(inventory["product_id"])
        warehouse_id = int(inventory["warehouse_id"])
        variant_id = inventory.get("product_variant_id")

        inventory_log_repository.insert_stock_log(
            {
                "inventory_id": inventory_id,
                "product_id": product_id,
                "warehouse_id": warehouse_id,
                "action_type": f"ADJUSTMENT_{adjustment_type}",
                "quantity_before": quantity_before,
                "quantity_after": quantity_after,
                "quantity_changed": quantity_changed,
                "reason": to_db_text(reason),
                "reference_type": "STOCK_ADJUSTMENT",
                "reference_id": adjustment_id,
                "performed_by": performed_by,
            },
            conn=conn,
        )
        inventory_log_repository.insert_inventory_transaction(
            {
                "inventory_id": inventory_id,
                "product_id": product_id,
                "product_variant_id": variant_id,
                "warehouse_id": warehouse_id,
                "transaction_type": f"ADJUSTMENT_{adjustment_type}",
                "quantity": abs(quantity_changed),
                "reference_type": "STOCK_ADJUSTMENT",
                "reference_id": adjustment_id,
                "notes": to_db_text(reason),
                "performed_by": performed_by,
            },
            conn=conn,
        )

    def update_adjustment(
        self,
        adjustment_id: int,
        payload: dict[str, Any],
        *,
        admin_id: int,
    ) -> dict[str, Any]:
        status = (payload.get("status") or "").strip().upper()
        if status not in {"APPROVED", "REJECTED"}:
            raise ValidationException(
                details=[{
                    "field": "status",
                    "message": "Status must be APPROVED or REJECTED",
                }]
            )

        with atomic() as conn:
            adjustment = stock_adjustment_repository.fetch_for_update(adjustment_id, conn=conn)
            if not adjustment:
                raise NotFoundException("Stock adjustment not found")

            current_status = (adjustment.get("status") or "").upper()
            if current_status != "PENDING":
                raise ValidationException(
                    details=[{"field": "status", "message": "Only pending adjustments can be updated"}]
                )

            if status == "REJECTED":
                row = stock_adjustment_repository.update(
                    adjustment_id,
                    {
                        "status": "REJECTED",
                        "approved_by": admin_id,
                        "adjusted_at": datetime.now(),
                    },
                    conn=conn,
                )
                return self._serialize(row or adjustment)

            inventory = inventory_repository.fetch_for_update(
                int(adjustment["inventory_id"]),
                conn=conn,
            )
            if not inventory:
                raise NotFoundException("Inventory record not found")

            adjustment_type = (adjustment.get("adjustment_type") or "").upper()
            quantity = int(adjustment.get("quantity") or 0)
            quantity_before = int(inventory.get("available_stock") or 0)

            stock_updates = self._apply_stock_change(inventory, adjustment_type, quantity)
            quantity_after = stock_updates["available_stock"]
            quantity_changed = quantity_after - quantity_before

            inventory_repository.update_stock_levels(
                int(inventory["inventory_id"]),
                stock_updates,
                conn=conn,
            )

            self._write_logs(
                inventory=inventory,
                adjustment_id=adjustment_id,
                adjustment_type=adjustment_type,
                quantity_before=quantity_before,
                quantity_after=quantity_after,
                quantity_changed=quantity_changed,
                reason=from_db_text(adjustment.get("reason")) or "",
                performed_by=admin_id,
                conn=conn,
            )

            row = stock_adjustment_repository.update(
                adjustment_id,
                {
                    "status": "APPROVED",
                    "approved_by": admin_id,
                    "adjusted_at": datetime.now(),
                },
                conn=conn,
            )

        refreshed = stock_adjustment_repository.fetch_by_id(adjustment_id)
        return self._serialize(refreshed or row or adjustment)


adjustment_service = AdjustmentService()
