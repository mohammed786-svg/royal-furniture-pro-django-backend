from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

# India Standard Time — fixed UTC+5:30 (no DST). stdlib-only for Python 3.8 VPS.
IST = timezone(timedelta(hours=5, minutes=30))


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
