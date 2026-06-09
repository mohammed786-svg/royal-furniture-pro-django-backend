from __future__ import annotations

from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.request import Request
from rest_framework.views import APIView

from apps.authentication.services.admin_meta_options_service import admin_meta_options_service
from apps.authentication.services.admin_user_service import admin_user_service
from apps.authentication.services.login_history_service import login_history_service
from core.exceptions.base import AuthenticationException, AuthorizationException
from core.permissions import ROLE_SUPER_ADMIN
from core.pagination import PaginationParams
from core.responses.formatter import APIResponse


def _require_admin(request: Request) -> int:
    user_id = getattr(request, "user_id", None)
    if not user_id:
        raise AuthenticationException("Not authenticated")
    return int(user_id)


def _require_super_admin(request: Request) -> int:
    user_id = _require_admin(request)
    role = getattr(request, "user_role", None)
    if role != ROLE_SUPER_ADMIN:
        raise AuthorizationException("Super admin access required")
    return user_id


def _optional_int(value) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _list_params(request: Request) -> dict:
    page = int(request.query_params.get("page", 1))
    page_size = int(request.query_params.get("pageSize", settings.DEFAULT_PAGE_SIZE))
    pagination = PaginationParams(page=page, page_size=page_size)
    return {
        "page": pagination.page,
        "page_size": pagination.page_size,
        "search": (request.query_params.get("search") or "").strip(),
        "sort_by": request.query_params.get("sortBy", "created_at"),
        "sort_dir": request.query_params.get("sortDir", "desc"),
    }


@method_decorator(csrf_exempt, name="dispatch")
class AdminUserListCreateView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request: Request):
        _require_admin(request)
        params = _list_params(request)
        data = admin_user_service.list_users(**params)
        return APIResponse.success(data=data, endpoint=request.path)

    def post(self, request: Request):
        _require_super_admin(request)
        item = admin_user_service.create_user(request.data)
        return APIResponse.success(
            data={"item": item},
            message="Admin user created",
            status_code=201,
            endpoint=request.path,
        )


@method_decorator(csrf_exempt, name="dispatch")
class AdminUserDetailView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request: Request, user_id: int):
        _require_admin(request)
        item = admin_user_service.get_user(user_id)
        return APIResponse.success(data={"item": item}, endpoint=request.path)

    def patch(self, request: Request, user_id: int):
        _require_super_admin(request)
        item = admin_user_service.update_user(user_id, request.data)
        return APIResponse.success(
            data={"item": item},
            message="Admin user updated",
            endpoint=request.path,
        )

    def delete(self, request: Request, user_id: int):
        acting_admin_id = _require_super_admin(request)
        admin_user_service.delete_user(user_id, acting_admin_id=acting_admin_id)
        return APIResponse.success(message="Admin user deleted", endpoint=request.path)


@method_decorator(csrf_exempt, name="dispatch")
class LoginHistoryListView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request: Request):
        _require_admin(request)
        params = _list_params(request)
        params["sort_by"] = request.query_params.get("sortBy", "login_at")
        params["user_id"] = _optional_int(request.query_params.get("userId"))
        params["status"] = (request.query_params.get("status") or "").strip()
        params["login_type"] = (request.query_params.get("loginType") or "").strip()
        data = login_history_service.list_history(**params)
        return APIResponse.success(data=data, endpoint=request.path)


@method_decorator(csrf_exempt, name="dispatch")
class LoginHistoryDetailView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request: Request, login_history_id: int):
        _require_admin(request)
        item = login_history_service.get_history(login_history_id)
        return APIResponse.success(data={"item": item}, endpoint=request.path)


@method_decorator(csrf_exempt, name="dispatch")
class AdministrationMetaOptionsView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request: Request):
        _require_admin(request)
        return APIResponse.success(
            data=admin_meta_options_service.get_options(),
            endpoint=request.path,
        )
