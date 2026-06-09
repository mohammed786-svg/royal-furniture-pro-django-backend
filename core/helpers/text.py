"""Text helpers for API payloads and DB storage."""
from __future__ import annotations

import re
import uuid
from typing import Any, Optional

from django.utils.text import slugify


def to_db_text(value: Any, *, default: str = "NA") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text or default


def from_db_text(value: Any) -> Optional[str]:
    if value in (None, "", "NA"):
        return None
    return str(value)


def make_slug(value: str, *, fallback: str = "item") -> str:
    base = slugify(value) or fallback
    return base[:120]


def unique_slug(base: str, exists_fn) -> str:
    candidate = base
    suffix = 1
    while exists_fn(candidate):
        candidate = f"{base}-{suffix}"
        suffix += 1
    return candidate


def save_base64_image(data: str, *, subdir: str, prefix: str) -> str:
    import base64
    from pathlib import Path

    from django.conf import settings

    from core.storage.media import ensure_media_dirs

    ensure_media_dirs()

    match = re.match(r"^data:(image/[\w.+-]+);base64,(.+)$", data)
    if match:
        content_type = match.group(1)
        raw = match.group(2)
        ext = content_type.split("/")[-1].replace("jpeg", "jpg")
    else:
        raw = data
        ext = "jpg"

    binary = base64.b64decode(raw)
    filename = f"{prefix}-{uuid.uuid4().hex[:12]}.{ext}"
    folder = Path(settings.MEDIA_ROOT) / subdir
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / filename
    path.write_bytes(binary)
    return f"{settings.MEDIA_URL.rstrip('/')}/{subdir}/{filename}"
