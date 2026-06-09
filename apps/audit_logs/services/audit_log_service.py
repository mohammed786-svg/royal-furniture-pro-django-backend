from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Optional

from apps.audit_logs.repositories.audit_log_repository import audit_log_repository
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


def _parse_json(value: Any) -> dict[str, Any]:
    if value in (None, "", "NA"):
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def _base_list_params(kwargs: dict[str, Any]) -> dict[str, Any]:
    return {
        "page": kwargs.get("page", 1),
        "page_size": kwargs.get("page_size", 20),
        "search": kwargs.get("search", ""),
        "action_type": kwargs.get("action_type", ""),
        "table_name": kwargs.get("table_name", ""),
        "user_id": kwargs.get("user_id"),
        "sort_by": kwargs.get("sort_by", "logged_at"),
        "sort_dir": kwargs.get("sort_dir", "desc"),
    }


def _pagination(page: int, page_size: int, total: int) -> dict[str, Any]:
    return {
        "page": page,
        "pageSize": page_size,
        "total": total,
        "totalPages": max(1, (total + page_size - 1) // page_size),
    }


class AuditLogService:
    def _serialize(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": str(row["audit_log_id"]),
            "userId": str(row["user_id"]) if row.get("user_id") else None,
            "customerId": str(row["customer_id"]) if row.get("customer_id") else None,
            "actionType": from_db_text(row.get("action_type")) or "",
            "tableName": from_db_text(row.get("table_name")) or "",
            "recordId": str(row["record_id"]) if row.get("record_id") else None,
            "oldValues": _parse_json(row.get("old_values")),
            "newValues": _parse_json(row.get("new_values")),
            "ipAddress": from_db_text(row.get("ip_address")),
            "userAgent": from_db_text(row.get("user_agent")),
            "remarks": from_db_text(row.get("remarks")),
            "loggedAt": _format_dt(row.get("logged_at")),
            "createdAt": _format_dt(row.get("created_at")),
        }

    def list_audit_logs(self, **kwargs) -> dict[str, Any]:
        rows, total = audit_log_repository.list_paginated(**_base_list_params(kwargs))
        page = kwargs.get("page", 1)
        page_size = kwargs.get("page_size", 20)
        return {
            "items": [self._serialize(r) for r in rows],
            "pagination": _pagination(page, page_size, total),
        }

    def get_audit_log(self, audit_log_id: int) -> dict[str, Any]:
        row = audit_log_repository.fetch_by_id(audit_log_id)
        if not row:
            raise NotFoundException("Audit log not found")
        return self._serialize(row)

    def create_audit_log(self, payload: dict[str, Any], *, admin_id: Optional[int] = None) -> dict[str, Any]:
        action_type = (payload.get("actionType") or "").strip()
        table_name = (payload.get("tableName") or "").strip()
        if not action_type:
            raise ValidationException(
                details=[{"field": "actionType", "message": "Action type is required"}]
            )
        if not table_name:
            raise ValidationException(
                details=[{"field": "tableName", "message": "Table name is required"}]
            )

        row = audit_log_repository.create({
            "user_id": _optional_int(payload.get("userId")) or admin_id,
            "customer_id": _optional_int(payload.get("customerId")),
            "action_type": to_db_text(action_type),
            "table_name": to_db_text(table_name),
            "record_id": _optional_int(payload.get("recordId")),
            "old_values": payload.get("oldValues") or {},
            "new_values": payload.get("newValues") or {},
            "ip_address": to_db_text(payload.get("ipAddress")),
            "user_agent": to_db_text(payload.get("userAgent")),
            "remarks": to_db_text(payload.get("remarks")),
            "logged_at": payload.get("loggedAt") or datetime.now(),
        })
        return self._serialize(row)


audit_log_service = AuditLogService()
