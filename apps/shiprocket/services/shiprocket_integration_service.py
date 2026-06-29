from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any, Optional

from django.conf import settings
from psycopg2.extras import Json

from apps.customers.repositories.address_repository import address_repository
from apps.customers.repositories.customer_repository import customer_repository
from apps.orders.repositories.order_item_repository import order_item_repository
from apps.orders.repositories.order_repository import order_repository
from apps.products.repositories.product_repository import product_repository
from apps.shiprocket.repositories.shipment_repository import shipment_repository
from apps.shiprocket.repositories.shipment_tracking_repository import (
    shipment_tracking_repository,
)
from apps.storefront.helpers.commerce_context import normalize_phone
from core.helpers.text import from_db_text, to_db_text
from core.integrations.shiprocket.client import ShiprocketClient, ShiprocketError, shiprocket_client

logger = logging.getLogger(__name__)


def _split_name(full_name: str) -> tuple[str, str]:
    parts = (full_name or "Customer").strip().split(None, 1)
    return parts[0], parts[1] if len(parts) > 1 else ""


def _clean_phone(value: Any) -> str:
    raw = from_db_text(value) or ""
    if not raw or raw.upper() in {"NA", "N/A"}:
        return ""
    digits = normalize_phone(raw)
    return digits if len(digits) == 10 else re.sub(r"\D", "", raw)[-10:]


def _parse_hsn(value: Any) -> int:
    raw = (from_db_text(value) or "").strip()
    if not raw or raw.upper() in {"NA", "N/A", "-", "NONE", "NULL"}:
        return 0
    digits = re.sub(r"\D", "", raw)
    if digits:
        try:
            return int(digits)
        except ValueError:
            return 0
    try:
        return int(float(raw))
    except (TypeError, ValueError):
        return 0


def _safe_float(value: Any, default: float = 0.0) -> float:
    if value in (None, ""):
        return default
    if isinstance(value, (int, float)):
        return float(value)
    raw = (from_db_text(value) or str(value)).strip()
    if not raw or raw.upper() in {"NA", "N/A"}:
        return default
    try:
        return float(raw)
    except (TypeError, ValueError):
        return default


def _order_package_metrics(items: list[dict[str, Any]]) -> tuple[float, float, float, float]:
    total_weight = 0.0
    max_length = 0.0
    max_breadth = 0.0
    max_height = 0.0
    for item in items:
        qty = int(item.get("quantity") or 1)
        product_id = item.get("product_id")
        if not product_id:
            continue
        product = product_repository.fetch_by_id(int(product_id))
        if not product:
            continue
        total_weight += _safe_float(product.get("weight")) * qty
        max_length = max(max_length, _safe_float(product.get("length_cm")))
        max_breadth = max(max_breadth, _safe_float(product.get("breadth_cm")))
        max_height = max(max_height, _safe_float(product.get("height_cm")))
    return total_weight, max_length, max_breadth, max_height


class ShiprocketIntegrationService:
    def __init__(self, client: ShiprocketClient | None = None) -> None:
        self.client = client or shiprocket_client

    @property
    def enabled(self) -> bool:
        flag = getattr(settings, "SHIPROCKET_ENABLED", True)
        if isinstance(flag, str):
            flag = flag.lower() == "true"
        return bool(flag) and self.client.is_configured

    def create_for_order(self, order_id: int) -> Optional[dict[str, Any]]:
        if not self.enabled:
            logger.info("Shiprocket skipped for order %s (not configured)", order_id)
            return None

        existing = shipment_repository.fetch_by_order_id(order_id)
        if existing:
            return existing

        order = order_repository.fetch_by_id(order_id)
        if not order:
            logger.warning("Shiprocket: order %s not found", order_id)
            return None

        shipping_address_id = order.get("shipping_address_id")
        if not shipping_address_id:
            logger.warning("Shiprocket: order %s has no shipping address", order_id)
            return None

        address = address_repository.fetch_by_id(int(shipping_address_id))
        if not address:
            logger.warning("Shiprocket: shipping address missing for order %s", order_id)
            return None

        customer = customer_repository.fetch_by_id(int(order["customer_id"]))
        items = order_item_repository.list_by_order(order_id)
        if not items:
            logger.warning("Shiprocket: order %s has no items", order_id)
            return None

        payload = self._build_create_payload(order, address, customer, items)
        try:
            response = self.client.create_adhoc_order(payload)
        except ShiprocketError:
            logger.exception("Shiprocket create-order failed for order %s", order_id)
            raise

        shiprocket_order_id = str(
            response.get("order_id")
            or response.get("sr_order_id")
            or response.get("shipment_id")
            or ""
        )
        shipment_external = str(response.get("shipment_id") or "")
        awb = from_db_text(response.get("awb_code")) or "NA"
        courier = from_db_text(response.get("courier_name")) or "NA"

        shipment = shipment_repository.create(
            {
                "order_id": order_id,
                "shiprocket_order_id": to_db_text(shiprocket_order_id or "NA"),
                "shipment_id_external": to_db_text(shipment_external or "NA"),
                "awb_number": to_db_text(awb),
                "courier_name": to_db_text(courier),
                "tracking_number": to_db_text(awb if awb != "NA" else shipment_external or "NA"),
                "pickup_status": to_db_text(response.get("status") or "CREATED"),
                "delivery_status": to_db_text(response.get("status") or "NEW"),
                "shipping_label_url": to_db_text(response.get("label_url") or "NA"),
                "estimated_delivery_date": None,
                "shipped_at": None,
                "delivered_at": None,
                "raw_response": Json(response),
            }
        )

        self._record_tracking_snapshot(int(shipment["shipment_id"]), order_id, response)
        return shipment

    def _build_create_payload(
        self,
        order: dict[str, Any],
        address: dict[str, Any],
        customer: Optional[dict[str, Any]],
        items: list[dict[str, Any]],
    ) -> dict[str, Any]:
        order_number = from_db_text(order.get("order_number")) or str(order["order_id"])
        full_name = from_db_text(address.get("full_name")) or from_db_text(
            (customer or {}).get("full_name")
        ) or "Customer"
        first_name, last_name = _split_name(full_name)
        phone = _clean_phone(address.get("phone")) or _clean_phone((customer or {}).get("phone"))
        if not phone:
            phone = "9999999999"

        email = from_db_text((customer or {}).get("email")) or ""
        if not email or email.upper() == "NA":
            email = f"{phone}@guest.royalfurniture.local"

        line1 = from_db_text(address.get("address_line1")) or ""
        line2 = from_db_text(address.get("address_line2")) or ""
        landmark_raw = from_db_text(address.get("landmark")) or ""
        if landmark_raw and landmark_raw.upper() != "NA":
            if "\x1f" in landmark_raw:
                _, delivery_landmark = landmark_raw.split("\x1f", 1)
                landmark_note = delivery_landmark.strip()
            else:
                addr_type = (from_db_text(address.get("address_type")) or "").upper()
                landmark_note = "" if addr_type == "OTHER" else landmark_raw.strip()
            if landmark_note:
                line2 = f"{line2}, Near {landmark_note}" if line2 and line2.upper() != "NA" else f"Near {landmark_note}"
        city = from_db_text(address.get("city")) or ""
        state = from_db_text(address.get("state")) or ""
        pincode = from_db_text(address.get("pincode")) or ""
        country = from_db_text(address.get("country")) or "India"

        order_items = []
        for item in items:
            unit_price = _safe_float(item.get("unit_price"))
            order_items.append(
                {
                    "name": from_db_text(item.get("product_name")) or "Product",
                    "sku": from_db_text(item.get("sku")) or f"SKU-{item['product_id']}",
                    "units": int(item.get("quantity") or 1),
                    "selling_price": unit_price,
                    "discount": _safe_float(item.get("discount_amount")),
                    "tax": _safe_float(item.get("tax_amount")),
                    "hsn": _parse_hsn(item.get("hsn_code")),
                }
            )

        sub_total = float(order.get("subtotal") or 0)
        created = order.get("created_at")
        if isinstance(created, datetime):
            order_date = created.strftime("%Y-%m-%d %H:%M")
        else:
            order_date = datetime.now().strftime("%Y-%m-%d %H:%M")

        pickup_location = getattr(settings, "SHIPROCKET_PICKUP_LOCATION", "Primary")
        pkg_weight, pkg_length, pkg_breadth, pkg_height = _order_package_metrics(items)
        weight = pkg_weight or float(getattr(settings, "SHIPROCKET_DEFAULT_WEIGHT_KG", 1.0))
        length = pkg_length or float(getattr(settings, "SHIPROCKET_DEFAULT_LENGTH_CM", 10))
        breadth = pkg_breadth or float(getattr(settings, "SHIPROCKET_DEFAULT_BREADTH_CM", 10))
        height = pkg_height or float(getattr(settings, "SHIPROCKET_DEFAULT_HEIGHT_CM", 10))
        weight = max(0.1, weight)

        return {
            "order_id": order_number[:50],
            "order_date": order_date,
            "pickup_location": pickup_location,
            "billing_customer_name": first_name,
            "billing_last_name": last_name,
            "billing_address": line1,
            "billing_address_2": line2,
            "billing_city": city,
            "billing_state": state,
            "billing_pincode": pincode,
            "billing_country": country,
            "billing_email": email,
            "billing_phone": phone,
            "shipping_is_billing": True,
            "order_items": order_items,
            "payment_method": "Prepaid",
            "sub_total": sub_total,
            "length": length,
            "breadth": breadth,
            "height": height,
            "weight": weight,
        }

    def sync_tracking_for_order(self, order_id: int) -> list[dict[str, Any]]:
        shipment = shipment_repository.fetch_by_order_id(order_id)
        if not shipment:
            return []
        return self._sync_tracking_for_shipment(shipment)

    def handle_webhook(self, payload: dict[str, Any]) -> None:
        shiprocket_order_id = str(
            payload.get("sr_order_id")
            or payload.get("order_id")
            or payload.get("shipment_id")
            or ""
        )
        shipment = None
        if shiprocket_order_id:
            shipment = shipment_repository.fetch_by_shiprocket_order_id(shiprocket_order_id)

        awb = from_db_text(payload.get("awb")) or ""
        if not shipment and awb:
            shipment = shipment_repository.fetch_by_awb(awb)

        if not shipment:
            logger.warning("Shiprocket webhook: shipment not found for payload keys %s", list(payload))
            return

        shipment_id = int(shipment["shipment_id"])
        order_id = int(shipment["order_id"])
        updates: dict[str, Any] = {
            "raw_response": Json(payload),
        }
        if awb:
            updates["awb_number"] = to_db_text(awb)
            updates["tracking_number"] = to_db_text(awb)
        courier = from_db_text(payload.get("courier_name"))
        if courier:
            updates["courier_name"] = to_db_text(courier)
        status = from_db_text(payload.get("current_status") or payload.get("shipment_status"))
        if status:
            updates["delivery_status"] = to_db_text(status)

        shipment_repository.update(shipment_id, updates)
        self._record_tracking_snapshot(shipment_id, order_id, payload)

    def _sync_tracking_for_shipment(self, shipment: dict[str, Any]) -> list[dict[str, Any]]:
        if not self.enabled:
            return shipment_tracking_repository.list_paginated(
                page=1, page_size=100, order_id=int(shipment["order_id"])
            )[0]

        shipment_id = int(shipment["shipment_id"])
        order_id = int(shipment["order_id"])
        awb = from_db_text(shipment.get("awb_number")) or ""
        external_id = from_db_text(shipment.get("shipment_id_external")) or ""

        try:
            if awb and awb.upper() != "NA":
                payload = self.client.track_awb(awb)
            elif external_id and external_id.upper() != "NA":
                payload = self.client.track_shipment(external_id)
            else:
                return shipment_tracking_repository.list_paginated(
                    page=1, page_size=100, order_id=order_id
                )[0]
        except ShiprocketError:
            logger.exception("Shiprocket tracking sync failed for shipment %s", shipment_id)
            return shipment_tracking_repository.list_paginated(
                page=1, page_size=100, order_id=order_id
            )[0]

        self._record_tracking_snapshot(shipment_id, order_id, payload)
        tracking_data = payload.get("tracking_data") or payload
        current_status = from_db_text(
            tracking_data.get("shipment_status")
            or tracking_data.get("current_status")
            or payload.get("current_status")
        )
        if current_status:
            shipment_repository.update(
                shipment_id,
                {"delivery_status": to_db_text(current_status), "raw_response": Json(payload)},
            )

        return shipment_tracking_repository.list_paginated(
            page=1, page_size=100, order_id=order_id
        )[0]

    def _parse_tracking_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        tracking_data = (
            payload.get("tracking_data")
            if isinstance(payload.get("tracking_data"), dict)
            else payload
        )
        scans = tracking_data.get("shipment_track_activities") or tracking_data.get("scans") or []
        events: list[dict[str, Any]] = []

        if isinstance(scans, list):
            for scan in scans:
                if not isinstance(scan, dict):
                    continue
                message = from_db_text(scan.get("activity") or scan.get("status")) or "Shipment update"
                location = from_db_text(scan.get("location")) or ""
                status_code = from_db_text(
                    scan.get("sr-status-label") or scan.get("status") or message
                ) or "UPDATE"
                tracked_at = scan.get("date")
                events.append(
                    {
                        "statusCode": status_code,
                        "statusMessage": message,
                        "location": location,
                        "trackedAt": _format_dt(tracked_at),
                        "source": "SHIPROCKET",
                    }
                )

        current_status = from_db_text(
            tracking_data.get("shipment_status")
            or tracking_data.get("current_status")
            or payload.get("current_status")
            or payload.get("shipment_status")
        )
        awb = from_db_text(tracking_data.get("awb") or payload.get("awb")) or ""
        courier = from_db_text(
            tracking_data.get("courier_name") or payload.get("courier_name") or payload.get("courier")
        ) or ""
        edd = from_db_text(tracking_data.get("edd") or payload.get("edd")) or ""

        if not events and current_status:
            events.append(
                {
                    "statusCode": current_status,
                    "statusMessage": current_status,
                    "location": from_db_text(payload.get("location")) or "",
                    "trackedAt": _format_dt(datetime.now()),
                    "source": "SHIPROCKET",
                }
            )

        return {
            "currentStatus": current_status,
            "awb": awb if awb.upper() != "NA" else "",
            "courier": courier if courier.upper() != "NA" else "",
            "edd": edd if edd.upper() != "NA" else "",
            "events": events,
        }

    def _events_from_db(self, order_id: int) -> list[dict[str, Any]]:
        rows = shipment_tracking_repository.list_paginated(
            page=1, page_size=100, order_id=order_id
        )[0]
        return [
            {
                "statusCode": from_db_text(row.get("status_code")) or "",
                "statusMessage": from_db_text(row.get("status_message")) or "",
                "location": from_db_text(row.get("location")) or "",
                "trackedAt": _format_dt(row.get("tracked_at")),
                "source": from_db_text(row.get("source")) or "SHIPROCKET",
            }
            for row in rows
        ]

    def _shipment_snapshot(self, shipment: dict[str, Any], *, extra: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        awb = from_db_text(shipment.get("awb_number")) or ""
        info = {
            "shiprocketOrderId": from_db_text(shipment.get("shiprocket_order_id")),
            "awbNumber": awb if awb.upper() != "NA" else "",
            "courierName": from_db_text(shipment.get("courier_name")) or "",
            "deliveryStatus": from_db_text(shipment.get("delivery_status")) or "",
            "trackingNumber": from_db_text(shipment.get("tracking_number")) or "",
            "estimatedDeliveryDate": _format_dt(shipment.get("estimated_delivery_date")),
        }
        if extra:
            for key, value in extra.items():
                if value not in (None, "", "NA"):
                    info[key] = value
        return info

    def get_live_tracking_for_order(self, order_id: int) -> dict[str, Any]:
        shipment = shipment_repository.fetch_by_order_id(order_id)
        if not shipment:
            return {"shipment": None, "events": []}

        shipment_id = int(shipment["shipment_id"])
        awb = from_db_text(shipment.get("awb_number")) or ""
        external_id = from_db_text(shipment.get("shipment_id_external")) or ""

        if not self.enabled:
            return {
                "shipment": self._shipment_snapshot(shipment),
                "events": self._events_from_db(order_id),
            }

        try:
            if awb and awb.upper() != "NA":
                payload = self.client.track_awb(awb)
            elif external_id and external_id.upper() != "NA":
                payload = self.client.track_shipment(external_id)
            else:
                return {
                    "shipment": self._shipment_snapshot(shipment),
                    "events": self._events_from_db(order_id),
                }
        except ShiprocketError:
            logger.exception("Shiprocket live tracking failed for order %s", order_id)
            return {
                "shipment": self._shipment_snapshot(shipment),
                "events": self._events_from_db(order_id),
            }

        self._record_tracking_snapshot(shipment_id, order_id, payload)
        parsed = self._parse_tracking_payload(payload)
        if parsed.get("currentStatus"):
            shipment_repository.update(
                shipment_id,
                {
                    "delivery_status": to_db_text(parsed["currentStatus"]),
                    "raw_response": Json(payload),
                },
            )

        return {
            "shipment": self._shipment_snapshot(
                shipment,
                extra={
                    "deliveryStatus": parsed.get("currentStatus"),
                    "courierName": parsed.get("courier"),
                    "awbNumber": parsed.get("awb"),
                    "estimatedDeliveryDate": parsed.get("edd"),
                },
            ),
            "events": parsed.get("events") or [],
        }

    def _record_tracking_snapshot(
        self,
        shipment_id: int,
        order_id: int,
        payload: dict[str, Any],
    ) -> None:
        tracking_data = payload.get("tracking_data") if isinstance(payload.get("tracking_data"), dict) else payload
        scans = tracking_data.get("shipment_track_activities") or tracking_data.get("scans") or []

        if scans:
            for scan in scans:
                if not isinstance(scan, dict):
                    continue
                message = from_db_text(scan.get("activity") or scan.get("status")) or "Update"
                location = from_db_text(scan.get("location")) or "NA"
                status_code = from_db_text(
                    scan.get("sr-status-label") or scan.get("status") or message
                ) or "UPDATE"
                tracked_at = scan.get("date") or datetime.now()
                shipment_tracking_repository.create(
                    {
                        "shipment_id": shipment_id,
                        "order_id": order_id,
                        "status_code": to_db_text(status_code),
                        "status_message": to_db_text(message),
                        "location": to_db_text(location),
                        "tracked_at": tracked_at,
                        "source": "SHIPROCKET",
                        "raw_payload": Json(scan),
                    }
                )
            return

        status = from_db_text(
            payload.get("current_status")
            or payload.get("shipment_status")
            or payload.get("status")
        )
        if status:
            shipment_tracking_repository.create(
                {
                    "shipment_id": shipment_id,
                    "order_id": order_id,
                    "status_code": to_db_text(status),
                    "status_message": to_db_text(
                        payload.get("current_status") or payload.get("shipment_status") or status
                    ),
                    "location": to_db_text(payload.get("location") or "NA"),
                    "tracked_at": datetime.now(),
                    "source": "SHIPROCKET",
                    "raw_payload": Json(payload),
                }
            )


def _format_dt(value: Any) -> Optional[str]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


shiprocket_integration_service = ShiprocketIntegrationService()
