from __future__ import annotations

from typing import Any, Optional

from django.http import HttpRequest

from apps.customers.repositories.address_repository import address_repository
from apps.storefront.helpers.commerce_context import require_customer_id
from core.database.transaction import atomic
from core.exceptions.base import NotFoundException, ValidationException
from core.helpers.text import from_db_text, to_db_text


def _optional_int(value: Any) -> Optional[int]:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


ADDRESS_TYPE_MAP = {
    "home": "HOME",
    "office": "OFFICE",
    "other": "OTHER",
}


class StorefrontAddressService:
    def _serialize(self, row: dict[str, Any]) -> dict[str, Any]:
        addr_type = (from_db_text(row.get("address_type")) or "HOME").lower()
        if addr_type not in ADDRESS_TYPE_MAP:
            addr_type = "home"
        return {
            "id": str(row["address_id"]),
            "type": addr_type if addr_type in ("home", "office", "other") else "home",
            "customLabel": from_db_text(row.get("landmark")) or None,
            "fullName": from_db_text(row.get("full_name")) or "",
            "phone": from_db_text(row.get("phone")) or "",
            "line1": from_db_text(row.get("address_line1")) or "",
            "line2": from_db_text(row.get("address_line2")) or None,
            "city": from_db_text(row.get("city")) or "",
            "state": from_db_text(row.get("state")) or "",
            "pincode": from_db_text(row.get("pincode")) or "",
            "isDefault": bool(row.get("is_default")),
        }

    def list_addresses(self, request: HttpRequest) -> dict[str, Any]:
        customer_id = require_customer_id(request)
        rows = address_repository.list_by_customer(customer_id)
        items = [self._serialize(row) for row in rows]
        selected = next((i["id"] for i in items if i.get("isDefault")), items[0]["id"] if items else None)
        return {"items": items, "selectedAddressId": selected}

    def create_address(self, request: HttpRequest, payload: dict[str, Any]) -> dict[str, Any]:
        customer_id = require_customer_id(request)
        data = self._parse_payload(payload)
        is_default = bool(payload.get("isDefault", False))

        with atomic() as conn:
            if is_default:
                address_repository.clear_default_for_customer(customer_id, conn=conn)
            row = address_repository.create(
                {
                    "customer_id": customer_id,
                    "address_type": data["address_type"],
                    "full_name": data["full_name"],
                    "phone": data["phone"],
                    "address_line1": data["address_line1"],
                    "address_line2": data["address_line2"],
                    "landmark": data["landmark"],
                    "city": data["city"],
                    "state": data["state"],
                    "pincode": data["pincode"],
                    "country": data["country"],
                    "is_default": is_default,
                    "is_active": True,
                },
                conn=conn,
            )
        return {"item": self._serialize(row)}

    def update_address(
        self,
        request: HttpRequest,
        address_id: int,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        customer_id = require_customer_id(request)
        existing = address_repository.fetch_by_id(address_id)
        if not existing or int(existing["customer_id"]) != customer_id:
            raise NotFoundException("Address not found")

        data = self._parse_payload(payload, partial=True)
        is_default = payload.get("isDefault")

        with atomic() as conn:
            if is_default:
                address_repository.clear_default_for_customer(
                    customer_id, exclude_id=address_id, conn=conn
                )
                data["is_default"] = True
            if data:
                row = address_repository.update(address_id, data, conn=conn)
            else:
                row = existing
        return {"item": self._serialize(row or existing)}

    def delete_address(self, request: HttpRequest, address_id: int) -> None:
        customer_id = require_customer_id(request)
        existing = address_repository.fetch_by_id(address_id)
        if not existing or int(existing["customer_id"]) != customer_id:
            raise NotFoundException("Address not found")
        address_repository.soft_delete(address_id)

    def _parse_payload(self, payload: dict[str, Any], *, partial: bool = False) -> dict[str, Any]:
        result: dict[str, Any] = {}
        if not partial or "type" in payload:
            addr_type = (payload.get("type") or "home").lower()
            result["address_type"] = ADDRESS_TYPE_MAP.get(addr_type, "HOME")
        if not partial or "fullName" in payload:
            full_name = (payload.get("fullName") or "").strip()
            if not full_name:
                raise ValidationException(
                    details=[{"field": "fullName", "message": "Full name is required"}]
                )
            result["full_name"] = to_db_text(full_name)
        if not partial or "phone" in payload:
            phone = (payload.get("phone") or "").strip()
            if not phone:
                raise ValidationException(
                    details=[{"field": "phone", "message": "Phone is required"}]
                )
            result["phone"] = to_db_text(phone)
        if not partial or "line1" in payload:
            line1 = (payload.get("line1") or "").strip()
            if not line1:
                raise ValidationException(
                    details=[{"field": "line1", "message": "Address line is required"}]
                )
            result["address_line1"] = to_db_text(line1)
        if "line2" in payload:
            result["address_line2"] = to_db_text(payload.get("line2") or "NA")
        if "customLabel" in payload:
            result["landmark"] = to_db_text(payload.get("customLabel") or "NA")
        if not partial or "city" in payload:
            result["city"] = to_db_text((payload.get("city") or "").strip() or "NA")
        if not partial or "state" in payload:
            result["state"] = to_db_text((payload.get("state") or "").strip() or "NA")
        if not partial or "pincode" in payload:
            pincode = (payload.get("pincode") or "").strip()
            if not pincode:
                raise ValidationException(
                    details=[{"field": "pincode", "message": "Pincode is required"}]
                )
            result["pincode"] = to_db_text(pincode)
        if not partial:
            result["country"] = to_db_text(payload.get("country") or "India")
        return result


storefront_address_service = StorefrontAddressService()
