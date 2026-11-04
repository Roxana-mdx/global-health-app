"""Incarca fisierul IHME GBD 2023 (endometrioza) in baza de date.

Rulare (din folderul proiectului, cu (.venv) activ):
    python -m etl.load_ihme
"""
from pathlib import Path

import pandas as pd
import pycountry
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.database import SessionLocal
from app.models import Country, ImportLog, Indicator, Observation, Source

CSV_FILE = Path("data/raw/IHME-GBD_2023_DATA-86b4db69-1.csv")
SOURCE_NAME = "IHME GBD 2023"
SOURCE_URL = "https://vizhub.healthdata.org/gbd-results/"
SEX = "FMLE"  # endometrioza apare doar la femei
BATCH = 5000

# Numele IHME care difera de cele din pycountry -> cod ISO3
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

MEASURES = {
    "Incidence": ("INC", "Incidence"),
    "Prevalence": ("PREV", "Prevalence"),
    "YLDs (Years Lived with Disability)": ("YLD", "YLDs"),
}
# (metric, age) -> (sufix cod, descriere, unitate)
VARIANTS = {
    ("Number", "All ages"): ("NUM", "number, all ages", "number"),
    ("Rate", "All ages"): ("RATE", "crude rate, all ages", "per 100,000"),
    ("Rate", "Age-standardized"): ("ASR", "age-standardized rate", "per 100,000"),
}
NUMBER_UNITS = {"INC": "cases", "PREV": "cases", "YLD": "years"}


def iso3_for(name):
    """Returneaza codul ISO3 pentru un nume de tara, sau None daca nu-l gaseste."""
    if name in ISO3_EXCEPTIONS:
        return ISO3_EXCEPTIONS[name]
    try:
        return pycountry.countries.lookup(name).alpha_3
    except LookupError:
        return None


def prepare(df):
    """Adauga coloanele iso3 si indicator_code. Returneaza (df, nume_nerecunoscute)."""
    names = sorted(df["location_name"].unique())
    iso_map = {n: iso3_for(n) for n in names}
    missing = [n for n, code in iso_map.items() if code is None]

    df = df.copy()
    df["iso3"] = df["location_name"].map(iso_map)
    df["indicator_code"] = [
        f"ENDO_{MEASURES[m][0]}_{VARIANTS[(me, a)][0]}"
        for m, me, a in zip(df["measure_name"], df["metric_name"], df["age_name"])
    ]
    return df, missing


def indicator_rows(df):
    """Lista de indicatori distincti (cod, nume, unitate, masura, metrica, varsta)."""
    rows = {}
    combos = df[["measure_name", "metric_name", "age_name"]].drop_duplicates()
    for m, me, a in combos.itertuples(index=False):
        short, label = MEASURES[m]
        suffix, descr, unit = VARIANTS[(me, a)]
        if suffix == "NUM":
            unit = NUMBER_UNITS[short]
        code = f"ENDO_{short}_{suffix}"
        rows[code] = dict(
            code=code,
            name=f"Endometriosis - {label} ({descr})",
            unit=unit,
            measure=label,
            metric=me,
            age_group=a,
        )
    return list(rows.values())


def main():
    df = pd.read_csv(CSV_FILE, encoding="utf-8")
    print(f"Citit {len(df)} randuri din {CSV_FILE}")

    df, missing = prepare(df)
    if missing:
        print("\nNu am gasit cod ISO3 pentru aceste nume. Adauga-le in ISO3_EXCEPTIONS:")
        for n in missing:
            print("  -", n)
        return

    with SessionLocal() as db:
        # 1. sursa
        source = db.scalar(select(Source).where(Source.name == SOURCE_NAME))
        if source is None:
            source = Source(name=SOURCE_NAME, url=SOURCE_URL)
            db.add(source)
            db.flush()

        # 2. tarile (inserare sau actualizare)
        countries = df[["iso3", "location_id", "location_name"]].drop_duplicates()
        for iso3, loc_id, name in countries.itertuples(index=False):
            iso2 = pycountry.countries.get(alpha_3=iso3).alpha_2
            stmt = insert(Country).values(
                iso3=iso3, iso2=iso2, gbd_location_id=int(loc_id), name=name
            )
            db.execute(stmt.on_conflict_do_update(
                index_elements=["iso3"],
                set_={"iso2": iso2, "gbd_location_id": int(loc_id), "name": name},
            ))

        # 3. indicatorii
        ids = {}
        for row in indicator_rows(df):
            ind = db.scalar(select(Indicator).where(Indicator.code == row["code"]))
            if ind is None:
                ind = Indicator(source_id=source.source_id, **row)
                db.add(ind)
                db.flush()
            ids[row["code"]] = ind.indicator_id

        # 4. observatiile (in loturi; upsert = fara duplicate la reimport)
        obs = pd.DataFrame({
            "country_iso3": df["iso3"],
            "indicator_id": df["indicator_code"].map(ids),
            "year": df["year"],
            "sex": SEX,
            "value": df["val"],
            "lower": df["lower"],
            "upper": df["upper"],
        })
        obs = obs.astype(object).where(obs.notna(), None)
        records = obs.to_dict("records")
        for i in range(0, len(records), BATCH):
            stmt = insert(Observation).values(records[i:i + BATCH])
            db.execute(stmt.on_conflict_do_update(
                constraint="uq_observation",
                set_={"value": stmt.excluded.value,
                      "lower": stmt.excluded.lower,
                      "upper": stmt.excluded.upper},
            ))
            print(f"  incarcat {min(i + BATCH, len(records))} / {len(records)}")

        # 5. jurnalul importului
        counts = df.groupby("indicator_code").size()
        for code, n in counts.items():
            db.add(ImportLog(
                source_name=SOURCE_NAME,
                indicator_code=code,
                url=f"{SOURCE_URL} ({CSV_FILE.name})",
                rows_loaded=int(n),
            ))

        db.commit()
    print("Import terminat.")


if __name__ == "__main__":
    main()