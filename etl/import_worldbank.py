"""Import the World Bank files saved by etl.extract_worldbank.

Run first: it loads the country table that the IHME import relies on.
    python -m etl.import_worldbank
"""
from __future__ import annotations

import logging

from sqlalchemy.exc import SQLAlchemyError

from app.database import SessionLocal
from etl.extract_worldbank import API, DEFAULT_RAW_DIR
from etl.import_runner import (
    IndicatorSpec,
    SourceSpec,
    import_for_loaded_countries,
    report_and_exit_on_failure,
)
from etl.load import upsert_countries
from etl.step_result import StepResult
from etl.transform_worldbank import transform_worldbank_countries, transform_worldbank_file

logger = logging.getLogger(__name__)

SOURCE = SourceSpec(name="World Bank Indicators API", url=API, raw_dir=DEFAULT_RAW_DIR)
YEARS = "1990-2023"


def _spec(code: str, name: str, unit: str) -> IndicatorSpec:
    return IndicatorSpec(
        code=code,
        remote_id=code,
        name=name,
        unit=unit,
        raw_filename=f"{code}_{YEARS}.json",
        request_url=f"{API}/country/all/indicator/{code}",
    )


INDICATORS = (
    _spec("NY.GDP.PCAP.CD", "GDP per capita (current US$)", "current US$"),
    _spec("SH.XPD.CHEX.GD.ZS", "Current health expenditure (% of GDP)", "% of GDP"),
    _spec("SH.XPD.CHEX.PC.CD", "Current health expenditure per capita (current US$)", "current US$"),
    _spec("SP.DYN.TFRT.IN", "Fertility rate, total (births per woman)", "births per woman"),
)


def import_all() -> list[StepResult]:
    """Load the country table, then every indicator; one result per step."""
    try:
        countries = transform_worldbank_countries(SOURCE.raw_dir / "countries.json")
        with SessionLocal() as session:
            count = upsert_countries(session, countries)
            session.commit()
    except (ValueError, OSError, SQLAlchemyError) as error:
        logger.exception("countries: import failed")
        return [StepResult.from_error(SOURCE.name, "countries", error)]
    return [
        StepResult.ok(SOURCE.name, "countries", f"upserted={count}"),
        *import_for_loaded_countries(SOURCE, INDICATORS, transform_worldbank_file),
    ]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    report_and_exit_on_failure(import_all())
