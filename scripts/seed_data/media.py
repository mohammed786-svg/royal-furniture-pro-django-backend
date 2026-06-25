"""Download and cache demo media files under MEDIA_ROOT."""
from __future__ import annotations

import hashlib
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from django.conf import settings

from core.storage.media import ensure_media_dirs

USER_AGENT = "RoyalFurniturePro-Seed/1.0"

# Stable remote placeholders (furniture-themed labels; cached locally after first fetch)
IMAGE_KEYS = (
    "sofa",
    "recliner",
    "bed",
    "dining",
    "chair",
    "table",
    "wardrobe",
    "decor",
    "outdoor",
    "mattress",
    "study",
    "living",
    "bedroom",
    "banner-hero",
    "banner-promo",
    "banner-offer",
    "feature",
    "person-1",
    "person-2",
    "person-3",
    "brand",
)


def _remote_url(key: str) -> str:
    label = key.replace("-", " ").title()
    # placehold.co — reliable for dev seeds; files are cached under MEDIA_ROOT
    return f"https://placehold.co/1200x800/EEE8DC/5C4A32/png?text={urllib.parse.quote(label)}"


IMAGE_SOURCES: dict[str, str] = {key: _remote_url(key) for key in IMAGE_KEYS}

# Smaller avatars for testimonials
IMAGE_SOURCES["person-1"] = "https://placehold.co/300x300/DCE6F0/2C3E50/png?text=PS"
IMAGE_SOURCES["person-2"] = "https://placehold.co/300x300/DCE6F0/2C3E50/png?text=RM"
IMAGE_SOURCES["person-3"] = "https://placehold.co/300x300/DCE6F0/2C3E50/png?text=AR"
IMAGE_SOURCES["feature"] = "https://placehold.co/400x400/F5F0E8/8B7355/png?text=Feature"
IMAGE_SOURCES["brand"] = "https://placehold.co/600x400/FFFFFF/8B1A1A/png?text=Royal+Furniture+Pro"


def media_url(subdir: str, filename: str) -> str:
    return f"{settings.MEDIA_URL.rstrip('/')}/{subdir}/{filename}"


def _write_minimal_jpeg(dest: Path) -> None:
    """1×1 JPEG — last-resort if remote download fails."""
    dest.write_bytes(
        bytes.fromhex(
            "ffd8ffe000104a46494600010100000100010000ffdb004300080606070605080707"
            "070909080a0c140d0c0b0b0c1912130f141d1a1f1e1d1a1c1c20242e2720222c"
            "231c1c2837292c30313434341f27393d38323c2e333432ffdb0043010909090c"
            "0b0c180d0d1832211c2132323232323232323232323232323232323232323232"
            "3232323232323232323232323232323232323232323232ffc00011080001000103"
            "011100021101031101ffc4001500010100000000000000000000000000000008"
            "ffc40014100100000000000000000000000000000000ffda000c03010002110311"
            "003f00aaffd9"
        )
    )


def download_image(key: str, *, subdir: str, skip_download: bool = False) -> str:
    """Return local /media/... path; download once and cache on disk."""
    ensure_media_dirs()
    source = IMAGE_SOURCES.get(key)
    if not source:
        source = _remote_url(key)

    ext = "png" if ".png" in source else "jpg"
    digest = hashlib.md5(source.encode()).hexdigest()[:10]
    filename = f"demo-{key}-{digest}.{ext}"
    dest = Path(settings.MEDIA_ROOT) / subdir / filename

    if not dest.exists() and not skip_download:
        req = urllib.request.Request(source, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                dest.write_bytes(resp.read())
        except (urllib.error.URLError, TimeoutError, OSError):
            _write_minimal_jpeg(dest.with_suffix(".jpg"))
            dest = dest.with_suffix(".jpg")
            filename = dest.name

    return media_url(subdir, filename)


def prefetch_images(keys: list[str], *, subdir: str, skip_download: bool = False) -> dict[str, str]:
    paths: dict[str, str] = {}
    for key in keys:
        paths[key] = download_image(key, subdir=subdir, skip_download=skip_download)
    return paths
