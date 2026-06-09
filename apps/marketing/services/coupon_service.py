from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from apps.marketing.repositories.coupon_repository import coupon_repository
from apps.marketing.repositories.coupon_usage_repository import coupon_usage_repository
from core.exceptions.base import NotFoundException, ValidationException
from core.helpers.text import from_db_text, to_db_text


def _format_dt(value: Any) -> Optional[str]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _parse_dt(value: Any) -> Optional[datetime]:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
    except ValueError:
        return None


def _base_list_params(kwargs: dict[str, Any]) -> dict[str, Any]:
    return {
        "page": kwargs.get("page", 1),
        "page_size": kwargs.get("page_size", 20),
        "search": kwargs.get("search", ""),
        "sort_by": kwargs.get("sort_by", "created_at"),
        "sort_dir": kwargs.get("sort_dir", "desc"),
    }


def _pagination(page: int, page_size: int, total: int) -> dict[str, Any]:
    return {
        "page": page,
        "pageSize": page_size,
        "total": total,
        "totalPages": max(1, (total + page_size - 1) // page_size),
    }


class CouponService:
    def _serialize_usage(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": str(row["coupon_usage_id"]),
            "customerId": str(row["customer_id"]),
            "customerName": from_db_text(row.get("customer_name")) or "",
            "customerEmail": from_db_text(row.get("customer_email")),
            "orderId": str(row["order_id"]),
            "discountApplied": float(row.get("discount_applied") or 0),
            "usedAt": _format_dt(row.get("used_at")),
        }

    def _serialize(self, row: dict[str, Any], *, include_usages: bool = False) -> dict[str, Any]:
        item = {
            "id": str(row["coupon_id"]),
            "couponCode": from_db_text(row.get("coupon_code")) or "",
            "couponName": from_db_text(row.get("coupon_name")) or "",
            "discountType": from_db_text(row.get("discount_type")) or "PERCENTAGE",
            "discountValue": float(row.get("discount_value") or 0),
            "maxDiscountAmount": float(row.get("max_discount_amount") or 0),
            "minimumOrderAmount": float(row.get("minimum_order_amount") or 0),
            "usageLimit": int(row.get("usage_limit") or 0),
            "usagePerCustomer": int(row.get("usage_per_customer") or 1),
            "usedCount": int(row.get("used_count") or 0),
            "startsAt": _format_dt(row.get("starts_at")),
            "expiresAt": _format_dt(row.get("expires_at")),
            "isActive": bool(row.get("is_active")),
            "createdAt": _format_dt(row.get("created_at")),
            "updatedAt": _format_dt(row.get("updated_at")),
        }
        if include_usages:
            usages = coupon_usage_repository.list_by_coupon(int(row["coupon_id"]))
            item["usages"] = [self._serialize_usage(u) for u in usages]
        return item

    def list_coupons(self, **kwargs) -> dict[str, Any]:
        params = _base_list_params(kwargs)
        params["is_active"] = kwargs.get("is_active")
        rows, total = coupon_repository.list_paginated(**params)
        page = kwargs.get("page", 1)
        page_size = kwargs.get("page_size", 20)
        return {
            "items": [self._serialize(r) for r in rows],
            "pagination": _pagination(page, page_size, total),
        }

    def get_coupon(self, coupon_id: int) -> dict[str, Any]:
        row = coupon_repository.fetch_by_id(coupon_id)
        if not row:
            raise NotFoundException("Coupon not found")
        return self._serialize(row, include_usages=True)

    def _validate_discount_type(self, discount_type: str) -> str:
        normalized = (discount_type or "PERCENTAGE").strip().upper()
        if normalized not in {"PERCENTAGE", "FIXED"}:
            raise ValidationException(
                details=[{"field": "discountType", "message": "Must be PERCENTAGE or FIXED"}]
            )
        return normalized

    def create_coupon(self, payload: dict[str, Any]) -> dict[str, Any]:
        coupon_code = (payload.get("couponCode") or "").strip().upper()
        if not coupon_code:
            raise ValidationException(
                details=[{"field": "couponCode", "message": "Coupon code is required"}]
            )
        if coupon_repository.code_exists(coupon_code):
            raise ValidationException(
                details=[{"field": "couponCode", "message": "Coupon code already exists"}]
            )

        row = coupon_repository.create({
            "coupon_code": coupon_code,
            "coupon_name": to_db_text(payload.get("couponName")),
            "discount_type": self._validate_discount_type(payload.get("discountType")),
            "discount_value": float(payload.get("discountValue") or 0),
            "max_discount_amount": float(payload.get("maxDiscountAmount") or 0),
            "minimum_order_amount": float(payload.get("minimumOrderAmount") or 0),
            "usage_limit": int(payload.get("usageLimit") or 0),
            "usage_per_customer": int(payload.get("usagePerCustomer") or 1),
            "used_count": int(payload.get("usedCount") or 0),
            "starts_at": _parse_dt(payload.get("startsAt")),
            "expires_at": _parse_dt(payload.get("expiresAt")),
            "is_active": bool(payload.get("isActive", True)),
        })
        return self._serialize(row)

    def update_coupon(self, coupon_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        existing = coupon_repository.fetch_by_id(coupon_id)
        if not existing:
            raise NotFoundException("Coupon not found")

        updates: dict[str, Any] = {}
        if "couponCode" in payload:
            coupon_code = (payload.get("couponCode") or "").strip().upper()
            if not coupon_code:
                raise ValidationException(
                    details=[{"field": "couponCode", "message": "Coupon code is required"}]
                )
            if coupon_repository.code_exists(coupon_code, exclude_id=coupon_id):
                raise ValidationException(
                    details=[{"field": "couponCode", "message": "Coupon code already exists"}]
                )
            updates["coupon_code"] = coupon_code
        if "couponName" in payload:
            updates["coupon_name"] = to_db_text(payload.get("couponName"))
        if "discountType" in payload:
            updates["discount_type"] = self._validate_discount_type(payload.get("discountType"))
        if "discountValue" in payload:
            updates["discount_value"] = float(payload.get("discountValue") or 0)
        if "maxDiscountAmount" in payload:
            updates["max_discount_amount"] = float(payload.get("maxDiscountAmount") or 0)
        if "minimumOrderAmount" in payload:
            updates["minimum_order_amount"] = float(payload.get("minimumOrderAmount") or 0)
        if "usageLimit" in payload:
            updates["usage_limit"] = int(payload.get("usageLimit") or 0)
        if "usagePerCustomer" in payload:
            updates["usage_per_customer"] = int(payload.get("usagePerCustomer") or 1)
        if "usedCount" in payload:
            updates["used_count"] = int(payload.get("usedCount") or 0)
        if "startsAt" in payload:
            updates["starts_at"] = _parse_dt(payload.get("startsAt"))
        if "expiresAt" in payload:
            updates["expires_at"] = _parse_dt(payload.get("expiresAt"))
        if "isActive" in payload:
            updates["is_active"] = bool(payload.get("isActive"))

        row = coupon_repository.update(coupon_id, updates)
        if not row:
            raise NotFoundException("Coupon not found")
        return self._serialize(row)

    def delete_coupon(self, coupon_id: int) -> None:
        if not coupon_repository.soft_delete(coupon_id):
            raise NotFoundException("Coupon not found")


coupon_service = CouponService()
