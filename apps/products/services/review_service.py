from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from apps.products.repositories.product_repository import product_repository
from apps.products.repositories.product_review_repository import product_review_repository
from core.database import select_one
from core.database.transaction import atomic
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


class ReviewService:
    schema = "royal"

    def _serialize(self, row: dict[str, Any]) -> dict[str, Any]:
        approved_by = row.get("approved_by")
        order_id = row.get("order_id")
        return {
            "id": str(row["product_review_id"]),
            "productId": str(row["product_id"]),
            "productName": from_db_text(row.get("product_name")) or "",
            "productSku": from_db_text(row.get("product_sku")) or "",
            "customerId": str(row["customer_id"]),
            "customerName": from_db_text(row.get("customer_name")) or "",
            "customerEmail": from_db_text(row.get("customer_email")),
            "orderId": str(order_id) if order_id else None,
            "title": from_db_text(row.get("title")) or "",
            "reviewText": from_db_text(row.get("review_text")) or "",
            "rating": int(row.get("rating") or 0),
            "isVerifiedPurchase": bool(row.get("is_verified_purchase")),
            "isApproved": bool(row.get("is_approved")),
            "approvedBy": str(approved_by) if approved_by else None,
            "approvedAt": _format_dt(row.get("approved_at")),
            "isActive": bool(row.get("is_active")),
            "createdAt": _format_dt(row.get("created_at")),
            "updatedAt": _format_dt(row.get("updated_at")),
        }

    def _validate_customer(self, customer_id: int) -> None:
        sql = f"""
            SELECT customer_id
            FROM {self.schema}.customertbl
            WHERE customer_id = %s AND is_deleted = FALSE
        """
        if not select_one(sql, [customer_id]):
            raise ValidationException(
                details=[{"field": "customerId", "message": "Customer not found"}]
            )

    def _validate_rating(self, rating: int) -> None:
        if rating < 1 or rating > 5:
            raise ValidationException(
                details=[{"field": "rating", "message": "Rating must be between 1 and 5"}]
            )

    def list_reviews(self, **kwargs) -> dict[str, Any]:
        params = _base_list_params(kwargs)
        if kwargs.get("product_id") is not None:
            params["product_id"] = kwargs["product_id"]
        if kwargs.get("is_approved") is not None:
            params["is_approved"] = kwargs["is_approved"]
        rows, total = product_review_repository.list_paginated(**params)
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

    def get_review(self, review_id: int) -> dict[str, Any]:
        row = product_review_repository.fetch_by_id(review_id)
        if not row:
            raise NotFoundException("Review not found")
        return self._serialize(row)

    def create_review(self, payload: dict[str, Any]) -> dict[str, Any]:
        product_id = _optional_int(payload.get("productId"))
        customer_id = _optional_int(payload.get("customerId"))
        if not product_id:
            raise ValidationException(
                details=[{"field": "productId", "message": "Product is required"}]
            )
        if not customer_id:
            raise ValidationException(
                details=[{"field": "customerId", "message": "Customer is required"}]
            )
        if not product_repository.fetch_by_id(product_id):
            raise ValidationException(
                details=[{"field": "productId", "message": "Product not found"}]
            )
        self._validate_customer(customer_id)

        rating = int(payload.get("rating") or 0)
        self._validate_rating(rating)

        is_approved = bool(payload.get("isApproved", False))
        approved_by = None
        approved_at = None
        if is_approved:
            approved_by = _optional_int(payload.get("approvedBy"))
            approved_at = datetime.now()

        row = product_review_repository.create({
            "product_id": product_id,
            "customer_id": customer_id,
            "order_id": _optional_int(payload.get("orderId")),
            "title": to_db_text(payload.get("title")),
            "review_text": to_db_text(payload.get("reviewText")),
            "rating": rating,
            "is_verified_purchase": bool(payload.get("isVerifiedPurchase", False)),
            "is_approved": is_approved,
            "approved_by": approved_by,
            "approved_at": approved_at,
            "is_active": bool(payload.get("isActive", True)),
        })

        if is_approved:
            product_review_repository.recalculate_product_rating(product_id)

        refreshed = product_review_repository.fetch_by_id(int(row["product_review_id"]))
        return self._serialize(refreshed or row)

    def update_review(
        self,
        review_id: int,
        payload: dict[str, Any],
        *,
        admin_id: Optional[int] = None,
    ) -> dict[str, Any]:
        existing = product_review_repository.fetch_by_id(review_id)
        if not existing:
            raise NotFoundException("Review not found")

        status = (payload.get("status") or "").strip().upper()
        if status in {"APPROVED", "REJECTED"}:
            return self._update_review_status(
                review_id,
                existing,
                status=status,
                admin_id=admin_id,
            )

        updates: dict[str, Any] = {}
        was_approved = bool(existing.get("is_approved"))
        product_id = int(existing["product_id"])

        if "productId" in payload:
            new_product_id = _optional_int(payload.get("productId"))
            if not new_product_id:
                raise ValidationException(
                    details=[{"field": "productId", "message": "Product is required"}]
                )
            if not product_repository.fetch_by_id(new_product_id):
                raise ValidationException(
                    details=[{"field": "productId", "message": "Product not found"}]
                )
            updates["product_id"] = new_product_id
            product_id = new_product_id

        if "customerId" in payload:
            customer_id = _optional_int(payload.get("customerId"))
            if not customer_id:
                raise ValidationException(
                    details=[{"field": "customerId", "message": "Customer is required"}]
                )
            self._validate_customer(customer_id)
            updates["customer_id"] = customer_id

        if "orderId" in payload:
            updates["order_id"] = _optional_int(payload.get("orderId"))
        if "title" in payload:
            updates["title"] = to_db_text(payload.get("title"))
        if "reviewText" in payload:
            updates["review_text"] = to_db_text(payload.get("reviewText"))
        if "rating" in payload:
            rating = int(payload.get("rating") or 0)
            self._validate_rating(rating)
            updates["rating"] = rating
        if "isVerifiedPurchase" in payload:
            updates["is_verified_purchase"] = bool(payload.get("isVerifiedPurchase"))
        if "isActive" in payload:
            updates["is_active"] = bool(payload.get("isActive"))

        is_approved = was_approved
        if "isApproved" in payload:
            is_approved = bool(payload.get("isApproved"))
            updates["is_approved"] = is_approved
            if is_approved:
                updates["approved_by"] = admin_id
                updates["approved_at"] = datetime.now()
            else:
                updates["approved_by"] = None
                updates["approved_at"] = None

        row = product_review_repository.update(review_id, updates)
        if not row:
            raise NotFoundException("Review not found")

        old_product_id = int(existing["product_id"])
        new_product_id = int(row["product_id"])
        final_approved = bool(row.get("is_approved"))
        if was_approved:
            product_review_repository.recalculate_product_rating(old_product_id)
        if final_approved:
            product_review_repository.recalculate_product_rating(new_product_id)

        refreshed = product_review_repository.fetch_by_id(review_id)
        return self._serialize(refreshed or row)

    def _update_review_status(
        self,
        review_id: int,
        existing: dict[str, Any],
        *,
        status: str,
        admin_id: Optional[int],
    ) -> dict[str, Any]:
        was_approved = bool(existing.get("is_approved"))
        is_approved = status == "APPROVED"
        product_id = int(existing["product_id"])

        updates: dict[str, Any] = {
            "is_approved": is_approved,
            "approved_by": admin_id if is_approved else None,
            "approved_at": datetime.now() if is_approved else None,
        }

        with atomic() as conn:
            row = product_review_repository.update(review_id, updates, conn=conn)
            if not row:
                raise NotFoundException("Review not found")
            if was_approved or is_approved:
                product_review_repository.recalculate_product_rating(product_id, conn=conn)

        refreshed = product_review_repository.fetch_by_id(review_id)
        return self._serialize(refreshed or row)

    def delete_review(self, review_id: int) -> None:
        deleted = product_review_repository.soft_delete(review_id)
        if not deleted:
            raise NotFoundException("Review not found")
        if deleted.get("is_approved"):
            product_review_repository.recalculate_product_rating(int(deleted["product_id"]))


review_service = ReviewService()
