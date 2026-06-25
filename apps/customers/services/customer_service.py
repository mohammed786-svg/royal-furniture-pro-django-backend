from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from apps.customers.repositories.customer_repository import customer_repository
from core.database.transaction import atomic
from core.exceptions.base import ConflictException, NotFoundException, ValidationException
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
        "sort_by": kwargs.get("sort_by", "created_at"),
        "sort_dir": kwargs.get("sort_dir", "desc"),
    }


class CustomerService:
    def _serialize_profile(self, row: dict[str, Any]) -> Optional[dict[str, Any]]:
        if not row.get("customer_profile_id"):
            return None
        return {
            "id": str(row["customer_profile_id"]),
            "dateOfBirth": _format_dt(row.get("date_of_birth")),
            "gender": from_db_text(row.get("gender")),
            "profileImage": from_db_text(row.get("profile_image")),
            "preferences": row.get("preferences") or {},
            "newsletterSubscribed": bool(row.get("newsletter_subscribed")),
        }

    def _serialize(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": str(row["customer_id"]),
            "userId": str(row["user_id"]) if row.get("user_id") else None,
            "guestToken": from_db_text(row.get("guest_token")),
            "email": from_db_text(row.get("email")) or "",
            "phone": from_db_text(row.get("phone")) or "",
            "fullName": from_db_text(row.get("full_name")) or "",
            "isGuest": bool(row.get("is_guest")),
            "isActive": bool(row.get("is_active")),
            "profile": self._serialize_profile(row),
            "createdAt": _format_dt(row.get("created_at")),
            "updatedAt": _format_dt(row.get("updated_at")),
        }

    def list_customers(self, **kwargs) -> dict[str, Any]:
        params = _base_list_params(kwargs)
        if kwargs.get("is_guest") is not None:
            params["is_guest"] = kwargs["is_guest"]
        rows, total = customer_repository.list_paginated(**params)
        page = params["page"]
        page_size = params["page_size"]
        return {
            "items": [self._serialize(r) for r in rows],
            "pagination": {
                "page": page,
                "pageSize": page_size,
                "total": total,
                "totalPages": max(1, (total + page_size - 1) // page_size),
            },
        }

    def get_customer(self, customer_id: int) -> dict[str, Any]:
        row = customer_repository.fetch_by_id(customer_id)
        if not row:
            raise NotFoundException("Customer not found")
        return self._serialize(row)

    def create_customer(self, payload: dict[str, Any]) -> dict[str, Any]:
        email = (payload.get("email") or "").strip()
        full_name = (payload.get("fullName") or "").strip()
        if not full_name:
            raise ValidationException(
                details=[{"field": "fullName", "message": "Full name is required"}]
            )
        if email and customer_repository.email_exists(email):
            raise ConflictException("Email already registered")

        with atomic() as conn:
            row = customer_repository.create({
                "user_id": _optional_int(payload.get("userId")),
                "guest_token": to_db_text(payload.get("guestToken")),
                "email": to_db_text(email),
                "phone": to_db_text(payload.get("phone")),
                "full_name": to_db_text(full_name),
                "is_guest": bool(payload.get("isGuest", False)),
                "is_active": bool(payload.get("isActive", True)),
            }, conn=conn)
            customer_id = int(row["customer_id"])

            profile = payload.get("profile")
            if profile:
                dob = profile.get("dateOfBirth")
                customer_repository.upsert_profile(customer_id, {
                    "date_of_birth": dob if dob not in ("", None) else None,
                    "gender": to_db_text(profile.get("gender")),
                    "profile_image": to_db_text(profile.get("profileImage")),
                    "preferences": profile.get("preferences") or {},
                    "newsletter_subscribed": bool(profile.get("newsletterSubscribed", False)),
                }, conn=conn)

        return self.get_customer(customer_id)

    def update_customer(self, customer_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        if not customer_repository.fetch_by_id(customer_id):
            raise NotFoundException("Customer not found")

        updates: dict[str, Any] = {}
        if "email" in payload:
            email = (payload.get("email") or "").strip()
            if email and customer_repository.email_exists(email, exclude_id=customer_id):
                raise ConflictException("Email already registered")
            updates["email"] = to_db_text(email)
        if "phone" in payload:
            updates["phone"] = to_db_text(payload.get("phone"))
        if "fullName" in payload:
            updates["full_name"] = to_db_text(payload.get("fullName"))
        if "isGuest" in payload:
            updates["is_guest"] = bool(payload.get("isGuest"))
        if "isActive" in payload:
            updates["is_active"] = bool(payload.get("isActive"))

        with atomic() as conn:
            if updates:
                customer_repository.update(customer_id, updates, conn=conn)
            profile = payload.get("profile")
            if profile:
                profile_updates: dict[str, Any] = {}
                if "dateOfBirth" in profile:
                    dob = profile.get("dateOfBirth")
                    profile_updates["date_of_birth"] = dob if dob not in ("", None) else None
                if "gender" in profile:
                    profile_updates["gender"] = to_db_text(profile.get("gender"))
                if "profileImage" in profile:
                    profile_updates["profile_image"] = to_db_text(profile.get("profileImage"))
                if "preferences" in profile:
                    profile_updates["preferences"] = profile.get("preferences") or {}
                if "newsletterSubscribed" in profile:
                    profile_updates["newsletter_subscribed"] = bool(profile.get("newsletterSubscribed"))
                if profile_updates:
                    customer_repository.upsert_profile(customer_id, profile_updates, conn=conn)

        return self.get_customer(customer_id)

    def delete_customer(self, customer_id: int) -> None:
        if not customer_repository.soft_delete(customer_id):
            raise NotFoundException("Customer not found")


customer_service = CustomerService()
