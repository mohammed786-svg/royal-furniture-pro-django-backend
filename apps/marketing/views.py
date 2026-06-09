from __future__ import annotations

from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.request import Request
from rest_framework.views import APIView

from apps.marketing.services.banner_position_service import banner_position_service
from apps.marketing.services.banner_service import banner_service
from apps.marketing.services.cms_page_service import cms_page_service
from apps.marketing.services.coupon_service import coupon_service
from apps.marketing.services.faq_service import faq_service
from apps.marketing.services.marketing_meta_options_service import marketing_meta_options_service
from apps.marketing.services.testimonial_service import testimonial_service
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
    }


@method_decorator(csrf_exempt, name="dispatch")
class CouponListCreateView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request: Request):
        _require_admin(request)
        params = _list_params(request)
        params["is_active"] = _optional_bool(request.query_params.get("isActive"))
        data = coupon_service.list_coupons(**params)
        return APIResponse.success(data=data, endpoint=request.path)

    def post(self, request: Request):
        _require_admin(request)
        item = coupon_service.create_coupon(request.data)
        return APIResponse.success(
            data={"item": item},
            message="Coupon created",
            status_code=201,
            endpoint=request.path,
        )


@method_decorator(csrf_exempt, name="dispatch")
class CouponDetailView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request: Request, coupon_id: int):
        _require_admin(request)
        item = coupon_service.get_coupon(coupon_id)
        return APIResponse.success(data={"item": item}, endpoint=request.path)

    def patch(self, request: Request, coupon_id: int):
        _require_admin(request)
        item = coupon_service.update_coupon(coupon_id, request.data)
        return APIResponse.success(
            data={"item": item},
            message="Coupon updated",
            endpoint=request.path,
        )

    def delete(self, request: Request, coupon_id: int):
        _require_admin(request)
        coupon_service.delete_coupon(coupon_id)
        return APIResponse.success(message="Coupon deleted", endpoint=request.path)


@method_decorator(csrf_exempt, name="dispatch")
class BannerListCreateView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request: Request):
        _require_admin(request)
        params = _list_params(request)
        params["sort_by"] = request.query_params.get("sortBy", "display_order")
        params["sort_dir"] = request.query_params.get("sortDir", "asc")
        params["position_id"] = _optional_int(request.query_params.get("positionId"))
        data = banner_service.list_banners(**params)
        return APIResponse.success(data=data, endpoint=request.path)

    def post(self, request: Request):
        _require_admin(request)
        item = banner_service.create_banner(request.data)
        return APIResponse.success(
            data={"item": item},
            message="Banner created",
            status_code=201,
            endpoint=request.path,
        )


@method_decorator(csrf_exempt, name="dispatch")
class BannerDetailView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request: Request, banner_id: int):
        _require_admin(request)
        item = banner_service.get_banner(banner_id)
        return APIResponse.success(data={"item": item}, endpoint=request.path)

    def patch(self, request: Request, banner_id: int):
        _require_admin(request)
        item = banner_service.update_banner(banner_id, request.data)
        return APIResponse.success(
            data={"item": item},
            message="Banner updated",
            endpoint=request.path,
        )

    def delete(self, request: Request, banner_id: int):
        _require_admin(request)
        banner_service.delete_banner(banner_id)
        return APIResponse.success(message="Banner deleted", endpoint=request.path)


@method_decorator(csrf_exempt, name="dispatch")
class BannerPositionListView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request: Request):
        _require_admin(request)
        data = banner_position_service.list_positions()
        return APIResponse.success(data=data, endpoint=request.path)


@method_decorator(csrf_exempt, name="dispatch")
class CmsPageListCreateView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request: Request):
        _require_admin(request)
        data = cms_page_service.list_cms_pages(**_list_params(request))
        return APIResponse.success(data=data, endpoint=request.path)

    def post(self, request: Request):
        _require_admin(request)
        item = cms_page_service.create_cms_page(request.data)
        return APIResponse.success(
            data={"item": item},
            message="CMS page created",
            status_code=201,
            endpoint=request.path,
        )


@method_decorator(csrf_exempt, name="dispatch")
class CmsPageDetailView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request: Request, cms_page_id: int):
        _require_admin(request)
        item = cms_page_service.get_cms_page(cms_page_id)
        return APIResponse.success(data={"item": item}, endpoint=request.path)

    def patch(self, request: Request, cms_page_id: int):
        _require_admin(request)
        item = cms_page_service.update_cms_page(cms_page_id, request.data)
        return APIResponse.success(
            data={"item": item},
            message="CMS page updated",
            endpoint=request.path,
        )

    def delete(self, request: Request, cms_page_id: int):
        _require_admin(request)
        cms_page_service.delete_cms_page(cms_page_id)
        return APIResponse.success(message="CMS page deleted", endpoint=request.path)


@method_decorator(csrf_exempt, name="dispatch")
class TestimonialListCreateView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request: Request):
        _require_admin(request)
        params = _list_params(request)
        params["sort_by"] = request.query_params.get("sortBy", "display_order")
        params["sort_dir"] = request.query_params.get("sortDir", "asc")
        data = testimonial_service.list_testimonials(**params)
        return APIResponse.success(data=data, endpoint=request.path)

    def post(self, request: Request):
        _require_admin(request)
        item = testimonial_service.create_testimonial(request.data)
        return APIResponse.success(
            data={"item": item},
            message="Testimonial created",
            status_code=201,
            endpoint=request.path,
        )


@method_decorator(csrf_exempt, name="dispatch")
class TestimonialDetailView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request: Request, testimonial_id: int):
        _require_admin(request)
        item = testimonial_service.get_testimonial(testimonial_id)
        return APIResponse.success(data={"item": item}, endpoint=request.path)

    def patch(self, request: Request, testimonial_id: int):
        _require_admin(request)
        item = testimonial_service.update_testimonial(testimonial_id, request.data)
        return APIResponse.success(
            data={"item": item},
            message="Testimonial updated",
            endpoint=request.path,
        )

    def delete(self, request: Request, testimonial_id: int):
        _require_admin(request)
        testimonial_service.delete_testimonial(testimonial_id)
        return APIResponse.success(message="Testimonial deleted", endpoint=request.path)


@method_decorator(csrf_exempt, name="dispatch")
class FaqListCreateView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request: Request):
        _require_admin(request)
        params = _list_params(request)
        params["sort_by"] = request.query_params.get("sortBy", "display_order")
        params["sort_dir"] = request.query_params.get("sortDir", "asc")
        data = faq_service.list_faqs(**params)
        return APIResponse.success(data=data, endpoint=request.path)

    def post(self, request: Request):
        _require_admin(request)
        item = faq_service.create_faq(request.data)
        return APIResponse.success(
            data={"item": item},
            message="FAQ created",
            status_code=201,
            endpoint=request.path,
        )


@method_decorator(csrf_exempt, name="dispatch")
class FaqDetailView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request: Request, faq_id: int):
        _require_admin(request)
        item = faq_service.get_faq(faq_id)
        return APIResponse.success(data={"item": item}, endpoint=request.path)

    def patch(self, request: Request, faq_id: int):
        _require_admin(request)
        item = faq_service.update_faq(faq_id, request.data)
        return APIResponse.success(
            data={"item": item},
            message="FAQ updated",
            endpoint=request.path,
        )

    def delete(self, request: Request, faq_id: int):
        _require_admin(request)
        faq_service.delete_faq(faq_id)
        return APIResponse.success(message="FAQ deleted", endpoint=request.path)


@method_decorator(csrf_exempt, name="dispatch")
class MarketingMetaOptionsView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request: Request):
        _require_admin(request)
        return APIResponse.success(
            data=marketing_meta_options_service.get_options(),
            endpoint=request.path,
        )
