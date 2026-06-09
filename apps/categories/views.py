from __future__ import annotations

from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.request import Request
from rest_framework.views import APIView

from apps.categories.services.category_service import category_service
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
        "sort_by": request.query_params.get("sortBy", "display_order"),
        "sort_dir": request.query_params.get("sortDir", "asc"),
        "category_id": _optional_int(request.query_params.get("categoryId")),
        "sub_category_id": _optional_int(request.query_params.get("subCategoryId")),
    }


def _optional_int(value) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


@method_decorator(csrf_exempt, name="dispatch")
class CategoryListCreateView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request: Request):
        _require_admin(request)
        data = category_service.list_categories(**_list_params(request))
        return APIResponse.success(data=data, endpoint=request.path)

    def post(self, request: Request):
        _require_admin(request)
        item = category_service.create_category(request.data)
        return APIResponse.success(
            data={"item": item},
            message="Category created",
            status_code=201,
            endpoint=request.path,
        )


@method_decorator(csrf_exempt, name="dispatch")
class CategoryDetailView(APIView):
    authentication_classes = []
    permission_classes = []

    def patch(self, request: Request, category_id: int):
        _require_admin(request)
        item = category_service.update_category(category_id, request.data)
        return APIResponse.success(
            data={"item": item},
            message="Category updated",
            endpoint=request.path,
        )

    def delete(self, request: Request, category_id: int):
        _require_admin(request)
        category_service.delete_category(category_id)
        return APIResponse.success(message="Category deleted", endpoint=request.path)


@method_decorator(csrf_exempt, name="dispatch")
class SubCategoryListCreateView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request: Request):
        _require_admin(request)
        data = category_service.list_sub_categories(**_list_params(request))
        return APIResponse.success(data=data, endpoint=request.path)

    def post(self, request: Request):
        _require_admin(request)
        item = category_service.create_sub_category(request.data)
        return APIResponse.success(
            data={"item": item},
            message="Sub-category created",
            status_code=201,
            endpoint=request.path,
        )


@method_decorator(csrf_exempt, name="dispatch")
class SubCategoryDetailView(APIView):
    authentication_classes = []
    permission_classes = []

    def patch(self, request: Request, sub_category_id: int):
        _require_admin(request)
        item = category_service.update_sub_category(sub_category_id, request.data)
        return APIResponse.success(
            data={"item": item},
            message="Sub-category updated",
            endpoint=request.path,
        )

    def delete(self, request: Request, sub_category_id: int):
        _require_admin(request)
        category_service.delete_sub_category(sub_category_id)
        return APIResponse.success(message="Sub-category deleted", endpoint=request.path)


@method_decorator(csrf_exempt, name="dispatch")
class UnderSubCategoryListCreateView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request: Request):
        _require_admin(request)
        data = category_service.list_under_sub_categories(**_list_params(request))
        return APIResponse.success(data=data, endpoint=request.path)

    def post(self, request: Request):
        _require_admin(request)
        item = category_service.create_under_sub_category(request.data)
        return APIResponse.success(
            data={"item": item},
            message="Under sub-category created",
            status_code=201,
            endpoint=request.path,
        )


@method_decorator(csrf_exempt, name="dispatch")
class UnderSubCategoryDetailView(APIView):
    authentication_classes = []
    permission_classes = []

    def patch(self, request: Request, under_sub_category_id: int):
        _require_admin(request)
        item = category_service.update_under_sub_category(under_sub_category_id, request.data)
        return APIResponse.success(
            data={"item": item},
            message="Under sub-category updated",
            endpoint=request.path,
        )

    def delete(self, request: Request, under_sub_category_id: int):
        _require_admin(request)
        category_service.delete_under_sub_category(under_sub_category_id)
        return APIResponse.success(message="Under sub-category deleted", endpoint=request.path)


@method_decorator(csrf_exempt, name="dispatch")
class CatalogOptionsView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request: Request):
        _require_admin(request)
        category_id = _optional_int(request.query_params.get("categoryId"))
        data = {
            **category_service.get_options(),
            **category_service.get_sub_category_options(category_id),
        }
        return APIResponse.success(data=data, endpoint=request.path)
