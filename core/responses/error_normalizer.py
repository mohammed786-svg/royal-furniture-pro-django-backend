"""Normalize validation / DRF errors into a consistent field format."""
from __future__ import annotations

from typing import Any


def normalize_errors(errors: Any) -> list[dict[str, str]] | None:
    if errors is None:
        return None

    if isinstance(errors, list):
        if not errors:
            return None
        normalized: list[dict[str, str]] = []
        for item in errors:
            if isinstance(item, dict) and "field" in item and "message" in item:
                normalized.append(
                    {"field": str(item["field"]), "message": str(item["message"])},
                )
            else:
                normalized.append({"field": "_", "message": str(item)})
        return normalized

    if isinstance(errors, dict):
        normalized = []
        for field, value in errors.items():
            if isinstance(value, list):
                for message in value:
                    normalized.append({"field": str(field), "message": str(message)})
            elif isinstance(value, dict):
                for nested_field, nested_value in value.items():
                    nested_messages = (
                        nested_value if isinstance(nested_value, list) else [nested_value]
                    )
                    for message in nested_messages:
                        normalized.append(
                            {
                                "field": f"{field}.{nested_field}",
                                "message": str(message),
                            },
                        )
            else:
                normalized.append({"field": str(field), "message": str(value)})
        return normalized or None

    return [{"field": "_", "message": str(errors)}]
