from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from apps.payments.repositories.payment_repository import payment_repository
from apps.payments.repositories.payment_verification_repository import (
    payment_verification_repository,
)
from core.exceptions.base import NotFoundException, ValidationException
from core.helpers.text import from_db_text, save_base64_image, to_db_text


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


VERIFICATION_STATUSES = {"PENDING", "APPROVED", "REJECTED"}


class PaymentVerificationService:
    def _serialize(self, row: dict[str, Any]) -> dict[str, Any]:
        verified_by = row.get("verified_by")
        return {
            "id": str(row["payment_verification_id"]),
            "paymentId": str(row["payment_id"]),
            "orderId": str(row["order_id"]),
            "orderNumber": from_db_text(row.get("order_number")) or "",
            "customerName": from_db_text(row.get("customer_name")) or "",
            "utrNumber": from_db_text(row.get("utr_number")) or "",
            "paymentAmount": float(row.get("payment_amount") or 0),
            "screenshotUrl": from_db_text(row.get("screenshot_url")),
            "verificationStatus": from_db_text(row.get("verification_status")) or "PENDING",
            "verifiedBy": str(verified_by) if verified_by else None,
            "verifiedByName": from_db_text(row.get("verified_by_name")),
            "verificationTime": _format_dt(row.get("verification_time")),
            "remarks": from_db_text(row.get("remarks")),
            "createdAt": _format_dt(row.get("created_at")),
            "updatedAt": _format_dt(row.get("updated_at")),
        }

    def _resolve_screenshot(self, payload: dict[str, Any], *, prefix: str) -> Optional[str]:
        value = payload.get("screenshotUrl") or payload.get("screenshot")
        if not value:
            return None
        if isinstance(value, str) and value.startswith(("http://", "https://", "/")):
            return value
        return save_base64_image(str(value), subdir="payments", prefix=prefix)

    def list_verifications(self, **kwargs) -> dict[str, Any]:
        params = _base_list_params(kwargs)
        if kwargs.get("payment_id") is not None:
            params["payment_id"] = kwargs["payment_id"]
        if kwargs.get("order_id") is not None:
            params["order_id"] = kwargs["order_id"]
        if kwargs.get("verification_status"):
            params["verification_status"] = kwargs["verification_status"]
        rows, total = payment_verification_repository.list_paginated(**params)
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

    def get_verification(self, verification_id: int) -> dict[str, Any]:
        row = payment_verification_repository.fetch_by_id(verification_id)
        if not row:
            raise NotFoundException("Payment verification not found")
        return self._serialize(row)

    def create_verification(self, payload: dict[str, Any]) -> dict[str, Any]:
        payment_id = _optional_int(payload.get("paymentId"))
        order_id = _optional_int(payload.get("orderId"))
        if not payment_id:
            raise ValidationException(
                details=[{"field": "paymentId", "message": "Payment is required"}]
            )

        payment = payment_repository.fetch_by_id(payment_id)
        if not payment:
            raise NotFoundException("Payment not found")

        if not order_id:
            order_id = int(payment["order_id"])
        elif order_id != int(payment["order_id"]):
            raise ValidationException(
                details=[{"field": "orderId", "message": "Order does not match payment"}]
            )

        utr_number = (payload.get("utrNumber") or "").strip()
        if not utr_number:
            raise ValidationException(
                details=[{"field": "utrNumber", "message": "UTR number is required"}]
            )

        screenshot_url = self._resolve_screenshot(payload, prefix=f"ver-{payment_id}")
        if not screenshot_url:
            screenshot_url = "NA"

        row = payment_verification_repository.create({
            "payment_id": payment_id,
            "order_id": order_id,
            "utr_number": utr_number,
            "payment_amount": float(
                payload.get("paymentAmount") or payment.get("payment_amount") or 0
            ),
            "screenshot_url": screenshot_url,
            "verification_status": "PENDING",
            "remarks": to_db_text(payload.get("remarks")),
        })
        return self._serialize(row)

    def update_verification(
        self,
        verification_id: int,
        payload: dict[str, Any],
        *,
        admin_id: Optional[int] = None,
    ) -> dict[str, Any]:
        existing = payment_verification_repository.fetch_by_id(verification_id)
        if not existing:
            raise NotFoundException("Payment verification not found")

        updates: dict[str, Any] = {}
        if "utrNumber" in payload:
            utr = (payload.get("utrNumber") or "").strip()
            if not utr:
                raise ValidationException(
                    details=[{"field": "utrNumber", "message": "UTR number cannot be empty"}]
                )
            updates["utr_number"] = utr
        if "paymentAmount" in payload:
            updates["payment_amount"] = float(payload.get("paymentAmount") or 0)
        if "remarks" in payload:
            updates["remarks"] = to_db_text(payload.get("remarks"))
        if "screenshotUrl" in payload or "screenshot" in payload:
            screenshot = self._resolve_screenshot(
                payload,
                prefix=f"ver-{existing['payment_id']}",
            )
            if screenshot:
                updates["screenshot_url"] = screenshot

        if "verificationStatus" in payload:
            status = (payload.get("verificationStatus") or "").strip().upper()
            if status not in VERIFICATION_STATUSES:
                raise ValidationException(
                    details=[{
                        "field": "verificationStatus",
                        "message": f"Must be one of: {', '.join(sorted(VERIFICATION_STATUSES))}",
                    }]
                )
            updates["verification_status"] = status
            if status in ("APPROVED", "REJECTED"):
                if not admin_id:
                    raise ValidationException(
                        details=[{"field": "verificationStatus", "message": "Admin required"}]
                    )
                updates["verified_by"] = admin_id
                updates["verification_time"] = datetime.now()
                if status == "APPROVED":
                    payment_repository.update(
                        int(existing["payment_id"]),
                        {"payment_status": "VERIFIED", "paid_at": datetime.now()},
                    )

        row = payment_verification_repository.update(verification_id, updates)
        if not row:
            raise NotFoundException("Payment verification not found")
        return self._serialize(row)

    def delete_verification(self, verification_id: int) -> None:
        if not payment_verification_repository.soft_delete(verification_id):
            raise NotFoundException("Payment verification not found")


payment_verification_service = PaymentVerificationService()
