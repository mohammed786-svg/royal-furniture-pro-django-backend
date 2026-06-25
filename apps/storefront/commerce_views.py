from __future__ import annotations

from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.request import Request
from rest_framework.views import APIView

from apps.storefront.helpers.commerce_context import (
    GUEST_SESSION_COOKIE,
    ensure_guest_session,
    resolve_guest_session,
)
from apps.storefront.services.cart_service import cart_service
from apps.storefront.services.checkout_service import checkout_service
from apps.storefront.services.customer_auth_service import customer_auth_service
from apps.storefront.services.storefront_address_service import storefront_address_service
from apps.storefront.services.storefront_wishlist_service import storefront_wishlist_service
from core.responses.formatter import APIResponse


def _with_guest_session(response: HttpResponse, session_id: str) -> HttpResponse:
    if session_id and not response.cookies.get(GUEST_SESSION_COOKIE):
        response.set_cookie(
            GUEST_SESSION_COOKIE,
            session_id,
            max_age=365 * 24 * 3600,
            httponly=False,
            samesite="Lax",
            path="/",
        )
    return response


@method_decorator(csrf_exempt, name="dispatch")
class StorefrontSendOtpView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request: Request):
        phone = request.data.get("phone", "")
        purpose = request.data.get("purpose", "login")
        data = customer_auth_service.send_otp(phone, purpose=purpose)
        return APIResponse.success(data=data, message="OTP sent", endpoint=request.path)


@method_decorator(csrf_exempt, name="dispatch")
class StorefrontVerifyOtpView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request: Request):
        phone = request.data.get("phone", "")
        otp = request.data.get("otp", "")
        purpose = (request.data.get("purpose") or "login").strip().lower()
        session_id = resolve_guest_session(request)

        if purpose == "register":
            data = customer_auth_service.verify_register_otp(
                request,
                phone,
                otp,
                full_name=request.data.get("fullName", ""),
                email=request.data.get("email"),
            )
        else:
            data = customer_auth_service.verify_otp(request, phone, otp)

        if session_id and data.get("user", {}).get("customerId"):
            cart_service.merge_guest_cart(
                int(data["user"]["customerId"]),
                session_id,
            )
        response = APIResponse.success(data=data, message="Login successful", endpoint=request.path)
        return _with_guest_session(response, session_id)


@method_decorator(csrf_exempt, name="dispatch")
class StorefrontMeView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request: Request):
        from apps.storefront.helpers.commerce_context import require_customer_id

        customer_id = require_customer_id(request)
        data = customer_auth_service.get_me(customer_id)
        return APIResponse.success(data=data, endpoint=request.path)


@method_decorator(csrf_exempt, name="dispatch")
class StorefrontCartView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request: Request):
        data = cart_service.get_cart(request)
        session_id = ensure_guest_session(request)
        response = APIResponse.success(data=data, endpoint=request.path)
        return _with_guest_session(response, session_id)

    def delete(self, request: Request):
        data = cart_service.clear_cart(request)
        return APIResponse.success(data=data, message="Cart cleared", endpoint=request.path)


@method_decorator(csrf_exempt, name="dispatch")
class StorefrontCartItemsView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request: Request):
        data = cart_service.add_item(request, request.data)
        session_id = ensure_guest_session(request)
        response = APIResponse.success(data=data, message="Added to cart", endpoint=request.path)
        return _with_guest_session(response, session_id)


@method_decorator(csrf_exempt, name="dispatch")
class StorefrontCartItemDetailView(APIView):
    authentication_classes = []
    permission_classes = []

    def patch(self, request: Request, cart_item_id: int):
        data = cart_service.update_item(request, cart_item_id, request.data)
        return APIResponse.success(data=data, message="Cart updated", endpoint=request.path)

    def delete(self, request: Request, cart_item_id: int):
        data = cart_service.remove_item(request, cart_item_id)
        return APIResponse.success(data=data, message="Item removed", endpoint=request.path)


@method_decorator(csrf_exempt, name="dispatch")
class StorefrontWishlistView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request: Request):
        data = storefront_wishlist_service.list_wishlist(request)
        return APIResponse.success(data=data, endpoint=request.path)

    def post(self, request: Request):
        data = storefront_wishlist_service.add_item(request, request.data)
        return APIResponse.success(data=data, message="Added to wishlist", endpoint=request.path)


@method_decorator(csrf_exempt, name="dispatch")
class StorefrontWishlistProductView(APIView):
    authentication_classes = []
    permission_classes = []

    def delete(self, request: Request, product_id: int):
        data = storefront_wishlist_service.remove_item(request, product_id)
        return APIResponse.success(data=data, message="Removed from wishlist", endpoint=request.path)


@method_decorator(csrf_exempt, name="dispatch")
class StorefrontAddressesView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request: Request):
        data = storefront_address_service.list_addresses(request)
        return APIResponse.success(data=data, endpoint=request.path)

    def post(self, request: Request):
        data = storefront_address_service.create_address(request, request.data)
        return APIResponse.success(data=data, message="Address saved", endpoint=request.path)


@method_decorator(csrf_exempt, name="dispatch")
class StorefrontAddressDetailView(APIView):
    authentication_classes = []
    permission_classes = []

    def patch(self, request: Request, address_id: int):
        data = storefront_address_service.update_address(request, address_id, request.data)
        return APIResponse.success(data=data, message="Address updated", endpoint=request.path)

    def delete(self, request: Request, address_id: int):
        storefront_address_service.delete_address(request, address_id)
        return APIResponse.success(data=None, message="Address deleted", endpoint=request.path)


@method_decorator(csrf_exempt, name="dispatch")
class StorefrontCheckoutView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request: Request):
        data = checkout_service.place_order(request, request.data)
        return APIResponse.success(data=data, message="Order placed", endpoint=request.path)
