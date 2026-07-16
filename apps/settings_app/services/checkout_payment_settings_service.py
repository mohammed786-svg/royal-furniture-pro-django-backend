from __future__ import annotations

from typing import Any

from apps.settings_app.repositories.setting_repository import setting_repository
from core.helpers.text import from_db_text, save_base64_image, to_db_text

PAYMENT_GROUP = "checkout_payment"

SETTING_KEYS = {
    "qrImageUrl": "payment.qr_image_url",
    "accountName": "payment.account_name",
    "bankName": "payment.bank_name",
    "accountNumber": "payment.account_number",
    "ifsc": "payment.ifsc",
    "branch": "payment.branch",
    "upiId": "payment.upi_id",
}

DEFAULTS = {
    "qrImageUrl": "/payment/royal-payment-qr.svg",
    "accountName": "Royal Furniture Pro Pvt Ltd",
    "bankName": "HDFC Bank",
    "accountNumber": "50200012345678",
    "ifsc": "HDFC0001234",
    "branch": "1st Cross, Azam Nagar, Belagavi, Karnataka 590010",
    "upiId": "royalfurniture@hdfcbank",
}

DESCRIPTIONS = {
    "qrImageUrl": "Checkout payment QR code image URL",
    "accountName": "Bank account name shown at checkout",
    "bankName": "Bank name shown at checkout",
    "accountNumber": "Bank account number shown at checkout",
    "ifsc": "IFSC code shown at checkout",
    "branch": "Bank branch / address shown at checkout",
    "upiId": "UPI ID shown at checkout",
}


class CheckoutPaymentSettingsService:
    def get_instructions(self) -> dict[str, Any]:
        rows = setting_repository.list_by_group(PAYMENT_GROUP)
        by_key = {
            (from_db_text(row.get("setting_key")) or ""): from_db_text(row.get("setting_value")) or ""
            for row in rows
        }
        data: dict[str, Any] = {}
        for field, setting_key in SETTING_KEYS.items():
            value = by_key.get(setting_key) or DEFAULTS[field]
            data[field] = value
        return data

    def update_instructions(self, payload: dict[str, Any]) -> dict[str, Any]:
        current = self.get_instructions()
        next_values = {**current}

        for field in SETTING_KEYS:
            if field not in payload:
                continue
            raw = payload.get(field)
            if raw is None:
                continue
            value = str(raw).strip()
            if field == "qrImageUrl" and value.startswith("data:image"):
                saved = save_base64_image(value, subdir="payments", prefix="checkout-qr")
                value = saved or current.get("qrImageUrl") or DEFAULTS["qrImageUrl"]
            next_values[field] = value or DEFAULTS[field]

        for field, setting_key in SETTING_KEYS.items():
            value_type = "IMAGE" if field == "qrImageUrl" else "TEXT"
            setting_repository.upsert_by_key(
                key=setting_key,
                value=to_db_text(next_values[field]),
                group=PAYMENT_GROUP,
                value_type=value_type,
                description=DESCRIPTIONS[field],
            )

        return self.get_instructions()


checkout_payment_settings_service = CheckoutPaymentSettingsService()
