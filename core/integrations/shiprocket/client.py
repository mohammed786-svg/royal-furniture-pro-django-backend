from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from typing import Any, Optional

from django.conf import settings

from core.cache.cache_manager import cache_manager

logger = logging.getLogger(__name__)

TOKEN_CACHE_KEY = "royal:shiprocket:auth_token"
TOKEN_TTL_SECONDS = 9 * 24 * 3600  # 9 days (token valid ~10 days)


class ShiprocketError(Exception):
    def __init__(self, message: str, *, status_code: int | None = None, payload: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload


class ShiprocketClient:
    def __init__(self) -> None:
        self.base_url = getattr(
            settings,
            "SHIPROCKET_API_BASE_URL",
            "https://apiv2.shiprocket.in",
        ).rstrip("/")
        self.email = getattr(settings, "SHIPROCKET_EMAIL", "") or ""
        self.password = getattr(settings, "SHIPROCKET_PASSWORD", "") or ""

    @property
    def is_configured(self) -> bool:
        return bool(self.email and self.password)

    def _request(
        self,
        method: str,
        path: str,
        *,
        body: Optional[dict[str, Any]] = None,
        auth: bool = True,
    ) -> Any:
        url = f"{self.base_url}{path}"
        data = None
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if auth:
            headers["Authorization"] = f"Bearer {self.get_token()}"
        if body is not None:
            data = json.dumps(body).encode("utf-8")

        request = urllib.request.Request(url, data=data, headers=headers, method=method.upper())
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                raw = response.read().decode("utf-8")
                if not raw:
                    return {}
                return json.loads(raw)
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            try:
                payload = json.loads(detail) if detail else {}
            except json.JSONDecodeError:
                payload = {"message": detail}
            message = (
                payload.get("message")
                or payload.get("error")
                or f"Shiprocket HTTP {exc.code}"
            )
            raise ShiprocketError(str(message), status_code=exc.code, payload=payload) from exc
        except urllib.error.URLError as exc:
            raise ShiprocketError(f"Shiprocket connection error: {exc.reason}") from exc

    def get_token(self) -> str:
        cached = cache_manager.get(TOKEN_CACHE_KEY)
        if cached and cached.get("token"):
            return str(cached["token"])

        if not self.is_configured:
            raise ShiprocketError("Shiprocket credentials are not configured")

        payload = self._request(
            "POST",
            "/v1/external/auth/login",
            body={"email": self.email, "password": self.password},
            auth=False,
        )
        token = payload.get("token")
        if not token:
            raise ShiprocketError("Shiprocket login did not return a token", payload=payload)

        cache_manager.set(TOKEN_CACHE_KEY, {"token": token}, ttl=TOKEN_TTL_SECONDS)
        return str(token)

    def create_adhoc_order(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = self._request("POST", "/v1/external/orders/create/adhoc", body=payload)
        if not isinstance(response, dict):
            raise ShiprocketError("Unexpected Shiprocket create-order response")
        return response

    def cancel_orders(self, order_ids: list[int]) -> dict[str, Any]:
        if not order_ids:
            return {}
        response = self._request(
            "POST",
            "/v1/external/orders/cancel",
            body={"ids": order_ids},
        )
        return response if isinstance(response, dict) else {}

    def assign_awb(
        self,
        shipment_id: int | str,
        *,
        courier_id: int | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"shipment_id": int(shipment_id)}
        if courier_id:
            body["courier_id"] = int(courier_id)
        response = self._request("POST", "/v1/external/courier/assign/awb", body=body)
        if not isinstance(response, dict):
            raise ShiprocketError("Unexpected Shiprocket assign-AWB response")
        return response

    def create_return_order(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = self._request("POST", "/v1/external/orders/create/return", body=payload)
        if not isinstance(response, dict):
            raise ShiprocketError("Unexpected Shiprocket return-order response")
        return response

    def track_awb(self, awb: str) -> dict[str, Any]:
        awb_code = (awb or "").strip()
        if not awb_code or awb_code.upper() == "NA":
            raise ShiprocketError("AWB is not available yet")
        response = self._request("GET", f"/v1/external/courier/track/awb/{awb_code}")
        if not isinstance(response, dict):
            raise ShiprocketError("Unexpected Shiprocket tracking response")
        return response

    def track_shipment(self, shipment_id: str | int) -> dict[str, Any]:
        response = self._request(
            "GET",
            f"/v1/external/courier/track/shipment/{shipment_id}",
        )
        if not isinstance(response, dict):
            raise ShiprocketError("Unexpected Shiprocket shipment tracking response")
        return response

    def list_orders(self, *, params: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        query = ""
        if params:
            from urllib.parse import urlencode

            filtered = {k: v for k, v in params.items() if v not in (None, "")}
            if filtered:
                query = "?" + urlencode(filtered)
        response = self._request("GET", f"/v1/external/orders{query}")
        if not isinstance(response, dict):
            raise ShiprocketError("Unexpected Shiprocket orders list response")
        return response

    def get_order(self, shiprocket_order_id: str | int) -> dict[str, Any]:
        response = self._request("GET", f"/v1/external/orders/show/{shiprocket_order_id}")
        if not isinstance(response, dict):
            raise ShiprocketError("Unexpected Shiprocket order detail response")
        return response

    def check_serviceability(
        self,
        *,
        pickup_postcode: str | int,
        delivery_postcode: str | int,
        weight: float,
        cod: int = 0,
        length: Optional[float] = None,
        breadth: Optional[float] = None,
        height: Optional[float] = None,
    ) -> dict[str, Any]:
        from urllib.parse import urlencode

        params: dict[str, Any] = {
            "pickup_postcode": str(pickup_postcode).strip(),
            "delivery_postcode": str(delivery_postcode).strip(),
            "weight": weight,
            "cod": cod,
        }
        if length:
            params["length"] = length
        if breadth:
            params["breadth"] = breadth
        if height:
            params["height"] = height
        response = self._request(
            "GET",
            f"/v1/external/courier/serviceability/?{urlencode(params)}",
        )
        if not isinstance(response, dict):
            raise ShiprocketError("Unexpected Shiprocket serviceability response")
        return response


shiprocket_client = ShiprocketClient()
