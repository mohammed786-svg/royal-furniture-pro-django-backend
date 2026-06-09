"""Pagination helpers for raw SQL list endpoints."""
from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings


@dataclass
class PaginationParams:
    page: int = 1
    page_size: int = settings.DEFAULT_PAGE_SIZE

    def __post_init__(self) -> None:
        self.page = max(1, self.page)
        max_size = settings.MAX_PAGE_SIZE
        self.page_size = min(max(self.page_size, 1), max_size)

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size
