"""Incarca indicatori World Bank (PIB, cheltuieli de sanatate, fertilitate) in baza de date.

Trebuie rulat DUPA etl.load_ihme (are nevoie de tabelul country).
Rulare (din folderul proiectului, cu (.venv) activ):
    python -m etl.load_worldbank
"""
import json
import time
from pathlib import Path

import requests
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert

from app.database import SessionLocal
from app.models import Country, ImportLog, Indicator, Observation, Source

API = "https://api.worldbank.org/v2"
SOURCE_NAME = "World Bank Indicators API"
RAW_DIR = Path("data/raw")
FIRST_YEAR, LAST_YEAR = 1990, 2023
SEX = "BTSX"  # valori pentru intreaga populatie
BATCH = 5000

# cod World Bank -> (nume, unitate)
INDICATORS = {
    "NY.GDP.PCAP.CD": ("GDP per capita", "current US$"),
    "SH.XPD.CHEX.GD.ZS": ("Current health expenditure", "% of GDP"),
    "SH.XPD.CHEX.PC.CD": ("Current health expenditure per capita", "current US$"),
    "SP.DYN.TFRT.IN": ("Fertility rate, total", "births per woman"),
}


def get_json(url, params):
    """Cere date de la API; reincearca de 3 ori daca apare o eroare de retea."""
    for attempt in range(3):
        try:
            response = requests.get(url, params=params, timeout=60)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as error:
            print(f"  eroare ({error}), reincerc...")
            time.sleep(2 ** attempt)
    raise RuntimeError(f"Nu pot descarca {url}")


def fetch_all(path, extra_params, cache_name):
    """Descarca toate paginile unui raspuns si le salveaza in data/raw/.

    Daca fisierul exista deja, il foloseste pe el (nu descarca a doua oara).
    Intoarce (lista de inregistrari, data ultimei actualizari la World Bank).
    """
    cache_file = RAW_DIR / cache_name
    if cache_file.exists():
        cached = json.loads(cache_file.read_text(encoding="utf-8"))
        print(f"  folosesc fisierul salvat {cache_file}")
        return cached["records"], cached["lastupdated"]

    params = {"format": "json", "per_page": 1000, **extra_params}
    records, page = [], 1
    while True:
        params["page"] = page
        data = get_json(f"{API}/{path}", params)
        if len(data) < 2:  # API-ul a raspuns cu un mesaj de eroare
            raise RuntimeError(f"Raspuns neasteptat de la API: {data}")
        meta, rows = data[0], data[1] or []
        records.extend(rows)
        if page >= meta["pages"]:
            break
        page += 1

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(
        json.dumps({"lastupdated": meta.get("lastupdated"), "records": records}),
        encoding="utf-8",
    )
    return records, meta.get("lastupdated")


def parse_observations(records, valid_iso3):
    """Pastreaza doar tarile din baza noastra (nu regiunile). Lipsa = None, nu 0."""
    out = []
    for r in records:
        iso3 = r.get("countryiso3code")
        if iso3 not in valid_iso3:
            continue
        year = int(r["date"])
        if not FIRST_YEAR <= year <= LAST_YEAR:
            continue
        out.append((iso3, year, r["value"]))
    return out


def get_or_create_source(db):
    source = db.scalar(select(Source).where(Source.name == SOURCE_NAME))
    if source is None:
        source = Source(name=SOURCE_NAME, url=API)
        db.add(source)
        db.flush()
    return source


def main():
    with SessionLocal() as db:
        valid = set(db.scalars(select(Country.iso3)))
        if not valid:
            print("Tabelul country este gol. Ruleaza mai intai: python -m etl.load_ihme")
            return

        source = get_or_create_source(db)

        # 1. regiunea si grupa de venit pentru fiecare tara
        print("Descarc lista de tari World Bank...")
        wb_countries, _ = fetch_all("country", {}, "worldbank_countries.json")
        updated = 0
        for c in wb_countries:
            if c["id"] in valid:
                db.execute(
                    update(Country)
                    .where(Country.iso3 == c["id"])
                    .values(region=c["region"]["value"].strip(),
                            income_group=c["incomeLevel"]["value"].strip())
                )
                updated += 1
        print(f"  regiune si grupa de venit completate pentru {updated} tari")

        # 2. indicatorii
        for code, (name, unit) in INDICATORS.items():
            print(f"Indicator {code} ({name})")
            records, lastupdated = fetch_all(
                f"country/all/indicator/{code}",
                {"date": f"{FIRST_YEAR}:{LAST_YEAR}"},
                f"worldbank_{code}.json",
            )

            ind = db.scalar(select(Indicator).where(Indicator.code == code))
            if ind is None:
                ind = Indicator(code=code, name=name, unit=unit,
                                source_id=source.source_id)
                db.add(ind)
                db.flush()

            rows = parse_observations(records, valid)
            payload = [
                {"country_iso3": iso3, "indicator_id": ind.indicator_id,
                 "year": year, "sex": SEX, "value": value}
                for iso3, year, value in rows
            ]
            for i in range(0, len(payload), BATCH):
                stmt = insert(Observation).values(payload[i:i + BATCH])
                db.execute(stmt.on_conflict_do_update(
                    constraint="uq_observation",
                    set_={"value": stmt.excluded.value},
                ))
            with_value = sum(1 for _, _, v in rows if v is not None)
            print(f"  {len(rows)} randuri ({with_value} cu valoare)")

            db.add(ImportLog(
                source_name=SOURCE_NAME,
                indicator_code=code,
                url=f"{API}/country/all/indicator/{code} (lastupdated {lastupdated})",
                rows_loaded=len(rows),
            ))

        db.commit()
    print("Import terminat.")


if __name__ == "__main__":
    main()