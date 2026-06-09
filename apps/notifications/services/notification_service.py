from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from apps.notifications.repositories.notification_log_repository import notification_log_repository
from apps.notifications.repositories.notification_repository import notification_repository
from core.exceptions.base import NotFoundException, ValidationException
from core.helpers.text import from_db_text, to_db_text


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
        "sort_by": kwargs.get("sort_by", "created_at"),
        "sort_dir": kwargs.get("sort_dir", "desc"),
    }


class NotificationService:
    def _serialize_log(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": str(row["notification_log_id"]),
            "notificationId": str(row["notification_id"]) if row.get("notification_id") else None,
            "notificationTitle": from_db_text(row.get("notification_title")),
            "customerId": str(row["customer_id"]) if row.get("customer_id") else None,
            "customerFullName": from_db_text(row.get("customer_full_name")),
            "customerEmail": from_db_text(row.get("customer_email")),
            "userId": str(row["user_id"]) if row.get("user_id") else None,
            "userFullName": from_db_text(row.get("user_full_name")),
            "userEmail": from_db_text(row.get("user_email")),
            "channel": from_db_text(row.get("channel")) or "",
            "recipient": from_db_text(row.get("recipient")),
            "subject": from_db_text(row.get("subject")),
            "body": from_db_text(row.get("body")),
            "status": from_db_text(row.get("status")) or "",
            "sentAt": _format_dt(row.get("sent_at")),
            "failureReason": from_db_text(row.get("failure_reason")),
            "metadata": notification_log_repository.parse_metadata(row.get("metadata")),
            "createdAt": _format_dt(row.get("created_at")),
            "updatedAt": _format_dt(row.get("updated_at")),
        }

    def _serialize(self, row: dict[str, Any], *, include_logs: bool = False) -> dict[str, Any]:
        item = {
            "id": str(row["notification_id"]),
            "title": from_db_text(row.get("title")) or "",
            "message": from_db_text(row.get("message")) or "",
            "channel": from_db_text(row.get("channel")) or "",
            "templateCode": from_db_text(row.get("template_code")),
            "targetType": from_db_text(row.get("target_type")) or "",
            "isActive": bool(row.get("is_active")),
            "createdAt": _format_dt(row.get("created_at")),
            "updatedAt": _format_dt(row.get("updated_at")),
        }
        if include_logs:
            logs = notification_log_repository.list_by_notification_id(int(row["notification_id"]))
            item["logs"] = [self._serialize_log(log) for log in logs]
        return item

    def list_notifications(self, **kwargs) -> dict[str, Any]:
        params = _base_list_params(kwargs)
        params["channel"] = kwargs.get("channel", "")
        params["target_type"] = kwargs.get("target_type", "")
        params["is_active"] = kwargs.get("is_active")
        rows, total = notification_repository.list_paginated(**params)
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

    def get_notification(self, notification_id: int) -> dict[str, Any]:
        row = notification_repository.fetch_by_id(notification_id)
        if not row:
            raise NotFoundException("Notification not found")
        return self._serialize(row, include_logs=True)

    def create_notification(self, payload: dict[str, Any]) -> dict[str, Any]:
        title = (payload.get("title") or "").strip()
        message = (payload.get("message") or "").strip()
        channel = (payload.get("channel") or "").strip().upper()
        if not title:
            raise ValidationException(
                details=[{"field": "title", "message": "Title is required"}],
            )
        if not message:
            raise ValidationException(
                details=[{"field": "message", "message": "Message is required"}],
            )
        if not channel:
            raise ValidationException(
                details=[{"field": "channel", "message": "Channel is required"}],
            )

        row = notification_repository.create({
            "title": to_db_text(title),
            "message": to_db_text(message),
            "channel": to_db_text(channel),
            "template_code": to_db_text(payload.get("templateCode")),
            "target_type": to_db_text((payload.get("targetType") or "ALL").upper()),
            "is_active": bool(payload.get("isActive", True)),
        })
        return self._serialize(row)

    def update_notification(self, notification_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        existing = notification_repository.fetch_by_id(notification_id)
        if not existing:
            raise NotFoundException("Notification not found")

        updates: dict[str, Any] = {}
        if "title" in payload:
            title = (payload.get("title") or "").strip()
            if not title:
                raise ValidationException(
                    details=[{"field": "title", "message": "Title is required"}],
                )
            updates["title"] = to_db_text(title)
        if "message" in payload:
            message = (payload.get("message") or "").strip()
            if not message:
                raise ValidationException(
                    details=[{"field": "message", "message": "Message is required"}],
                )
            updates["message"] = to_db_text(message)
        if "channel" in payload:
            channel = (payload.get("channel") or "").strip().upper()
            if not channel:
                raise ValidationException(
                    details=[{"field": "channel", "message": "Channel is required"}],
                )
            updates["channel"] = to_db_text(channel)
        if "templateCode" in payload:
            updates["template_code"] = to_db_text(payload.get("templateCode"))
        if "targetType" in payload:
            updates["target_type"] = to_db_text((payload.get("targetType") or "ALL").upper())
        if "isActive" in payload:
            updates["is_active"] = bool(payload.get("isActive"))

        row = notification_repository.update(notification_id, updates)
        if not row:
            raise NotFoundException("Notification not found")
        return self._serialize(row, include_logs=True)

    def delete_notification(self, notification_id: int) -> None:
        if not notification_repository.soft_delete(notification_id):
            raise NotFoundException("Notification not found")


notification_service = NotificationService()
