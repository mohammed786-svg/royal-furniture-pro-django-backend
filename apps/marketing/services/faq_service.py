from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from apps.marketing.repositories.faq_repository import faq_repository
from core.exceptions.base import NotFoundException, ValidationException
from core.helpers.text import from_db_text, to_db_text


def _format_dt(value: Any) -> Optional[str]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _base_list_params(kwargs: dict[str, Any]) -> dict[str, Any]:
    return {
        "page": kwargs.get("page", 1),
        "page_size": kwargs.get("page_size", 20),
        "search": kwargs.get("search", ""),
        "sort_by": kwargs.get("sort_by", "display_order"),
        "sort_dir": kwargs.get("sort_dir", "asc"),
    }


def _pagination(page: int, page_size: int, total: int) -> dict[str, Any]:
    return {
        "page": page,
        "pageSize": page_size,
        "total": total,
        "totalPages": max(1, (total + page_size - 1) // page_size),
    }


class FaqService:
    def _serialize(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": str(row["faq_id"]),
            "category": from_db_text(row.get("category")) or "",
            "question": from_db_text(row.get("question")) or "",
            "answer": from_db_text(row.get("answer")) or "",
            "displayOrder": int(row.get("display_order") or 0),
            "isActive": bool(row.get("is_active")),
            "createdAt": _format_dt(row.get("created_at")),
            "updatedAt": _format_dt(row.get("updated_at")),
        }

    def list_faqs(self, **kwargs) -> dict[str, Any]:
        rows, total = faq_repository.list_paginated(**_base_list_params(kwargs))
        page = kwargs.get("page", 1)
        page_size = kwargs.get("page_size", 20)
        return {
            "items": [self._serialize(r) for r in rows],
            "pagination": _pagination(page, page_size, total),
        }

    def get_faq(self, faq_id: int) -> dict[str, Any]:
        row = faq_repository.fetch_by_id(faq_id)
        if not row:
            raise NotFoundException("FAQ not found")
        return self._serialize(row)

    def create_faq(self, payload: dict[str, Any]) -> dict[str, Any]:
        question = (payload.get("question") or "").strip()
        if not question:
            raise ValidationException(
                details=[{"field": "question", "message": "Question is required"}]
            )

        row = faq_repository.create({
            "category": to_db_text(payload.get("category")),
            "question": to_db_text(question),
            "answer": to_db_text(payload.get("answer")),
            "display_order": int(payload.get("displayOrder") or 0),
            "is_active": bool(payload.get("isActive", True)),
        })
        return self._serialize(row)

    def update_faq(self, faq_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        existing = faq_repository.fetch_by_id(faq_id)
        if not existing:
            raise NotFoundException("FAQ not found")

        updates: dict[str, Any] = {}
        if "category" in payload:
            updates["category"] = to_db_text(payload.get("category"))
        if "question" in payload:
            question = (payload.get("question") or "").strip()
            if not question:
                raise ValidationException(
                    details=[{"field": "question", "message": "Question is required"}]
                )
            updates["question"] = to_db_text(question)
        if "answer" in payload:
            updates["answer"] = to_db_text(payload.get("answer"))
        if "displayOrder" in payload:
            updates["display_order"] = int(payload.get("displayOrder") or 0)
        if "isActive" in payload:
            updates["is_active"] = bool(payload.get("isActive"))

        row = faq_repository.update(faq_id, updates)
        if not row:
            raise NotFoundException("FAQ not found")
        return self._serialize(row)

    def delete_faq(self, faq_id: int) -> None:
        if not faq_repository.soft_delete(faq_id):
            raise NotFoundException("FAQ not found")


faq_service = FaqService()
