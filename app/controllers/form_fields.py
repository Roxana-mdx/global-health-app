"""Helpers that turn the text fields of a form into clean values."""
from __future__ import annotations


def blank_to_none(value: str | None) -> str | None:
    """A browser sends an untouched field as an empty string: treat it as "no filter"."""
    if value is None:
        return None
    value = value.strip()
    return value or None


def to_int_or_none(value: str | None) -> int | None:
    """Years arrive as text; blank or invalid values are ignored instead of failing."""
    cleaned = blank_to_none(value)
    if cleaned is None:
        return None
    try:
        return int(cleaned)
    except ValueError:
        return None