from __future__ import annotations

from typing import Any, Optional

from django.http import HttpRequest

from apps.products.repositories.product_child_repository import product_child_repository
from apps.products.repositories.product_repository import product_repository
from apps.storefront.helpers.commerce_context import resolve_customer_id, resolve_guest_session
from apps.storefront.repositories.cart_repository import cart_repository
from apps.storefront.services.inventory_stock_service import inventory_stock_service
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


class CartService:
    def _resolve_variant_id(self, product_id: int, variant_id: Optional[int]) -> Optional[int]:
        if variant_id is not None:
            return variant_id
        return product_child_repository.fetch_default_variant_id(product_id)

    def _available_stock(
        self,
        product_id: int,
        variant_id: Optional[int],
        *,
        conn,
    ) -> int:
        resolved = self._resolve_variant_id(product_id, variant_id)
        return inventory_stock_service.get_available_stock(
            product_id=product_id,
            product_variant_id=resolved,
            conn=conn,
        )

    def _serialize_item(self, row: dict[str, Any], *, conn=None) -> dict[str, Any]:
        slug = from_db_text(row.get("product_slug")) or ""
        sale = float(row.get("unit_price") or row.get("product_sale_price") or 0)
        mrp = float(row.get("product_mrp") or sale)
        product_id = int(row["product_id"])
        variant_raw = row.get("product_variant_id")
        variant_id = int(variant_raw) if variant_raw else None
        available_stock = self._available_stock(product_id, variant_id, conn=conn)
        return {
            "id": str(row["cart_item_id"]),
            "productId": str(row["product_id"]),
            "productSlug": slug,
            "name": from_db_text(row.get("product_name")) or "",
            "image": from_db_text(row.get("product_image_url")) or "",
            "href": f"/product/{slug}" if slug else "/",
            "price": sale,
            "mrp": mrp,
            "quantity": int(row.get("quantity") or 1),
            "lineTotal": float(row.get("line_total") or sale * int(row.get("quantity") or 1)),
            "productVariantId": (
                str(row["product_variant_id"]) if row.get("product_variant_id") else None
            ),
            "availableStock": available_stock,
            "maxQuantity": available_stock,
        }

    def _serialize_cart(
        self,
        cart: dict[str, Any],
        items: list[dict[str, Any]],
        *,
        conn=None,
    ) -> dict[str, Any]:
        serialized_items = [self._serialize_item(row, conn=conn) for row in items]
        return {
            "cartId": str(cart["cart_id"]),
            "items": serialized_items,
            "itemCount": sum(i["quantity"] for i in serialized_items),
            "subtotal": float(cart.get("subtotal") or 0),
            "discountAmount": float(cart.get("discount_amount") or 0),
            "taxAmount": float(cart.get("tax_amount") or 0),
            "totalAmount": float(cart.get("total_amount") or 0),
        }

    def _recalculate(self, cart_id: int, *, conn) -> None:
        items = cart_repository.list_items(cart_id, conn=conn)
        subtotal = sum(float(i.get("line_total") or 0) for i in items)
        item_count = sum(int(i.get("quantity") or 0) for i in items)
        cart_repository.update_cart(
            cart_id,
            {
                "subtotal": subtotal,
                "total_amount": subtotal,
                "item_count": item_count,
            },
            conn=conn,
        )

    def _get_or_create_cart(
        self,
        *,
        customer_id: Optional[int],
        session_id: str,
        conn,
    ) -> dict[str, Any]:
        cart = cart_repository.fetch_active_cart(
            customer_id=customer_id,
            session_id=session_id if not customer_id else None,
            conn=conn,
        )
        if cart:
            return cart
        return cart_repository.create_cart(
            {
                "customer_id": customer_id,
                "session_id": session_id or "NA",
                "is_guest": customer_id is None,
                "subtotal": 0,
                "discount_amount": 0,
                "tax_amount": 0,
                "total_amount": 0,
                "item_count": 0,
            },
            conn=conn,
        )

    def get_cart(self, request: HttpRequest) -> dict[str, Any]:
        customer_id = resolve_customer_id(request)
        session_id = resolve_guest_session(request)
        if not customer_id and not session_id:
            return self._serialize_cart(
                {"cart_id": 0, "subtotal": 0, "discount_amount": 0, "tax_amount": 0, "total_amount": 0},
                [],
            )

        with atomic() as conn:
            cart = self._get_or_create_cart(
                customer_id=customer_id,
                session_id=session_id,
                conn=conn,
            )
            items = cart_repository.list_items(int(cart["cart_id"]), conn=conn)
            return self._serialize_cart(cart, items, conn=conn)

    def add_item(self, request: HttpRequest, payload: dict[str, Any]) -> dict[str, Any]:
        from apps.storefront.helpers.commerce_context import require_customer_mobile

        customer_id = require_customer_mobile(request)
        product_id = _optional_int(payload.get("productId"))
        if not product_id:
            raise ValidationException(
                details=[{"field": "productId", "message": "Product is required"}]
            )
        product = product_repository.fetch_by_id(product_id)
        if not product:
            raise NotFoundException("Product not found")

        quantity = max(1, int(payload.get("quantity") or 1))
        variant_id = _optional_int(payload.get("productVariantId"))
        unit_price = float(product.get("sale_price") or product.get("base_price") or 0)

        variant_id = self._resolve_variant_id(product_id, variant_id)
        if variant_id:
            variants = product_child_repository.list_variants(product_id)
            variant = next(
                (v for v in variants if int(v["product_variant_id"]) == variant_id),
                None,
            )
            if variant:
                unit_price = float(variant.get("sale_price") or variant.get("price") or unit_price)

        line_total = unit_price * quantity

        session_id = resolve_guest_session(request) or "guest"

        with atomic() as conn:
            cart = self._get_or_create_cart(
                customer_id=customer_id,
                session_id=session_id,
                conn=conn,
            )
            cart_id = int(cart["cart_id"])
            existing = cart_repository.fetch_item_by_product(
                cart_id, product_id, variant_id, conn=conn
            )
            available = self._available_stock(product_id, variant_id, conn=conn)
            if available <= 0:
                raise ValidationException(
                    details=[{"field": "quantity", "message": "This product is out of stock"}]
                )
            existing_qty = int(existing["quantity"]) if existing else 0
            new_qty = existing_qty + quantity
            if new_qty > available:
                if existing_qty > 0:
                    message = (
                        f"Only {available} unit(s) available. "
                        f"You already have {existing_qty} in your cart."
                    )
                else:
                    message = f"Only {available} unit(s) available"
                raise ValidationException(
                    details=[{"field": "quantity", "message": message}]
                )
            if existing:
                cart_repository.update_item(
                    int(existing["cart_item_id"]),
                    {"quantity": new_qty, "line_total": unit_price * new_qty},
                    conn=conn,
                )
            else:
                cart_repository.add_item(
                    {
                        "cart_id": cart_id,
                        "product_id": product_id,
                        "product_variant_id": variant_id,
                        "quantity": quantity,
                        "unit_price": unit_price,
                        "line_total": line_total,
                    },
                    conn=conn,
                )
            self._recalculate(cart_id, conn=conn)
            items = cart_repository.list_items(cart_id, conn=conn)
            cart = cart_repository.fetch_active_cart(
                customer_id=customer_id,
                session_id=session_id if not customer_id else None,
                conn=conn,
            ) or cart
            return self._serialize_cart(cart, items, conn=conn)

    def update_item(
        self,
        request: HttpRequest,
        cart_item_id: int,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        quantity = max(1, int(payload.get("quantity") or 1))
        customer_id = resolve_customer_id(request)
        session_id = resolve_guest_session(request)

        with atomic() as conn:
            item = cart_repository.fetch_item(cart_item_id, conn=conn)
            if not item:
                raise NotFoundException("Cart item not found")
            cart = cart_repository.fetch_active_cart(
                customer_id=customer_id,
                session_id=session_id if not customer_id else None,
                conn=conn,
            )
            if not cart or int(cart["cart_id"]) != int(item["cart_id"]):
                raise NotFoundException("Cart item not found")

            product_id = int(item["product_id"])
            variant_raw = item.get("product_variant_id")
            variant_id = int(variant_raw) if variant_raw else None
            available = self._available_stock(product_id, variant_id, conn=conn)
            if available <= 0:
                raise ValidationException(
                    details=[{"field": "quantity", "message": "This product is out of stock"}]
                )
            if quantity > available:
                raise ValidationException(
                    details=[
                        {
                            "field": "quantity",
                            "message": f"Only {available} unit(s) available",
                        }
                    ]
                )

            unit_price = float(item.get("unit_price") or 0)
            cart_repository.update_item(
                cart_item_id,
                {"quantity": quantity, "line_total": unit_price * quantity},
                conn=conn,
            )
            self._recalculate(int(cart["cart_id"]), conn=conn)
            items = cart_repository.list_items(int(cart["cart_id"]), conn=conn)
            return self._serialize_cart(cart, items, conn=conn)

    def remove_item(self, request: HttpRequest, cart_item_id: int) -> dict[str, Any]:
        customer_id = resolve_customer_id(request)
        session_id = resolve_guest_session(request)

        with atomic() as conn:
            item = cart_repository.fetch_item(cart_item_id, conn=conn)
            if not item:
                raise NotFoundException("Cart item not found")
            cart = cart_repository.fetch_active_cart(
                customer_id=customer_id,
                session_id=session_id if not customer_id else None,
                conn=conn,
            )
            if not cart or int(cart["cart_id"]) != int(item["cart_id"]):
                raise NotFoundException("Cart item not found")

            cart_repository.soft_delete_item(cart_item_id, conn=conn)
            self._recalculate(int(cart["cart_id"]), conn=conn)
            items = cart_repository.list_items(int(cart["cart_id"]), conn=conn)
            return self._serialize_cart(cart, items, conn=conn)

    def clear_cart(self, request: HttpRequest) -> dict[str, Any]:
        customer_id = resolve_customer_id(request)
        session_id = resolve_guest_session(request)

        with atomic() as conn:
            cart = cart_repository.fetch_active_cart(
                customer_id=customer_id,
                session_id=session_id if not customer_id else None,
                conn=conn,
            )
            if cart:
                cart_repository.clear_items(int(cart["cart_id"]), conn=conn)
                self._recalculate(int(cart["cart_id"]), conn=conn)
                items = []
                return self._serialize_cart(cart, items, conn=conn)
        return self.get_cart(request)

    def merge_guest_cart(self, customer_id: int, session_id: str) -> None:
        if not session_id:
            return
        with atomic() as conn:
            guest_cart = cart_repository.fetch_active_cart(session_id=session_id, conn=conn)
            if not guest_cart:
                return
            customer_cart = self._get_or_create_cart(
                customer_id=customer_id,
                session_id=session_id,
                conn=conn,
            )
            guest_items = cart_repository.list_items(int(guest_cart["cart_id"]), conn=conn)
            for item in guest_items:
                product_id = int(item["product_id"])
                variant_id = item.get("product_variant_id")
                variant_int = int(variant_id) if variant_id else None
                existing = cart_repository.fetch_item_by_product(
                    int(customer_cart["cart_id"]),
                    product_id,
                    variant_int,
                    conn=conn,
                )
                if existing:
                    new_qty = int(existing["quantity"]) + int(item["quantity"])
                    unit_price = float(existing.get("unit_price") or 0)
                    cart_repository.update_item(
                        int(existing["cart_item_id"]),
                        {"quantity": new_qty, "line_total": unit_price * new_qty},
                        conn=conn,
                    )
                else:
                    cart_repository.add_item(
                        {
                            "cart_id": int(customer_cart["cart_id"]),
                            "product_id": product_id,
                            "product_variant_id": variant_int,
                            "quantity": int(item["quantity"]),
                            "unit_price": float(item.get("unit_price") or 0),
                            "line_total": float(item.get("line_total") or 0),
                        },
                        conn=conn,
                    )
            cart_repository.deactivate_cart(int(guest_cart["cart_id"]), conn=conn)
            self._recalculate(int(customer_cart["cart_id"]), conn=conn)


cart_service = CartService()
