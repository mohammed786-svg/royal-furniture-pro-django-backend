from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from apps.categories.repositories.category_repository import category_repository
from apps.categories.repositories.sub_category_repository import sub_category_repository
from apps.categories.repositories.under_sub_category_repository import under_sub_category_repository
from core.cache.cache_keys import CacheKeys
from core.cache.cache_manager import cache_manager
from core.exceptions.base import NotFoundException, ValidationException
from core.helpers.text import from_db_text, make_slug, save_base64_image, to_db_text, unique_slug


def _format_dt(value: Any) -> Optional[str]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _maybe_image(value: Any, *, prefix: str, field_key: str, updates: dict[str, Any]) -> None:
    if value is None:
        return
    if isinstance(value, str) and value.startswith("data:image"):
        updates[field_key] = save_base64_image(value, subdir="categories", prefix=prefix)
    elif value == "":
        updates[field_key] = "NA"
    elif isinstance(value, str):
        updates[field_key] = value


def _base_list_params(kwargs: dict[str, Any]) -> dict[str, Any]:
    return {
        "page": kwargs.get("page", 1),
        "page_size": kwargs.get("page_size", 20),
        "search": kwargs.get("search", ""),
        "sort_by": kwargs.get("sort_by", "display_order"),
        "sort_dir": kwargs.get("sort_dir", "asc"),
    }


class CategoryService:
    def _invalidate_nav_cache(self) -> None:
        cache_manager.delete(CacheKeys.navbar())

    def _serialize_category(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": str(row["category_id"]),
            "name": from_db_text(row.get("name")) or "",
            "slug": from_db_text(row.get("slug")) or "",
            "imageUrl": from_db_text(row.get("image_url")),
            "iconUrl": from_db_text(row.get("icon_url")),
            "bannerUrl": from_db_text(row.get("banner_url")),
            "seoTitle": from_db_text(row.get("seo_title")),
            "seoDescription": from_db_text(row.get("seo_description")),
            "seoKeywords": from_db_text(row.get("seo_keywords")),
            "displayOrder": int(row.get("display_order") or 0),
            "isVisible": bool(row.get("is_visible")),
            "isFeatured": bool(row.get("is_featured")),
            "isActive": bool(row.get("is_active")),
            "subCategoryCount": int(row.get("sub_category_count") or 0),
            "createdAt": _format_dt(row.get("created_at")),
            "updatedAt": _format_dt(row.get("updated_at")),
        }

    def _serialize_sub_category(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": str(row["sub_category_id"]),
            "categoryId": str(row["category_id"]),
            "categoryName": from_db_text(row.get("category_name")) or "",
            "name": from_db_text(row.get("name")) or "",
            "slug": from_db_text(row.get("slug")) or "",
            "imageUrl": from_db_text(row.get("image_url")),
            "iconUrl": from_db_text(row.get("icon_url")),
            "bannerUrl": from_db_text(row.get("banner_url")),
            "seoTitle": from_db_text(row.get("seo_title")),
            "seoDescription": from_db_text(row.get("seo_description")),
            "seoKeywords": from_db_text(row.get("seo_keywords")),
            "displayOrder": int(row.get("display_order") or 0),
            "isVisible": bool(row.get("is_visible")),
            "isActive": bool(row.get("is_active")),
            "underSubCategoryCount": int(row.get("under_sub_category_count") or 0),
            "createdAt": _format_dt(row.get("created_at")),
            "updatedAt": _format_dt(row.get("updated_at")),
        }

    def _serialize_under_sub_category(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": str(row["under_sub_category_id"]),
            "subCategoryId": str(row["sub_category_id"]),
            "categoryId": str(row["category_id"]),
            "categoryName": from_db_text(row.get("category_name")) or "",
            "subCategoryName": from_db_text(row.get("sub_category_name")) or "",
            "name": from_db_text(row.get("name")) or "",
            "slug": from_db_text(row.get("slug")) or "",
            "imageUrl": from_db_text(row.get("image_url")),
            "iconUrl": from_db_text(row.get("icon_url")),
            "bannerUrl": from_db_text(row.get("banner_url")),
            "seoTitle": from_db_text(row.get("seo_title")),
            "seoDescription": from_db_text(row.get("seo_description")),
            "seoKeywords": from_db_text(row.get("seo_keywords")),
            "displayOrder": int(row.get("display_order") or 0),
            "isVisible": bool(row.get("is_visible")),
            "isActive": bool(row.get("is_active")),
            "createdAt": _format_dt(row.get("created_at")),
            "updatedAt": _format_dt(row.get("updated_at")),
        }

    def list_categories(self, **kwargs) -> dict[str, Any]:
        rows, total = category_repository.list_paginated(**_base_list_params(kwargs))
        page = kwargs.get("page", 1)
        page_size = kwargs.get("page_size", 20)
        return {
            "items": [self._serialize_category(r) for r in rows],
            "pagination": {
                "page": page,
                "pageSize": page_size,
                "total": total,
                "totalPages": max(1, (total + page_size - 1) // page_size),
            },
        }

    def list_sub_categories(self, **kwargs) -> dict[str, Any]:
        params = _base_list_params(kwargs)
        if kwargs.get("category_id") is not None:
            params["category_id"] = kwargs["category_id"]
        rows, total = sub_category_repository.list_paginated(**params)
        page = kwargs.get("page", 1)
        page_size = kwargs.get("page_size", 20)
        return {
            "items": [self._serialize_sub_category(r) for r in rows],
            "pagination": {
                "page": page,
                "pageSize": page_size,
                "total": total,
                "totalPages": max(1, (total + page_size - 1) // page_size),
            },
        }

    def list_under_sub_categories(self, **kwargs) -> dict[str, Any]:
        params = _base_list_params(kwargs)
        if kwargs.get("category_id") is not None:
            params["category_id"] = kwargs["category_id"]
        if kwargs.get("sub_category_id") is not None:
            params["sub_category_id"] = kwargs["sub_category_id"]
        rows, total = under_sub_category_repository.list_paginated(**params)
        page = kwargs.get("page", 1)
        page_size = kwargs.get("page_size", 20)
        return {
            "items": [self._serialize_under_sub_category(r) for r in rows],
            "pagination": {
                "page": page,
                "pageSize": page_size,
                "total": total,
                "totalPages": max(1, (total + page_size - 1) // page_size),
            },
        }

    def get_options(self) -> dict[str, Any]:
        categories = category_repository.list_options()
        return {
            "categories": [
                {
                    "id": str(c["category_id"]),
                    "name": from_db_text(c.get("name")) or "",
                    "slug": from_db_text(c.get("slug")) or "",
                }
                for c in categories
            ],
        }

    def get_sub_category_options(self, category_id: Optional[int] = None) -> dict[str, Any]:
        rows = sub_category_repository.list_options(category_id)
        return {
            "subCategories": [
                {
                    "id": str(r["sub_category_id"]),
                    "categoryId": str(r["category_id"]),
                    "categoryName": from_db_text(r.get("category_name")) or "",
                    "name": from_db_text(r.get("name")) or "",
                    "slug": from_db_text(r.get("slug")) or "",
                }
                for r in rows
            ],
        }

    def create_category(self, payload: dict[str, Any]) -> dict[str, Any]:
        name = (payload.get("name") or "").strip()
        if not name:
            raise ValidationException(details=[{"field": "name", "message": "Name is required"}])

        slug_input = (payload.get("slug") or "").strip()
        base_slug = make_slug(slug_input or name)
        slug = unique_slug(base_slug, lambda s: category_repository.slug_exists(s))

        data = {
            "name": to_db_text(name),
            "slug": slug,
            "image_url": "NA",
            "icon_url": "NA",
            "banner_url": "NA",
            "seo_title": to_db_text(payload.get("seoTitle")),
            "seo_description": to_db_text(payload.get("seoDescription")),
            "seo_keywords": to_db_text(payload.get("seoKeywords")),
            "display_order": int(payload.get("displayOrder") or 0),
            "is_visible": bool(payload.get("isVisible", True)),
            "is_featured": bool(payload.get("isFeatured", False)),
            "is_active": bool(payload.get("isActive", True)),
        }
        _maybe_image(payload.get("imageUrl"), prefix="category", field_key="image_url", updates=data)
        _maybe_image(payload.get("iconUrl"), prefix="category-icon", field_key="icon_url", updates=data)
        _maybe_image(payload.get("bannerUrl"), prefix="category-banner", field_key="banner_url", updates=data)

        row = category_repository.create(data)
        self._invalidate_nav_cache()
        return self._serialize_category(row)

    def update_category(self, category_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        existing = category_repository.fetch_by_id(category_id)
        if not existing:
            raise NotFoundException("Category not found")

        updates: dict[str, Any] = {}
        if "name" in payload:
            name = (payload.get("name") or "").strip()
            if not name:
                raise ValidationException(details=[{"field": "name", "message": "Name is required"}])
            updates["name"] = to_db_text(name)
        if "slug" in payload:
            slug = make_slug((payload.get("slug") or "").strip() or updates.get("name", existing["name"]))
            slug = unique_slug(
                slug,
                lambda s: category_repository.slug_exists(s, exclude_id=category_id),
            )
            updates["slug"] = slug
        for key, db_key in [
            ("seoTitle", "seo_title"),
            ("seoDescription", "seo_description"),
            ("seoKeywords", "seo_keywords"),
        ]:
            if key in payload:
                updates[db_key] = to_db_text(payload.get(key))
        if "displayOrder" in payload:
            updates["display_order"] = int(payload.get("displayOrder") or 0)
        if "isVisible" in payload:
            updates["is_visible"] = bool(payload.get("isVisible"))
        if "isFeatured" in payload:
            updates["is_featured"] = bool(payload.get("isFeatured"))
        if "isActive" in payload:
            updates["is_active"] = bool(payload.get("isActive"))

        _maybe_image(payload.get("imageUrl"), prefix="category", field_key="image_url", updates=updates)
        _maybe_image(payload.get("iconUrl"), prefix="category-icon", field_key="icon_url", updates=updates)
        _maybe_image(payload.get("bannerUrl"), prefix="category-banner", field_key="banner_url", updates=updates)

        row = category_repository.update(category_id, updates)
        if not row:
            raise NotFoundException("Category not found")
        self._invalidate_nav_cache()
        refreshed = category_repository.fetch_by_id(category_id)
        return self._serialize_category(refreshed or row)

    def delete_category(self, category_id: int) -> None:
        if not category_repository.soft_delete(category_id):
            raise NotFoundException("Category not found")
        self._invalidate_nav_cache()

    def create_sub_category(self, payload: dict[str, Any]) -> dict[str, Any]:
        name = (payload.get("name") or "").strip()
        category_id = payload.get("categoryId")
        if not name:
            raise ValidationException(details=[{"field": "name", "message": "Name is required"}])
        if not category_id:
            raise ValidationException(details=[{"field": "categoryId", "message": "Category is required"}])

        category_id = int(category_id)
        if not category_repository.fetch_by_id(category_id):
            raise ValidationException(details=[{"field": "categoryId", "message": "Category not found"}])

        base_slug = make_slug((payload.get("slug") or "").strip() or name)
        slug = unique_slug(
            base_slug,
            lambda s: sub_category_repository.slug_exists(category_id, s),
        )

        data = {
            "category_id": category_id,
            "name": to_db_text(name),
            "slug": slug,
            "image_url": "NA",
            "icon_url": "NA",
            "banner_url": "NA",
            "seo_title": to_db_text(payload.get("seoTitle")),
            "seo_description": to_db_text(payload.get("seoDescription")),
            "seo_keywords": to_db_text(payload.get("seoKeywords")),
            "display_order": int(payload.get("displayOrder") or 0),
            "is_visible": bool(payload.get("isVisible", True)),
            "is_active": bool(payload.get("isActive", True)),
        }
        _maybe_image(payload.get("imageUrl"), prefix="sub-category", field_key="image_url", updates=data)
        _maybe_image(payload.get("iconUrl"), prefix="sub-category-icon", field_key="icon_url", updates=data)
        _maybe_image(payload.get("bannerUrl"), prefix="sub-category-banner", field_key="banner_url", updates=data)

        row = sub_category_repository.create(data)
        self._invalidate_nav_cache()
        full = sub_category_repository.fetch_by_id(row["sub_category_id"])
        return self._serialize_sub_category(full or row)

    def update_sub_category(self, sub_category_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        existing = sub_category_repository.fetch_by_id(sub_category_id)
        if not existing:
            raise NotFoundException("Sub-category not found")

        updates: dict[str, Any] = {}
        category_id = int(payload.get("categoryId") or existing["category_id"])

        if "categoryId" in payload:
            if not category_repository.fetch_by_id(category_id):
                raise ValidationException(details=[{"field": "categoryId", "message": "Category not found"}])
            updates["category_id"] = category_id
        if "name" in payload:
            name = (payload.get("name") or "").strip()
            if not name:
                raise ValidationException(details=[{"field": "name", "message": "Name is required"}])
            updates["name"] = to_db_text(name)
        if "slug" in payload or "name" in payload:
            slug = make_slug(
                (payload.get("slug") or "").strip()
                or updates.get("name", existing["name"]),
            )
            slug = unique_slug(
                slug,
                lambda s: sub_category_repository.slug_exists(
                    category_id,
                    s,
                    exclude_id=sub_category_id,
                ),
            )
            updates["slug"] = slug
        for key, db_key in [
            ("seoTitle", "seo_title"),
            ("seoDescription", "seo_description"),
            ("seoKeywords", "seo_keywords"),
        ]:
            if key in payload:
                updates[db_key] = to_db_text(payload.get(key))
        if "displayOrder" in payload:
            updates["display_order"] = int(payload.get("displayOrder") or 0)
        if "isVisible" in payload:
            updates["is_visible"] = bool(payload.get("isVisible"))
        if "isActive" in payload:
            updates["is_active"] = bool(payload.get("isActive"))

        _maybe_image(payload.get("imageUrl"), prefix="sub-category", field_key="image_url", updates=updates)
        _maybe_image(payload.get("iconUrl"), prefix="sub-category-icon", field_key="icon_url", updates=updates)
        _maybe_image(payload.get("bannerUrl"), prefix="sub-category-banner", field_key="banner_url", updates=updates)

        row = sub_category_repository.update(sub_category_id, updates)
        if not row:
            raise NotFoundException("Sub-category not found")
        self._invalidate_nav_cache()
        full = sub_category_repository.fetch_by_id(sub_category_id)
        return self._serialize_sub_category(full or row)

    def delete_sub_category(self, sub_category_id: int) -> None:
        if not sub_category_repository.soft_delete(sub_category_id):
            raise NotFoundException("Sub-category not found")
        self._invalidate_nav_cache()

    def create_under_sub_category(self, payload: dict[str, Any]) -> dict[str, Any]:
        name = (payload.get("name") or "").strip()
        category_id = payload.get("categoryId")
        sub_category_id = payload.get("subCategoryId")
        if not name:
            raise ValidationException(details=[{"field": "name", "message": "Name is required"}])
        if not category_id:
            raise ValidationException(details=[{"field": "categoryId", "message": "Category is required"}])
        if not sub_category_id:
            raise ValidationException(details=[{"field": "subCategoryId", "message": "Sub-category is required"}])

        category_id = int(category_id)
        sub_category_id = int(sub_category_id)
        sub_row = sub_category_repository.fetch_by_id(sub_category_id)
        if not sub_row or int(sub_row["category_id"]) != category_id:
            raise ValidationException(details=[{"field": "subCategoryId", "message": "Invalid sub-category"}])

        base_slug = make_slug((payload.get("slug") or "").strip() or name)
        slug = unique_slug(
            base_slug,
            lambda s: under_sub_category_repository.slug_exists(sub_category_id, s),
        )

        data = {
            "sub_category_id": sub_category_id,
            "category_id": category_id,
            "name": to_db_text(name),
            "slug": slug,
            "image_url": "NA",
            "icon_url": "NA",
            "banner_url": "NA",
            "seo_title": to_db_text(payload.get("seoTitle")),
            "seo_description": to_db_text(payload.get("seoDescription")),
            "seo_keywords": to_db_text(payload.get("seoKeywords")),
            "display_order": int(payload.get("displayOrder") or 0),
            "is_visible": bool(payload.get("isVisible", True)),
            "is_active": bool(payload.get("isActive", True)),
        }
        _maybe_image(payload.get("imageUrl"), prefix="under-sub", field_key="image_url", updates=data)
        _maybe_image(payload.get("iconUrl"), prefix="under-sub-icon", field_key="icon_url", updates=data)
        _maybe_image(payload.get("bannerUrl"), prefix="under-sub-banner", field_key="banner_url", updates=data)

        row = under_sub_category_repository.create(data)
        self._invalidate_nav_cache()
        full = under_sub_category_repository.fetch_by_id(row["under_sub_category_id"])
        return self._serialize_under_sub_category(full or row)

    def update_under_sub_category(self, under_sub_category_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        existing = under_sub_category_repository.fetch_by_id(under_sub_category_id)
        if not existing:
            raise NotFoundException("Under sub-category not found")

        updates: dict[str, Any] = {}
        category_id = int(payload.get("categoryId") or existing["category_id"])
        sub_category_id = int(payload.get("subCategoryId") or existing["sub_category_id"])

        if "categoryId" in payload or "subCategoryId" in payload:
            sub_row = sub_category_repository.fetch_by_id(sub_category_id)
            if not sub_row or int(sub_row["category_id"]) != category_id:
                raise ValidationException(details=[{"field": "subCategoryId", "message": "Invalid sub-category"}])
            updates["category_id"] = category_id
            updates["sub_category_id"] = sub_category_id

        if "name" in payload:
            name = (payload.get("name") or "").strip()
            if not name:
                raise ValidationException(details=[{"field": "name", "message": "Name is required"}])
            updates["name"] = to_db_text(name)
        if "slug" in payload or "name" in payload:
            slug = make_slug(
                (payload.get("slug") or "").strip()
                or updates.get("name", existing["name"]),
            )
            slug = unique_slug(
                slug,
                lambda s: under_sub_category_repository.slug_exists(
                    sub_category_id,
                    s,
                    exclude_id=under_sub_category_id,
                ),
            )
            updates["slug"] = slug
        for key, db_key in [
            ("seoTitle", "seo_title"),
            ("seoDescription", "seo_description"),
            ("seoKeywords", "seo_keywords"),
        ]:
            if key in payload:
                updates[db_key] = to_db_text(payload.get(key))
        if "displayOrder" in payload:
            updates["display_order"] = int(payload.get("displayOrder") or 0)
        if "isVisible" in payload:
            updates["is_visible"] = bool(payload.get("isVisible"))
        if "isActive" in payload:
            updates["is_active"] = bool(payload.get("isActive"))

        _maybe_image(payload.get("imageUrl"), prefix="under-sub", field_key="image_url", updates=updates)
        _maybe_image(payload.get("iconUrl"), prefix="under-sub-icon", field_key="icon_url", updates=updates)
        _maybe_image(payload.get("bannerUrl"), prefix="under-sub-banner", field_key="banner_url", updates=updates)

        row = under_sub_category_repository.update(under_sub_category_id, updates)
        if not row:
            raise NotFoundException("Under sub-category not found")
        self._invalidate_nav_cache()
        full = under_sub_category_repository.fetch_by_id(under_sub_category_id)
        return self._serialize_under_sub_category(full or row)

    def delete_under_sub_category(self, under_sub_category_id: int) -> None:
        if not under_sub_category_repository.soft_delete(under_sub_category_id):
            raise NotFoundException("Under sub-category not found")
        self._invalidate_nav_cache()


category_service = CategoryService()
