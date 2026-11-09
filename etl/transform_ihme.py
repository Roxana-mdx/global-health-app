"""Turn the IHME GBD CSV into the normalized table (no download here)."""
from pathlib import Path

import pandas as pd
import pycountry

COLUMNS = ["country_iso3", "indicator_code", "year", "sex", "value", "lower", "upper"]
REQUIRED = [
    "location_id", "location_name", "sex_name", "measure_name",
    "metric_name", "age_name", "year", "val", "upper", "lower",
]

# IHME location names that pycountry does not recognize -> ISO3 code
ISO3_EXCEPTIONS = {
    "Bolivia (Plurinational State of)": "BOL",
    "Brunei Darussalam": "BRN",
    "Cabo Verde": "CPV",
    "Congo": "COG",
    "Democratic Republic of the Congo": "COD",
    "Côte d'Ivoire": "CIV",
    "Democratic People's Republic of Korea": "PRK",
    "Republic of Korea": "KOR",
    "Republic of Moldova": "MDA",
    "Iran (Islamic Republic of)": "IRN",
    "Lao People's Democratic Republic": "LAO",
    "Micronesia (Federated States of)": "FSM",
    "Palestine": "PSE",
    "Russian Federation": "RUS",
    "Syrian Arab Republic": "SYR",
    "Taiwan": "TWN",
    "Türkiye": "TUR",
    "United Republic of Tanzania": "TZA",
    "United States Virgin Islands": "VIR",
    "United States of America": "USA",
    "Venezuela (Bolivarian Republic of)": "VEN",
    "Viet Nam": "VNM",
}

SEX_CODES = {"Female": "FMLE", "Male": "MLE", "Both": "BTSX"}

# IHME measure -> (code part, short name)
MEASURES = {
    "Incidence": ("INC", "Incidence"),
    "Prevalence": ("PREV", "Prevalence"),
    "YLDs (Years Lived with Disability)": ("YLD", "YLDs"),
}
# (metric, age group) -> (code part, description, unit)
VARIANTS = {
    ("Number", "All ages"): ("NUM", "number, all ages", "number"),
    ("Rate", "All ages"): ("RATE", "crude rate, all ages", "per 100,000"),
    ("Rate", "Age-standardized"): ("ASR", "age-standardized rate", "per 100,000"),
}
NUMBER_UNITS = {"INC": "cases", "PREV": "cases", "YLD": "years"}


def _build_indicators() -> dict[str, dict]:
    """The 9 IHME indicators: code -> name, unit, measure, metric, age group."""
    indicators = {}
    for short, label in MEASURES.values():
        for (metric, age), (suffix, descr, unit) in VARIANTS.items():
            if suffix == "NUM":
                unit = NUMBER_UNITS[short]
            indicators[f"ENDO_{short}_{suffix}"] = {
                "name": f"Endometriosis - {label} ({descr})",
                "unit": unit,
                "measure": label,
                "metric": metric,
                "age_group": age,
            }
    return indicators


INDICATORS = _build_indicators()


def iso3_for(name: str) -> str | None:
    """ISO3 code for a location name, or None if it is not recognized."""
    if name in ISO3_EXCEPTIONS:
        return ISO3_EXCEPTIONS[name]
    try:
        return pycountry.countries.lookup(name).alpha_3
    except LookupError:
        return None


def _read(path: Path) -> pd.DataFrame:
    raw = pd.read_csv(path, encoding="utf-8")
    missing = [column for column in REQUIRED if column not in raw.columns]
    if missing:
        raise ValueError(f"{path}: missing columns {missing}")
    return raw


def _iso3_map(raw: pd.DataFrame) -> dict[str, str]:
    mapping = {name: iso3_for(name) for name in sorted(raw["location_name"].unique())}
    unknown = [name for name, code in mapping.items() if code is None]
    if unknown:
        raise ValueError(
            "No ISO3 code for these locations; add them to ISO3_EXCEPTIONS: "
            + ", ".join(unknown)
        )
    return mapping


def transform_ihme_file(path: Path) -> pd.DataFrame:
    """IHME CSV -> table with the normalized columns (plus lower and upper)."""
    raw = _read(path)
    iso3 = _iso3_map(raw)

    unknown_sex = set(raw["sex_name"]) - set(SEX_CODES)
    if unknown_sex:
        raise ValueError(f"{path}: unknown sex values {sorted(unknown_sex)}")

    codes = []
    for measure, metric, age in zip(raw["measure_name"], raw["metric_name"], raw["age_name"]):
        if measure not in MEASURES or (metric, age) not in VARIANTS:
            raise ValueError(f"{path}: unexpected combination {measure!r}, {metric!r}, {age!r}")
        codes.append(f"ENDO_{MEASURES[measure][0]}_{VARIANTS[(metric, age)][0]}")

    return pd.DataFrame(
        {
            "country_iso3": raw["location_name"].map(iso3),
            "indicator_code": codes,
            "year": raw["year"],
            "sex": raw["sex_name"].map(SEX_CODES),
            "value": raw["val"],
            "lower": raw["lower"],
            "upper": raw["upper"],
        },
        columns=COLUMNS,
    )


def transform_ihme_locations(path: Path) -> pd.DataFrame:
    """IHME CSV -> country list: iso3, iso2, gbd_location_id, name."""
    raw = _read(path)
    iso3 = _iso3_map(raw)
    locations = raw[["location_id", "location_name"]].drop_duplicates()
    out = pd.DataFrame(
        {
            "iso3": locations["location_name"].map(iso3),
            "gbd_location_id": locations["location_id"],
            "name": locations["location_name"],
        }
    )
    out["iso2"] = [pycountry.countries.get(alpha_3=code).alpha_2 for code in out["iso3"]]
    return out[["iso3", "iso2", "gbd_location_id", "name"]].reset_index(drop=True)
