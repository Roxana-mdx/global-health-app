"""Cleaning step: turns a transformed table into rows that are safe to store."""
from __future__ import annotations

import logging
from typing import Iterable, NamedTuple

import pandas as pd

from app.models import Sex

logger = logging.getLogger(__name__)

_KEY_COLUMNS = ["country_iso3", "indicator_code", "year", "sex"]

# Harmonize sex codes: our three codes map to themselves, a few common spellings are added.
_SEX_MAP = {s.value: s.value for s in Sex} | {
    "BOTH": Sex.BOTH.value,
    "MALE": Sex.MALE.value,
    "FEMALE": Sex.FEMALE.value,
}
_VALID_SEX = set(_SEX_MAP.values())


class _Bounds(NamedTuple):
    low: float
    high: float
    low_inclusive: bool = True


# Plausible limits per indicator. A value outside them is an error, not an outlier.
_INDICATOR_BOUNDS: dict[str, _Bounds] = {
    # IHME counts (cases / years lived with disability): never negative
    "ENDO_INC_NUM": _Bounds(0, 1_000_000_000),
    "ENDO_PREV_NUM": _Bounds(0, 1_000_000_000),
    "ENDO_YLD_NUM": _Bounds(0, 1_000_000_000),
    # IHME rates per 100,000 people
    "ENDO_INC_RATE": _Bounds(0, 100_000),
    "ENDO_PREV_RATE": _Bounds(0, 100_000),
    "ENDO_YLD_RATE": _Bounds(0, 100_000),
    "ENDO_INC_ASR": _Bounds(0, 100_000),
    "ENDO_PREV_ASR": _Bounds(0, 100_000),
    "ENDO_YLD_ASR": _Bounds(0, 100_000),
    # World Bank: exactly 0 is not a real measurement, so the lower bound is exclusive
    "NY.GDP.PCAP.CD": _Bounds(0, 500_000, low_inclusive=False),
    "SH.XPD.CHEX.GD.ZS": _Bounds(0, 100, low_inclusive=False),
    "SH.XPD.CHEX.PC.CD": _Bounds(0, 50_000, low_inclusive=False),
    "SP.DYN.TFRT.IN": _Bounds(0, 10, low_inclusive=False),
}


def _drop(cleaned: pd.DataFrame, mask: pd.Series, reason: str) -> pd.DataFrame:
    """Drop the rows where ``mask`` is true, logging how many."""
    dropped = int(mask.sum())
    if dropped:
        logger.info("dropped %d observation rows: %s", dropped, reason)
    return cleaned[~mask]


def _out_of_bounds(df: pd.DataFrame) -> pd.Series:
    """True for rows whose value is outside the bounds of their indicator."""
    bad = pd.Series(False, index=df.index)
    for code, b in _INDICATOR_BOUNDS.items():
        is_code = df["indicator_code"] == code
        below = df["value"] < b.low if b.low_inclusive else df["value"] <= b.low
        bad |= is_code & (below | (df["value"] > b.high))
    return bad


def clean_observations(
    raw: pd.DataFrame,
    valid_iso3: Iterable[str],
    year_window: tuple[int, int] = (1990, 2023),
) -> pd.DataFrame:
    """Apply all cleaning rules and return the rows to store."""
    cleaned = raw.copy()

    # Standardizing identifiers
    cleaned["country_iso3"] = cleaned["country_iso3"].astype("string").str.strip().str.upper()
    cleaned["indicator_code"] = cleaned["indicator_code"].astype("string").str.strip()

    # Filtering to valid entities (drops regions and aggregates)
    cleaned = _drop(
        cleaned, ~cleaned["country_iso3"].isin(set(valid_iso3)), "not a valid country code"
    )

    # Type conversion: invalid text becomes NaN
    cleaned["year"] = pd.to_numeric(cleaned["year"], errors="coerce")
    cleaned["value"] = pd.to_numeric(cleaned["value"], errors="coerce")
    for col in ("lower", "upper"):
        cleaned[col] = pd.to_numeric(cleaned[col], errors="coerce")

    # Missing values are dropped, never stored as 0
    cleaned = _drop(
        cleaned,
        cleaned["year"].isna() | cleaned["value"].isna(),
        "missing or non-numeric year/value",
    )
    # astype(int) would truncate 2010.5 to 2010 and overwrite the real 2010 row
    cleaned = _drop(cleaned, cleaned["year"] % 1 != 0, "year is not a whole number")
    cleaned["year"] = cleaned["year"].astype(int)

    # Year window
    low, high = year_window
    cleaned = _drop(
        cleaned, (cleaned["year"] < low) | (cleaned["year"] > high), "year outside the study window"
    )

    # Harmonizing categories: missing sex becomes BTSX, unknown codes are dropped
    cleaned["sex"] = (
        cleaned["sex"].astype("string").str.strip().str.upper()
        .fillna(Sex.BOTH.value)
        .replace(_SEX_MAP)
    )
    cleaned = _drop(cleaned, ~cleaned["sex"].isin(_VALID_SEX), "unknown sex code")

    # Range checks
    cleaned = _drop(cleaned, _out_of_bounds(cleaned), "value outside plausible bounds")

    # Deduplication on the natural key
    cleaned = _drop(
        cleaned,
        cleaned.duplicated(subset=_KEY_COLUMNS, keep="last"),
        "duplicate (country, indicator, year, sex); kept the last",
    )

    return cleaned.reset_index(drop=True)