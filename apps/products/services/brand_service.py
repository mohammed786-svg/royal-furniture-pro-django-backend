from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from apps.products.repositories.brand_repository import brand_repository
from core.exceptions.base import NotFoundException, ValidationException
from core.helpers.text import from_db_text, make_slug, save_base64_image, to_db_text, unique_slug


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


def _maybe_logo(value: Any, *, prefix: str) -> str:
    if value is None or value == "":
        return "NA"
    if isinstance(value, str) and value.startswith("data:image"):
        return save_base64_image(value, subdir="brands", prefix=prefix)
    return str(value)


class BrandService:
    def _serialize(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": str(row["brand_id"]),
            "name": from_db_text(row.get("name")) or "",
            "slug": from_db_text(row.get("slug")) or "",
            "logoUrl": from_db_text(row.get("logo_url")),
            "description": from_db_text(row.get("description")),
            "websiteUrl": from_db_text(row.get("website_url")),
            "displayOrder": int(row.get("display_order") or 0),
            "isActive": bool(row.get("is_active")),
            "createdAt": _format_dt(row.get("created_at")),
            "updatedAt": _format_dt(row.get("updated_at")),
        }

    def list_brands(self, **kwargs) -> dict[str, Any]:
        rows, total = brand_repository.list_paginated(**_base_list_params(kwargs))
        page = kwargs.get("page", 1)
        page_size = kwargs.get("page_size", 20)
        return {
            "items": [self._serialize(r) for r in rows],
            "pagination": {
                "page": page,
                "pageSize": page_size,
                "total": total,
                "totalPages": max(1, (total + page_size - 1) // page_size),
            },
        }

    def get_brand(self, brand_id: int) -> dict[str, Any]:
        row = brand_repository.fetch_by_id(brand_id)
        if not row:
            raise NotFoundException("Brand not found")
        return self._serialize(row)

    def create_brand(self, payload: dict[str, Any]) -> dict[str, Any]:
        name = (payload.get("name") or "").strip()
        if not name:
            raise ValidationException(
                details=[{"field": "name", "message": "Brand name is required"}]
            )

        base_slug = make_slug((payload.get("slug") or "").strip() or name)
        slug = unique_slug(base_slug, lambda s: brand_repository.slug_exists(s))

        row = brand_repository.create({
            "name": to_db_text(name),
            "slug": slug,
            "logo_url": _maybe_logo(payload.get("logoUrl"), prefix="brand"),
            "description": to_db_text(payload.get("description")),
            "website_url": to_db_text(payload.get("websiteUrl")),
            "display_order": int(payload.get("displayOrder", 0)),
            "is_active": bool(payload.get("isActive", True)),
        })
        return self._serialize(row)

    def update_brand(self, brand_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        existing = brand_repository.fetch_by_id(brand_id)
        if not existing:
            raise NotFoundException("Brand not found")

        updates: dict[str, Any] = {}
        if "name" in payload:
            name = (payload.get("name") or "").strip()
            if not name:
                raise ValidationException(
                    details=[{"field": "name", "message": "Brand name is required"}]
                )
            updates["name"] = to_db_text(name)
        if "slug" in payload or "name" in payload:
            slug_input = (payload.get("slug") or "").strip()
            name_for_slug = updates.get("name", existing.get("name"))
            base_slug = make_slug(slug_input or from_db_text(name_for_slug) or "brand")
            updates["slug"] = unique_slug(
                base_slug,
                lambda s: brand_repository.slug_exists(s, exclude_id=brand_id),
            )
        if "logoUrl" in payload:
            updates["logo_url"] = _maybe_logo(payload.get("logoUrl"), prefix=f"brand-{brand_id}")
        if "description" in payload:
            updates["description"] = to_db_text(payload.get("description"))
        if "websiteUrl" in payload:
            updates["website_url"] = to_db_text(payload.get("websiteUrl"))
        if "displayOrder" in payload:
            updates["display_order"] = int(payload.get("displayOrder") or 0)
        if "isActive" in payload:
            updates["is_active"] = bool(payload.get("isActive"))

        row = brand_repository.update(brand_id, updates)
        if not row:
            raise NotFoundException("Brand not found")
        return self._serialize(row)

    def delete_brand(self, brand_id: int) -> None:
        if not brand_repository.soft_delete(brand_id):
            raise NotFoundException("Brand not found")


brand_service = BrandService()
