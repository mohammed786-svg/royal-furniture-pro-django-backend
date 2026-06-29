from __future__ import annotations

from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.request import Request
from rest_framework.views import APIView

from apps.shiprocket.services.shiprocket_admin_service import shiprocket_admin_service
from apps.shiprocket.services.shiprocket_integration_service import shiprocket_integration_service
from apps.shiprocket.services.shipment_service import shipment_service
from apps.shiprocket.services.shipment_tracking_service import shipment_tracking_service
from apps.shiprocket.services.shipping_options_service import shipping_options_service
from core.exceptions.base import AuthenticationException, ValidationException
from core.integrations.shiprocket.client import ShiprocketError
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
class ShipmentListCreateView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request: Request):
        _require_admin(request)
        params = _list_params(request)
        params["order_id"] = _optional_int(request.query_params.get("orderId"))
        params["delivery_status"] = (request.query_params.get("deliveryStatus") or "").strip()
        data = shipment_service.list_shipments(**params)
        return APIResponse.success(data=data, endpoint=request.path)

    def post(self, request: Request):
        _require_admin(request)
        item = shipment_service.create_shipment(request.data)
        return APIResponse.success(
            data={"item": item},
            message="Shipment created",
            status_code=201,
            endpoint=request.path,
        )


@method_decorator(csrf_exempt, name="dispatch")
class ShipmentDetailView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request: Request, shipment_id: int):
        _require_admin(request)
        item = shipment_service.get_shipment(shipment_id)
        return APIResponse.success(data={"item": item}, endpoint=request.path)

    def patch(self, request: Request, shipment_id: int):
        _require_admin(request)
        item = shipment_service.update_shipment(shipment_id, request.data)
        return APIResponse.success(
            data={"item": item},
            message="Shipment updated",
            endpoint=request.path,
        )

    def delete(self, request: Request, shipment_id: int):
        _require_admin(request)
        shipment_service.delete_shipment(shipment_id)
        return APIResponse.success(message="Shipment deleted", endpoint=request.path)


@method_decorator(csrf_exempt, name="dispatch")
class ShipmentTrackingListCreateView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request: Request):
        _require_admin(request)
        params = _list_params(request)
        params["sort_by"] = request.query_params.get("sortBy", "tracked_at")
        params["shipment_id"] = _optional_int(request.query_params.get("shipmentId"))
        params["order_id"] = _optional_int(request.query_params.get("orderId"))
        data = shipment_tracking_service.list_tracking(**params)
        return APIResponse.success(data=data, endpoint=request.path)

    def post(self, request: Request):
        _require_admin(request)
        item = shipment_tracking_service.create_tracking(request.data)
        return APIResponse.success(
            data={"item": item},
            message="Shipment tracking record created",
            status_code=201,
            endpoint=request.path,
        )


@method_decorator(csrf_exempt, name="dispatch")
class ShipmentTrackingDetailView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request: Request, tracking_id: int):
        _require_admin(request)
        item = shipment_tracking_service.get_tracking(tracking_id)
        return APIResponse.success(data={"item": item}, endpoint=request.path)

    def patch(self, request: Request, tracking_id: int):
        _require_admin(request)
        item = shipment_tracking_service.update_tracking(tracking_id, request.data)
        return APIResponse.success(
            data={"item": item},
            message="Shipment tracking record updated",
            endpoint=request.path,
        )

    def delete(self, request: Request, tracking_id: int):
        _require_admin(request)
        shipment_tracking_service.delete_tracking(tracking_id)
        return APIResponse.success(
            message="Shipment tracking record deleted",
            endpoint=request.path,
        )


@method_decorator(csrf_exempt, name="dispatch")
class ShiprocketWebhookView(APIView):
    """Shiprocket tracking webhook — configure in Shiprocket panel."""

    authentication_classes = []
    permission_classes = []

    def post(self, request: Request):
        payload = request.data if isinstance(request.data, dict) else {}
        shiprocket_integration_service.handle_webhook(payload)
        return APIResponse.success(data={"received": True}, endpoint=request.path)


@method_decorator(csrf_exempt, name="dispatch")
class ShippingOptionsView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request: Request):
        _require_admin(request)
        return APIResponse.success(
            data=shipping_options_service.get_options(),
            endpoint=request.path,
        )


@method_decorator(csrf_exempt, name="dispatch")
class ShiprocketOrdersListView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request: Request):
        _require_admin(request)
        params = _list_params(request)
        params["date_from"] = (request.query_params.get("from") or "").strip()
        params["date_to"] = (request.query_params.get("to") or "").strip()
        try:
            data = shiprocket_admin_service.list_orders(**params)
            return APIResponse.success(data=data, endpoint=request.path)
        except ShiprocketError as exc:
            return APIResponse.error(message=str(exc), status_code=502, endpoint=request.path)


@method_decorator(csrf_exempt, name="dispatch")
class ShiprocketOrderDetailView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request: Request, shiprocket_order_id: str):
        _require_admin(request)
        try:
            data = shiprocket_admin_service.get_order(shiprocket_order_id)
            return APIResponse.success(data=data, endpoint=request.path)
        except ShiprocketError as exc:
            status = 404 if exc.status_code == 404 else 502
            return APIResponse.error(message=str(exc), status_code=status, endpoint=request.path)


@method_decorator(csrf_exempt, name="dispatch")
class ShiprocketTrackView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request: Request):
        _require_admin(request)
        awb = (request.query_params.get("awb") or "").strip()
        shipment_id = (request.query_params.get("shipmentId") or "").strip()
        if not awb and not shipment_id:
            raise ValidationException(
                details=[{"field": "awb", "message": "AWB or shipment ID is required"}]
            )
        try:
            if awb:
                data = shiprocket_admin_service.track_awb(awb)
            else:
                data = shiprocket_admin_service.track_shipment(shipment_id)
            return APIResponse.success(data=data, endpoint=request.path)
        except ShiprocketError as exc:
            return APIResponse.error(message=str(exc), status_code=502, endpoint=request.path)


@method_decorator(csrf_exempt, name="dispatch")
class ShiprocketServiceabilityView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request: Request):
        _require_admin(request)
        pickup = (request.query_params.get("pickupPostcode") or "").strip()
        delivery = (request.query_params.get("deliveryPostcode") or "").strip()
        weight = request.query_params.get("weight")
        if not pickup or not delivery:
            raise ValidationException(
                details=[{"field": "pickupPostcode", "message": "Pickup and delivery pincodes are required"}]
            )
        try:
            weight_val = float(weight) if weight not in (None, "") else 1.0
        except (TypeError, ValueError):
            weight_val = 1.0
        cod = (request.query_params.get("cod") or "0").strip() in {"1", "true", "True"}
        length = _optional_float(request.query_params.get("lengthCm"))
        breadth = _optional_float(request.query_params.get("breadthCm"))
        height = _optional_float(request.query_params.get("heightCm"))
        try:
            data = shiprocket_admin_service.calculate_rates(
                pickup_postcode=pickup,
                delivery_postcode=delivery,
                weight=weight_val,
                cod=cod,
                length=length,
                breadth=breadth,
                height=height,
            )
            return APIResponse.success(data=data, endpoint=request.path)
        except ShiprocketError as exc:
            return APIResponse.error(message=str(exc), status_code=502, endpoint=request.path)


def _optional_float(value) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
