from __future__ import annotations

from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.request import Request
from rest_framework.views import APIView

from apps.audit_logs.services.audit_log_service import audit_log_service
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


def _list_params(request: Request) -> dict:
    page = int(request.query_params.get("page", 1))
    page_size = int(request.query_params.get("pageSize", settings.DEFAULT_PAGE_SIZE))
    pagination = PaginationParams(page=page, page_size=page_size)
    return {
        "page": pagination.page,
        "page_size": pagination.page_size,
        "search": (request.query_params.get("search") or "").strip(),
        "action_type": (request.query_params.get("actionType") or "").strip(),
        "table_name": (request.query_params.get("tableName") or "").strip(),
        "user_id": _optional_int(request.query_params.get("userId")),
        "sort_by": request.query_params.get("sortBy", "logged_at"),
        "sort_dir": request.query_params.get("sortDir", "desc"),
    }


@method_decorator(csrf_exempt, name="dispatch")
class AuditLogListCreateView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request: Request):
        _require_admin(request)
        data = audit_log_service.list_audit_logs(**_list_params(request))
        return APIResponse.success(data=data, endpoint=request.path)

    def post(self, request: Request):
        admin_id = _require_admin(request)
        item = audit_log_service.create_audit_log(request.data, admin_id=admin_id)
        return APIResponse.success(
            data={"item": item},
            message="Audit log created",
            status_code=201,
            endpoint=request.path,
        )


@method_decorator(csrf_exempt, name="dispatch")
class AuditLogDetailView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request: Request, audit_log_id: int):
        _require_admin(request)
        item = audit_log_service.get_audit_log(audit_log_id)
        return APIResponse.success(data={"item": item}, endpoint=request.path)
