"""Import the IHME GBD file saved in data/raw/ihme/.

Run after etl.import_worldbank (it loads the country table):
    python -m etl.import_ihme
"""
from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.models import Country
from etl.extract_ihme import DEFAULT_RAW_DIR, SOURCE_URL, locate_ihme_csv
from etl.import_runner import (
    IndicatorSpec,
    SourceSpec,
    import_for_loaded_countries,
    report_and_exit_on_failure,
)
from etl.step_result import StepResult
from etl.transform_ihme import INDICATORS, transform_ihme_file, transform_ihme_locations

logger = logging.getLogger(__name__)

SOURCE = SourceSpec(name="IHME GBD 2023", url=SOURCE_URL, raw_dir=DEFAULT_RAW_DIR)


def _transform(path: Path, code: str) -> pd.DataFrame:
    """The rows of one indicator (one CSV file holds all nine)."""
    everything = transform_ihme_file(path)
    return everything[everything["indicator_code"] == code]


def import_all() -> list[StepResult]:
    """Import the nine IHME indicators; one result per step."""
    try:
        path, url = locate_ihme_csv()
    except (ValueError, OSError) as error:
        logger.exception("IHME file not found")
        return [StepResult.from_error(SOURCE.name, "IHME CSV", error)]

    indicators = tuple(
        IndicatorSpec(
            code=code,
            remote_id=code,
            name=meta["name"],
            unit=meta["unit"],
            raw_filename=path.name,
            request_url=url,
            measure=meta["measure"],
            metric=meta["metric"],
            age_group=meta["age_group"],
        )
        for code, meta in INDICATORS.items()
    )

    def add_gbd_ids(session: Session, valid_iso3: set[str]) -> str:
        """Set the GBD location id on the countries that exist (other locations are skipped)."""
        locations = transform_ihme_locations(path)
        known = locations[locations["iso3"].isin(valid_iso3)]
        for iso3, gbd_id in zip(known["iso3"], known["gbd_location_id"]):
            session.execute(
                update(Country).where(Country.iso3 == iso3).values(gbd_location_id=int(gbd_id))
            )
        return f"matched {len(known)} of {len(locations)} IHME locations"

    return import_for_loaded_countries(SOURCE, indicators, _transform, before=add_gbd_ids)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    report_and_exit_on_failure(import_all())
