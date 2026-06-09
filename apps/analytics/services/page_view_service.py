from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from apps.analytics.repositories.page_view_repository import page_view_repository
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
        "sort_by": kwargs.get("sort_by", "viewed_at"),
        "sort_dir": kwargs.get("sort_dir", "desc"),
    }


def _pagination(page: int, page_size: int, total: int) -> dict[str, Any]:
    return {
        "page": page,
        "pageSize": page_size,
        "total": total,
        "totalPages": max(1, (total + page_size - 1) // page_size),
    }


class PageViewService:
    def _serialize(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": str(row["page_view_id"]),
            "pageUrl": from_db_text(row.get("page_url")) or "",
            "pageTitle": from_db_text(row.get("page_title")) or "",
            "customerId": str(row["customer_id"]) if row.get("customer_id") else None,
            "sessionId": from_db_text(row.get("session_id")) or "",
            "categoryId": str(row["category_id"]) if row.get("category_id") else None,
            "subCategoryId": str(row["sub_category_id"]) if row.get("sub_category_id") else None,
            "productId": str(row["product_id"]) if row.get("product_id") else None,
            "referrer": from_db_text(row.get("referrer")),
            "ipAddress": from_db_text(row.get("ip_address")),
            "viewedAt": _format_dt(row.get("viewed_at")),
            "createdAt": _format_dt(row.get("created_at")),
            "updatedAt": _format_dt(row.get("updated_at")),
        }

    def list_page_views(self, **kwargs) -> dict[str, Any]:
        params = _base_list_params(kwargs)
        params["customer_id"] = kwargs.get("customer_id")
        params["product_id"] = kwargs.get("product_id")
        rows, total = page_view_repository.list_paginated(**params)
        page = kwargs.get("page", 1)
        page_size = kwargs.get("page_size", 20)
        return {
            "items": [self._serialize(r) for r in rows],
            "pagination": _pagination(page, page_size, total),
        }

    def get_page_view(self, page_view_id: int) -> dict[str, Any]:
        row = page_view_repository.fetch_by_id(page_view_id)
        if not row:
            raise NotFoundException("Page view not found")
        return self._serialize(row)

    def create_page_view(self, payload: dict[str, Any]) -> dict[str, Any]:
        page_url = (payload.get("pageUrl") or "").strip()
        if not page_url:
            raise ValidationException(
                details=[{"field": "pageUrl", "message": "Page URL is required"}]
            )

        row = page_view_repository.create({
            "page_url": to_db_text(page_url),
            "page_title": to_db_text(payload.get("pageTitle")),
            "customer_id": _optional_int(payload.get("customerId")),
            "session_id": to_db_text(payload.get("sessionId")),
            "category_id": _optional_int(payload.get("categoryId")),
            "sub_category_id": _optional_int(payload.get("subCategoryId")),
            "product_id": _optional_int(payload.get("productId")),
            "referrer": to_db_text(payload.get("referrer")),
            "ip_address": to_db_text(payload.get("ipAddress")),
            "viewed_at": payload.get("viewedAt") or datetime.now(),
        })
        return self._serialize(row)

    def update_page_view(self, page_view_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        existing = page_view_repository.fetch_by_id(page_view_id)
        if not existing:
            raise NotFoundException("Page view not found")

        updates: dict[str, Any] = {}
        if "pageUrl" in payload:
            page_url = (payload.get("pageUrl") or "").strip()
            if not page_url:
                raise ValidationException(
                    details=[{"field": "pageUrl", "message": "Page URL is required"}]
                )
            updates["page_url"] = to_db_text(page_url)
        for api_key, db_key in (
            ("pageTitle", "page_title"),
            ("sessionId", "session_id"),
            ("referrer", "referrer"),
            ("ipAddress", "ip_address"),
        ):
            if api_key in payload:
                updates[db_key] = to_db_text(payload.get(api_key))
        for api_key, db_key in (
            ("customerId", "customer_id"),
            ("categoryId", "category_id"),
            ("subCategoryId", "sub_category_id"),
            ("productId", "product_id"),
        ):
            if api_key in payload:
                updates[db_key] = _optional_int(payload.get(api_key))
        if "viewedAt" in payload:
            updates["viewed_at"] = payload.get("viewedAt")

        row = page_view_repository.update(page_view_id, updates)
        if not row:
            raise NotFoundException("Page view not found")
        return self._serialize(row)

    def delete_page_view(self, page_view_id: int) -> None:
        if not page_view_repository.soft_delete(page_view_id):
            raise NotFoundException("Page view not found")

    def get_dashboard(self, *, period: str = "30d") -> dict[str, Any]:
        days = {"7d": 7, "30d": 30, "90d": 90}.get(period, 30)
        summary_row = page_view_repository.dashboard_summary(days=days)
        return {
            "summary": {
                "totalViews": int(summary_row.get("total_views") or 0),
                "uniqueSessions": int(summary_row.get("unique_sessions") or 0),
                "topReferrer": from_db_text(summary_row.get("top_referrer")),
            },
            "viewsTrend": [
                {
                    "label": from_db_text(row.get("label")) or "",
                    "value": int(row.get("value") or 0),
                }
                for row in page_view_repository.views_trend(days=days)
            ],
            "topPages": [
                {
                    "pageUrl": from_db_text(row.get("page_url")) or "",
                    "pageTitle": from_db_text(row.get("page_title")) or "",
                    "views": int(row.get("views") or 0),
                }
                for row in page_view_repository.top_pages(days=days)
            ],
            "viewsByProduct": [
                {
                    "productName": from_db_text(row.get("product_name")) or "",
                    "views": int(row.get("views") or 0),
                }
                for row in page_view_repository.views_by_product(days=days)
            ],
        }


page_view_service = PageViewService()
