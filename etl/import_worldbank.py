"""Import the World Bank files saved by etl.extract_worldbank.

Run first: it loads the country table that the IHME import relies on.
    python -m etl.import_worldbank
"""
from __future__ import annotations

import logging
import sys

from sqlalchemy.exc import SQLAlchemyError

from app.database import SessionLocal
from etl.clean import clean_observations
from etl.extract_worldbank import API, DEFAULT_RAW_DIR
from etl.load import (
    get_or_create_indicator,
    get_or_create_source,
    log_import,
    upsert_countries,
    upsert_observations,
)
from etl.transform_worldbank import transform_worldbank_countries, transform_worldbank_file

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

SOURCE_NAME = "World Bank Indicators API"
RAW_DIR = DEFAULT_RAW_DIR
YEARS = "1990-2023"

# code, name, unit, saved file
INDICATORS = [
    ("NY.GDP.PCAP.CD", "GDP per capita (current US$)", "current US$", f"NY.GDP.PCAP.CD_{YEARS}.json"),
    ("SH.XPD.CHEX.GD.ZS", "Current health expenditure (% of GDP)", "% of GDP", f"SH.XPD.CHEX.GD.ZS_{YEARS}.json"),
    ("SH.XPD.CHEX.PC.CD", "Current health expenditure per capita (current US$)", "current US$", f"SH.XPD.CHEX.PC.CD_{YEARS}.json"),
    ("SP.DYN.TFRT.IN", "Fertility rate, total (births per woman)", "births per woman", f"SP.DYN.TFRT.IN_{YEARS}.json"),
]


def main() -> None:
    failed: list[str] = []
    with SessionLocal() as session:
        source_id = get_or_create_source(session, SOURCE_NAME, API)

        countries = transform_worldbank_countries(RAW_DIR / "countries.json")
        n = upsert_countries(session, countries)
        session.commit()
        print(f"countries upserted: {n}")
        valid_iso3 = set(countries["iso3"])

        for code, name, unit, filename in INDICATORS:
            path = RAW_DIR / filename
            if not path.exists():
                print(f"{code:<22} SKIP (missing {path.name})")
                continue
            try:
                raw = transform_worldbank_file(path, code)
                cleaned = clean_observations(raw, valid_iso3)
                indicator_id = get_or_create_indicator(session, code, name, unit, source_id)
                loaded = upsert_observations(session, cleaned, indicator_id)
                log_import(session, SOURCE_NAME, code, f"{API}/country/all/indicator/{code}", loaded)
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
