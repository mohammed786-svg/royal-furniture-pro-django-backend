from __future__ import annotations

from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.request import Request
from rest_framework.views import APIView

from apps.settings_app.services.setting_service import setting_service
from core.exceptions.base import AuthenticationException
from core.pagination import PaginationParams
from core.responses.formatter import APIResponse


def _require_admin(request: Request) -> int:
    user_id = getattr(request, "user_id", None)
    if not user_id:
        raise AuthenticationException("Not authenticated")
    return int(user_id)


def _list_params(request: Request) -> dict:
    page = int(request.query_params.get("page", 1))
    page_size = int(request.query_params.get("pageSize", settings.DEFAULT_PAGE_SIZE))
    pagination = PaginationParams(page=page, page_size=page_size)
    return {
        "page": pagination.page,
        "page_size": pagination.page_size,
        "search": (request.query_params.get("search") or "").strip(),
        "group": (request.query_params.get("group") or "").strip(),
        "sort_by": request.query_params.get("sortBy", "setting_key"),
        "sort_dir": request.query_params.get("sortDir", "asc"),
    }


@method_decorator(csrf_exempt, name="dispatch")
class SettingListCreateView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request: Request):
        _require_admin(request)
        data = setting_service.list_settings(**_list_params(request))
        return APIResponse.success(data=data, endpoint=request.path)

    def post(self, request: Request):
        _require_admin(request)
        item = setting_service.create_setting(request.data)
        return APIResponse.success(
            data={"item": item},
            message="Setting created",
            status_code=201,
            endpoint=request.path,
        )


@method_decorator(csrf_exempt, name="dispatch")
class SettingDetailView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request: Request, setting_id: int):
        _require_admin(request)
        item = setting_service.get_setting(setting_id)
        return APIResponse.success(data={"item": item}, endpoint=request.path)

    def patch(self, request: Request, setting_id: int):
        _require_admin(request)
        item = setting_service.update_setting(setting_id, request.data)
        return APIResponse.success(
            data={"item": item},
            message="Setting updated",
            endpoint=request.path,
        )

    def delete(self, request: Request, setting_id: int):
        _require_admin(request)
        setting_service.delete_setting(setting_id)
        return APIResponse.success(message="Setting deleted", endpoint=request.path)


@method_decorator(csrf_exempt, name="dispatch")
class SettingGroupsView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request: Request):
        _require_admin(request)
        groups = setting_service.list_groups()
        return APIResponse.success(data={"groups": groups}, endpoint=request.path)
