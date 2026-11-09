"""Turn saved World Bank files into normalized tables (no download here)."""
from pathlib import Path

import pandas as pd

from etl.json_types import read_json_records, require_keys

COLUMNS = ["country_iso3", "indicator_code", "year", "sex", "value", "lower", "upper"]


def transform_worldbank_file(path: Path, code: str) -> pd.DataFrame:
    """Saved indicator file -> table with the normalized columns.

    Years and values are left as delivered; clean.py converts the types.
    World Bank has no sex split and no uncertainty interval, so those are empty.
    """
    rows = []
    for record in read_json_records(path):
        require_keys(record, ["countryiso3code", "date", "value"], str(path))
        rows.append(
            {
                "country_iso3": record["countryiso3code"],
                "indicator_code": code,
                "year": record["date"],
                "sex": None,
                "value": record["value"],
                "lower": None,
                "upper": None,
            }
        )
    return pd.DataFrame(rows, columns=COLUMNS)


def transform_worldbank_countries(path: Path) -> pd.DataFrame:
    """Saved country list -> iso3, iso2, name, region, income_group.

    Drops aggregates such as 'World' (region 'Aggregates').
    """
    rows = []
    for record in read_json_records(path):
        require_keys(
            record, ["id", "iso2Code", "name", "region", "incomeLevel"], str(path)
        )
        region = str(record["region"]["value"]).strip()
        if region == "Aggregates":
            continue
        rows.append(
            {
                "iso3": record["id"],
                "iso2": record["iso2Code"],
                "name": record["name"],
                "region": region,
                "income_group": str(record["incomeLevel"]["value"]).strip(),
            }
        )
    return pd.DataFrame(rows, columns=["iso3", "iso2", "name", "region", "income_group"])
