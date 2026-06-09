from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from apps.analytics.repositories.search_history_repository import search_history_repository
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
        "sort_by": kwargs.get("sort_by", "searched_at"),
        "sort_dir": kwargs.get("sort_dir", "desc"),
    }


def _pagination(page: int, page_size: int, total: int) -> dict[str, Any]:
    return {
        "page": page,
        "pageSize": page_size,
        "total": total,
        "totalPages": max(1, (total + page_size - 1) // page_size),
    }


class SearchHistoryService:
    def _serialize(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": str(row["search_history_id"]),
            "searchQuery": from_db_text(row.get("search_query")) or "",
            "customerId": str(row["customer_id"]) if row.get("customer_id") else None,
            "sessionId": from_db_text(row.get("session_id")) or "",
            "resultsCount": int(row.get("results_count") or 0),
            "clickedProductId": (
                str(row["clicked_product_id"]) if row.get("clicked_product_id") else None
            ),
            "ipAddress": from_db_text(row.get("ip_address")),
            "searchedAt": _format_dt(row.get("searched_at")),
            "createdAt": _format_dt(row.get("created_at")),
            "updatedAt": _format_dt(row.get("updated_at")),
        }

    def list_searches(self, **kwargs) -> dict[str, Any]:
        params = _base_list_params(kwargs)
        params["customer_id"] = kwargs.get("customer_id")
        rows, total = search_history_repository.list_paginated(**params)
        page = kwargs.get("page", 1)
        page_size = kwargs.get("page_size", 20)
        return {
            "items": [self._serialize(r) for r in rows],
            "pagination": _pagination(page, page_size, total),
        }

    def get_search(self, search_history_id: int) -> dict[str, Any]:
        row = search_history_repository.fetch_by_id(search_history_id)
        if not row:
            raise NotFoundException("Search history not found")
        return self._serialize(row)

    def create_search(self, payload: dict[str, Any]) -> dict[str, Any]:
        query = (payload.get("searchQuery") or "").strip()
        if not query:
            raise ValidationException(
                details=[{"field": "searchQuery", "message": "Search query is required"}]
            )

        row = search_history_repository.create({
            "search_query": to_db_text(query),
            "customer_id": _optional_int(payload.get("customerId")),
            "session_id": to_db_text(payload.get("sessionId")),
            "results_count": int(payload.get("resultsCount") or 0),
            "clicked_product_id": _optional_int(payload.get("clickedProductId")),
            "ip_address": to_db_text(payload.get("ipAddress")),
            "searched_at": payload.get("searchedAt") or datetime.now(),
        })
        return self._serialize(row)

    def update_search(self, search_history_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        existing = search_history_repository.fetch_by_id(search_history_id)
        if not existing:
            raise NotFoundException("Search history not found")

        updates: dict[str, Any] = {}
        if "searchQuery" in payload:
            query = (payload.get("searchQuery") or "").strip()
            if not query:
                raise ValidationException(
                    details=[{"field": "searchQuery", "message": "Search query is required"}]
                )
            updates["search_query"] = to_db_text(query)
        if "sessionId" in payload:
            updates["session_id"] = to_db_text(payload.get("sessionId"))
        if "resultsCount" in payload:
            updates["results_count"] = int(payload.get("resultsCount") or 0)
        if "clickedProductId" in payload:
            updates["clicked_product_id"] = _optional_int(payload.get("clickedProductId"))
        if "customerId" in payload:
            updates["customer_id"] = _optional_int(payload.get("customerId"))
        if "ipAddress" in payload:
            updates["ip_address"] = to_db_text(payload.get("ipAddress"))
        if "searchedAt" in payload:
            updates["searched_at"] = payload.get("searchedAt")

        row = search_history_repository.update(search_history_id, updates)
        if not row:
            raise NotFoundException("Search history not found")
        return self._serialize(row)

    def delete_search(self, search_history_id: int) -> None:
        if not search_history_repository.soft_delete(search_history_id):
            raise NotFoundException("Search history not found")

    def get_dashboard(self, *, period: str = "30d") -> dict[str, Any]:
        days = {"7d": 7, "30d": 30, "90d": 90}.get(period, 30)
        summary_row = search_history_repository.dashboard_summary(days=days)
        total_searches = int(summary_row.get("total_searches") or 0)
        zero_result_count = int(summary_row.get("zero_result_count") or 0)
        zero_result_rate = (
            round((zero_result_count / total_searches) * 100, 1) if total_searches else 0.0
        )

        return {
            "summary": {
                "totalSearches": total_searches,
                "avgResults": round(float(summary_row.get("avg_results") or 0), 1),
                "zeroResultRate": zero_result_rate,
            },
            "topQueries": [
                {
                    "query": from_db_text(row.get("query")) or "",
                    "count": int(row.get("count") or 0),
                }
                for row in search_history_repository.top_queries(days=days)
            ],
            "searchesTrend": [
                {
                    "label": from_db_text(row.get("label")) or "",
                    "value": int(row.get("value") or 0),
                }
                for row in search_history_repository.searches_trend(days=days)
            ],
            "zeroResultQueries": [
                {
                    "query": from_db_text(row.get("query")) or "",
                    "count": int(row.get("count") or 0),
                }
                for row in search_history_repository.zero_result_queries(days=days)
            ],
        }


search_history_service = SearchHistoryService()
