from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")


def serialize_datetime(value: Any) -> Optional[str]:
    """
    Serialize DB datetimes for JSON APIs.

    Naive timestamps from PostgreSQL TIMESTAMP columns are treated as
    Asia/Kolkata wall-clock (matches NOW() when DB/session uses IST).
    """
    if not value:
        return None
    if isinstance(value, datetime):
        dt = value
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=IST)
        else:
            dt = dt.astimezone(IST)
        return dt.isoformat()
    text = str(value).strip()
    return text or None
