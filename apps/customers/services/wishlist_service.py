from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from apps.customers.repositories.wishlist_repository import wishlist_repository
from core.exceptions.base import NotFoundException
from core.helpers.text import from_db_text


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
        "sort_by": kwargs.get("sort_by", "created_at"),
        "sort_dir": kwargs.get("sort_dir", "desc"),
    }


class WishlistService:
    def _serialize(self, row: dict[str, Any]) -> dict[str, Any]:
        variant_id = row.get("product_variant_id")
        return {
            "id": str(row["wishlist_id"]),
            "customerId": str(row["customer_id"]) if row.get("customer_id") else None,
            "customerName": from_db_text(row.get("customer_name")),
            "productId": str(row["product_id"]),
            "productName": from_db_text(row.get("product_name")) or "",
            "productSku": from_db_text(row.get("product_sku")) or "",
            "productSalePrice": float(row.get("product_sale_price") or 0),
            "productImageUrl": from_db_text(row.get("product_image_url")),
            "productVariantId": str(variant_id) if variant_id else None,
            "isGuest": bool(row.get("is_guest")),
            "isActive": bool(row.get("is_active")),
            "createdAt": _format_dt(row.get("created_at")),
        }

    def list_wishlists(self, **kwargs) -> dict[str, Any]:
        params = _base_list_params(kwargs)
        if kwargs.get("customer_id") is not None:
            params["customer_id"] = kwargs["customer_id"]
        rows, total = wishlist_repository.list_paginated(**params)
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

    def delete_wishlist(self, wishlist_id: int) -> None:
        if not wishlist_repository.soft_delete(wishlist_id):
            raise NotFoundException("Wishlist item not found")


wishlist_service = WishlistService()
