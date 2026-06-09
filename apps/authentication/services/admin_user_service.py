from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from django.contrib.auth.hashers import make_password

from apps.authentication.repositories.role_repository import role_repository
from apps.authentication.repositories.user_repository import user_repository
from core.exceptions.base import AuthorizationException, NotFoundException, ValidationException
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


class AdminUserService:
    def _serialize(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": str(row["user_id"]),
            "email": row["email"],
            "fullName": from_db_text(row.get("full_name")) or "",
            "phone": from_db_text(row.get("phone")),
            "avatarUrl": from_db_text(row.get("avatar_url")),
            "roleId": str(row["role_id"]),
            "roleCode": row["role_code"],
            "roleName": row["role_name"],
            "isActive": bool(row.get("is_active")),
            "lastLoginAt": _format_dt(row.get("last_login_at")),
            "loginCount": int(row.get("login_count") or 0),
            "createdAt": _format_dt(row.get("created_at")),
            "updatedAt": _format_dt(row.get("updated_at")),
        }

    def list_users(self, **kwargs) -> dict[str, Any]:
        rows, total = user_repository.list_admin_users_paginated(**_base_list_params(kwargs))
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

    def get_user(self, user_id: int) -> dict[str, Any]:
        row = user_repository.fetch_admin_user_for_management(user_id)
        if not row:
            raise NotFoundException("Admin user not found")
        return self._serialize(row)

    def create_user(self, payload: dict[str, Any]) -> dict[str, Any]:
        email = (payload.get("email") or "").strip().lower()
        password = payload.get("password") or ""
        full_name = (payload.get("fullName") or "").strip()
        role_id = payload.get("roleId")

        errors: list[dict[str, str]] = []
        if not email:
            errors.append({"field": "email", "message": "Email is required"})
        if not password:
            errors.append({"field": "password", "message": "Password is required"})
        elif len(password) < 8:
            errors.append({"field": "password", "message": "Password must be at least 8 characters"})
        if not full_name:
            errors.append({"field": "fullName", "message": "Full name is required"})
        if not role_id:
            errors.append({"field": "roleId", "message": "Role is required"})
        if errors:
            raise ValidationException(details=errors)

        try:
            role_id_int = int(role_id)
        except (TypeError, ValueError):
            raise ValidationException(
                details=[{"field": "roleId", "message": "Invalid role"}],
            )

        role = role_repository.fetch_admin_role_by_id(role_id_int)
        if not role:
            raise ValidationException(
                details=[{"field": "roleId", "message": "Invalid admin role"}],
            )

        if user_repository.admin_email_exists(email):
            raise ValidationException(
                details=[{"field": "email", "message": "Email already in use"}],
            )

        row = user_repository.create_admin_user({
            "role_id": role_id_int,
            "email": email,
            "password_hash": make_password(password),
            "full_name": to_db_text(full_name),
            "phone": to_db_text(payload.get("phone")),
            "is_active": bool(payload.get("isActive", True)),
        })
        return self._serialize(row)

    def update_user(self, user_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        existing = user_repository.fetch_admin_user_for_management(user_id)
        if not existing:
            raise NotFoundException("Admin user not found")

        updates: dict[str, Any] = {}
        if "email" in payload:
            email = (payload.get("email") or "").strip().lower()
            if not email:
                raise ValidationException(
                    details=[{"field": "email", "message": "Email is required"}],
                )
            if user_repository.admin_email_exists(email, exclude_id=user_id):
                raise ValidationException(
                    details=[{"field": "email", "message": "Email already in use"}],
                )
            updates["email"] = email
        if "fullName" in payload:
            full_name = (payload.get("fullName") or "").strip()
            if not full_name:
                raise ValidationException(
                    details=[{"field": "fullName", "message": "Full name is required"}],
                )
            updates["full_name"] = to_db_text(full_name)
        if "phone" in payload:
            updates["phone"] = to_db_text(payload.get("phone"))
        if "isActive" in payload:
            updates["is_active"] = bool(payload.get("isActive"))
        if "roleId" in payload:
            try:
                role_id_int = int(payload.get("roleId"))
            except (TypeError, ValueError):
                raise ValidationException(
                    details=[{"field": "roleId", "message": "Invalid role"}],
                )
            role = role_repository.fetch_admin_role_by_id(role_id_int)
            if not role:
                raise ValidationException(
                    details=[{"field": "roleId", "message": "Invalid admin role"}],
                )
            updates["role_id"] = role_id_int
        if "password" in payload and payload.get("password"):
            password = payload.get("password") or ""
            if len(password) < 8:
                raise ValidationException(
                    details=[{"field": "password", "message": "Password must be at least 8 characters"}],
                )
            updates["password_hash"] = make_password(password)

        row = user_repository.update_admin_user(user_id, updates)
        if not row:
            raise NotFoundException("Admin user not found")
        return self._serialize(row)

    def delete_user(self, user_id: int, *, acting_admin_id: int) -> None:
        if user_id == acting_admin_id:
            raise AuthorizationException("Cannot delete your own account")
        if not user_repository.soft_delete_admin_user(user_id):
            raise NotFoundException("Admin user not found")


admin_user_service = AdminUserService()
