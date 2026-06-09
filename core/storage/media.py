"""Local VPS media storage paths — served by NGINX."""
from pathlib import Path

from django.conf import settings

MEDIA_SUBDIRS = (
    "products",
    "categories",
    "banners",
    "payments",
    "customers",
    "documents",
)


def ensure_media_dirs() -> None:
    root = Path(settings.MEDIA_ROOT)
    for sub in MEDIA_SUBDIRS:
        (root / sub).mkdir(parents=True, exist_ok=True)


def media_path(subdir: str, filename: str) -> Path:
    if subdir not in MEDIA_SUBDIRS:
        raise ValueError(f"Invalid media subdir: {subdir}")
    return Path(settings.MEDIA_ROOT) / subdir / filename
