from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from apps.marketing.repositories.banner_repository import banner_repository
from core.database import select_one
from core.exceptions.base import NotFoundException, ValidationException
from core.helpers.text import from_db_text, save_base64_image, to_db_text


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
        return save_base64_image(value, subdir="banners", prefix=prefix)
    return str(value)


class BannerService:
    schema = "royal"

    def _serialize(self, row: dict[str, Any]) -> dict[str, Any]:
        category_id = row.get("category_id")
        return {
            "id": str(row["banner_id"]),
            "positionId": str(row["banner_position_id"]),
            "positionCode": from_db_text(row.get("position_code")) or "",
            "positionName": from_db_text(row.get("position_name")) or "",
            "categoryId": str(category_id) if category_id else None,
            "categoryName": from_db_text(row.get("category_name")),
            "title": from_db_text(row.get("title")) or "",
            "subtitle": from_db_text(row.get("subtitle")),
            "imageUrl": from_db_text(row.get("image_url")),
            "mobileImageUrl": from_db_text(row.get("mobile_image_url")),
            "linkUrl": from_db_text(row.get("link_url")),
            "linkType": from_db_text(row.get("link_type")),
            "displayOrder": int(row.get("display_order") or 0),
            "startsAt": _format_dt(row.get("starts_at")),
            "endsAt": _format_dt(row.get("ends_at")),
            "isActive": bool(row.get("is_active")),
            "createdAt": _format_dt(row.get("created_at")),
            "updatedAt": _format_dt(row.get("updated_at")),
        }

    def _validate_position(self, position_id: int) -> None:
        sql = f"""
            SELECT banner_position_id
            FROM {self.schema}.banner_positiontbl
            WHERE banner_position_id = %s AND is_deleted = FALSE AND is_active = TRUE
        """
        if not select_one(sql, [position_id]):
            raise ValidationException(
                details=[{"field": "positionId", "message": "Banner position not found"}]
            )

    def list_banners(self, **kwargs) -> dict[str, Any]:
        params = _base_list_params(kwargs)
        params["position_id"] = kwargs.get("position_id")
        rows, total = banner_repository.list_paginated(**params)
        page = kwargs.get("page", 1)
        page_size = kwargs.get("page_size", 20)
        return {
            "items": [self._serialize(r) for r in rows],
            "pagination": _pagination(page, page_size, total),
        }

    def get_banner(self, banner_id: int) -> dict[str, Any]:
        row = banner_repository.fetch_by_id(banner_id)
        if not row:
            raise NotFoundException("Banner not found")
        return self._serialize(row)

    def create_banner(self, payload: dict[str, Any]) -> dict[str, Any]:
        position_id = _optional_int(payload.get("positionId"))
        if not position_id:
            raise ValidationException(
                details=[{"field": "positionId", "message": "Banner position is required"}]
            )
        self._validate_position(position_id)

        row = banner_repository.create({
            "banner_position_id": position_id,
            "category_id": _optional_int(payload.get("categoryId")),
            "title": to_db_text(payload.get("title")),
            "subtitle": to_db_text(payload.get("subtitle")),
            "image_url": _maybe_image(payload.get("imageUrl"), prefix="banner"),
            "mobile_image_url": _maybe_image(payload.get("mobileImageUrl"), prefix="banner-mobile"),
            "link_url": to_db_text(payload.get("linkUrl")),
            "link_type": to_db_text(payload.get("linkType")),
            "display_order": int(payload.get("displayOrder") or 0),
            "starts_at": _parse_dt(payload.get("startsAt")),
            "ends_at": _parse_dt(payload.get("endsAt")),
            "is_active": bool(payload.get("isActive", True)),
        })
        detail = banner_repository.fetch_by_id(int(row["banner_id"]))
        return self._serialize(detail or row)

    def update_banner(self, banner_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        existing = banner_repository.fetch_by_id(banner_id)
        if not existing:
            raise NotFoundException("Banner not found")

        updates: dict[str, Any] = {}
        if "positionId" in payload:
            position_id = _optional_int(payload.get("positionId"))
            if not position_id:
                raise ValidationException(
                    details=[{"field": "positionId", "message": "Banner position is required"}]
                )
            self._validate_position(position_id)
            updates["banner_position_id"] = position_id
        if "categoryId" in payload:
            updates["category_id"] = _optional_int(payload.get("categoryId"))
        if "title" in payload:
            updates["title"] = to_db_text(payload.get("title"))
        if "subtitle" in payload:
            updates["subtitle"] = to_db_text(payload.get("subtitle"))
        if "imageUrl" in payload:
            updates["image_url"] = _maybe_image(
                payload.get("imageUrl"),
                prefix=f"banner-{banner_id}",
            )
        if "mobileImageUrl" in payload:
            updates["mobile_image_url"] = _maybe_image(
                payload.get("mobileImageUrl"),
                prefix=f"banner-mobile-{banner_id}",
            )
        if "linkUrl" in payload:
            updates["link_url"] = to_db_text(payload.get("linkUrl"))
        if "linkType" in payload:
            updates["link_type"] = to_db_text(payload.get("linkType"))
        if "displayOrder" in payload:
            updates["display_order"] = int(payload.get("displayOrder") or 0)
        if "startsAt" in payload:
            updates["starts_at"] = _parse_dt(payload.get("startsAt"))
        if "endsAt" in payload:
            updates["ends_at"] = _parse_dt(payload.get("endsAt"))
        if "isActive" in payload:
            updates["is_active"] = bool(payload.get("isActive"))

        row = banner_repository.update(banner_id, updates)
        if not row:
            raise NotFoundException("Banner not found")
        return self._serialize(row)

    def delete_banner(self, banner_id: int) -> None:
        if not banner_repository.soft_delete(banner_id):
            raise NotFoundException("Banner not found")


banner_service = BannerService()
