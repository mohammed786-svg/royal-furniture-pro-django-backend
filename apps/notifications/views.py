from __future__ import annotations

from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.request import Request
from rest_framework.views import APIView

from apps.notifications.services.notification_log_service import notification_log_service
from apps.notifications.services.notification_options_service import notification_options_service
from apps.notifications.services.notification_service import notification_service
from core.exceptions.base import AuthenticationException
from core.pagination import PaginationParams
from core.responses.formatter import APIResponse


def _require_admin(request: Request) -> int:
    user_id = getattr(request, "user_id", None)
    if not user_id:
        raise AuthenticationException("Not authenticated")
    return int(user_id)


def _optional_int(value) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _optional_bool(value) -> bool | None:
    if value in (None, ""):
        return None
    return str(value).lower() in ("1", "true", "yes")


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
class NotificationListCreateView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request: Request):
        _require_admin(request)
        params = _list_params(request)
        params["channel"] = (request.query_params.get("channel") or "").strip().upper()
        params["target_type"] = (request.query_params.get("targetType") or "").strip().upper()
        params["is_active"] = _optional_bool(request.query_params.get("isActive"))
        data = notification_service.list_notifications(**params)
        return APIResponse.success(data=data, endpoint=request.path)

    def post(self, request: Request):
        _require_admin(request)
        item = notification_service.create_notification(request.data)
        return APIResponse.success(
            data={"item": item},
            message="Notification created",
            status_code=201,
            endpoint=request.path,
        )


@method_decorator(csrf_exempt, name="dispatch")
class NotificationDetailView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request: Request, notification_id: int):
        _require_admin(request)
        item = notification_service.get_notification(notification_id)
        return APIResponse.success(data={"item": item}, endpoint=request.path)

    def patch(self, request: Request, notification_id: int):
        _require_admin(request)
        item = notification_service.update_notification(notification_id, request.data)
        return APIResponse.success(
            data={"item": item},
            message="Notification updated",
            endpoint=request.path,
        )

    def delete(self, request: Request, notification_id: int):
        _require_admin(request)
        notification_service.delete_notification(notification_id)
        return APIResponse.success(message="Notification deleted", endpoint=request.path)


@method_decorator(csrf_exempt, name="dispatch")
class NotificationLogListView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request: Request):
        _require_admin(request)
        params = _list_params(request)
        params["notification_id"] = _optional_int(request.query_params.get("notificationId"))
        params["status"] = (request.query_params.get("status") or "").strip().upper()
        data = notification_log_service.list_logs(**params)
        return APIResponse.success(data=data, endpoint=request.path)


@method_decorator(csrf_exempt, name="dispatch")
class NotificationLogDetailView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request: Request, notification_log_id: int):
        _require_admin(request)
        item = notification_log_service.get_log(notification_log_id)
        return APIResponse.success(data={"item": item}, endpoint=request.path)


@method_decorator(csrf_exempt, name="dispatch")
class NotificationMetaOptionsView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request: Request):
        _require_admin(request)
        return APIResponse.success(
            data=notification_options_service.get_options(),
            endpoint=request.path,
        )
