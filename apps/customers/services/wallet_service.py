from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from apps.customers.repositories.customer_repository import customer_repository
from apps.customers.repositories.wallet_repository import wallet_repository
from apps.customers.repositories.wallet_transaction_repository import wallet_transaction_repository
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


class WalletService:
    def _serialize_wallet(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": str(row["customer_wallet_id"]),
            "customerId": str(row["customer_id"]),
            "customerName": from_db_text(row.get("customer_name")) or "",
            "customerEmail": from_db_text(row.get("customer_email")) or "",
            "customerPhone": from_db_text(row.get("customer_phone")) or "",
            "balance": float(row.get("balance") or 0),
            "currency": from_db_text(row.get("currency")) or "INR",
            "isActive": bool(row.get("is_active")),
            "createdAt": _format_dt(row.get("created_at")),
            "updatedAt": _format_dt(row.get("updated_at")),
        }

    def _serialize_transaction(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": str(row["wallet_transaction_id"]),
            "walletId": str(row["customer_wallet_id"]),
            "customerId": str(row["customer_id"]),
            "transactionType": from_db_text(row.get("transaction_type")) or "",
            "amount": float(row.get("amount") or 0),
            "balanceBefore": float(row.get("balance_before") or 0),
            "balanceAfter": float(row.get("balance_after") or 0),
            "referenceType": from_db_text(row.get("reference_type")),
            "referenceId": str(row["reference_id"]) if row.get("reference_id") else None,
            "description": from_db_text(row.get("description")),
            "createdAt": _format_dt(row.get("created_at")),
        }

    def list_wallets(self, **kwargs) -> dict[str, Any]:
        rows, total = wallet_repository.list_paginated(**_base_list_params(kwargs))
        page = kwargs.get("page", 1)
        page_size = kwargs.get("page_size", 20)
        return {
            "items": [self._serialize_wallet(r) for r in rows],
            "pagination": {
                "page": page,
                "pageSize": page_size,
                "total": total,
                "totalPages": max(1, (total + page_size - 1) // page_size),
            },
        }

    def get_wallet(self, customer_wallet_id: int, *, txn_limit: int = 50) -> dict[str, Any]:
        row = wallet_repository.fetch_by_id(customer_wallet_id)
        if not row:
            raise NotFoundException("Wallet not found")
        detail = self._serialize_wallet(row)
        transactions = wallet_transaction_repository.list_by_wallet(customer_wallet_id, limit=txn_limit)
        detail["transactions"] = [self._serialize_transaction(t) for t in transactions]
        return detail

    def _ensure_wallet(self, customer_id: int, *, conn) -> dict[str, Any]:
        wallet = wallet_repository.fetch_by_customer(customer_id)
        if wallet:
            return wallet_repository.fetch_for_update(int(wallet["customer_wallet_id"]), conn=conn) or wallet
        return wallet_repository.create({
            "customer_id": customer_id,
            "balance": 0,
            "currency": "INR",
            "is_active": True,
        }, conn=conn)

    def process_transaction(self, customer_wallet_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        txn_type = (payload.get("transactionType") or "").strip().upper()
        if txn_type not in ("CREDIT", "DEBIT"):
            raise ValidationException(
                details=[{"field": "transactionType", "message": "Transaction type must be CREDIT or DEBIT"}]
            )
        amount = float(payload.get("amount") or 0)
        if amount <= 0:
            raise ValidationException(
                details=[{"field": "amount", "message": "Amount must be greater than zero"}]
            )

        with atomic() as conn:
            wallet = wallet_repository.fetch_for_update(customer_wallet_id, conn=conn)
            if not wallet:
                raise NotFoundException("Wallet not found")

            balance_before = float(wallet.get("balance") or 0)
            if txn_type == "CREDIT":
                balance_after = balance_before + amount
            else:
                if balance_before < amount:
                    raise ValidationException(
                        details=[{"field": "amount", "message": "Insufficient wallet balance"}]
                    )
                balance_after = balance_before - amount

            wallet_repository.update_balance(customer_wallet_id, balance_after, conn=conn)
            wallet_transaction_repository.create({
                "customer_wallet_id": customer_wallet_id,
                "customer_id": int(wallet["customer_id"]),
                "transaction_type": txn_type,
                "amount": amount,
                "balance_before": balance_before,
                "balance_after": balance_after,
                "reference_type": to_db_text(payload.get("referenceType") or "MANUAL"),
                "reference_id": _optional_int(payload.get("referenceId")),
                "description": to_db_text(payload.get("description")),
            }, conn=conn)

        return self.get_wallet(customer_wallet_id)

    def credit_or_debit_by_customer(self, customer_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        if not customer_repository.fetch_by_id(customer_id):
            raise NotFoundException("Customer not found")
        with atomic() as conn:
            wallet = self._ensure_wallet(customer_id, conn=conn)
        return self.process_transaction(int(wallet["customer_wallet_id"]), payload)


wallet_service = WalletService()
