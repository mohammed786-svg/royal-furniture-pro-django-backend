from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from apps.orders.repositories.order_status_repository import order_status_repository
from core.exceptions.base import ConflictException, NotFoundException, ValidationException
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
        "sort_by": kwargs.get("sort_by", "display_order"),
        "sort_dir": kwargs.get("sort_dir", "asc"),
    }


class OrderStatusService:
    def _serialize(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": str(row["order_status_id"]),
            "statusCode": from_db_text(row.get("status_code")) or "",
            "statusName": from_db_text(row.get("status_name")) or "",
            "description": from_db_text(row.get("description")),
            "displayOrder": int(row.get("display_order") or 0),
            "isTerminal": bool(row.get("is_terminal")),
            "isActive": bool(row.get("is_active")),
            "createdAt": _format_dt(row.get("created_at")),
            "updatedAt": _format_dt(row.get("updated_at")),
        }

    def list_statuses(self, **kwargs) -> dict[str, Any]:
        rows, total = order_status_repository.list_paginated(**_base_list_params(kwargs))
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

    def get_status(self, order_status_id: int) -> dict[str, Any]:
        row = order_status_repository.fetch_by_id(order_status_id)
        if not row:
            raise NotFoundException("Order status not found")
        return self._serialize(row)

    def create_status(self, payload: dict[str, Any]) -> dict[str, Any]:
        code = (payload.get("statusCode") or "").strip().upper()
        name = (payload.get("statusName") or "").strip()
        if not code:
            raise ValidationException(
                details=[{"field": "statusCode", "message": "Status code is required"}]
            )
        if not name:
            raise ValidationException(
                details=[{"field": "statusName", "message": "Status name is required"}]
            )
        if order_status_repository.code_exists(code):
            raise ConflictException("Status code already exists")
        row = order_status_repository.create({
            "status_code": code,
            "status_name": to_db_text(name),
            "description": to_db_text(payload.get("description")),
            "display_order": int(payload.get("displayOrder") or 0),
            "is_terminal": bool(payload.get("isTerminal", False)),
            "is_active": bool(payload.get("isActive", True)),
        })
        return self._serialize(row)

    def update_status(self, order_status_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        existing = order_status_repository.fetch_by_id(order_status_id)
        if not existing:
            raise NotFoundException("Order status not found")
        updates: dict[str, Any] = {}
        if "statusCode" in payload:
            code = (payload.get("statusCode") or "").strip().upper()
            if not code:
                raise ValidationException(
                    details=[{"field": "statusCode", "message": "Status code is required"}]
                )
            if order_status_repository.code_exists(code, exclude_id=order_status_id):
                raise ConflictException("Status code already exists")
            updates["status_code"] = code
        if "statusName" in payload:
            updates["status_name"] = to_db_text(payload.get("statusName"))
        if "description" in payload:
            updates["description"] = to_db_text(payload.get("description"))
        if "displayOrder" in payload:
            updates["display_order"] = int(payload.get("displayOrder") or 0)
        if "isTerminal" in payload:
            updates["is_terminal"] = bool(payload.get("isTerminal"))
        if "isActive" in payload:
            updates["is_active"] = bool(payload.get("isActive"))
        row = order_status_repository.update(order_status_id, updates)
        if not row:
            raise NotFoundException("Order status not found")
        return self._serialize(row)

    def delete_status(self, order_status_id: int) -> None:
        if not order_status_repository.soft_delete(order_status_id):
            raise NotFoundException("Order status not found")


order_status_service = OrderStatusService()
