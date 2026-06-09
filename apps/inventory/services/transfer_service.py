from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from apps.inventory.repositories.inventory_log_repository import inventory_log_repository
from apps.inventory.repositories.inventory_repository import inventory_repository
from apps.inventory.repositories.stock_transfer_repository import stock_transfer_repository
from apps.inventory.repositories.warehouse_repository import warehouse_repository
from apps.products.repositories.product_repository import product_repository
from core.database import select_one
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


TRANSFER_STATUSES = {"PENDING", "IN_TRANSIT", "COMPLETED", "CANCELLED"}


class TransferService:
    schema = "royal"

    def _serialize(self, row: dict[str, Any]) -> dict[str, Any]:
        variant_id = row.get("product_variant_id")
        initiated_by = row.get("initiated_by")
        return {
            "id": str(row["stock_transfer_id"]),
            "productId": str(row["product_id"]),
            "productName": from_db_text(row.get("product_name")) or "",
            "productSku": from_db_text(row.get("product_sku")) or "",
            "productVariantId": str(variant_id) if variant_id else None,
            "variantName": from_db_text(row.get("variant_name")),
            "variantSku": from_db_text(row.get("variant_sku")),
            "fromWarehouseId": str(row["from_warehouse_id"]),
            "fromWarehouseCode": from_db_text(row.get("from_warehouse_code")) or "",
            "fromWarehouseName": from_db_text(row.get("from_warehouse_name")) or "",
            "toWarehouseId": str(row["to_warehouse_id"]),
            "toWarehouseCode": from_db_text(row.get("to_warehouse_code")) or "",
            "toWarehouseName": from_db_text(row.get("to_warehouse_name")) or "",
            "quantity": int(row.get("quantity") or 0),
            "status": from_db_text(row.get("status")) or "PENDING",
            "initiatedBy": str(initiated_by) if initiated_by else None,
            "completedAt": _format_dt(row.get("completed_at")),
            "notes": from_db_text(row.get("notes")) or "",
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

    def list_transfers(self, **kwargs) -> dict[str, Any]:
        params = _base_list_params(kwargs)
        if kwargs.get("status"):
            params["status"] = kwargs["status"]
        if kwargs.get("from_warehouse_id") is not None:
            params["from_warehouse_id"] = kwargs["from_warehouse_id"]
        if kwargs.get("to_warehouse_id") is not None:
            params["to_warehouse_id"] = kwargs["to_warehouse_id"]
        rows, total = stock_transfer_repository.list_paginated(**params)
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

    def get_transfer(self, transfer_id: int) -> dict[str, Any]:
        row = stock_transfer_repository.fetch_by_id(transfer_id)
        if not row:
            raise NotFoundException("Stock transfer not found")
        return self._serialize(row)

    def create_transfer(self, payload: dict[str, Any], *, admin_id: int) -> dict[str, Any]:
        product_id = _optional_int(payload.get("productId"))
        variant_id = _optional_int(payload.get("productVariantId"))
        from_warehouse_id = _optional_int(payload.get("fromWarehouseId"))
        to_warehouse_id = _optional_int(payload.get("toWarehouseId"))
        quantity = int(payload.get("quantity") or 0)

        if not product_id:
            raise ValidationException(
                details=[{"field": "productId", "message": "Product is required"}]
            )
        if not from_warehouse_id:
            raise ValidationException(
                details=[{"field": "fromWarehouseId", "message": "Source warehouse is required"}]
            )
        if not to_warehouse_id:
            raise ValidationException(
                details=[{"field": "toWarehouseId", "message": "Destination warehouse is required"}]
            )
        if from_warehouse_id == to_warehouse_id:
            raise ValidationException(
                details=[{"field": "toWarehouseId", "message": "Source and destination must differ"}]
            )
        if quantity <= 0:
            raise ValidationException(
                details=[{"field": "quantity", "message": "Quantity must be greater than zero"}]
            )

        if not product_repository.fetch_by_id(product_id):
            raise NotFoundException("Product not found")
        self._validate_variant(product_id, variant_id)
        if not warehouse_repository.fetch_by_id(from_warehouse_id):
            raise NotFoundException("Source warehouse not found")
        if not warehouse_repository.fetch_by_id(to_warehouse_id):
            raise NotFoundException("Destination warehouse not found")

        source = inventory_repository.fetch_by_product_warehouse(
            product_id=product_id,
            warehouse_id=from_warehouse_id,
            product_variant_id=variant_id,
        )
        if not source:
            raise ValidationException(
                details=[{"field": "fromWarehouseId", "message": "No inventory at source warehouse"}]
            )
        if int(source.get("available_stock") or 0) < quantity:
            raise ValidationException(
                details=[{"field": "quantity", "message": "Insufficient available stock at source"}]
            )

        row = stock_transfer_repository.create({
            "product_id": product_id,
            "product_variant_id": variant_id,
            "from_warehouse_id": from_warehouse_id,
            "to_warehouse_id": to_warehouse_id,
            "quantity": quantity,
            "status": "PENDING",
            "initiated_by": admin_id,
            "notes": to_db_text(payload.get("notes")),
        })
        return self._serialize(row)

    def _write_transfer_logs(
        self,
        *,
        inventory: dict[str, Any],
        transfer_id: int,
        action_type: str,
        transaction_type: str,
        quantity_before: int,
        quantity_after: int,
        quantity_changed: int,
        notes: str,
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
                "action_type": action_type,
                "quantity_before": quantity_before,
                "quantity_after": quantity_after,
                "quantity_changed": quantity_changed,
                "reason": to_db_text(notes),
                "reference_type": "STOCK_TRANSFER",
                "reference_id": transfer_id,
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
                "transaction_type": transaction_type,
                "quantity": abs(quantity_changed),
                "reference_type": "STOCK_TRANSFER",
                "reference_id": transfer_id,
                "notes": to_db_text(notes),
                "performed_by": performed_by,
            },
            conn=conn,
        )

    def update_transfer(
        self,
        transfer_id: int,
        payload: dict[str, Any],
        *,
        admin_id: int,
    ) -> dict[str, Any]:
        status = (payload.get("status") or "").strip().upper()
        if status == "COMPLETED":
            return self._complete_transfer(transfer_id, admin_id=admin_id)
        if status == "CANCELLED":
            return self._cancel_transfer(transfer_id, admin_id=admin_id)
        if status == "IN_TRANSIT":
            return self._set_in_transit(transfer_id)

        raise ValidationException(
            details=[{
                "field": "status",
                "message": "Status must be COMPLETED, CANCELLED, or IN_TRANSIT",
            }]
        )

    def _set_in_transit(self, transfer_id: int) -> dict[str, Any]:
        transfer = stock_transfer_repository.fetch_by_id(transfer_id)
        if not transfer:
            raise NotFoundException("Stock transfer not found")
        current_status = (transfer.get("status") or "").upper()
        if current_status != "PENDING":
            raise ValidationException(
                details=[{"field": "status", "message": "Only pending transfers can be set in transit"}]
            )
        row = stock_transfer_repository.update(transfer_id, {"status": "IN_TRANSIT"})
        refreshed = stock_transfer_repository.fetch_by_id(transfer_id)
        return self._serialize(refreshed or row or transfer)

    def _cancel_transfer(self, transfer_id: int, *, admin_id: int) -> dict[str, Any]:
        transfer = stock_transfer_repository.fetch_by_id(transfer_id)
        if not transfer:
            raise NotFoundException("Stock transfer not found")
        current_status = (transfer.get("status") or "").upper()
        if current_status in {"COMPLETED", "CANCELLED"}:
            raise ValidationException(
                details=[{"field": "status", "message": "Transfer cannot be cancelled"}]
            )
        row = stock_transfer_repository.update(transfer_id, {"status": "CANCELLED"})
        refreshed = stock_transfer_repository.fetch_by_id(transfer_id)
        return self._serialize(refreshed or row or transfer)

    def _complete_transfer(self, transfer_id: int, *, admin_id: int) -> dict[str, Any]:
        with atomic() as conn:
            transfer = stock_transfer_repository.fetch_for_update(transfer_id, conn=conn)
            if not transfer:
                raise NotFoundException("Stock transfer not found")

            current_status = (transfer.get("status") or "").upper()
            if current_status not in {"PENDING", "IN_TRANSIT"}:
                raise ValidationException(
                    details=[{"field": "status", "message": "Transfer cannot be completed"}]
                )

            product_id = int(transfer["product_id"])
            variant_id = transfer.get("product_variant_id")
            from_warehouse_id = int(transfer["from_warehouse_id"])
            to_warehouse_id = int(transfer["to_warehouse_id"])
            quantity = int(transfer.get("quantity") or 0)
            notes = from_db_text(transfer.get("notes")) or ""

            source = inventory_repository.fetch_by_product_warehouse_for_update(
                product_id=product_id,
                warehouse_id=from_warehouse_id,
                product_variant_id=int(variant_id) if variant_id else None,
                conn=conn,
            )
            if not source:
                raise ValidationException(
                    details=[{"field": "fromWarehouseId", "message": "No inventory at source warehouse"}]
                )

            source_available = int(source.get("available_stock") or 0)
            source_warehouse_stock = int(source.get("warehouse_stock") or 0)
            if source_available < quantity:
                raise ValidationException(
                    details=[{"field": "quantity", "message": "Insufficient available stock at source"}]
                )

            source_before = source_available
            source_after = source_available - quantity
            inventory_repository.update_stock_levels(
                int(source["inventory_id"]),
                {
                    "available_stock": source_after,
                    "warehouse_stock": source_warehouse_stock - quantity,
                },
                conn=conn,
            )
            self._write_transfer_logs(
                inventory=source,
                transfer_id=transfer_id,
                action_type="TRANSFER_OUT",
                transaction_type="TRANSFER_OUT",
                quantity_before=source_before,
                quantity_after=source_after,
                quantity_changed=-quantity,
                notes=notes,
                performed_by=admin_id,
                conn=conn,
            )

            dest = inventory_repository.fetch_by_product_warehouse_for_update(
                product_id=product_id,
                warehouse_id=to_warehouse_id,
                product_variant_id=int(variant_id) if variant_id else None,
                conn=conn,
            )
            if dest:
                dest_before = int(dest.get("available_stock") or 0)
                dest_after = dest_before + quantity
                dest_warehouse_stock = int(dest.get("warehouse_stock") or 0)
                inventory_repository.update_stock_levels(
                    int(dest["inventory_id"]),
                    {
                        "available_stock": dest_after,
                        "warehouse_stock": dest_warehouse_stock + quantity,
                        "last_restocked_at": datetime.now(),
                    },
                    conn=conn,
                )
                dest_inventory = dest
            else:
                dest_before = 0
                dest_after = quantity
                dest_inventory = inventory_repository.create(
                    {
                        "product_id": product_id,
                        "product_variant_id": int(variant_id) if variant_id else None,
                        "warehouse_id": to_warehouse_id,
                        "available_stock": quantity,
                        "reserved_stock": 0,
                        "sold_stock": 0,
                        "damaged_stock": 0,
                        "returned_stock": 0,
                        "warehouse_stock": quantity,
                        "reorder_level": 0,
                        "is_active": True,
                    },
                    conn=conn,
                )

            self._write_transfer_logs(
                inventory=dest_inventory,
                transfer_id=transfer_id,
                action_type="TRANSFER_IN",
                transaction_type="TRANSFER_IN",
                quantity_before=dest_before,
                quantity_after=dest_after,
                quantity_changed=quantity,
                notes=notes,
                performed_by=admin_id,
                conn=conn,
            )

            stock_transfer_repository.update(
                transfer_id,
                {"status": "COMPLETED", "completed_at": datetime.now()},
                conn=conn,
            )

        refreshed = stock_transfer_repository.fetch_by_id(transfer_id)
        return self._serialize(refreshed or transfer)


transfer_service = TransferService()
