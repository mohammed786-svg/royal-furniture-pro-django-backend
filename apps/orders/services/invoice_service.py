from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from apps.orders.repositories.order_item_repository import order_item_repository
from apps.orders.repositories.order_repository import order_repository
from core.exceptions.base import NotFoundException
from core.helpers.text import from_db_text


COMPANY_INFO = {
    "name": "ROYAL FURNITURE PRO INCORPORATION PRIVATE LIMITED",
    "address": (
        "4th Floor, No 5, Raj square, Vijaya Bank Colony Main Road, "
        "Banaswadi Ring Road, Bengaluru Urban, Karnataka — 560043"
    ),
    "phone": "+91-7676367636",
    "email": "customercare@royalfurniturepro.com",
}


def _format_dt(value: Any) -> Optional[str]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _format_address(prefix: str, row: dict[str, Any]) -> dict[str, Any]:
    return {
        "fullName": from_db_text(row.get(f"{prefix}_full_name")) or from_db_text(row.get("customer_name")) or "",
        "phone": from_db_text(row.get(f"{prefix}_phone")) or from_db_text(row.get("customer_phone")) or "",
        "addressLine1": from_db_text(row.get(f"{prefix}_address_line1")) or "",
        "addressLine2": from_db_text(row.get(f"{prefix}_address_line2")) or "",
        "city": from_db_text(row.get(f"{prefix}_city")) or "",
        "state": from_db_text(row.get(f"{prefix}_state")) or "",
        "pincode": from_db_text(row.get(f"{prefix}_pincode")) or "",
    }


class InvoiceService:
    def build_invoice(self, order_id: int) -> dict[str, Any]:
        order = order_repository.fetch_by_id(order_id)
        if not order:
            raise NotFoundException("Order not found")

        items = order_item_repository.list_by_order(order_id)
        line_items = []
        subtotal = 0.0
        total_tax = 0.0
        total_discount = 0.0

        for item in items:
            qty = int(item.get("quantity") or 1)
            unit_price = float(item.get("unit_price") or 0)
            discount = float(item.get("discount_amount") or 0)
            tax = float(item.get("tax_amount") or 0)
            line_total = float(item.get("line_total") or 0)
            gst_percent = float(item.get("product_gst_percent") or 0)
            hsn = from_db_text(item.get("hsn_code")) or ""

            subtotal += unit_price * qty
            total_tax += tax
            total_discount += discount

            line_items.append({
                "id": str(item["order_item_id"]),
                "productId": str(item["product_id"]),
                "productName": from_db_text(item.get("product_name")) or "",
                "sku": from_db_text(item.get("sku")) or "",
                "quantity": qty,
                "unitPrice": unit_price,
                "discountAmount": discount,
                "taxAmount": tax,
                "lineTotal": line_total,
                "hsnCode": hsn,
                "gstPercent": gst_percent,
            })

        shipping = float(order.get("shipping_amount") or 0)
        grand_total = float(order.get("total_amount") or 0)

        return {
            "invoiceNumber": from_db_text(order.get("order_number")) or "",
            "invoiceDate": _format_dt(order.get("created_at")),
            "orderId": str(order["order_id"]),
            "orderNumber": from_db_text(order.get("order_number")) or "",
            "company": COMPANY_INFO,
            "customer": {
                "id": str(order["customer_id"]),
                "fullName": from_db_text(order.get("customer_name")) or "",
                "email": from_db_text(order.get("customer_email")) or "",
                "phone": from_db_text(order.get("customer_phone")) or "",
            },
            "shippingAddress": _format_address("shipping", order),
            "billingAddress": _format_address("billing", order),
            "lineItems": line_items,
            "totals": {
                "subtotal": round(subtotal, 2),
                "discountAmount": round(float(order.get("discount_amount") or total_discount), 2),
                "taxAmount": round(float(order.get("tax_amount") or total_tax), 2),
                "shippingAmount": round(shipping, 2),
                "grandTotal": round(grand_total, 2),
            },
            "paymentMethod": from_db_text(order.get("payment_method")) or "",
            "currentStatus": from_db_text(order.get("current_status")) or "",
            "couponCode": from_db_text(order.get("coupon_code")),
            "notes": from_db_text(order.get("notes")),
        }


invoice_service = InvoiceService()
