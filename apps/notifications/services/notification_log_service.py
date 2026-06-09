from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from apps.notifications.repositories.notification_log_repository import notification_log_repository
from apps.notifications.services.notification_service import NotificationService
from core.exceptions.base import NotFoundException


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
        "sort_by": kwargs.get("sort_by", "created_at"),
        "sort_dir": kwargs.get("sort_dir", "desc"),
    }


class NotificationLogService:
    def __init__(self) -> None:
        self._notification_service = NotificationService()

    def list_logs(self, **kwargs) -> dict[str, Any]:
        params = _base_list_params(kwargs)
        params["notification_id"] = kwargs.get("notification_id")
        params["status"] = kwargs.get("status", "")
        rows, total = notification_log_repository.list_paginated(**params)
        page = kwargs.get("page", 1)
        page_size = kwargs.get("page_size", 20)
        return {
            "items": [self._notification_service._serialize_log(r) for r in rows],
            "pagination": {
                "page": page,
                "pageSize": page_size,
                "total": total,
                "totalPages": max(1, (total + page_size - 1) // page_size),
            },
        }

    def get_log(self, notification_log_id: int) -> dict[str, Any]:
        row = notification_log_repository.fetch_by_id(notification_log_id)
        if not row:
            raise NotFoundException("Notification log not found")
        return self._notification_service._serialize_log(row)


notification_log_service = NotificationLogService()
