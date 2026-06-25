from __future__ import annotations

from typing import Any, Optional

from django.http import HttpRequest

from apps.customers.repositories.wishlist_repository import wishlist_repository
from apps.products.repositories.product_repository import product_repository
from apps.storefront.helpers.commerce_context import require_customer_id
from core.database.transaction import atomic
from core.exceptions.base import NotFoundException, ValidationException
from core.helpers.text import from_db_text


def _optional_int(value: Any) -> Optional[int]:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


class StorefrontWishlistService:
    def _serialize_item(self, row: dict[str, Any]) -> dict[str, Any]:
        slug = from_db_text(row.get("product_slug")) or ""
        sale = float(row.get("product_sale_price") or 0)
        mrp = float(row.get("product_mrp") or sale)
        return {
            "id": str(row["wishlist_id"]),
            "productId": str(row["product_id"]),
            "productSlug": slug,
            "name": from_db_text(row.get("product_name")) or "",
            "image": from_db_text(row.get("product_image_url")) or "",
            "href": f"/product/{slug}" if slug else "/",
            "price": sale,
            "mrp": mrp,
            "quantity": 1,
        }

    def list_wishlist(self, request: HttpRequest) -> dict[str, Any]:
        customer_id = require_customer_id(request)
        rows = wishlist_repository.list_by_customer(customer_id)
        items = [self._serialize_item(row) for row in rows]
        return {"items": items, "itemCount": len(items)}

    def add_item(self, request: HttpRequest, payload: dict[str, Any]) -> dict[str, Any]:
        customer_id = require_customer_id(request)
        product_id = _optional_int(payload.get("productId"))
        if not product_id:
            raise ValidationException(
                details=[{"field": "productId", "message": "Product is required"}]
            )
        if not product_repository.fetch_by_id(product_id):
            raise NotFoundException("Product not found")

        with atomic() as conn:
            existing = wishlist_repository.fetch_by_customer_product(
                customer_id, product_id, conn=conn
            )
            if existing and existing.get("is_deleted"):
                wishlist_repository.reactivate(int(existing["wishlist_id"]), conn=conn)
            elif not existing:
                wishlist_repository.create(
                    {
                        "customer_id": customer_id,
                        "session_id": "NA",
                        "product_id": product_id,
                        "product_variant_id": _optional_int(payload.get("productVariantId")),
                        "is_guest": False,
                    },
                    conn=conn,
                )
        return self.list_wishlist(request)

    def remove_item(self, request: HttpRequest, product_id: int) -> dict[str, Any]:
        customer_id = require_customer_id(request)
        wishlist_repository.soft_delete_by_product(customer_id, product_id)
        return self.list_wishlist(request)


storefront_wishlist_service = StorefrontWishlistService()
