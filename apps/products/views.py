from __future__ import annotations

from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.request import Request
from rest_framework.views import APIView

from apps.products.services.brand_service import brand_service
from apps.products.services.catalog_meta_options_service import catalog_meta_options_service
from apps.products.services.product_service import product_service
from apps.products.services.review_service import review_service
from apps.products.services.tag_service import tag_service
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
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in {"true", "1", "yes"}:
        return True
    if normalized in {"false", "0", "no"}:
        return False
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
        "category_id": _optional_int(request.query_params.get("categoryId")),
        "sub_category_id": _optional_int(request.query_params.get("subCategoryId")),
        "under_sub_category_id": _optional_int(request.query_params.get("underSubCategoryId")),
        "brand_id": _optional_int(request.query_params.get("brandId")),
    }


@method_decorator(csrf_exempt, name="dispatch")
class ProductListCreateView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request: Request):
        _require_admin(request)
        data = product_service.list_products(**_list_params(request))
        return APIResponse.success(data=data, endpoint=request.path)

    def post(self, request: Request):
        _require_admin(request)
        item = product_service.create_product(request.data)
        return APIResponse.success(
            data={"item": item},
            message="Product created",
            status_code=201,
            endpoint=request.path,
        )


@method_decorator(csrf_exempt, name="dispatch")
class ProductDetailView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request: Request, product_id: int):
        _require_admin(request)
        item = product_service.get_product(product_id)
        return APIResponse.success(data={"item": item}, endpoint=request.path)

    def patch(self, request: Request, product_id: int):
        _require_admin(request)
        item = product_service.update_product(product_id, request.data)
        return APIResponse.success(
            data={"item": item},
            message="Product updated",
            endpoint=request.path,
        )

    def delete(self, request: Request, product_id: int):
        _require_admin(request)
        product_service.delete_product(product_id)
        return APIResponse.success(message="Product deleted", endpoint=request.path)


@method_decorator(csrf_exempt, name="dispatch")
class ProductOptionsView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request: Request):
        _require_admin(request)
        return APIResponse.success(data=product_service.get_form_options(), endpoint=request.path)


@method_decorator(csrf_exempt, name="dispatch")
class BrandListCreateView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request: Request):
        _require_admin(request)
        params = _list_params(request)
        params["sort_by"] = request.query_params.get("sortBy", "display_order")
        params["sort_dir"] = request.query_params.get("sortDir", "asc")
        data = brand_service.list_brands(**params)
        return APIResponse.success(data=data, endpoint=request.path)

    def post(self, request: Request):
        _require_admin(request)
        item = brand_service.create_brand(request.data)
        return APIResponse.success(
            data={"item": item},
            message="Brand created",
            status_code=201,
            endpoint=request.path,
        )


@method_decorator(csrf_exempt, name="dispatch")
class BrandDetailView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request: Request, brand_id: int):
        _require_admin(request)
        item = brand_service.get_brand(brand_id)
        return APIResponse.success(data={"item": item}, endpoint=request.path)

    def patch(self, request: Request, brand_id: int):
        _require_admin(request)
        item = brand_service.update_brand(brand_id, request.data)
        return APIResponse.success(
            data={"item": item},
            message="Brand updated",
            endpoint=request.path,
        )

    def delete(self, request: Request, brand_id: int):
        _require_admin(request)
        brand_service.delete_brand(brand_id)
        return APIResponse.success(message="Brand deleted", endpoint=request.path)


@method_decorator(csrf_exempt, name="dispatch")
class ReviewListCreateView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request: Request):
        _require_admin(request)
        params = _list_params(request)
        params["product_id"] = _optional_int(request.query_params.get("productId"))
        params["is_approved"] = _optional_bool(request.query_params.get("isApproved"))
        data = review_service.list_reviews(**params)
        return APIResponse.success(data=data, endpoint=request.path)

    def post(self, request: Request):
        _require_admin(request)
        item = review_service.create_review(request.data)
        return APIResponse.success(
            data={"item": item},
            message="Review created",
            status_code=201,
            endpoint=request.path,
        )


@method_decorator(csrf_exempt, name="dispatch")
class ReviewDetailView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request: Request, review_id: int):
        _require_admin(request)
        item = review_service.get_review(review_id)
        return APIResponse.success(data={"item": item}, endpoint=request.path)

    def patch(self, request: Request, review_id: int):
        admin_id = _require_admin(request)
        item = review_service.update_review(review_id, request.data, admin_id=admin_id)
        return APIResponse.success(
            data={"item": item},
            message="Review updated",
            endpoint=request.path,
        )

    def delete(self, request: Request, review_id: int):
        _require_admin(request)
        review_service.delete_review(review_id)
        return APIResponse.success(message="Review deleted", endpoint=request.path)


@method_decorator(csrf_exempt, name="dispatch")
class TagListCreateView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request: Request):
        _require_admin(request)
        params = _list_params(request)
        params["sort_by"] = request.query_params.get("sortBy", "tag_name")
        params["sort_dir"] = request.query_params.get("sortDir", "asc")
        data = tag_service.list_tags(**params)
        return APIResponse.success(data=data, endpoint=request.path)

    def post(self, request: Request):
        _require_admin(request)
        item = tag_service.create_tag(request.data)
        return APIResponse.success(
            data={"item": item},
            message="Tag created",
            status_code=201,
            endpoint=request.path,
        )


@method_decorator(csrf_exempt, name="dispatch")
class TagDetailView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request: Request, tag_id: int):
        _require_admin(request)
        item = tag_service.get_tag(tag_id)
        return APIResponse.success(data={"item": item}, endpoint=request.path)

    def patch(self, request: Request, tag_id: int):
        _require_admin(request)
        item = tag_service.update_tag(tag_id, request.data)
        return APIResponse.success(
            data={"item": item},
            message="Tag updated",
            endpoint=request.path,
        )

    def delete(self, request: Request, tag_id: int):
        _require_admin(request)
        tag_service.delete_tag(tag_id)
        return APIResponse.success(message="Tag deleted", endpoint=request.path)


@method_decorator(csrf_exempt, name="dispatch")
class CatalogMetaOptionsView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request: Request):
        _require_admin(request)
        return APIResponse.success(
            data=catalog_meta_options_service.get_options(),
            endpoint=request.path,
        )
