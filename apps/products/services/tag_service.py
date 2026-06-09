from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from apps.products.repositories.product_repository import product_repository
from apps.products.repositories.product_tag_map_repository import product_tag_map_repository
from apps.products.repositories.product_tag_repository import product_tag_repository
from core.database.transaction import atomic
from core.exceptions.base import NotFoundException, ValidationException
from core.helpers.text import from_db_text, make_slug, to_db_text, unique_slug


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


def _parse_product_ids(payload: dict[str, Any]) -> Optional[list[int]]:
    if "productIds" not in payload:
        return None
    raw = payload.get("productIds")
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise ValidationException(
            details=[{"field": "productIds", "message": "productIds must be an array"}]
        )
    product_ids: list[int] = []
    for item in raw:
        pid = _optional_int(item)
        if pid is None:
            raise ValidationException(
                details=[{"field": "productIds", "message": "Invalid product id in productIds"}]
            )
        product_ids.append(pid)
    return product_ids


def _base_list_params(kwargs: dict[str, Any]) -> dict[str, Any]:
    return {
        "page": kwargs.get("page", 1),
        "page_size": kwargs.get("page_size", 20),
        "search": kwargs.get("search", ""),
        "sort_by": kwargs.get("sort_by", "tag_name"),
        "sort_dir": kwargs.get("sort_dir", "asc"),
    }


class TagService:
    def _serialize(self, row: dict[str, Any], *, product_ids: Optional[list[int]] = None) -> dict[str, Any]:
        tag_id = int(row["product_tag_id"])
        if product_ids is None:
            product_ids = product_tag_map_repository.list_product_ids_for_tag(tag_id)
        product_count = row.get("product_count")
        if product_count is None:
            product_count = len(product_ids)
        return {
            "id": str(tag_id),
            "tagName": from_db_text(row.get("tag_name")) or "",
            "slug": from_db_text(row.get("slug")) or "",
            "isActive": bool(row.get("is_active")),
            "productCount": int(product_count or 0),
            "productIds": [str(pid) for pid in product_ids],
            "createdAt": _format_dt(row.get("created_at")),
            "updatedAt": _format_dt(row.get("updated_at")),
        }

    def _validate_product_ids(self, product_ids: list[int]) -> None:
        for product_id in product_ids:
            if not product_repository.fetch_by_id(product_id):
                raise ValidationException(
                    details=[{
                        "field": "productIds",
                        "message": f"Product {product_id} not found",
                    }]
                )

    def list_tags(self, **kwargs) -> dict[str, Any]:
        rows, total = product_tag_repository.list_paginated(**_base_list_params(kwargs))
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

    def get_tag(self, tag_id: int) -> dict[str, Any]:
        row = product_tag_repository.fetch_by_id(tag_id)
        if not row:
            raise NotFoundException("Tag not found")
        return self._serialize(row)

    def create_tag(self, payload: dict[str, Any]) -> dict[str, Any]:
        tag_name = (payload.get("tagName") or "").strip()
        if not tag_name:
            raise ValidationException(
                details=[{"field": "tagName", "message": "Tag name is required"}]
            )

        base_slug = make_slug((payload.get("slug") or "").strip() or tag_name)
        slug = unique_slug(base_slug, lambda s: product_tag_repository.slug_exists(s))

        product_ids = _parse_product_ids(payload) or []
        if product_ids:
            self._validate_product_ids(product_ids)

        with atomic() as conn:
            row = product_tag_repository.create(
                {
                    "tag_name": to_db_text(tag_name),
                    "slug": slug,
                    "is_active": bool(payload.get("isActive", True)),
                },
                conn=conn,
            )
            tag_id = int(row["product_tag_id"])
            if product_ids:
                product_tag_map_repository.sync_for_tag(tag_id, product_ids, conn=conn)

        return self.get_tag(tag_id)

    def update_tag(self, tag_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        existing = product_tag_repository.fetch_by_id(tag_id)
        if not existing:
            raise NotFoundException("Tag not found")

        updates: dict[str, Any] = {}
        if "tagName" in payload:
            tag_name = (payload.get("tagName") or "").strip()
            if not tag_name:
                raise ValidationException(
                    details=[{"field": "tagName", "message": "Tag name is required"}]
                )
            updates["tag_name"] = to_db_text(tag_name)
        if "slug" in payload or "tagName" in payload:
            slug_input = (payload.get("slug") or "").strip()
            name_for_slug = updates.get("tag_name", existing.get("tag_name"))
            base_slug = make_slug(slug_input or from_db_text(name_for_slug) or "tag")
            updates["slug"] = unique_slug(
                base_slug,
                lambda s: product_tag_repository.slug_exists(s, exclude_id=tag_id),
            )
        if "isActive" in payload:
            updates["is_active"] = bool(payload.get("isActive"))

        product_ids = _parse_product_ids(payload)
        if product_ids is not None:
            self._validate_product_ids(product_ids)

        with atomic() as conn:
            if updates:
                row = product_tag_repository.update(tag_id, updates, conn=conn)
                if not row:
                    raise NotFoundException("Tag not found")
            if product_ids is not None:
                product_tag_map_repository.sync_for_tag(tag_id, product_ids, conn=conn)

        return self.get_tag(tag_id)

    def delete_tag(self, tag_id: int) -> None:
        if not product_tag_repository.fetch_by_id(tag_id):
            raise NotFoundException("Tag not found")
        with atomic() as conn:
            product_tag_map_repository.deactivate_all_for_tag(tag_id, conn=conn)
            if not product_tag_repository.soft_delete(tag_id, conn=conn):
                raise NotFoundException("Tag not found")


tag_service = TagService()
