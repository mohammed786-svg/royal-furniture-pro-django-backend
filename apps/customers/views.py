from __future__ import annotations

from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.request import Request
from rest_framework.views import APIView

from apps.customers.services.address_service import address_service
from apps.customers.services.customer_options_service import customer_options_service
from apps.customers.services.customer_service import customer_service
from apps.customers.services.wallet_service import wallet_service
from apps.customers.services.wishlist_service import wishlist_service
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
    return str(value).lower() in ("1", "true", "yes")


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
class CustomerOptionsView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request: Request):
        _require_admin(request)
        data = customer_options_service.get_options()
        return APIResponse.success(data=data, endpoint=request.path)


@method_decorator(csrf_exempt, name="dispatch")
class CustomerListCreateView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request: Request):
        _require_admin(request)
        params = _list_params(request)
        params["is_guest"] = _optional_bool(request.query_params.get("isGuest"))
        data = customer_service.list_customers(**params)
        return APIResponse.success(data=data, endpoint=request.path)

    def post(self, request: Request):
        _require_admin(request)
        item = customer_service.create_customer(request.data)
        return APIResponse.success(
            data={"item": item},
            message="Customer created",
            status_code=201,
            endpoint=request.path,
        )


@method_decorator(csrf_exempt, name="dispatch")
class CustomerDetailView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request: Request, customer_id: int):
        _require_admin(request)
        item = customer_service.get_customer(customer_id)
        return APIResponse.success(data={"item": item}, endpoint=request.path)

    def patch(self, request: Request, customer_id: int):
        _require_admin(request)
        item = customer_service.update_customer(customer_id, request.data)
        return APIResponse.success(
            data={"item": item},
            message="Customer updated",
            endpoint=request.path,
        )

    def delete(self, request: Request, customer_id: int):
        _require_admin(request)
        customer_service.delete_customer(customer_id)
        return APIResponse.success(message="Customer deleted", endpoint=request.path)


@method_decorator(csrf_exempt, name="dispatch")
class AddressListCreateView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request: Request):
        _require_admin(request)
        params = _list_params(request)
        params["customer_id"] = _optional_int(request.query_params.get("customerId"))
        data = address_service.list_addresses(**params)
        return APIResponse.success(data=data, endpoint=request.path)

    def post(self, request: Request):
        _require_admin(request)
        item = address_service.create_address(request.data)
        return APIResponse.success(
            data={"item": item},
            message="Address created",
            status_code=201,
            endpoint=request.path,
        )


@method_decorator(csrf_exempt, name="dispatch")
class AddressDetailView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request: Request, address_id: int):
        _require_admin(request)
        item = address_service.get_address(address_id)
        return APIResponse.success(data={"item": item}, endpoint=request.path)

    def patch(self, request: Request, address_id: int):
        _require_admin(request)
        item = address_service.update_address(address_id, request.data)
        return APIResponse.success(
            data={"item": item},
            message="Address updated",
            endpoint=request.path,
        )

    def delete(self, request: Request, address_id: int):
        _require_admin(request)
        address_service.delete_address(address_id)
        return APIResponse.success(message="Address deleted", endpoint=request.path)


@method_decorator(csrf_exempt, name="dispatch")
class WishlistListView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request: Request):
        _require_admin(request)
        params = _list_params(request)
        params["customer_id"] = _optional_int(request.query_params.get("customerId"))
        data = wishlist_service.list_wishlists(**params)
        return APIResponse.success(data=data, endpoint=request.path)


@method_decorator(csrf_exempt, name="dispatch")
class WishlistDetailView(APIView):
    authentication_classes = []
    permission_classes = []

    def delete(self, request: Request, wishlist_id: int):
        _require_admin(request)
        wishlist_service.delete_wishlist(wishlist_id)
        return APIResponse.success(message="Wishlist item removed", endpoint=request.path)


@method_decorator(csrf_exempt, name="dispatch")
class WalletListView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request: Request):
        _require_admin(request)
        data = wallet_service.list_wallets(**_list_params(request))
        return APIResponse.success(data=data, endpoint=request.path)


@method_decorator(csrf_exempt, name="dispatch")
class WalletDetailView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request: Request, customer_wallet_id: int):
        _require_admin(request)
        item = wallet_service.get_wallet(customer_wallet_id)
        return APIResponse.success(data={"item": item}, endpoint=request.path)


@method_decorator(csrf_exempt, name="dispatch")
class WalletTransactionView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request: Request, customer_wallet_id: int):
        _require_admin(request)
        item = wallet_service.process_transaction(customer_wallet_id, request.data)
        return APIResponse.success(
            data={"item": item},
            message="Wallet transaction processed",
            status_code=201,
            endpoint=request.path,
        )
