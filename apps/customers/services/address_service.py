from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from apps.customers.repositories.address_repository import address_repository
from apps.customers.repositories.customer_repository import customer_repository
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


class AddressService:
    def _serialize(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": str(row["address_id"]),
            "customerId": str(row["customer_id"]),
            "customerName": from_db_text(row.get("customer_name")) or "",
            "addressType": from_db_text(row.get("address_type")) or "",
            "fullName": from_db_text(row.get("full_name")) or "",
            "phone": from_db_text(row.get("phone")) or "",
            "addressLine1": from_db_text(row.get("address_line1")) or "",
            "addressLine2": from_db_text(row.get("address_line2")),
            "landmark": from_db_text(row.get("landmark")),
            "city": from_db_text(row.get("city")) or "",
            "state": from_db_text(row.get("state")) or "",
            "pincode": from_db_text(row.get("pincode")) or "",
            "country": from_db_text(row.get("country")) or "India",
            "isDefault": bool(row.get("is_default")),
            "isActive": bool(row.get("is_active")),
            "createdAt": _format_dt(row.get("created_at")),
            "updatedAt": _format_dt(row.get("updated_at")),
        }

    def list_addresses(self, **kwargs) -> dict[str, Any]:
        params = _base_list_params(kwargs)
        if kwargs.get("customer_id") is not None:
            params["customer_id"] = kwargs["customer_id"]
        rows, total = address_repository.list_paginated(**params)
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

    def get_address(self, address_id: int) -> dict[str, Any]:
        row = address_repository.fetch_by_id(address_id)
        if not row:
            raise NotFoundException("Address not found")
        return self._serialize(row)

    def create_address(self, payload: dict[str, Any]) -> dict[str, Any]:
        customer_id = _optional_int(payload.get("customerId"))
        if not customer_id:
            raise ValidationException(
                details=[{"field": "customerId", "message": "Customer is required"}]
            )
        if not customer_repository.fetch_by_id(customer_id):
            raise NotFoundException("Customer not found")

        line1 = (payload.get("addressLine1") or "").strip()
        if not line1:
            raise ValidationException(
                details=[{"field": "addressLine1", "message": "Address line 1 is required"}]
            )

        is_default = bool(payload.get("isDefault", False))
        with atomic() as conn:
            if is_default:
                address_repository.clear_default_for_customer(customer_id, conn=conn)
            row = address_repository.create({
                "customer_id": customer_id,
                "address_type": to_db_text(payload.get("addressType") or "SHIPPING"),
                "full_name": to_db_text(payload.get("fullName")),
                "phone": to_db_text(payload.get("phone")),
                "address_line1": to_db_text(line1),
                "address_line2": to_db_text(payload.get("addressLine2")),
                "landmark": to_db_text(payload.get("landmark")),
                "city": to_db_text(payload.get("city")),
                "state": to_db_text(payload.get("state")),
                "pincode": to_db_text(payload.get("pincode")),
                "country": to_db_text(payload.get("country") or "India"),
                "is_default": is_default,
                "is_active": bool(payload.get("isActive", True)),
            }, conn=conn)

        return self._serialize(row)

    def update_address(self, address_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        existing = address_repository.fetch_by_id(address_id)
        if not existing:
            raise NotFoundException("Address not found")

        updates: dict[str, Any] = {}
        field_map = {
            "addressType": "address_type",
            "fullName": "full_name",
            "phone": "phone",
            "addressLine1": "address_line1",
            "addressLine2": "address_line2",
            "landmark": "landmark",
            "city": "city",
            "state": "state",
            "pincode": "pincode",
            "country": "country",
            "isActive": "is_active",
        }
        for api_key, db_key in field_map.items():
            if api_key in payload:
                updates[db_key] = to_db_text(payload.get(api_key))

        is_default = payload.get("isDefault")
        with atomic() as conn:
            if is_default is not None and bool(is_default):
                address_repository.clear_default_for_customer(
                    int(existing["customer_id"]),
                    exclude_id=address_id,
                    conn=conn,
                )
                updates["is_default"] = True
            elif is_default is not None:
                updates["is_default"] = bool(is_default)

            if updates:
                row = address_repository.update(address_id, updates, conn=conn)
            else:
                row = existing

        return self._serialize(row or existing)

    def delete_address(self, address_id: int) -> None:
        if not address_repository.soft_delete(address_id):
            raise NotFoundException("Address not found")


address_service = AddressService()
