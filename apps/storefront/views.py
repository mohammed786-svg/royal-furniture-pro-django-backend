from __future__ import annotations

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.request import Request
from rest_framework.views import APIView

from apps.storefront.services.catalog_service import (
    storefront_catalog_service,
    storefront_product_service,
)
from apps.storefront.services.home_service import storefront_home_service
from core.exceptions.base import NotFoundException
from core.responses.formatter import APIResponse


@method_decorator(csrf_exempt, name="dispatch")
class StorefrontHomeView(APIView):
    """Public homepage aggregate payload — cached in Redis."""

    authentication_classes = []
    permission_classes = []

    def get(self, request: Request):
        data = storefront_home_service.get_homepage()
        return APIResponse.success(data=data, endpoint=request.path)


@method_decorator(csrf_exempt, name="dispatch")
class StorefrontCategoryListingView(APIView):
    """Public PLP for category + sub-category slugs."""

    authentication_classes = []
    permission_classes = []

    def get(self, request: Request, category_slug: str, sub_category_slug: str):
        try:
            page = max(1, int(request.query_params.get("page", 1)))
            page_size = min(48, max(1, int(request.query_params.get("pageSize", 24))))
            sort = request.query_params.get("sort")
            data = storefront_catalog_service.get_category_listing(
                category_slug,
                sub_category_slug,
                page=page,
                page_size=page_size,
                sort=sort,
            )
            return APIResponse.success(data=data, endpoint=request.path)
        except NotFoundException as exc:
            return APIResponse.error(message=str(exc), status_code=404, endpoint=request.path)
        except (TypeError, ValueError):
            return APIResponse.error(message="Invalid query parameters", status_code=400, endpoint=request.path)


@method_decorator(csrf_exempt, name="dispatch")
class StorefrontProductDetailView(APIView):
    """Public PDP by product slug."""

    authentication_classes = []
    permission_classes = []

    def get(self, request: Request, slug: str):
        try:
            data = storefront_product_service.get_product_by_slug(slug)
            return APIResponse.success(data=data, endpoint=request.path)
        except NotFoundException as exc:
            return APIResponse.error(message=str(exc), status_code=404, endpoint=request.path)
