from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from psycopg2.extras import Json

from apps.customers.repositories.address_repository import address_repository
from apps.customers.repositories.customer_repository import customer_repository
from apps.orders.repositories.order_history_repository import order_history_repository
from apps.orders.repositories.order_item_repository import order_item_repository
from apps.orders.repositories.order_repository import order_repository
from apps.orders.repositories.order_status_repository import order_status_repository
from apps.orders.repositories.order_tracking_repository import order_tracking_repository
from apps.payments.repositories.payment_repository import payment_repository
from apps.products.repositories.product_child_repository import product_child_repository
from apps.products.repositories.product_repository import product_repository
from core.database import select_one
from core.database.transaction import atomic
from core.exceptions.base import NotFoundException, ValidationException
from core.helpers.text import from_db_text, to_db_text


def _format_dt(value: Any) -> Optional[str]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _optional_int(value: Any) -> Optional[int]:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _base_list_params(kwargs: dict[str, Any]) -> dict[str, Any]:
    return {
        "page": kwargs.get("page", 1),
        "page_size": kwargs.get("page_size", 20),
        "search": kwargs.get("search", ""),
        "sort_by": kwargs.get("sort_by", "created_at"),
        "sort_dir": kwargs.get("sort_dir", "desc"),
    }


def _generate_order_number(*, conn) -> str:
    today = datetime.now().strftime("%Y%m%d")
    prefix = f"RF-ORD-{today}-"
    count = order_repository.count_orders_for_date_prefix(prefix, conn=conn)
    return f"{prefix}{count + 1:04d}"


class OrderService:
    schema = "royal"

    def _serialize_address(self, prefix: str, row: dict[str, Any]) -> Optional[dict[str, Any]]:
        line1 = row.get(f"{prefix}_address_line1")
        if not line1 or from_db_text(line1) in (None, "", "NA"):
            return None
        return {
            "fullName": from_db_text(row.get(f"{prefix}_full_name")) or "",
            "phone": from_db_text(row.get(f"{prefix}_phone")) or "",
            "addressLine1": from_db_text(row.get(f"{prefix}_address_line1")) or "",
            "addressLine2": from_db_text(row.get(f"{prefix}_address_line2")),
            "city": from_db_text(row.get(f"{prefix}_city")) or "",
            "state": from_db_text(row.get(f"{prefix}_state")) or "",
            "pincode": from_db_text(row.get(f"{prefix}_pincode")) or "",
        }

    def _serialize_item(self, row: dict[str, Any]) -> dict[str, Any]:
        variant_id = row.get("product_variant_id")
        return {
            "id": str(row["order_item_id"]),
            "productId": str(row["product_id"]),
            "productVariantId": str(variant_id) if variant_id else None,
            "productName": from_db_text(row.get("product_name")) or "",
            "sku": from_db_text(row.get("sku")) or "",
            "quantity": int(row.get("quantity") or 1),
            "unitPrice": float(row.get("unit_price") or 0),
            "discountAmount": float(row.get("discount_amount") or 0),
            "taxAmount": float(row.get("tax_amount") or 0),
            "lineTotal": float(row.get("line_total") or 0),
            "hsnCode": from_db_text(row.get("hsn_code")) or "",
            "gstPercent": float(row.get("product_gst_percent") or 0),
            "warehouseId": str(row["warehouse_id"]) if row.get("warehouse_id") else None,
        }

    def _serialize_payment(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": str(row["payment_id"]),
            "paymentMethod": from_db_text(row.get("payment_method")) or "",
            "paymentAmount": float(row.get("payment_amount") or 0),
            "currency": from_db_text(row.get("currency")) or "INR",
            "paymentStatus": from_db_text(row.get("payment_status")) or "",
            "transactionRef": from_db_text(row.get("transaction_ref")),
            "paidAt": _format_dt(row.get("paid_at")),
            "createdAt": _format_dt(row.get("created_at")),
        }

    def _serialize_tracking(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": str(row["order_tracking_id"]),
            "statusCode": from_db_text(row.get("status_code")) or "",
            "statusMessage": from_db_text(row.get("status_message")) or "",
            "location": from_db_text(row.get("location")),
            "trackedAt": _format_dt(row.get("tracked_at")),
            "isCustomerVisible": bool(row.get("is_customer_visible")),
        }

    def _serialize_history(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": str(row["order_history_id"]),
            "fromStatus": from_db_text(row.get("from_status")) or "",
            "toStatus": from_db_text(row.get("to_status")) or "",
            "changedBy": str(row["changed_by"]) if row.get("changed_by") else None,
            "changedByName": from_db_text(row.get("changed_by_name")),
            "changeReason": from_db_text(row.get("change_reason")),
            "metadata": row.get("metadata") or {},
            "changedAt": _format_dt(row.get("changed_at")),
        }

    def _serialize_shipment(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": str(row["shipment_id"]),
            "shiprocketOrderId": from_db_text(row.get("shiprocket_order_id")),
            "shipmentIdExternal": from_db_text(row.get("shipment_id_external")),
            "awbNumber": from_db_text(row.get("awb_number")),
            "courierName": from_db_text(row.get("courier_name")),
            "trackingNumber": from_db_text(row.get("tracking_number")),
            "pickupStatus": from_db_text(row.get("pickup_status")),
            "deliveryStatus": from_db_text(row.get("delivery_status")),
            "estimatedDeliveryDate": _format_dt(row.get("estimated_delivery_date")),
            "shippedAt": _format_dt(row.get("shipped_at")),
            "deliveredAt": _format_dt(row.get("delivered_at")),
        }

    def _serialize_shipment_tracking(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": str(row["shipment_tracking_id"]),
            "shipmentId": str(row["shipment_id"]),
            "statusCode": from_db_text(row.get("status_code")) or "",
            "statusMessage": from_db_text(row.get("status_message")) or "",
            "location": from_db_text(row.get("location")),
            "trackedAt": _format_dt(row.get("tracked_at")),
            "source": from_db_text(row.get("source")) or "",
        }

    def _serialize_summary(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": str(row["order_id"]),
            "orderNumber": from_db_text(row.get("order_number")) or "",
            "customerId": str(row["customer_id"]),
            "customerName": from_db_text(row.get("customer_name")) or "",
            "customerEmail": from_db_text(row.get("customer_email")) or "",
            "customerPhone": from_db_text(row.get("customer_phone")) or "",
            "statusCode": from_db_text(row.get("status_code")) or "",
            "statusName": from_db_text(row.get("status_name")) or "",
            "currentStatus": from_db_text(row.get("current_status")) or "",
            "subtotal": float(row.get("subtotal") or 0),
            "discountAmount": float(row.get("discount_amount") or 0),
            "taxAmount": float(row.get("tax_amount") or 0),
            "shippingAmount": float(row.get("shipping_amount") or 0),
            "totalAmount": float(row.get("total_amount") or 0),
            "paymentMethod": from_db_text(row.get("payment_method")) or "",
            "couponCode": from_db_text(row.get("coupon_code")),
            "createdAt": _format_dt(row.get("created_at")),
            "updatedAt": _format_dt(row.get("updated_at")),
            "confirmedAt": _format_dt(row.get("confirmed_at")),
            "shippedAt": _format_dt(row.get("shipped_at")),
            "deliveredAt": _format_dt(row.get("delivered_at")),
            "cancelledAt": _format_dt(row.get("cancelled_at")),
        }

    def _serialize_detail(self, row: dict[str, Any], order_id: int) -> dict[str, Any]:
        detail = self._serialize_summary(row)
        detail.update({
            "orderStatusId": str(row["order_status_id"]),
            "shippingAddressId": str(row["shipping_address_id"]) if row.get("shipping_address_id") else None,
            "billingAddressId": str(row["billing_address_id"]) if row.get("billing_address_id") else None,
            "shippingAddress": self._serialize_address("shipping", row),
            "billingAddress": self._serialize_address("billing", row),
            "notes": from_db_text(row.get("notes")),
            "cancelReason": from_db_text(row.get("cancel_reason")),
            "items": [self._serialize_item(i) for i in order_item_repository.list_by_order(order_id)],
            "payments": [self._serialize_payment(p) for p in payment_repository.list_by_order(order_id)],
            "tracking": [self._serialize_tracking(t) for t in order_tracking_repository.list_by_order(order_id)],
            "history": [self._serialize_history(h) for h in order_history_repository.list_by_order(order_id)],
            "shipments": [self._serialize_shipment(s) for s in order_repository.fetch_shipments(order_id)],
            "shipmentTracking": [
                self._serialize_shipment_tracking(st)
                for st in order_repository.fetch_shipment_tracking(order_id)
            ],
        })
        return detail

    def list_orders(self, **kwargs) -> dict[str, Any]:
        params = _base_list_params(kwargs)
        if kwargs.get("customer_id") is not None:
            params["customer_id"] = kwargs["customer_id"]
        if kwargs.get("status_code"):
            params["status_code"] = kwargs["status_code"]
        if kwargs.get("current_status"):
            params["current_status"] = kwargs["current_status"]
        rows, total = order_repository.list_paginated(**params)
        page = params["page"]
        page_size = params["page_size"]
        return {
            "items": [self._serialize_summary(r) for r in rows],
            "pagination": {
                "page": page,
                "pageSize": page_size,
                "total": total,
                "totalPages": max(1, (total + page_size - 1) // page_size),
            },
        }

    def get_order(self, order_id: int) -> dict[str, Any]:
        row = order_repository.fetch_by_id(order_id)
        if not row:
            raise NotFoundException("Order not found")
        return self._serialize_detail(row, order_id)

    def _resolve_item(self, item: dict[str, Any]) -> dict[str, Any]:
        product_id = _optional_int(item.get("productId"))
        if not product_id:
            raise ValidationException(
                details=[{"field": "items.productId", "message": "Product is required"}]
            )
        product = product_repository.fetch_by_id(product_id)
        if not product:
            raise ValidationException(
                details=[{"field": "items.productId", "message": "Product not found"}]
            )

        variant_id = _optional_int(item.get("productVariantId"))
        if variant_id is None:
            variant_id = product_child_repository.fetch_default_variant_id(product_id)
        variant_name = ""
        sku = from_db_text(product.get("sku")) or ""
        unit_price = float(item.get("unitPrice") or product.get("sale_price") or product.get("base_price") or 0)
        hsn_code = from_db_text(product.get("hsn_code")) or ""
        gst_percent = float(product.get("gst_percent") or 0)

        if variant_id:
            variant_sql = f"""
                SELECT variant_name, sku, sale_price
                FROM {self.schema}.product_varianttbl
                WHERE product_variant_id = %s AND product_id = %s AND is_deleted = FALSE
            """
            variant = select_one(variant_sql, [variant_id, product_id])
            if not variant:
                raise ValidationException(
                    details=[{"field": "items.productVariantId", "message": "Product variant not found"}]
                )
            variant_name = from_db_text(variant.get("variant_name")) or ""
            sku = from_db_text(variant.get("sku")) or sku
            if not item.get("unitPrice"):
                unit_price = float(variant.get("sale_price") or unit_price)

        quantity = int(item.get("quantity") or 1)
        if quantity < 1:
            raise ValidationException(
                details=[{"field": "items.quantity", "message": "Quantity must be at least 1"}]
            )

        discount = float(item.get("discountAmount") or 0)
        taxable = (unit_price * quantity) - discount
        tax_amount = float(item.get("taxAmount") or 0)
        if tax_amount == 0 and gst_percent > 0:
            tax_amount = round(taxable * gst_percent / 100, 2)
        line_total = float(item.get("lineTotal") or (taxable + tax_amount))

        product_name = from_db_text(product.get("name")) or ""
        if variant_name:
            product_name = f"{product_name} - {variant_name}"

        return {
            "product_id": product_id,
            "product_variant_id": variant_id,
            "product_name": to_db_text(product_name),
            "sku": to_db_text(sku),
            "quantity": quantity,
            "unit_price": unit_price,
            "discount_amount": discount,
            "tax_amount": tax_amount,
            "line_total": line_total,
            "hsn_code": to_db_text(item.get("hsnCode") or hsn_code),
            "warehouse_id": _optional_int(item.get("warehouseId")),
        }

    def create_order(self, payload: dict[str, Any], *, created_by: Optional[int] = None) -> dict[str, Any]:
        customer_id = _optional_int(payload.get("customerId"))
        if not customer_id:
            raise ValidationException(
                details=[{"field": "customerId", "message": "Customer is required"}]
            )
        if not customer_repository.fetch_by_id(customer_id):
            raise NotFoundException("Customer not found")

        items_payload = payload.get("items") or []
        if not items_payload:
            raise ValidationException(
                details=[{"field": "items", "message": "At least one order item is required"}]
            )

        status_code = (payload.get("statusCode") or "CONFIRMED").strip().upper()
        status_row = order_status_repository.fetch_by_code(status_code)
        if not status_row:
            status_row = order_status_repository.fetch_by_code("PENDING")
        if not status_row:
            raise ValidationException(
                details=[{"field": "statusCode", "message": "Order status not configured"}]
            )

        shipping_address_id = _optional_int(payload.get("shippingAddressId"))
        billing_address_id = _optional_int(payload.get("billingAddressId"))
        if shipping_address_id and not address_repository.fetch_by_id(shipping_address_id):
            raise ValidationException(
                details=[{"field": "shippingAddressId", "message": "Shipping address not found"}]
            )
        if billing_address_id and not address_repository.fetch_by_id(billing_address_id):
            raise ValidationException(
                details=[{"field": "billingAddressId", "message": "Billing address not found"}]
            )

        resolved_items = [self._resolve_item(item) for item in items_payload]
        subtotal = sum(i["unit_price"] * i["quantity"] for i in resolved_items)
        discount_amount = float(payload.get("discountAmount") or 0)
        tax_amount = sum(i["tax_amount"] for i in resolved_items)
        shipping_amount = float(payload.get("shippingAmount") or 0)
        total_amount = float(
            payload.get("totalAmount") or (subtotal - discount_amount + tax_amount + shipping_amount)
        )

        payment_method = (payload.get("paymentMethod") or "QR").strip()
        payment_status = (payload.get("paymentStatus") or "PENDING").strip().upper()
        create_payment = bool(payload.get("createPayment", payment_status in ("PAID", "VERIFIED")))

        with atomic() as conn:
            order_number = _generate_order_number(conn=conn)
            order = order_repository.create({
                "order_number": order_number,
                "customer_id": customer_id,
                "order_status_id": int(status_row["order_status_id"]),
                "current_status": status_code,
                "subtotal": subtotal,
                "discount_amount": discount_amount,
                "tax_amount": tax_amount,
                "shipping_amount": shipping_amount,
                "total_amount": total_amount,
                "coupon_id": _optional_int(payload.get("couponId")),
                "coupon_code": to_db_text(payload.get("couponCode")),
                "shipping_address_id": shipping_address_id,
                "billing_address_id": billing_address_id,
                "payment_method": payment_method,
                "notes": to_db_text(payload.get("notes")),
                "ip_address": to_db_text(payload.get("ipAddress")),
                "user_agent": to_db_text(payload.get("userAgent")),
            }, conn=conn)
            order_id = int(order["order_id"])

            for item in resolved_items:
                order_item_repository.create({"order_id": order_id, **item}, conn=conn)

            order_history_repository.create({
                "order_id": order_id,
                "from_status": "NA",
                "to_status": status_code,
                "changed_by": created_by,
                "change_reason": to_db_text(payload.get("changeReason") or "Manual order created"),
                "metadata": Json({"source": "admin_manual"}),
                "changed_at": datetime.now(),
            }, conn=conn)

            if create_payment:
                payment_repository.create({
                    "order_id": order_id,
                    "customer_id": customer_id,
                    "payment_method": payment_method,
                    "payment_amount": total_amount,
                    "currency": payload.get("currency") or "INR",
                    "payment_status": payment_status,
                    "transaction_ref": to_db_text(payload.get("transactionRef")),
                    "paid_at": datetime.now() if payment_status in ("PAID", "VERIFIED") else None,
                }, conn=conn)

        from apps.orders.services.order_notification_service import order_notification_service

        order_notification_service.notify_created(order_id)
        return self.get_order(order_id)

    def update_order(
        self,
        order_id: int,
        payload: dict[str, Any],
        *,
        changed_by: Optional[int] = None,
    ) -> dict[str, Any]:
        order = order_repository.fetch_by_id(order_id)
        if not order:
            raise NotFoundException("Order not found")

        updates: dict[str, Any] = {}
        from_status = from_db_text(order.get("current_status")) or "NA"
        to_status = from_status

        if "notes" in payload:
            updates["notes"] = to_db_text(payload.get("notes"))

        if "statusCode" in payload or "currentStatus" in payload:
            status_code = (payload.get("statusCode") or payload.get("currentStatus") or "").strip().upper()
            if not status_code:
                raise ValidationException(
                    details=[{"field": "statusCode", "message": "Status code is required"}]
                )
            status_row = order_status_repository.fetch_by_code(status_code)
            if not status_row:
                raise ValidationException(
                    details=[{"field": "statusCode", "message": "Order status not found"}]
                )
            updates["order_status_id"] = int(status_row["order_status_id"])
            updates["current_status"] = status_code
            to_status = status_code

            if status_code == "CONFIRMED":
                updates["confirmed_at"] = datetime.now()
            elif status_code == "SHIPPED":
                updates["shipped_at"] = datetime.now()
            elif status_code == "DELIVERED":
                updates["delivered_at"] = datetime.now()
            elif status_code == "CANCELLED":
                updates["cancelled_at"] = datetime.now()
                if payload.get("cancelReason"):
                    updates["cancel_reason"] = to_db_text(payload.get("cancelReason"))

        with atomic() as conn:
            if updates:
                order_repository.update(order_id, updates, conn=conn)
            if to_status != from_status:
                order_history_repository.create({
                    "order_id": order_id,
                    "from_status": from_status,
                    "to_status": to_status,
                    "changed_by": changed_by,
                    "change_reason": to_db_text(payload.get("changeReason")),
                    "metadata": Json(payload.get("metadata") or {}),
                    "changed_at": datetime.now(),
                }, conn=conn)
                if to_status == "CANCELLED":
                    from apps.storefront.services.inventory_stock_service import inventory_stock_service

                    inventory_stock_service.restore_for_order(
                        order_id,
                        performed_by=changed_by,
                        conn=conn,
                    )
            if payload.get("tracking"):
                tracking = payload["tracking"]
                order_tracking_repository.create({
                    "order_id": order_id,
                    "status_code": tracking.get("statusCode") or to_status,
                    "status_message": to_db_text(tracking.get("statusMessage") or to_status),
                    "location": to_db_text(tracking.get("location")),
                    "tracked_at": tracking.get("trackedAt") or datetime.now(),
                    "is_customer_visible": bool(tracking.get("isCustomerVisible", True)),
                }, conn=conn)

        from apps.orders.services.order_notification_service import order_notification_service

        if to_status != from_status:
            if to_status == "CANCELLED":
                order_notification_service.notify_cancelled(order_id)
            elif to_status == "RETURNED":
                order_notification_service.notify_return(order_id)
            else:
                order_notification_service.notify_updated(
                    order_id,
                    from_status=from_status,
                    to_status=to_status,
                )
        elif updates:
            order_notification_service.notify_updated(order_id)

        return self.get_order(order_id)


order_service = OrderService()
