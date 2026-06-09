from __future__ import annotations

from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.request import Request
from rest_framework.views import APIView

from apps.inventory.services.adjustment_service import adjustment_service
from apps.inventory.services.alert_service import alert_service
from apps.inventory.services.inventory_options_service import inventory_options_service
from apps.inventory.services.stock_service import stock_service
from apps.inventory.services.transfer_service import transfer_service
from apps.inventory.services.warehouse_service import warehouse_service
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
class WarehouseListCreateView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request: Request):
        _require_admin(request)
        params = _list_params(request)
        params["sort_by"] = request.query_params.get("sortBy", "name")
        params["sort_dir"] = request.query_params.get("sortDir", "asc")
        data = warehouse_service.list_warehouses(**params)
        return APIResponse.success(data=data, endpoint=request.path)

    def post(self, request: Request):
        _require_admin(request)
        item = warehouse_service.create_warehouse(request.data)
        return APIResponse.success(
            data={"item": item},
            message="Warehouse created",
            status_code=201,
            endpoint=request.path,
        )


@method_decorator(csrf_exempt, name="dispatch")
class WarehouseDetailView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request: Request, warehouse_id: int):
        _require_admin(request)
        item = warehouse_service.get_warehouse(warehouse_id)
        return APIResponse.success(data={"item": item}, endpoint=request.path)

    def patch(self, request: Request, warehouse_id: int):
        _require_admin(request)
        item = warehouse_service.update_warehouse(warehouse_id, request.data)
        return APIResponse.success(
            data={"item": item},
            message="Warehouse updated",
            endpoint=request.path,
        )

    def delete(self, request: Request, warehouse_id: int):
        _require_admin(request)
        warehouse_service.delete_warehouse(warehouse_id)
        return APIResponse.success(message="Warehouse deleted", endpoint=request.path)


@method_decorator(csrf_exempt, name="dispatch")
class StockListCreateView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request: Request):
        _require_admin(request)
        params = _list_params(request)
        params["warehouse_id"] = _optional_int(request.query_params.get("warehouseId"))
        params["product_id"] = _optional_int(request.query_params.get("productId"))
        data = stock_service.list_stock(**params)
        return APIResponse.success(data=data, endpoint=request.path)

    def post(self, request: Request):
        _require_admin(request)
        item = stock_service.create_stock(request.data)
        return APIResponse.success(
            data={"item": item},
            message="Inventory record created",
            status_code=201,
            endpoint=request.path,
        )


@method_decorator(csrf_exempt, name="dispatch")
class StockDetailView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request: Request, inventory_id: int):
        _require_admin(request)
        item = stock_service.get_stock(inventory_id)
        return APIResponse.success(data={"item": item}, endpoint=request.path)

    def patch(self, request: Request, inventory_id: int):
        _require_admin(request)
        item = stock_service.update_stock(inventory_id, request.data)
        return APIResponse.success(
            data={"item": item},
            message="Inventory record updated",
            endpoint=request.path,
        )

    def delete(self, request: Request, inventory_id: int):
        _require_admin(request)
        stock_service.delete_stock(inventory_id)
        return APIResponse.success(message="Inventory record deleted", endpoint=request.path)


@method_decorator(csrf_exempt, name="dispatch")
class AdjustmentListCreateView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request: Request):
        _require_admin(request)
        params = _list_params(request)
        params["status"] = (request.query_params.get("status") or "").strip()
        params["warehouse_id"] = _optional_int(request.query_params.get("warehouseId"))
        data = adjustment_service.list_adjustments(**params)
        return APIResponse.success(data=data, endpoint=request.path)

    def post(self, request: Request):
        _require_admin(request)
        item = adjustment_service.create_adjustment(request.data)
        return APIResponse.success(
            data={"item": item},
            message="Stock adjustment created",
            status_code=201,
            endpoint=request.path,
        )


@method_decorator(csrf_exempt, name="dispatch")
class AdjustmentDetailView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request: Request, adjustment_id: int):
        _require_admin(request)
        item = adjustment_service.get_adjustment(adjustment_id)
        return APIResponse.success(data={"item": item}, endpoint=request.path)

    def patch(self, request: Request, adjustment_id: int):
        admin_id = _require_admin(request)
        item = adjustment_service.update_adjustment(
            adjustment_id,
            request.data,
            admin_id=admin_id,
        )
        return APIResponse.success(
            data={"item": item},
            message="Stock adjustment updated",
            endpoint=request.path,
        )


@method_decorator(csrf_exempt, name="dispatch")
class TransferListCreateView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request: Request):
        _require_admin(request)
        params = _list_params(request)
        params["status"] = (request.query_params.get("status") or "").strip()
        params["from_warehouse_id"] = _optional_int(request.query_params.get("fromWarehouseId"))
        params["to_warehouse_id"] = _optional_int(request.query_params.get("toWarehouseId"))
        data = transfer_service.list_transfers(**params)
        return APIResponse.success(data=data, endpoint=request.path)

    def post(self, request: Request):
        admin_id = _require_admin(request)
        item = transfer_service.create_transfer(request.data, admin_id=admin_id)
        return APIResponse.success(
            data={"item": item},
            message="Stock transfer created",
            status_code=201,
            endpoint=request.path,
        )


@method_decorator(csrf_exempt, name="dispatch")
class TransferDetailView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request: Request, transfer_id: int):
        _require_admin(request)
        item = transfer_service.get_transfer(transfer_id)
        return APIResponse.success(data={"item": item}, endpoint=request.path)

    def patch(self, request: Request, transfer_id: int):
        admin_id = _require_admin(request)
        item = transfer_service.update_transfer(
            transfer_id,
            request.data,
            admin_id=admin_id,
        )
        return APIResponse.success(
            data={"item": item},
            message="Stock transfer updated",
            endpoint=request.path,
        )


@method_decorator(csrf_exempt, name="dispatch")
class AlertListView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request: Request):
        _require_admin(request)
        params = _list_params(request)
        params["warehouse_id"] = _optional_int(request.query_params.get("warehouseId"))
        data = alert_service.list_alerts(**params)
        return APIResponse.success(data=data, endpoint=request.path)


@method_decorator(csrf_exempt, name="dispatch")
class InventoryOptionsView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request: Request):
        _require_admin(request)
        return APIResponse.success(
            data=inventory_options_service.get_options(),
            endpoint=request.path,
        )
