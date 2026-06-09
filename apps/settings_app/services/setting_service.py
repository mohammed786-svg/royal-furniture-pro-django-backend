from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from apps.settings_app.repositories.setting_repository import setting_repository
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
        "group": kwargs.get("group", ""),
        "sort_by": kwargs.get("sort_by", "setting_key"),
        "sort_dir": kwargs.get("sort_dir", "asc"),
    }


def _pagination(page: int, page_size: int, total: int) -> dict[str, Any]:
    return {
        "page": page,
        "pageSize": page_size,
        "total": total,
        "totalPages": max(1, (total + page_size - 1) // page_size),
    }


class SettingService:
    def _serialize(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": str(row["setting_id"]),
            "settingKey": from_db_text(row.get("setting_key")) or "",
            "settingValue": from_db_text(row.get("setting_value")) or "",
            "settingGroup": from_db_text(row.get("setting_group")) or "",
            "valueType": from_db_text(row.get("value_type")) or "TEXT",
            "isEncrypted": bool(row.get("is_encrypted")),
            "description": from_db_text(row.get("description")),
            "isActive": bool(row.get("is_active")),
            "createdAt": _format_dt(row.get("created_at")),
            "updatedAt": _format_dt(row.get("updated_at")),
        }

    def list_settings(self, **kwargs) -> dict[str, Any]:
        rows, total = setting_repository.list_paginated(**_base_list_params(kwargs))
        page = kwargs.get("page", 1)
        page_size = kwargs.get("page_size", 20)
        return {
            "items": [self._serialize(r) for r in rows],
            "pagination": _pagination(page, page_size, total),
        }

    def get_setting(self, setting_id: int) -> dict[str, Any]:
        row = setting_repository.fetch_by_id(setting_id)
        if not row:
            raise NotFoundException("Setting not found")
        return self._serialize(row)

    def create_setting(self, payload: dict[str, Any]) -> dict[str, Any]:
        key = (payload.get("settingKey") or "").strip()
        if not key:
            raise ValidationException(
                details=[{"field": "settingKey", "message": "Setting key is required"}]
            )
        if setting_repository.key_exists(key):
            raise ConflictException("Setting key already exists")

        row = setting_repository.create({
            "setting_key": to_db_text(key),
            "setting_value": to_db_text(payload.get("settingValue")),
            "setting_group": to_db_text(payload.get("settingGroup")),
            "value_type": to_db_text(payload.get("valueType") or "TEXT"),
            "is_encrypted": bool(payload.get("isEncrypted", False)),
            "description": to_db_text(payload.get("description")),
            "is_active": bool(payload.get("isActive", True)),
        })
        return self._serialize(row)

    def update_setting(self, setting_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        existing = setting_repository.fetch_by_id(setting_id)
        if not existing:
            raise NotFoundException("Setting not found")

        updates: dict[str, Any] = {}
        if "settingKey" in payload:
            key = (payload.get("settingKey") or "").strip()
            if not key:
                raise ValidationException(
                    details=[{"field": "settingKey", "message": "Setting key is required"}]
                )
            if setting_repository.key_exists(key, exclude_id=setting_id):
                raise ConflictException("Setting key already exists")
            updates["setting_key"] = to_db_text(key)
        for api_key, db_key in (
            ("settingValue", "setting_value"),
            ("settingGroup", "setting_group"),
            ("valueType", "value_type"),
            ("description", "description"),
        ):
            if api_key in payload:
                updates[db_key] = to_db_text(payload.get(api_key))
        if "isEncrypted" in payload:
            updates["is_encrypted"] = bool(payload.get("isEncrypted"))
        if "isActive" in payload:
            updates["is_active"] = bool(payload.get("isActive"))

        row = setting_repository.update(setting_id, updates)
        if not row:
            raise NotFoundException("Setting not found")
        return self._serialize(row)

    def delete_setting(self, setting_id: int) -> None:
        if not setting_repository.soft_delete(setting_id):
            raise NotFoundException("Setting not found")

    def list_groups(self) -> list[str]:
        return [from_db_text(g) or g for g in setting_repository.list_groups()]


setting_service = SettingService()
