"""
Central API / SQL debug logger.

Toggle all debug output with a single env flag:
  DEBUG_API_LOGS=True   → prints decrypted JSON + SQL on server console
  DEBUG_API_LOGS=False  → silent (default)
"""
from __future__ import annotations

import json
import logging
from typing import Any

from django.conf import settings

_logger = logging.getLogger("royal.api.debug")


def _enabled() -> bool:
    return bool(getattr(settings, "DEBUG_API_LOGS", False))


def _pretty(data: Any) -> str:
    try:
        return json.dumps(data, indent=2, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        return str(data)


def log_api_request(method: str, endpoint: str, body: Any) -> None:
    if not _enabled():
        return
    _logger.info(
        "\n── API REQUEST ──────────────────────────────\n"
        "%s %s\n%s\n"
        "──────────────────────────────────────────────",
        method,
        endpoint,
        _pretty(body),
    )


def log_api_response(endpoint: str, status_code: int, body: Any) -> None:
    if not _enabled():
        return
    _logger.info(
        "\n── API RESPONSE ─────────────────────────────\n"
        "%s → %s\n%s\n"
        "──────────────────────────────────────────────",
        endpoint,
        status_code,
        _pretty(body),
    )


def log_sql_query(sql: str, params: Any = None) -> None:
    if not _enabled():
        return
    _logger.info(
        "\n── SQL QUERY ──────────────────────────────────\n%s\nParams: %s\n"
        "──────────────────────────────────────────────",
        sql.strip(),
        params,
    )
