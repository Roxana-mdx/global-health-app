"""The loop shared by the import scripts: transform -> clean -> load, one indicator at a time."""
from __future__ import annotations

import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence

import pandas as pd
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Country
from etl.clean import clean_observations
from etl.load import get_or_create_indicator, get_or_create_source, log_import, upsert_observations
from etl.step_result import StepResult

logger = logging.getLogger(__name__)

RAW_ROOT = Path("data/raw")

# Errors that are expected (bad data, missing files, database errors). Anything else is a bug.
EXPECTED_ERRORS = (ValueError, OSError, SQLAlchemyError)


@dataclass(frozen=True)
class SourceSpec:
    name: str
    url: str
    raw_dir: Path


@dataclass(frozen=True)
class IndicatorSpec:
    code: str
    remote_id: str
    name: str
    unit: str | None
    raw_filename: str
    request_url: str
    measure: str | None = None
    metric: str | None = None
    age_group: str | None = None


# (saved file, indicator code) -> normalized table
Transform = Callable[[Path, str], pd.DataFrame]
# Runs once before the indicators (e.g. to complete the country table); returns a short message.
BeforeHook = Callable[[Session, set[str]], str]


def import_indicators(
    session: Session,
    source: SourceSpec,
    source_id: int,
    indicators: Sequence[IndicatorSpec],
    transform: Transform,
    valid_iso3: set[str],
) -> list[StepResult]:
    """Import every indicator of one source; one result per indicator."""
    results: list[StepResult] = []
    for spec in indicators:
        path = source.raw_dir / spec.raw_filename
        if not path.exists():
            results.append(StepResult.skipped(source.name, spec.code, f"missing {path.name}"))
            continue
        try:
            raw = transform(path, spec.code)
            cleaned = clean_observations(raw, valid_iso3)
            indicator_id = get_or_create_indicator(
                session, spec.code, spec.name, spec.unit, source_id,
                measure=spec.measure, metric=spec.metric, age_group=spec.age_group,
            )
            loaded = upsert_observations(session, cleaned, indicator_id)
            log_import(session, source.name, spec.code, spec.request_url, loaded)
            session.commit()
            results.append(
                StepResult.ok(
                    source.name, spec.code,
                    f"raw={len(raw)}  clean={len(cleaned)}  loaded={loaded}",
                )
            )
        except EXPECTED_ERRORS as error:
            session.rollback()
            logger.exception("%s: import failed", spec.code)
            results.append(StepResult.from_error(source.name, spec.code, error))
    return results


def import_for_loaded_countries(
    source: SourceSpec,
    indicators: Sequence[IndicatorSpec],
    transform: Transform,
    *,
    before: BeforeHook | None = None,
) -> list[StepResult]:
    """Open a session, take the valid countries from the country table and import."""
    try:
        with SessionLocal() as session:
            valid_iso3 = set(session.scalars(select(Country.iso3)))
            if not valid_iso3:
                raise ValueError(
                    "The country table is empty. Import the World Bank data first."
                )
            source_id = get_or_create_source(session, source.name, source.url)
            results: list[StepResult] = []
            if before is not None:
                message = before(session, valid_iso3)
                session.commit()
                results.append(StepResult.ok(source.name, "countries", message))
            results.extend(
                import_indicators(session, source, source_id, indicators, transform, valid_iso3)
            )
            return results
    except EXPECTED_ERRORS as error:
        logger.exception("%s: import could not start", source.name)
        return [StepResult.from_error(source.name, "import", error)]


def report_and_exit_on_failure(results: Sequence[StepResult]) -> None:
    """Print one line per result; exit with an error if any step failed."""
    for result in results:
        print(f"{result.item:<22} {result.status.value:<8} {result.detail}")
    failed = [r.item for r in results if r.is_failed]
    if failed:
        sys.exit(f"failed: {', '.join(failed)}")
