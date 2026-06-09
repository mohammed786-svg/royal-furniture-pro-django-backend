from __future__ import annotations

from typing import Any, Optional

from django.contrib.auth.hashers import check_password, make_password
from django.http import HttpRequest

from apps.authentication.repositories.admin_session_repository import admin_session_repository
from apps.authentication.repositories.login_history_repository import login_history_repository
from apps.authentication.repositories.permission_repository import permission_repository
from apps.authentication.repositories.user_repository import user_repository
from core.auth.jwt_handler import jwt_handler
from core.cache.cache_keys import CacheKeys
from core.cache.cache_manager import cache_manager
from core.database import atomic
from core.exceptions.base import AuthenticationException, ValidationException
from core.helpers.ip import get_client_ip


REFRESH_COOKIE = "royal_admin_refresh"


class AdminAuthService:
    def login(self, request: HttpRequest, email: str, password: str) -> dict[str, Any]:
        email = (email or "").strip().lower()
        password = password or ""
        ip_address = get_client_ip(request)
        user_agent = request.META.get("HTTP_USER_AGENT", "unknown")[:500]

        if not email and not password:
            raise ValidationException(
                details=[
                    {"field": "email", "message": "Email is required"},
                    {"field": "password", "message": "Password is required"},
                ],
            )
        if not email:
            raise ValidationException(
                details=[{"field": "email", "message": "Email is required"}],
            )
        if not password:
            raise ValidationException(
                details=[{"field": "password", "message": "Password is required"}],
            )

        user = user_repository.fetch_admin_by_email(email)
        if not user or not check_password(password, user["password_hash"]):
            login_history_repository.record(
                user_id=user["user_id"] if user else None,
                login_type="admin",
                status="failed",
                ip_address=ip_address,
                user_agent=user_agent,
                failure_reason="invalid_credentials",
            )
            raise AuthenticationException("Invalid email or password")

        payload = {
            "user_id": user["user_id"],
            "role": user["role_code"],
            "email": user["email"],
            "session": True,
        }
        access_token = jwt_handler.create_access_token(payload, admin=True)
        refresh_token = jwt_handler.create_refresh_token(
            {"user_id": user["user_id"], "role": user["role_code"], "session": True},
        )

        with atomic():
            session = admin_session_repository.create_session(
                user_id=user["user_id"],
                access_token=access_token,
                refresh_token=refresh_token,
                ip_address=ip_address,
                user_agent=user_agent,
            )
            user_repository.record_login(user["user_id"])

        login_history_repository.record(
            user_id=user["user_id"],
            login_type="admin",
            status="success",
            ip_address=ip_address,
            user_agent=user_agent,
        )

        profile = self._build_user_profile(user)
        self._cache_user_profile(user["user_id"], profile)

        return {
            "user": profile,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "session_id": session.get("admin_session_id"),
            "expires_in_hours": jwt_handler.admin_hours,
        }

    def refresh(self, request: HttpRequest, refresh_token: str) -> dict[str, Any]:
        if not refresh_token:
            raise AuthenticationException("Refresh token missing")

        session = admin_session_repository.fetch_active_by_refresh_token(refresh_token)
        if not session:
            raise AuthenticationException("Session expired or revoked")

        user = user_repository.fetch_admin_by_id(session["user_id"])
        if not user:
            raise AuthenticationException("User not found or inactive")

        payload = {
            "user_id": user["user_id"],
            "role": user["role_code"],
            "email": user["email"],
            "session": True,
        }
        access_token = jwt_handler.create_access_token(payload, admin=True)
        new_refresh = jwt_handler.create_refresh_token(
            {"user_id": user["user_id"], "role": user["role_code"], "session": True},
        )

        admin_session_repository.rotate_tokens(
            session["admin_session_id"],
            access_token=access_token,
            refresh_token=new_refresh,
        )

        profile = self._build_user_profile(user)
        self._cache_user_profile(user["user_id"], profile)

        return {
            "user": profile,
            "access_token": access_token,
            "refresh_token": new_refresh,
            "expires_in_hours": jwt_handler.admin_hours,
        }

    def logout(self, request: HttpRequest, access_token: Optional[str], refresh_token: Optional[str]) -> None:
        user_id = None
        if access_token:
            session = admin_session_repository.fetch_active_by_access_token(access_token)
            if session:
                admin_session_repository.revoke_session(session["admin_session_id"])
                user_id = session["user_id"]
        elif refresh_token:
            session = admin_session_repository.fetch_active_by_refresh_token(refresh_token)
            if session:
                admin_session_repository.revoke_session(session["admin_session_id"])
                user_id = session["user_id"]

        if user_id:
            cache_manager.delete(CacheKeys.admin_user(user_id))
            cache_manager.delete(CacheKeys.session(user_id))

    def me(self, user_id: int) -> dict[str, Any]:
        cached = cache_manager.get(CacheKeys.admin_user(user_id))
        if cached:
            return cached

        user = user_repository.fetch_admin_by_id(user_id)
        if not user:
            raise AuthenticationException("User not found or inactive")

        profile = self._build_user_profile(user)
        self._cache_user_profile(user_id, profile)
        return profile

    def change_password(
        self,
        user_id: int,
        current_password: str,
        new_password: str,
    ) -> None:
        if len(new_password) < 8:
            raise ValidationException(
                details=[
                    {
                        "field": "newPassword",
                        "message": "New password must be at least 8 characters",
                    },
                ],
            )

        user = user_repository.fetch_admin_auth_by_id(user_id)
        if not user:
            raise AuthenticationException("User not found")

        if not check_password(current_password, user["password_hash"]):
            raise AuthenticationException("Current password is incorrect")

        user_repository.update_password(user_id, make_password(new_password))
        admin_session_repository.revoke_all_for_user(user_id)
        cache_manager.delete(CacheKeys.admin_user(user_id))
        cache_manager.delete(CacheKeys.session(user_id))

    def update_profile(
        self,
        user_id: int,
        *,
        full_name: str,
        phone: Optional[str] = None,
    ) -> dict[str, Any]:
        full_name = (full_name or "").strip()
        if not full_name:
            raise ValidationException(
                details=[{"field": "fullName", "message": "Full name is required"}],
            )

        user_repository.update_profile(user_id, full_name=full_name, phone=phone)
        cache_manager.delete(CacheKeys.admin_user(user_id))
        return self.me(user_id)

    def _build_user_profile(self, user: dict[str, Any]) -> dict[str, Any]:
        allowed_menus = permission_repository.fetch_menu_permissions_for_role(user["role_code"])
        return {
            "id": str(user["user_id"]),
            "email": user["email"],
            "fullName": user["full_name"],
            "phone": None if user.get("phone") in (None, "NA") else user.get("phone"),
            "avatarUrl": None if user.get("avatar_url") in (None, "NA") else user.get("avatar_url"),
            "role": user["role_code"],
            "roleName": user["role_name"],
            "allowedMenus": allowed_menus,
        }

    def _cache_user_profile(self, user_id: int, profile: dict[str, Any]) -> None:
        cache_manager.set(CacheKeys.admin_user(user_id), profile, ttl=300)


admin_auth_service = AdminAuthService()
