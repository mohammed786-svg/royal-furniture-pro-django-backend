from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from django.http import HttpRequest
from psycopg2.extras import Json

from apps.customers.repositories.address_repository import address_repository
from apps.orders.repositories.order_history_repository import order_history_repository
from apps.orders.repositories.order_item_repository import order_item_repository
from apps.orders.repositories.order_repository import order_repository
from apps.orders.repositories.order_status_repository import order_status_repository
from apps.orders.services.order_service import order_service
from apps.payments.repositories.payment_repository import payment_repository
from apps.payments.repositories.payment_verification_repository import payment_verification_repository
from apps.storefront.helpers.commerce_context import require_customer_id, resolve_guest_session
from apps.storefront.repositories.cart_repository import cart_repository
from apps.storefront.services.cart_service import cart_service
from apps.storefront.services.inventory_stock_service import inventory_stock_service
from core.database.transaction import atomic
from core.exceptions.base import ValidationException
from core.helpers.ip import get_client_ip
from core.helpers.text import from_db_text, save_base64_image, to_db_text


def _optional_int(value: Any) -> Optional[int]:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


PAYMENT_METHOD_MAP = {
    "upi_qr": "UPI_QR",
    "bank_transfer": "BANK_TRANSFER",
    "gpay": "GPAY",
}


class CheckoutService:
    def place_order(self, request: HttpRequest, payload: dict[str, Any]) -> dict[str, Any]:
        customer_id = require_customer_id(request)
        shipping_address_id = _optional_int(payload.get("shippingAddressId"))
        billing_address_id = _optional_int(payload.get("billingAddressId")) or shipping_address_id
        if not shipping_address_id:
            raise ValidationException(
                details=[{"field": "shippingAddressId", "message": "Shipping address is required"}]
            )

        shipping = address_repository.fetch_by_id(shipping_address_id)
        if not shipping or int(shipping["customer_id"]) != customer_id:
            raise ValidationException(
                details=[{"field": "shippingAddressId", "message": "Shipping address not found"}]
            )
        if billing_address_id:
            billing = address_repository.fetch_by_id(billing_address_id)
            if not billing or int(billing["customer_id"]) != customer_id:
                raise ValidationException(
                    details=[{"field": "billingAddressId", "message": "Billing address not found"}]
                )

        transaction_ref = (payload.get("transactionRef") or payload.get("paymentReference") or "").strip()
        if len(transaction_ref) < 4:
            raise ValidationException(
                details=[{"field": "transactionRef", "message": "Payment reference is required"}]
            )

        method_key = (payload.get("paymentMethod") or "upi_qr").strip().lower()
        payment_method = PAYMENT_METHOD_MAP.get(method_key, method_key.upper())

        session_id = resolve_guest_session(request)
        cart = cart_service.get_cart(request)
        if not cart.get("items"):
            raise ValidationException(
                details=[{"field": "cart", "message": "Your cart is empty"}]
            )

        items_payload = [
            {
                "productId": int(item["productId"]),
                "productVariantId": _optional_int(item.get("productVariantId")),
                "quantity": int(item["quantity"]),
            }
            for item in cart["items"]
        ]

        status_row = order_status_repository.fetch_by_code("PENDING")
        if not status_row:
            status_row = order_status_repository.fetch_by_code("CONFIRMED")
        status_code = from_db_text(status_row.get("status_code")) or "PENDING"

        with atomic() as conn:
            from apps.orders.services.order_service import _generate_order_number

            resolved_items = [order_service._resolve_item(item) for item in items_payload]
            subtotal = sum(i["unit_price"] * i["quantity"] for i in resolved_items)
            tax_amount = sum(i["tax_amount"] for i in resolved_items)
            total_amount = subtotal + tax_amount
            order_number = _generate_order_number(conn=conn)
            order = order_repository.create(
                {
                    "order_number": order_number,
                    "customer_id": customer_id,
                    "order_status_id": int(status_row["order_status_id"]),
                    "current_status": status_code,
                    "subtotal": subtotal,
                    "discount_amount": 0,
                    "tax_amount": tax_amount,
                    "shipping_amount": 0,
                    "total_amount": total_amount,
                    "coupon_id": None,
                    "coupon_code": "NA",
                    "shipping_address_id": shipping_address_id,
                    "billing_address_id": billing_address_id,
                    "payment_method": payment_method,
                    "notes": "NA",
                    "ip_address": to_db_text(get_client_ip(request)),
                    "user_agent": to_db_text(request.META.get("HTTP_USER_AGENT", "unknown")[:500]),
                },
                conn=conn,
            )
            order_id = int(order["order_id"])

            for item in resolved_items:
                wh_id = inventory_stock_service.deduct_for_order_item(
                    product_id=item["product_id"],
                    product_variant_id=item.get("product_variant_id"),
                    warehouse_id=item.get("warehouse_id"),
                    quantity=item["quantity"],
                    order_id=order_id,
                    performed_by=getattr(request, "user_id", None),
                    conn=conn,
                )
                item["warehouse_id"] = wh_id
                order_item_repository.create({"order_id": order_id, **item}, conn=conn)

            order_history_repository.create(
                {
                    "order_id": order_id,
                    "from_status": "NA",
                    "to_status": status_code,
                    "changed_by": getattr(request, "user_id", None),
                    "change_reason": to_db_text("Order placed via storefront checkout"),
                    "metadata": Json({"source": "storefront", "stockDeducted": True}),
                    "changed_at": datetime.now(),
                },
                conn=conn,
            )

            payment = payment_repository.create(
                {
                    "order_id": order_id,
                    "customer_id": customer_id,
                    "payment_method": payment_method,
                    "payment_amount": total_amount,
                    "currency": "INR",
                    "payment_status": "PENDING",
                    "transaction_ref": to_db_text(transaction_ref),
                    "paid_at": None,
                },
                conn=conn,
            )
            payment_id = int(payment["payment_id"])

            screenshot = payload.get("screenshot") or payload.get("screenshotUrl")
            screenshot_url = "NA"
            if screenshot:
                if isinstance(screenshot, str) and screenshot.startswith(("http://", "https://", "/")):
                    screenshot_url = screenshot
                else:
                    saved = save_base64_image(str(screenshot), subdir="payments", prefix=f"order-{order_id}")
                    if saved:
                        screenshot_url = saved

            payment_verification_repository.create(
                {
                    "payment_id": payment_id,
                    "order_id": order_id,
                    "utr_number": transaction_ref,
                    "payment_amount": total_amount,
                    "screenshot_url": screenshot_url,
                    "verification_status": "PENDING",
                    "remarks": to_db_text(payload.get("remarks") or "NA"),
                },
                conn=conn,
            )

            active_cart = cart_repository.fetch_active_cart(customer_id=customer_id, conn=conn)
            if active_cart:
                cart_repository.clear_items(int(active_cart["cart_id"]), conn=conn)
                cart_repository.update_cart(
                    int(active_cart["cart_id"]),
                    {"subtotal": 0, "total_amount": 0, "item_count": 0},
                    conn=conn,
                )

        detail = order_service.get_order(order_id)
        return {
            "orderId": str(order_id),
            "orderNumber": detail.get("orderNumber") or order_number,
            "status": detail.get("currentStatus") or status_code,
            "totalAmount": detail.get("totalAmount") or total_amount,
            "paymentStatus": "PENDING",
        }


checkout_service = CheckoutService()
