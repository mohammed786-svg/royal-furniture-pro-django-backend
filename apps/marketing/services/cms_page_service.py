from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from apps.marketing.repositories.cms_page_repository import cms_page_repository
from core.exceptions.base import NotFoundException, ValidationException
from core.helpers.text import from_db_text, make_slug, to_db_text, unique_slug


def _format_dt(value: Any) -> Optional[str]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _parse_dt(value: Any) -> Optional[datetime]:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
    except ValueError:
        return None


def _base_list_params(kwargs: dict[str, Any]) -> dict[str, Any]:
    return {
        "page": kwargs.get("page", 1),
        "page_size": kwargs.get("page_size", 20),
        "search": kwargs.get("search", ""),
        "sort_by": kwargs.get("sort_by", "created_at"),
        "sort_dir": kwargs.get("sort_dir", "desc"),
    }


def _pagination(page: int, page_size: int, total: int) -> dict[str, Any]:
    return {
        "page": page,
        "pageSize": page_size,
        "total": total,
        "totalPages": max(1, (total + page_size - 1) // page_size),
    }


class CmsPageService:
    def _serialize(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": str(row["cms_page_id"]),
            "pageCode": from_db_text(row.get("page_code")) or "",
            "title": from_db_text(row.get("title")) or "",
            "slug": from_db_text(row.get("slug")) or "",
            "content": from_db_text(row.get("content")) or "",
            "seoTitle": from_db_text(row.get("seo_title")),
            "seoDescription": from_db_text(row.get("seo_description")),
            "seoKeywords": from_db_text(row.get("seo_keywords")),
            "isPublished": bool(row.get("is_published")),
            "publishedAt": _format_dt(row.get("published_at")),
            "isActive": bool(row.get("is_active")),
            "createdAt": _format_dt(row.get("created_at")),
            "updatedAt": _format_dt(row.get("updated_at")),
        }

    def list_cms_pages(self, **kwargs) -> dict[str, Any]:
        rows, total = cms_page_repository.list_paginated(**_base_list_params(kwargs))
        page = kwargs.get("page", 1)
        page_size = kwargs.get("page_size", 20)
        return {
            "items": [self._serialize(r) for r in rows],
            "pagination": _pagination(page, page_size, total),
        }

    def get_cms_page(self, cms_page_id: int) -> dict[str, Any]:
        row = cms_page_repository.fetch_by_id(cms_page_id)
        if not row:
            raise NotFoundException("CMS page not found")
        return self._serialize(row)

    def create_cms_page(self, payload: dict[str, Any]) -> dict[str, Any]:
        page_code = (payload.get("pageCode") or "").strip().upper()
        title = (payload.get("title") or "").strip()
        if not page_code:
            raise ValidationException(
                details=[{"field": "pageCode", "message": "Page code is required"}]
            )
        if not title:
            raise ValidationException(
                details=[{"field": "title", "message": "Title is required"}]
            )
        if cms_page_repository.code_exists(page_code):
            raise ValidationException(
                details=[{"field": "pageCode", "message": "Page code already exists"}]
            )

        slug_input = (payload.get("slug") or "").strip()
        base_slug = make_slug(slug_input or title)
        slug = unique_slug(base_slug, lambda s: cms_page_repository.slug_exists(s))

        is_published = bool(payload.get("isPublished", False))
        published_at = _parse_dt(payload.get("publishedAt"))
        if is_published and not published_at:
            published_at = datetime.now()

        row = cms_page_repository.create({
            "page_code": page_code,
            "title": to_db_text(title),
            "slug": slug,
            "content": to_db_text(payload.get("content")),
            "seo_title": to_db_text(payload.get("seoTitle")),
            "seo_description": to_db_text(payload.get("seoDescription")),
            "seo_keywords": to_db_text(payload.get("seoKeywords")),
            "is_published": is_published,
            "published_at": published_at,
            "is_active": bool(payload.get("isActive", True)),
        })
        return self._serialize(row)

    def update_cms_page(self, cms_page_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        existing = cms_page_repository.fetch_by_id(cms_page_id)
        if not existing:
            raise NotFoundException("CMS page not found")

        updates: dict[str, Any] = {}
        if "pageCode" in payload:
            page_code = (payload.get("pageCode") or "").strip().upper()
            if not page_code:
                raise ValidationException(
                    details=[{"field": "pageCode", "message": "Page code is required"}]
                )
            if cms_page_repository.code_exists(page_code, exclude_id=cms_page_id):
                raise ValidationException(
                    details=[{"field": "pageCode", "message": "Page code already exists"}]
                )
            updates["page_code"] = page_code
        if "title" in payload:
            title = (payload.get("title") or "").strip()
            if not title:
                raise ValidationException(
                    details=[{"field": "title", "message": "Title is required"}]
                )
            updates["title"] = to_db_text(title)
        if "slug" in payload or "title" in payload:
            slug_input = (payload.get("slug") or "").strip()
            title_for_slug = updates.get("title", existing.get("title"))
            base_slug = make_slug(slug_input or from_db_text(title_for_slug) or "page")
            updates["slug"] = unique_slug(
                base_slug,
                lambda s: cms_page_repository.slug_exists(s, exclude_id=cms_page_id),
            )
        if "content" in payload:
            updates["content"] = to_db_text(payload.get("content"))
        if "seoTitle" in payload:
            updates["seo_title"] = to_db_text(payload.get("seoTitle"))
        if "seoDescription" in payload:
            updates["seo_description"] = to_db_text(payload.get("seoDescription"))
        if "seoKeywords" in payload:
            updates["seo_keywords"] = to_db_text(payload.get("seoKeywords"))
        if "isPublished" in payload:
            is_published = bool(payload.get("isPublished"))
            updates["is_published"] = is_published
            if is_published and not existing.get("is_published"):
                updates["published_at"] = _parse_dt(payload.get("publishedAt")) or datetime.now()
            elif not is_published:
                updates["published_at"] = None
        elif "publishedAt" in payload:
            updates["published_at"] = _parse_dt(payload.get("publishedAt"))
        if "isActive" in payload:
            updates["is_active"] = bool(payload.get("isActive"))

        row = cms_page_repository.update(cms_page_id, updates)
        if not row:
            raise NotFoundException("CMS page not found")
        return self._serialize(row)

    def delete_cms_page(self, cms_page_id: int) -> None:
        if not cms_page_repository.soft_delete(cms_page_id):
            raise NotFoundException("CMS page not found")


cms_page_service = CmsPageService()
