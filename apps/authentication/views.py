from __future__ import annotations

from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.request import Request
from rest_framework.views import APIView

from apps.authentication.services.admin_auth_service import REFRESH_COOKIE, admin_auth_service
from core.exceptions.base import AuthenticationException
from core.responses.formatter import APIResponse


def _set_refresh_cookie(response, refresh_token: str, remember: bool = False) -> None:
    max_age = 7 * 24 * 3600 if remember else settings.ADMIN_SESSION_HOURS * 3600
    response.set_cookie(
        REFRESH_COOKIE,
        refresh_token,
        max_age=max_age,
        httponly=True,
        secure=not settings.DEBUG,
        samesite="Lax",
        path="/api/v1/auth",
    )


def _clear_refresh_cookie(response) -> None:
    response.delete_cookie(REFRESH_COOKIE, path="/api/v1/auth")


@method_decorator(csrf_exempt, name="dispatch")
class AdminLoginView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request: Request):
        email = request.data.get("email", "")
        password = request.data.get("password", "")
        remember = bool(request.data.get("remember", False))

        result = admin_auth_service.login(request, email, password)
        response = APIResponse.success(
            data={
                "user": result["user"],
                "accessToken": result["access_token"],
                "refreshToken": result["refresh_token"],
                "expiresInHours": result["expires_in_hours"],
            },
            message="Login successful",
            endpoint=request.path,
        )
        _set_refresh_cookie(response, result["refresh_token"], remember=remember)
        return response


@method_decorator(csrf_exempt, name="dispatch")
class AdminRefreshView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request: Request):
        refresh_token = request.COOKIES.get(REFRESH_COOKIE) or request.data.get("refreshToken")
        result = admin_auth_service.refresh(request, refresh_token)
        response = APIResponse.success(
            data={
                "user": result["user"],
                "accessToken": result["access_token"],
                "refreshToken": result["refresh_token"],
                "expiresInHours": result["expires_in_hours"],
            },
            message="Token refreshed",
            endpoint=request.path,
        )
        _set_refresh_cookie(response, result["refresh_token"])
        return response


@method_decorator(csrf_exempt, name="dispatch")
class AdminLogoutView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request: Request):
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        access_token = auth_header[7:].strip() if auth_header.startswith("Bearer ") else None
        refresh_token = request.COOKIES.get(REFRESH_COOKIE) or request.data.get("refreshToken")
        admin_auth_service.logout(request, access_token, refresh_token)
        response = APIResponse.success(
            message="Logged out successfully",
            endpoint=request.path,
        )
        _clear_refresh_cookie(response)
        return response


class AdminMeView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request: Request):
        user_id = getattr(request, "user_id", None)
        if not user_id:
            raise AuthenticationException("Not authenticated")
        profile = admin_auth_service.me(user_id)
        return APIResponse.success(data={"user": profile}, endpoint=request.path)


@method_decorator(csrf_exempt, name="dispatch")
class AdminChangePasswordView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request: Request):
        user_id = getattr(request, "user_id", None)
        if not user_id:
            raise AuthenticationException("Not authenticated")
        admin_auth_service.change_password(
            user_id,
            request.data.get("currentPassword", ""),
            request.data.get("newPassword", ""),
        )
        response = APIResponse.success(
            message="Password updated successfully",
            endpoint=request.path,
        )
        _clear_refresh_cookie(response)
        return response


@method_decorator(csrf_exempt, name="dispatch")
class AdminUpdateProfileView(APIView):
    authentication_classes = []
    permission_classes = []

    def patch(self, request: Request):
        user_id = getattr(request, "user_id", None)
        if not user_id:
            raise AuthenticationException("Not authenticated")
        profile = admin_auth_service.update_profile(
            user_id,
            full_name=request.data.get("fullName", ""),
            phone=request.data.get("phone"),
        )
        return APIResponse.success(
            data={"user": profile},
            message="Profile updated",
            endpoint=request.path,
        )
