from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from apps.authentication.repositories.login_history_repository import login_history_repository
from core.exceptions.base import NotFoundException
from core.helpers.text import from_db_text


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
        "sort_by": kwargs.get("sort_by", "login_at"),
        "sort_dir": kwargs.get("sort_dir", "desc"),
    }


class LoginHistoryService:
    def _serialize(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": str(row["login_history_id"]),
            "userId": str(row["user_id"]) if row.get("user_id") else None,
            "customerId": str(row["customer_id"]) if row.get("customer_id") else None,
            "loginType": from_db_text(row.get("login_type")) or "",
            "ipAddress": from_db_text(row.get("ip_address")),
            "userAgent": from_db_text(row.get("user_agent")),
            "deviceType": from_db_text(row.get("device_type")),
            "location": from_db_text(row.get("location")),
            "status": from_db_text(row.get("status")) or "",
            "failureReason": from_db_text(row.get("failure_reason")),
            "loginAt": _format_dt(row.get("login_at")),
            "userEmail": from_db_text(row.get("user_email")),
            "userFullName": from_db_text(row.get("user_full_name")),
            "customerEmail": from_db_text(row.get("customer_email")),
            "customerFullName": from_db_text(row.get("customer_full_name")),
        }

    def list_history(self, **kwargs) -> dict[str, Any]:
        params = _base_list_params(kwargs)
        params["user_id"] = kwargs.get("user_id")
        params["status"] = kwargs.get("status", "")
        params["login_type"] = kwargs.get("login_type", "")
        rows, total = login_history_repository.list_paginated(**params)
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

    def get_history(self, login_history_id: int) -> dict[str, Any]:
        row = login_history_repository.fetch_by_id(login_history_id)
        if not row:
            raise NotFoundException("Login history record not found")
        return self._serialize(row)


login_history_service = LoginHistoryService()
