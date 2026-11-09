"""Import the IHME GBD file saved in data/raw/ihme/.

Run after etl.import_worldbank (it loads the country table):
    python -m etl.import_ihme
"""
from __future__ import annotations

import logging
import sys

from sqlalchemy import select, update
from sqlalchemy.exc import SQLAlchemyError

from app.database import SessionLocal
from app.models import Country
from etl.clean import clean_observations
from etl.extract_ihme import SOURCE_URL, locate_ihme_csv
from etl.load import (
    get_or_create_indicator,
    get_or_create_source,
    log_import,
    upsert_observations,
)
from etl.transform_ihme import INDICATORS, transform_ihme_file, transform_ihme_locations

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

SOURCE_NAME = "IHME GBD 2023"


def main() -> None:
    failed: list[str] = []
    with SessionLocal() as session:
        valid_iso3 = set(session.scalars(select(Country.iso3)))
        if not valid_iso3:
            sys.exit("The country table is empty. Run: python -m etl.import_worldbank")

        path, url = locate_ihme_csv()
        source_id = get_or_create_source(session, SOURCE_NAME, SOURCE_URL)

        # Add the GBD location id to the countries that already exist (other locations are skipped).
        locations = transform_ihme_locations(path)
        known = locations[locations["iso3"].isin(valid_iso3)]
        for iso3, gbd_id in zip(known["iso3"], known["gbd_location_id"]):
            session.execute(
                update(Country).where(Country.iso3 == iso3).values(gbd_location_id=int(gbd_id))
            )
        session.commit()
        print(f"IHME locations matched to countries: {len(known)} of {len(locations)}")

        everything = transform_ihme_file(path)
        for code, meta in INDICATORS.items():
            try:
                raw = everything[everything["indicator_code"] == code]
                cleaned = clean_observations(raw, valid_iso3)
                indicator_id = get_or_create_indicator(
                    session, code, meta["name"], meta["unit"], source_id,
                    measure=meta["measure"], metric=meta["metric"], age_group=meta["age_group"],
                )
                loaded = upsert_observations(session, cleaned, indicator_id)
                log_import(session, SOURCE_NAME, code, url, loaded)
                session.commit()
                print(f"{code:<22} raw={len(raw):>6}  clean={len(cleaned):>6}  loaded={loaded:>6}")
            except (ValueError, OSError, SQLAlchemyError):
                session.rollback()
                logger.exception("%s: import failed", code)
                failed.append(code)

    if failed:
        sys.exit(f"import failed for: {', '.join(failed)}")


if __name__ == "__main__":
    main()
