"""Structured logging helpers — extend for JSON log shipping."""
import logging


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
