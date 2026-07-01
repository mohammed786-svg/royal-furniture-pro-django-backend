from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

UTC = timezone.utc
# India Standard Time — fixed UTC+5:30 (no DST). stdlib-only for Python 3.8 VPS.
IST = timezone(timedelta(hours=5, minutes=30))


def serialize_datetime(value: Any) -> Optional[str]:
    """
    Serialize DB datetimes for JSON APIs in Asia/Kolkata (ISO 8601 with offset).

    PostgreSQL TIMESTAMP WITHOUT TIME ZONE + session timezone UTC stores naive UTC.
    Example: order at 11:10 PM IST is stored as 17:40 naive UTC → emitted as 23:10+05:30.
    """
    if not value:
        return None
    if isinstance(value, datetime):
        dt = value
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC).astimezone(IST)
        else:
            dt = dt.astimezone(IST)
        return dt.isoformat()
    text = str(value).strip()
    return text or None
