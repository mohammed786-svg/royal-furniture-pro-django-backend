"""Input sanitization helpers."""
import html
import re


def sanitize_string(value: str, max_length: int = 500) -> str:
    if not isinstance(value, str):
        return ""
    cleaned = html.escape(value.strip())
    return cleaned[:max_length]


def sanitize_sql_identifier(identifier: str) -> str:
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", identifier):
        raise ValueError("Invalid SQL identifier")
    return identifier
