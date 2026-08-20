from __future__ import annotations

from typing import Optional

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


def _optional_int(value: Optional[str]) -> Optional[int]:
    if value is None or value == "":
        return None
    return int(value)


@method_decorator(csrf_exempt, name="dispatch")
class StorefrontHomeView(APIView):
    """Public homepage aggregate payload — cached in Redis."""

    authentication_classes = []
    permission_classes = []

    def get(self, request: Request):
        nocache_raw = request.query_params.get("nocache")
        nocache = str(nocache_raw or "").strip().lower() in {"1", "true", "yes"}

        # Hard refresh / nocache mode: clear Redis homepage cache first so we rebuild fresh data.
        if nocache:
            storefront_home_service.invalidate_homepage_cache()

        data = storefront_home_service.get_homepage(use_cache=not nocache)
        return APIResponse.success(data=data, endpoint=request.path)


@method_decorator(csrf_exempt, name="dispatch")
class StorefrontCollectionView(APIView):
    """Public collection PLP: new-arrivals | online-exclusive (grouped by category)."""

    authentication_classes = []
    permission_classes = []

    def get(self, request: Request, kind: str):
        try:
            data = storefront_home_service.get_collection(kind)
            return APIResponse.success(data=data, endpoint=request.path)
        except NotFoundException as exc:
            return APIResponse.error(message=str(exc), status_code=404, endpoint=request.path)


@method_decorator(csrf_exempt, name="dispatch")
class StorefrontCategoryListingView(APIView):
    """Public PLP for category + sub-category slugs."""

    authentication_classes = []
    permission_classes = []

    def get(
        self,
        request: Request,
        category_slug: str,
        sub_category_slug: str,
        under_sub_category_slug: Optional[str] = None,
    ):
        try:
            page = max(1, int(request.query_params.get("page", 1)))
            page_size = min(48, max(1, int(request.query_params.get("pageSize", 24))))
            sort = request.query_params.get("sort")
            nocache_raw = request.query_params.get("nocache")
            nocache = str(nocache_raw or "").strip().lower() in {"1", "true", "yes"}
            if nocache:
                from core.cache.cache_keys import CacheKeys
                from core.cache.cache_manager import cache_manager
                from core.cache.product_cache import bump_catalog_generation, invalidate_plp_cache_for_category

                bump_catalog_generation()
                invalidate_plp_cache_for_category(
                    category_slug=category_slug,
                    sub_category_slug=sub_category_slug,
                )
                # Also wipe any legacy PLP keys that predate generation suffixes.
                cache_manager.delete_pattern(
                    f"{CacheKeys.PREFIX}:storefront:plp:{category_slug}:{sub_category_slug}*"
                )
                cache_manager.delete_pattern(f"{CacheKeys.PREFIX}:storefront:plp:id:*")
            data = storefront_catalog_service.get_category_listing(
                category_slug,
                sub_category_slug,
                category_id=_optional_int(request.query_params.get("categoryId")),
                sub_category_id=_optional_int(request.query_params.get("subCategoryId")),
                under_sub_category_id=_optional_int(
                    request.query_params.get("underSubCategoryId")
                ),
                under_sub_category_slug=under_sub_category_slug,
                page=page,
                page_size=page_size,
                sort=sort,
                use_cache=not nocache,
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
            nocache_raw = request.query_params.get("nocache")
            nocache = str(nocache_raw or "").strip().lower() in {"1", "true", "yes"}
            if nocache:
                storefront_product_service.invalidate_product_cache(slug)
            data = storefront_product_service.get_product_by_slug(
                slug, use_cache=not nocache
            )
            return APIResponse.success(data=data, endpoint=request.path)
        except NotFoundException as exc:
            return APIResponse.error(message=str(exc), status_code=404, endpoint=request.path)
