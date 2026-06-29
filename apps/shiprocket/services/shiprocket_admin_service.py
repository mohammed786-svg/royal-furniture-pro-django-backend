from __future__ import annotations

from typing import Any, Optional

from django.conf import settings

from core.integrations.shiprocket.client import ShiprocketClient, ShiprocketError, shiprocket_client


class ShiprocketAdminService:
    def __init__(self, client: ShiprocketClient | None = None) -> None:
        self.client = client or shiprocket_client

    def list_orders(self, **kwargs) -> dict[str, Any]:
        params = {
            "page": kwargs.get("page", 1),
            "per_page": kwargs.get("page_size", 20),
            "sort": kwargs.get("sort_dir", "DESC"),
            "sort_by": kwargs.get("sort_by", "id"),
        }
        search = (kwargs.get("search") or "").strip()
        if search:
            params["search"] = search
        date_from = (kwargs.get("date_from") or "").strip()
        date_to = (kwargs.get("date_to") or "").strip()
        if date_from:
            params["from"] = date_from
        if date_to:
            params["to"] = date_to
        return self.client.list_orders(params=params)

    def get_order(self, shiprocket_order_id: str) -> dict[str, Any]:
        return self.client.get_order(shiprocket_order_id)

    def track_awb(self, awb: str) -> dict[str, Any]:
        return self.client.track_awb(awb)

    def track_shipment(self, shipment_id: str) -> dict[str, Any]:
        return self.client.track_shipment(shipment_id)

    def calculate_rates(
        self,
        *,
        pickup_postcode: str,
        delivery_postcode: str,
        weight: float,
        cod: bool = False,
        length: Optional[float] = None,
        breadth: Optional[float] = None,
        height: Optional[float] = None,
    ) -> dict[str, Any]:
        weight = max(0.1, float(weight or 0.1))
        defaults = {
            "length": float(getattr(settings, "SHIPROCKET_DEFAULT_LENGTH_CM", 10)),
            "breadth": float(getattr(settings, "SHIPROCKET_DEFAULT_BREADTH_CM", 10)),
            "height": float(getattr(settings, "SHIPROCKET_DEFAULT_HEIGHT_CM", 10)),
        }
        return self.client.check_serviceability(
            pickup_postcode=pickup_postcode,
            delivery_postcode=delivery_postcode,
            weight=weight,
            cod=1 if cod else 0,
            length=length or defaults["length"],
            breadth=breadth or defaults["breadth"],
            height=height or defaults["height"],
        )


shiprocket_admin_service = ShiprocketAdminService()
