from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from apps.orders.repositories.order_repository import order_repository
from apps.payments.repositories.payment_repository import payment_repository
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


PAYMENT_STATUSES = {"PENDING", "PAID", "VERIFIED", "FAILED", "REFUNDED", "PARTIAL"}
PAYMENT_METHODS = {"QR", "UPI", "CARD", "COD", "WALLET", "BANK_TRANSFER"}


class PaymentService:
    def _serialize(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": str(row["payment_id"]),
            "orderId": str(row["order_id"]),
            "orderNumber": from_db_text(row.get("order_number")) or "",
            "customerId": str(row["customer_id"]),
            "customerName": from_db_text(row.get("customer_name")) or "",
            "paymentMethod": from_db_text(row.get("payment_method")) or "",
            "paymentAmount": float(row.get("payment_amount") or 0),
            "currency": from_db_text(row.get("currency")) or "INR",
            "paymentStatus": from_db_text(row.get("payment_status")) or "",
            "transactionRef": from_db_text(row.get("transaction_ref")),
            "paidAt": _format_dt(row.get("paid_at")),
            "createdAt": _format_dt(row.get("created_at")),
            "updatedAt": _format_dt(row.get("updated_at")),
        }

    def list_payments(self, **kwargs) -> dict[str, Any]:
        params = _base_list_params(kwargs)
        if kwargs.get("order_id") is not None:
            params["order_id"] = kwargs["order_id"]
        if kwargs.get("customer_id") is not None:
            params["customer_id"] = kwargs["customer_id"]
        if kwargs.get("payment_status"):
            params["payment_status"] = kwargs["payment_status"]
        rows, total = payment_repository.list_paginated(**params)
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

    def get_payment(self, payment_id: int) -> dict[str, Any]:
        row = payment_repository.fetch_by_id(payment_id)
        if not row:
            raise NotFoundException("Payment not found")
        return self._serialize(row)

    def create_payment(self, payload: dict[str, Any]) -> dict[str, Any]:
        order_id = _optional_int(payload.get("orderId"))
        customer_id = _optional_int(payload.get("customerId"))
        if not order_id:
            raise ValidationException(
                details=[{"field": "orderId", "message": "Order is required"}]
            )

        order = order_repository.fetch_by_id(order_id)
        if not order:
            raise NotFoundException("Order not found")

        if not customer_id:
            customer_id = int(order["customer_id"])

        payment_method = (payload.get("paymentMethod") or "QR").strip().upper()
        if payment_method not in PAYMENT_METHODS:
            raise ValidationException(
                details=[{
                    "field": "paymentMethod",
                    "message": f"Must be one of: {', '.join(sorted(PAYMENT_METHODS))}",
                }]
            )

        payment_status = (payload.get("paymentStatus") or "PENDING").strip().upper()
        if payment_status not in PAYMENT_STATUSES:
            raise ValidationException(
                details=[{
                    "field": "paymentStatus",
                    "message": f"Must be one of: {', '.join(sorted(PAYMENT_STATUSES))}",
                }]
            )

        paid_at = None
        if payload.get("paidAt"):
            paid_at = payload.get("paidAt")
        elif payment_status in ("PAID", "VERIFIED"):
            paid_at = datetime.now()

        row = payment_repository.create({
            "order_id": order_id,
            "customer_id": customer_id,
            "payment_method": payment_method,
            "payment_amount": float(payload.get("paymentAmount") or 0),
            "currency": payload.get("currency") or "INR",
            "payment_status": payment_status,
            "transaction_ref": to_db_text(payload.get("transactionRef")),
            "paid_at": paid_at,
        })
        return self._serialize(row)

    def update_payment(self, payment_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        existing = payment_repository.fetch_by_id(payment_id)
        if not existing:
            raise NotFoundException("Payment not found")

        updates: dict[str, Any] = {}
        if "paymentMethod" in payload:
            method = (payload.get("paymentMethod") or "").strip().upper()
            if method not in PAYMENT_METHODS:
                raise ValidationException(
                    details=[{"field": "paymentMethod", "message": "Invalid payment method"}]
                )
            updates["payment_method"] = method
        if "paymentAmount" in payload:
            updates["payment_amount"] = float(payload.get("paymentAmount") or 0)
        if "currency" in payload:
            updates["currency"] = payload.get("currency") or "INR"
        if "transactionRef" in payload:
            updates["transaction_ref"] = to_db_text(payload.get("transactionRef"))
        if "paidAt" in payload:
            updates["paid_at"] = payload.get("paidAt")
        if "paymentStatus" in payload:
            status = (payload.get("paymentStatus") or "").strip().upper()
            if status not in PAYMENT_STATUSES:
                raise ValidationException(
                    details=[{"field": "paymentStatus", "message": "Invalid payment status"}]
                )
            updates["payment_status"] = status
            if status in ("PAID", "VERIFIED") and "paidAt" not in payload:
                updates["paid_at"] = datetime.now()

        row = payment_repository.update(payment_id, updates)
        if not row:
            raise NotFoundException("Payment not found")
        return self._serialize(row)

    def delete_payment(self, payment_id: int) -> None:
        if not payment_repository.soft_delete(payment_id):
            raise NotFoundException("Payment not found")


payment_service = PaymentService()
