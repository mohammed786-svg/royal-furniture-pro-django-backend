from __future__ import annotations

from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.request import Request
from rest_framework.views import APIView

from apps.analytics.services.page_view_service import page_view_service
from apps.analytics.services.sales_service import sales_service
from apps.analytics.services.search_history_service import search_history_service
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
        "sort_by": request.query_params.get("sortBy", "created_at"),
        "sort_dir": request.query_params.get("sortDir", "desc"),
    }


@method_decorator(csrf_exempt, name="dispatch")
class SalesDashboardView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request: Request):
        _require_admin(request)
        period = (request.query_params.get("period") or "30d").strip()
        data = sales_service.get_dashboard(period=period)
        return APIResponse.success(data=data, endpoint=request.path)


@method_decorator(csrf_exempt, name="dispatch")
class PageViewListCreateView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request: Request):
        _require_admin(request)
        params = _list_params(request)
        params["sort_by"] = request.query_params.get("sortBy", "viewed_at")
        params["customer_id"] = _optional_int(request.query_params.get("customerId"))
        params["product_id"] = _optional_int(request.query_params.get("productId"))
        data = page_view_service.list_page_views(**params)
        return APIResponse.success(data=data, endpoint=request.path)

    def post(self, request: Request):
        _require_admin(request)
        item = page_view_service.create_page_view(request.data)
        return APIResponse.success(
            data={"item": item},
            message="Page view created",
            status_code=201,
            endpoint=request.path,
        )


@method_decorator(csrf_exempt, name="dispatch")
class PageViewDetailView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request: Request, page_view_id: int):
        _require_admin(request)
        item = page_view_service.get_page_view(page_view_id)
        return APIResponse.success(data={"item": item}, endpoint=request.path)

    def patch(self, request: Request, page_view_id: int):
        _require_admin(request)
        item = page_view_service.update_page_view(page_view_id, request.data)
        return APIResponse.success(
            data={"item": item},
            message="Page view updated",
            endpoint=request.path,
        )

    def delete(self, request: Request, page_view_id: int):
        _require_admin(request)
        page_view_service.delete_page_view(page_view_id)
        return APIResponse.success(message="Page view deleted", endpoint=request.path)


@method_decorator(csrf_exempt, name="dispatch")
class PageViewDashboardView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request: Request):
        _require_admin(request)
        period = (request.query_params.get("period") or "30d").strip()
        data = page_view_service.get_dashboard(period=period)
        return APIResponse.success(data=data, endpoint=request.path)


@method_decorator(csrf_exempt, name="dispatch")
class SearchListCreateView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request: Request):
        _require_admin(request)
        params = _list_params(request)
        params["sort_by"] = request.query_params.get("sortBy", "searched_at")
        params["customer_id"] = _optional_int(request.query_params.get("customerId"))
        data = search_history_service.list_searches(**params)
        return APIResponse.success(data=data, endpoint=request.path)

    def post(self, request: Request):
        _require_admin(request)
        item = search_history_service.create_search(request.data)
        return APIResponse.success(
            data={"item": item},
            message="Search history created",
            status_code=201,
            endpoint=request.path,
        )


@method_decorator(csrf_exempt, name="dispatch")
class SearchDetailView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request: Request, search_history_id: int):
        _require_admin(request)
        item = search_history_service.get_search(search_history_id)
        return APIResponse.success(data={"item": item}, endpoint=request.path)

    def patch(self, request: Request, search_history_id: int):
        _require_admin(request)
        item = search_history_service.update_search(search_history_id, request.data)
        return APIResponse.success(
            data={"item": item},
            message="Search history updated",
            endpoint=request.path,
        )

    def delete(self, request: Request, search_history_id: int):
        _require_admin(request)
        search_history_service.delete_search(search_history_id)
        return APIResponse.success(message="Search history deleted", endpoint=request.path)


@method_decorator(csrf_exempt, name="dispatch")
class SearchDashboardView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request: Request):
        _require_admin(request)
        period = (request.query_params.get("period") or "30d").strip()
        data = search_history_service.get_dashboard(period=period)
        return APIResponse.success(data=data, endpoint=request.path)
