from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from apps.orders.repositories.order_item_repository import order_item_repository
from apps.orders.repositories.order_repository import order_repository
from core.exceptions.base import NotFoundException
from core.helpers.text import from_db_text


from core.constants.company import COMPANY_INFO, COMPANY_STATE

DEFAULT_GST_PERCENT = 18.0


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


def _normalize_state(value: str) -> str:
    return " ".join((value or "").strip().lower().split())


def _is_intra_state(customer_state: str) -> bool:
    customer = _normalize_state(customer_state)
    if not customer:
        return True
    company = _normalize_state(COMPANY_STATE)
    return customer == company or customer in company or company in customer


def _infer_gst_percent(taxable_amount: float, tax_amount: float) -> float:
    if taxable_amount <= 0 or tax_amount <= 0:
        return DEFAULT_GST_PERCENT
    inferred = round((tax_amount / taxable_amount) * 100, 2)
    return inferred if inferred > 0 else DEFAULT_GST_PERCENT


def _build_gst_breakdown(
    *,
    customer_state: str,
    taxable_amount: float,
    tax_amount: float,
) -> dict[str, Any]:
    gst_percent = _infer_gst_percent(taxable_amount, tax_amount)
    tax_amount = round(tax_amount, 2)

    if _is_intra_state(customer_state):
        half_rate = round(gst_percent / 2, 2)
        cgst_amount = round(tax_amount / 2, 2)
        sgst_amount = round(tax_amount - cgst_amount, 2)
        return {
            "mode": "intra",
            "gstPercent": gst_percent,
            "taxableAmount": round(taxable_amount, 2),
            "cgstPercent": half_rate,
            "cgstAmount": cgst_amount,
            "sgstPercent": half_rate,
            "sgstAmount": sgst_amount,
            "igstPercent": 0.0,
            "igstAmount": 0.0,
        }

    return {
        "mode": "inter",
        "gstPercent": gst_percent,
        "taxableAmount": round(taxable_amount, 2),
        "cgstPercent": 0.0,
        "cgstAmount": 0.0,
        "sgstPercent": 0.0,
        "sgstAmount": 0.0,
        "igstPercent": gst_percent,
        "igstAmount": tax_amount,
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
            gst_percent = float(item.get("product_gst_percent") or DEFAULT_GST_PERCENT)
            hsn = from_db_text(item.get("hsn_code")) or ""
            taxable_value = round(max(line_total - tax, 0), 2)

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
                "taxableValue": taxable_value,
                "lineTotal": line_total,
                "hsnCode": hsn,
                "gstPercent": gst_percent,
            })

        shipping = float(order.get("shipping_amount") or 0)
        grand_total = float(order.get("total_amount") or 0)
        discount_total = round(float(order.get("discount_amount") or total_discount), 2)
        tax_total = round(float(order.get("tax_amount") or total_tax), 2)
        taxable_amount = round(max(subtotal - discount_total, 0), 2)

        billing = _format_address("billing", order)
        shipping_address = _format_address("shipping", order)
        customer_state = billing.get("state") or shipping_address.get("state") or ""

        gst_breakdown = _build_gst_breakdown(
            customer_state=customer_state,
            taxable_amount=taxable_amount,
            tax_amount=tax_total,
        )

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
            "shippingAddress": shipping_address,
            "billingAddress": billing,
            "lineItems": line_items,
            "totals": {
                "subtotal": round(subtotal, 2),
                "discountAmount": discount_total,
                "taxableAmount": taxable_amount,
                "taxAmount": tax_total,
                "shippingAmount": round(shipping, 2),
                "grandTotal": round(grand_total, 2),
                "gstBreakdown": gst_breakdown,
            },
            "paymentMethod": from_db_text(order.get("payment_method")) or "",
            "currentStatus": from_db_text(order.get("current_status")) or "",
            "couponCode": from_db_text(order.get("coupon_code")),
            "notes": from_db_text(order.get("notes")),
        }


invoice_service = InvoiceService()
