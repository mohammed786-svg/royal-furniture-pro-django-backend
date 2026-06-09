from __future__ import annotations

from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.request import Request
from rest_framework.views import APIView

from apps.payments.services.payment_options_service import payment_options_service
from apps.payments.services.payment_service import payment_service
from apps.payments.services.payment_verification_service import payment_verification_service
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
class PaymentListCreateView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request: Request):
        _require_admin(request)
        params = _list_params(request)
        params["order_id"] = _optional_int(request.query_params.get("orderId"))
        params["customer_id"] = _optional_int(request.query_params.get("customerId"))
        params["payment_status"] = (request.query_params.get("paymentStatus") or "").strip()
        data = payment_service.list_payments(**params)
        return APIResponse.success(data=data, endpoint=request.path)

    def post(self, request: Request):
        _require_admin(request)
        item = payment_service.create_payment(request.data)
        return APIResponse.success(
            data={"item": item},
            message="Payment created",
            status_code=201,
            endpoint=request.path,
        )


@method_decorator(csrf_exempt, name="dispatch")
class PaymentDetailView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request: Request, payment_id: int):
        _require_admin(request)
        item = payment_service.get_payment(payment_id)
        return APIResponse.success(data={"item": item}, endpoint=request.path)

    def patch(self, request: Request, payment_id: int):
        _require_admin(request)
        item = payment_service.update_payment(payment_id, request.data)
        return APIResponse.success(
            data={"item": item},
            message="Payment updated",
            endpoint=request.path,
        )

    def delete(self, request: Request, payment_id: int):
        _require_admin(request)
        payment_service.delete_payment(payment_id)
        return APIResponse.success(message="Payment deleted", endpoint=request.path)


@method_decorator(csrf_exempt, name="dispatch")
class PaymentVerificationListCreateView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request: Request):
        _require_admin(request)
        params = _list_params(request)
        params["payment_id"] = _optional_int(request.query_params.get("paymentId"))
        params["order_id"] = _optional_int(request.query_params.get("orderId"))
        params["verification_status"] = (
            request.query_params.get("verificationStatus") or ""
        ).strip()
        data = payment_verification_service.list_verifications(**params)
        return APIResponse.success(data=data, endpoint=request.path)

    def post(self, request: Request):
        _require_admin(request)
        item = payment_verification_service.create_verification(request.data)
        return APIResponse.success(
            data={"item": item},
            message="Payment verification created",
            status_code=201,
            endpoint=request.path,
        )


@method_decorator(csrf_exempt, name="dispatch")
class PaymentVerificationDetailView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request: Request, verification_id: int):
        _require_admin(request)
        item = payment_verification_service.get_verification(verification_id)
        return APIResponse.success(data={"item": item}, endpoint=request.path)

    def patch(self, request: Request, verification_id: int):
        admin_id = _require_admin(request)
        item = payment_verification_service.update_verification(
            verification_id,
            request.data,
            admin_id=admin_id,
        )
        return APIResponse.success(
            data={"item": item},
            message="Payment verification updated",
            endpoint=request.path,
        )

    def delete(self, request: Request, verification_id: int):
        _require_admin(request)
        payment_verification_service.delete_verification(verification_id)
        return APIResponse.success(
            message="Payment verification deleted",
            endpoint=request.path,
        )


@method_decorator(csrf_exempt, name="dispatch")
class PaymentOptionsView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request: Request):
        _require_admin(request)
        return APIResponse.success(
            data=payment_options_service.get_options(),
            endpoint=request.path,
        )
