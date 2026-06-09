from __future__ import annotations

from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.request import Request
from rest_framework.views import APIView

from apps.orders.services.invoice_service import invoice_service
from apps.orders.services.order_options_service import order_options_service
from apps.orders.services.order_service import order_service
from apps.orders.services.order_status_service import order_status_service
from apps.orders.services.order_tracking_service import order_tracking_service
from apps.orders.services.return_service import return_service
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
class OrderOptionsView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request: Request):
        _require_admin(request)
        data = order_options_service.get_options()
        return APIResponse.success(data=data, endpoint=request.path)


@method_decorator(csrf_exempt, name="dispatch")
class OrderListCreateView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request: Request):
        _require_admin(request)
        params = _list_params(request)
        params["customer_id"] = _optional_int(request.query_params.get("customerId"))
        params["status_code"] = (request.query_params.get("statusCode") or "").strip() or None
        params["current_status"] = (request.query_params.get("currentStatus") or "").strip() or None
        data = order_service.list_orders(**params)
        return APIResponse.success(data=data, endpoint=request.path)

    def post(self, request: Request):
        user_id = _require_admin(request)
        item = order_service.create_order(request.data, created_by=user_id)
        return APIResponse.success(
            data={"item": item},
            message="Order created",
            status_code=201,
            endpoint=request.path,
        )


@method_decorator(csrf_exempt, name="dispatch")
class OrderDetailView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request: Request, order_id: int):
        _require_admin(request)
        item = order_service.get_order(order_id)
        return APIResponse.success(data={"item": item}, endpoint=request.path)

    def patch(self, request: Request, order_id: int):
        user_id = _require_admin(request)
        item = order_service.update_order(order_id, request.data, changed_by=user_id)
        return APIResponse.success(
            data={"item": item},
            message="Order updated",
            endpoint=request.path,
        )


@method_decorator(csrf_exempt, name="dispatch")
class OrderInvoiceView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request: Request, order_id: int):
        _require_admin(request)
        invoice = invoice_service.build_invoice(order_id)
        return APIResponse.success(data={"invoice": invoice}, endpoint=request.path)


@method_decorator(csrf_exempt, name="dispatch")
class OrderStatusListCreateView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request: Request):
        _require_admin(request)
        params = _list_params(request)
        params["sort_by"] = request.query_params.get("sortBy", "display_order")
        params["sort_dir"] = request.query_params.get("sortDir", "asc")
        data = order_status_service.list_statuses(**params)
        return APIResponse.success(data=data, endpoint=request.path)

    def post(self, request: Request):
        _require_admin(request)
        item = order_status_service.create_status(request.data)
        return APIResponse.success(
            data={"item": item},
            message="Order status created",
            status_code=201,
            endpoint=request.path,
        )


@method_decorator(csrf_exempt, name="dispatch")
class OrderStatusDetailView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request: Request, order_status_id: int):
        _require_admin(request)
        item = order_status_service.get_status(order_status_id)
        return APIResponse.success(data={"item": item}, endpoint=request.path)

    def patch(self, request: Request, order_status_id: int):
        _require_admin(request)
        item = order_status_service.update_status(order_status_id, request.data)
        return APIResponse.success(
            data={"item": item},
            message="Order status updated",
            endpoint=request.path,
        )

    def delete(self, request: Request, order_status_id: int):
        _require_admin(request)
        order_status_service.delete_status(order_status_id)
        return APIResponse.success(message="Order status deleted", endpoint=request.path)


@method_decorator(csrf_exempt, name="dispatch")
class OrderTrackingListCreateView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request: Request):
        _require_admin(request)
        params = _list_params(request)
        params["order_id"] = _optional_int(request.query_params.get("orderId"))
        data = order_tracking_service.list_tracking(**params)
        return APIResponse.success(data=data, endpoint=request.path)

    def post(self, request: Request):
        _require_admin(request)
        item = order_tracking_service.add_tracking(request.data)
        return APIResponse.success(
            data={"item": item},
            message="Tracking event added",
            status_code=201,
            endpoint=request.path,
        )


@method_decorator(csrf_exempt, name="dispatch")
class ReturnListCreateView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request: Request):
        _require_admin(request)
        params = _list_params(request)
        params["customer_id"] = _optional_int(request.query_params.get("customerId"))
        data = return_service.list_returns(**params)
        return APIResponse.success(data=data, endpoint=request.path)

    def post(self, request: Request):
        user_id = _require_admin(request)
        item = return_service.initiate_return(request.data, changed_by=user_id)
        return APIResponse.success(
            data={"item": item},
            message="Return initiated",
            status_code=201,
            endpoint=request.path,
        )
