"""Load step: writes cleaned data to PostgreSQL with idempotent upserts."""
from __future__ import annotations

import logging

import pandas as pd
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models import Country, ImportLog, Indicator, Observation, Source

logger = logging.getLogger(__name__)

# PostgreSQL allows at most 65,535 parameters per statement; 8 columns x 5,000 rows is safe.
CHUNK_SIZE = 5_000


def _records(df: pd.DataFrame, columns: list[str]) -> list[dict]:
    """DataFrame -> list of dicts with plain Python values (NaN becomes None)."""
    part = df[columns].astype(object)
    part = part.where(part.notna(), None)
    return part.to_dict("records")


def get_or_create_source(session: Session, name: str, url: str | None = None) -> int:
    """Return the id of the source with this name, creating it if needed."""
    source = session.scalar(select(Source).where(Source.name == name))
    if source is None:
        source = Source(name=name, url=url)
        session.add(source)
        session.flush()
    return source.source_id


def get_or_create_indicator(
    session: Session,
    code: str,
    name: str,
    unit: str | None,
    source_id: int,
    *,
    measure: str | None = None,
    metric: str | None = None,
    age_group: str | None = None,
) -> int:
    """Return the id of the indicator with this code, creating or refreshing it."""
    indicator = session.scalar(select(Indicator).where(Indicator.code == code))
    if indicator is None:
        indicator = Indicator(code=code, source_id=source_id)
        session.add(indicator)
    indicator.name = name
    indicator.unit = unit
    indicator.measure = measure
    indicator.metric = metric
    indicator.age_group = age_group
    indicator.source_id = source_id
    session.flush()
    return indicator.indicator_id


def upsert_countries(session: Session, countries: pd.DataFrame) -> int:
    """Insert countries or update the columns present in ``countries`` (key: iso3).

    Columns that the table has but the DataFrame lacks are left untouched, so the
    World Bank import (region, income group) and the IHME import (gbd_location_id)
    can each fill in their own part of the same row.
    """
    columns = [c for c in countries.columns if c in Country.__table__.columns.keys()]
    rows = _records(countries.drop_duplicates("iso3"), columns)
    if not rows:
        return 0
    stmt = insert(Country).values(rows)
    update_cols = [c for c in columns if c != "iso3"]
    stmt = stmt.on_conflict_do_update(
        index_elements=["iso3"],
        set_={c: getattr(stmt.excluded, c) for c in update_cols},
    )
    session.execute(stmt)
    return len(rows)


def upsert_observations(
    session: Session, cleaned: pd.DataFrame, indicator_id: int, chunk_size: int = CHUNK_SIZE
) -> int:
    """Insert observations; on the natural key, update the existing row instead."""
    if cleaned.empty:
        return 0
    data = cleaned.assign(indicator_id=indicator_id)
    rows = _records(
        data,
        ["country_iso3", "indicator_id", "year", "sex", "value", "lower", "upper", "is_outlier"],
    )
    for start in range(0, len(rows), chunk_size):
        stmt = insert(Observation).values(rows[start : start + chunk_size])
        stmt = stmt.on_conflict_do_update(
            constraint="uq_observation",
            set_={
                "value": stmt.excluded.value,
                "lower": stmt.excluded.lower,
                "upper": stmt.excluded.upper,
                "is_outlier": stmt.excluded.is_outlier,
                "imported_at": func.now(),
            },
        )
        session.execute(stmt)
    return len(rows)


def log_import(
    session: Session, source_name: str, indicator_code: str, url: str, rows_loaded: int
) -> None:
    """Write one row to import_log."""
    session.add(
        ImportLog(
            source_name=source_name,
            indicator_code=indicator_code,
            url=url,
            rows_loaded=rows_loaded,
        )
    )
