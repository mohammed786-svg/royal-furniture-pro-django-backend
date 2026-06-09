from __future__ import annotations

class CustomerOptionsService:
    schema = "royal"

    def get_options(self) -> dict[str, object]:
        genders = ["MALE", "FEMALE", "OTHER", "PREFER_NOT_TO_SAY"]
        address_types = ["SHIPPING", "BILLING", "BOTH"]

        return {
            "genders": genders,
            "addressTypes": address_types,
            "transactionTypes": ["CREDIT", "DEBIT"],
            "referenceTypes": ["ORDER", "REFUND", "ADJUSTMENT", "REFERRAL", "MANUAL"],
        }


customer_options_service = CustomerOptionsService()
