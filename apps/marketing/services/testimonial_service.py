from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from apps.marketing.repositories.testimonial_repository import testimonial_repository
from core.database import select_one
from core.exceptions.base import NotFoundException, ValidationException
from core.helpers.text import from_db_text, save_base64_image, to_db_text


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
        "sort_by": kwargs.get("sort_by", "display_order"),
        "sort_dir": kwargs.get("sort_dir", "asc"),
    }


def _pagination(page: int, page_size: int, total: int) -> dict[str, Any]:
    return {
        "page": page,
        "pageSize": page_size,
        "total": total,
        "totalPages": max(1, (total + page_size - 1) // page_size),
    }


def _optional_int(value: Any) -> Optional[int]:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _maybe_image(value: Any, *, prefix: str) -> str:
    if value is None or value == "":
        return "NA"
    if isinstance(value, str) and value.startswith("data:image"):
        return save_base64_image(value, subdir="testimonials", prefix=prefix)
    return str(value)


class TestimonialService:
    schema = "royal"

    def _serialize(self, row: dict[str, Any]) -> dict[str, Any]:
        product_id = row.get("product_id")
        return {
            "id": str(row["testimonial_id"]),
            "customerName": from_db_text(row.get("customer_name")) or "",
            "customerImage": from_db_text(row.get("customer_image")),
            "location": from_db_text(row.get("location")),
            "rating": int(row.get("rating") or 5),
            "testimonialText": from_db_text(row.get("testimonial_text")) or "",
            "productId": str(product_id) if product_id else None,
            "productName": from_db_text(row.get("product_name")),
            "productSku": from_db_text(row.get("product_sku")),
            "isFeatured": bool(row.get("is_featured")),
            "displayOrder": int(row.get("display_order") or 0),
            "isActive": bool(row.get("is_active")),
            "createdAt": _format_dt(row.get("created_at")),
            "updatedAt": _format_dt(row.get("updated_at")),
        }

    def _validate_rating(self, rating: int) -> None:
        if rating < 1 or rating > 5:
            raise ValidationException(
                details=[{"field": "rating", "message": "Rating must be between 1 and 5"}]
            )

    def _validate_product(self, product_id: Optional[int]) -> None:
        if product_id is None:
            return
        sql = f"""
            SELECT product_id
            FROM {self.schema}.producttbl
            WHERE product_id = %s AND is_deleted = FALSE
        """
        if not select_one(sql, [product_id]):
            raise ValidationException(
                details=[{"field": "productId", "message": "Product not found"}]
            )

    def list_testimonials(self, **kwargs) -> dict[str, Any]:
        rows, total = testimonial_repository.list_paginated(**_base_list_params(kwargs))
        page = kwargs.get("page", 1)
        page_size = kwargs.get("page_size", 20)
        return {
            "items": [self._serialize(r) for r in rows],
            "pagination": _pagination(page, page_size, total),
        }

    def get_testimonial(self, testimonial_id: int) -> dict[str, Any]:
        row = testimonial_repository.fetch_by_id(testimonial_id)
        if not row:
            raise NotFoundException("Testimonial not found")
        return self._serialize(row)

    def create_testimonial(self, payload: dict[str, Any]) -> dict[str, Any]:
        customer_name = (payload.get("customerName") or "").strip()
        if not customer_name:
            raise ValidationException(
                details=[{"field": "customerName", "message": "Customer name is required"}]
            )

        rating = int(payload.get("rating") or 5)
        self._validate_rating(rating)
        product_id = _optional_int(payload.get("productId"))
        self._validate_product(product_id)

        row = testimonial_repository.create({
            "customer_name": to_db_text(customer_name),
            "customer_image": _maybe_image(payload.get("customerImage"), prefix="testimonial"),
            "location": to_db_text(payload.get("location")),
            "rating": rating,
            "testimonial_text": to_db_text(payload.get("testimonialText")),
            "product_id": product_id,
            "is_featured": bool(payload.get("isFeatured", False)),
            "display_order": int(payload.get("displayOrder") or 0),
            "is_active": bool(payload.get("isActive", True)),
        })
        detail = testimonial_repository.fetch_by_id(int(row["testimonial_id"]))
        return self._serialize(detail or row)

    def update_testimonial(self, testimonial_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        existing = testimonial_repository.fetch_by_id(testimonial_id)
        if not existing:
            raise NotFoundException("Testimonial not found")

        updates: dict[str, Any] = {}
        if "customerName" in payload:
            customer_name = (payload.get("customerName") or "").strip()
            if not customer_name:
                raise ValidationException(
                    details=[{"field": "customerName", "message": "Customer name is required"}]
                )
            updates["customer_name"] = to_db_text(customer_name)
        if "customerImage" in payload:
            updates["customer_image"] = _maybe_image(
                payload.get("customerImage"),
                prefix=f"testimonial-{testimonial_id}",
            )
        if "location" in payload:
            updates["location"] = to_db_text(payload.get("location"))
        if "rating" in payload:
            rating = int(payload.get("rating") or 5)
            self._validate_rating(rating)
            updates["rating"] = rating
        if "testimonialText" in payload:
            updates["testimonial_text"] = to_db_text(payload.get("testimonialText"))
        if "productId" in payload:
            product_id = _optional_int(payload.get("productId"))
            self._validate_product(product_id)
            updates["product_id"] = product_id
        if "isFeatured" in payload:
            updates["is_featured"] = bool(payload.get("isFeatured"))
        if "displayOrder" in payload:
            updates["display_order"] = int(payload.get("displayOrder") or 0)
        if "isActive" in payload:
            updates["is_active"] = bool(payload.get("isActive"))

        row = testimonial_repository.update(testimonial_id, updates)
        if not row:
            raise NotFoundException("Testimonial not found")
        return self._serialize(row)

    def delete_testimonial(self, testimonial_id: int) -> None:
        if not testimonial_repository.soft_delete(testimonial_id):
            raise NotFoundException("Testimonial not found")


testimonial_service = TestimonialService()
