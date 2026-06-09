from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from apps.inventory.repositories.warehouse_repository import warehouse_repository
from core.exceptions.base import ConflictException, NotFoundException, ValidationException
from core.helpers.text import from_db_text, to_db_text


def _format_dt(value: Any) -> Optional[str]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _base_list_params(kwargs: dict[str, Any]) -> dict[str, Any]:
    return {
        "page": kwargs.get("page", 1),
        "page_size": kwargs.get("page_size", 20),
        "search": kwargs.get("search", ""),
        "sort_by": kwargs.get("sort_by", "name"),
        "sort_dir": kwargs.get("sort_dir", "asc"),
    }


class WarehouseService:
    def _serialize(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": str(row["warehouse_id"]),
            "warehouseCode": from_db_text(row.get("warehouse_code")) or "",
            "name": from_db_text(row.get("name")) or "",
            "addressLine1": from_db_text(row.get("address_line1")),
            "addressLine2": from_db_text(row.get("address_line2")),
            "city": from_db_text(row.get("city")),
            "state": from_db_text(row.get("state")),
            "pincode": from_db_text(row.get("pincode")),
            "country": from_db_text(row.get("country")),
            "contactPhone": from_db_text(row.get("contact_phone")),
            "contactEmail": from_db_text(row.get("contact_email")),
            "isPrimary": bool(row.get("is_primary")),
            "isActive": bool(row.get("is_active")),
            "createdAt": _format_dt(row.get("created_at")),
            "updatedAt": _format_dt(row.get("updated_at")),
        }

    def list_warehouses(self, **kwargs) -> dict[str, Any]:
        rows, total = warehouse_repository.list_paginated(**_base_list_params(kwargs))
        page = kwargs.get("page", 1)
        page_size = kwargs.get("page_size", 20)
        return {
            "items": [self._serialize(r) for r in rows],
            "pagination": {
                "page": page,
                "pageSize": page_size,
                "total": total,
                "totalPages": max(1, (total + page_size - 1) // page_size),
            },
        }

    def get_warehouse(self, warehouse_id: int) -> dict[str, Any]:
        row = warehouse_repository.fetch_by_id(warehouse_id)
        if not row:
            raise NotFoundException("Warehouse not found")
        return self._serialize(row)

    def create_warehouse(self, payload: dict[str, Any]) -> dict[str, Any]:
        code = (payload.get("warehouseCode") or "").strip()
        name = (payload.get("name") or "").strip()
        if not code:
            raise ValidationException(
                details=[{"field": "warehouseCode", "message": "Warehouse code is required"}]
            )
        if not name:
            raise ValidationException(
                details=[{"field": "name", "message": "Warehouse name is required"}]
            )
        if warehouse_repository.code_exists(code):
            raise ConflictException("Warehouse code already exists")

        is_primary = bool(payload.get("isPrimary", False))
        if is_primary:
            warehouse_repository.clear_primary_flag()

        row = warehouse_repository.create({
            "warehouse_code": to_db_text(code),
            "name": to_db_text(name),
            "address_line1": to_db_text(payload.get("addressLine1")),
            "address_line2": to_db_text(payload.get("addressLine2")),
            "city": to_db_text(payload.get("city")),
            "state": to_db_text(payload.get("state")),
            "pincode": to_db_text(payload.get("pincode")),
            "country": to_db_text(payload.get("country")),
            "contact_phone": to_db_text(payload.get("contactPhone")),
            "contact_email": to_db_text(payload.get("contactEmail")),
            "is_primary": is_primary,
            "is_active": bool(payload.get("isActive", True)),
        })
        return self._serialize(row)

    def update_warehouse(self, warehouse_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        existing = warehouse_repository.fetch_by_id(warehouse_id)
        if not existing:
            raise NotFoundException("Warehouse not found")

        updates: dict[str, Any] = {}
        if "warehouseCode" in payload:
            code = (payload.get("warehouseCode") or "").strip()
            if not code:
                raise ValidationException(
                    details=[{"field": "warehouseCode", "message": "Warehouse code is required"}]
                )
            if warehouse_repository.code_exists(code, exclude_id=warehouse_id):
                raise ConflictException("Warehouse code already exists")
            updates["warehouse_code"] = to_db_text(code)
        if "name" in payload:
            name = (payload.get("name") or "").strip()
            if not name:
                raise ValidationException(
                    details=[{"field": "name", "message": "Warehouse name is required"}]
                )
            updates["name"] = to_db_text(name)
        for api_key, db_key in (
            ("addressLine1", "address_line1"),
            ("addressLine2", "address_line2"),
            ("city", "city"),
            ("state", "state"),
            ("pincode", "pincode"),
            ("country", "country"),
            ("contactPhone", "contact_phone"),
            ("contactEmail", "contact_email"),
        ):
            if api_key in payload:
                updates[db_key] = to_db_text(payload.get(api_key))
        if "isPrimary" in payload:
            is_primary = bool(payload.get("isPrimary"))
            if is_primary:
                warehouse_repository.clear_primary_flag(exclude_id=warehouse_id)
            updates["is_primary"] = is_primary
        if "isActive" in payload:
            updates["is_active"] = bool(payload.get("isActive"))

        row = warehouse_repository.update(warehouse_id, updates)
        if not row:
            raise NotFoundException("Warehouse not found")
        return self._serialize(row)

    def delete_warehouse(self, warehouse_id: int) -> None:
        if not warehouse_repository.soft_delete(warehouse_id):
            raise NotFoundException("Warehouse not found")


warehouse_service = WarehouseService()
