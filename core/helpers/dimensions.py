from __future__ import annotations

import re
from typing import Any, Optional

from core.helpers.text import from_db_text

DIMENSION_UNITS = {
    "cm": 1.0,
    "inch": 2.54,
    "in": 2.54,
    "feet": 30.48,
    "ft": 30.48,
    "meter": 100.0,
    "m": 100.0,
}


def normalize_dimension_unit(unit: str) -> str:
    key = (unit or "cm").strip().lower()
    if key in {"inches", "inch", "in"}:
        return "inch"
    if key in {"feet", "foot", "ft"}:
        return "feet"
    if key in {"meter", "metre", "m"}:
        return "meter"
    return "cm"


def convert_to_cm(value: Any, unit: str = "cm") -> float:
    if value in (None, ""):
        return 0.0
    raw = from_db_text(value) if not isinstance(value, (int, float)) else value
    if isinstance(raw, str):
        raw = raw.strip()
        if not raw or raw.upper() in {"NA", "N/A"}:
            return 0.0
    try:
        numeric = float(raw)
    except (TypeError, ValueError):
        return 0.0
    factor = DIMENSION_UNITS.get(normalize_dimension_unit(unit), 1.0)
    return round(numeric * factor, 2)


def parse_dimension_payload(payload: dict[str, Any]) -> dict[str, float]:
    if any(k in payload for k in ("lengthCm", "breadthCm", "heightCm")):
        return {
            "length_cm": convert_to_cm(payload.get("lengthCm"), "cm"),
            "breadth_cm": convert_to_cm(payload.get("breadthCm"), "cm"),
            "height_cm": convert_to_cm(payload.get("heightCm"), "cm"),
        }
    unit = normalize_dimension_unit(str(payload.get("packageDimensionUnit") or "cm"))
    return {
        "length_cm": convert_to_cm(payload.get("packageLength"), unit),
        "breadth_cm": convert_to_cm(payload.get("packageBreadth"), unit),
        "height_cm": convert_to_cm(payload.get("packageHeight"), unit),
    }
