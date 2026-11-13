# Global Health Data Platform: burden of endometriosis, economic development and health spending, 1990–2023

Project for the course CSP in Global Health. The project stores country-level
estimates of the burden of endometriosis (IHME) together with economic and
health-system indicators (World Bank) in a PostgreSQL database, ready for a REST
API, analysis and machine learning in later labs.

- Lab 1: environment, PostgreSQL, schema, repository
- Lab 2: extracting, cleaning and storing the data (this version)

## Data

| Source | Content | How it is obtained |
|---|---|---|
| IHME GBD 2023 | Endometriosis (female): incidence, prevalence, YLDs; number, crude rate and age-standardized rate (9 indicators), 204 locations, 1990–2023 | CSV from the GBD Results tool (no API) |
| World Bank Indicators API | GDP per capita (`NY.GDP.PCAP.CD`), health expenditure % of GDP (`SH.XPD.CHEX.GD.ZS`) and per capita (`SH.XPD.CHEX.PC.CD`), fertility rate (`SP.DYN.TFRT.IN`), 1990–2023 | API, downloaded by `etl/extract_worldbank.py` |

Four IHME locations (Taiwan, Tokelau, Cook Islands, Niue) have no counterpart in
the World Bank country list and are excluded, so the database covers 200
countries and territories with endometriosis data. Health expenditure series
start in 2000 and are missing for 24 economies (mostly territories).

Citations:

- Global Burden of Disease Collaborative Network. Global Burden of Disease Study
  2023 (GBD 2023) Results. Seattle, United States: Institute for Health Metrics
  and Evaluation (IHME), 2024. https://vizhub.healthdata.org/gbd-results/
  (free for non-commercial use; commercial use requires a licence).
- World Bank. World Development Indicators, Indicators API.
  https://api.worldbank.org/v2 (health expenditure data originate from the WHO
  Global Health Expenditure Database).

## Setup

1. Install Python 3.12 and PostgreSQL 18.
2. Create the user and database (in psql or pgAdmin):

       CREATE USER gh_user WITH PASSWORD 'gh_pass';
       CREATE DATABASE global_health OWNER gh_user ENCODING 'UTF8';

3. Create a virtual environment and install the dependencies:

       py -3.12 -m venv .venv
       .venv\Scripts\activate
       pip install -r requirements.txt

4. Create a `.env` file in the project root (it is not in Git):

       DATABASE_URL=postgresql+psycopg://gh_user:gh_pass@localhost:5432/global_health

5. Create the tables and tell Alembic that the database is up to date:

       python -m app.create_tables
       alembic stamp head

   The tables are created from the current models, which already include the
   `is_outlier` column; `alembic stamp head` records that state. (An existing
   database from an earlier version is updated with `alembic upgrade head`.)

## Getting the data

Raw files go to `data/raw/` (not in Git).

**IHME.** Request the data in the GBD Results tool
(https://vizhub.healthdata.org/gbd-results/): GBD Estimate = Cause of death or
injury; Measure = Incidence, Prevalence, YLDs; Metric = Number and Rate; Cause =
Endometriosis; Location = Countries and territories; Age = All ages and
Age-standardized; Sex = Female; Year = 1990–2023. Save the CSV as the only CSV
file in `data/raw/ihme/`.

**World Bank.** Run from the project root with the virtual environment active:

    python -c "from etl.extract_worldbank import download_worldbank_countries, download_worldbank_indicator; download_worldbank_countries(); [download_worldbank_indicator(c) for c in ('NY.GDP.PCAP.CD','SH.XPD.CHEX.GD.ZS','SH.XPD.CHEX.PC.CD','SP.DYN.TFRT.IN')]"

The files are saved in `data/raw/worldbank/`. The extractors only download; they
raise `WorldBankApiError` instead of saving an unexpected response.

## Importing the data

Run from the project root, PostgreSQL running, in this order (the World Bank
import fills the `country` table that the IHME import needs):

    python -m etl.import_worldbank
    python -m etl.import_ihme

Each import prints one line per indicator with the number of raw, clean and
loaded rows, plus log lines with the number of rows each cleaning rule dropped.
The imports are idempotent (`INSERT ... ON CONFLICT DO UPDATE`): running them
again updates existing rows and creates no duplicates. Every import is recorded
in the `import_log` table.

Expected result after a full import: 84,670 rows in `observation` (9 x 6,800 IHME
rows and 23,470 World Bank rows).

## Cleaning rules (`etl/clean.py`)

Keep only valid countries; standardize identifiers; convert types; drop missing
values (never stored as 0); drop fractional years; harmonize sex codes (BTSX,
MLE, FMLE); keep years 1990–2023; drop values outside plausible bounds per
indicator; remove duplicates on the natural key. Outliers by the IQR rule
(Q1 − 1.5·IQR, Q3 + 1.5·IQR per indicator) are not dropped but flagged in the
column `observation.is_outlier`.

## Checking the data

The SQL quality checks and their results are in `docs/lab2_results.md`. The
exploration of the raw downloads is in `notebooks/lab2_explore.ipynb`.

## Database migrations

Schema changes are managed with Alembic (`alembic/`). `alembic current` shows the
version of the database; `alembic upgrade head` applies pending migrations.

## Structure

- `app/`: database connection (`database.py`) and SQLAlchemy models (`models.py`)
- `etl/`: `extract_*.py` (download), `transform_*.py` (raw file to normalized
  table), `clean.py` (cleaning and outlier flag), `load.py` (upserts, import log),
  `import_*.py` (one script per source), `json_types.py` (JSON helpers)
- `alembic/`: database migrations
- `db/schema.sql`: design reference of the database; `schema_dump.sql`: schema
  exported with `pg_dump`
- `notebooks/`: exploration notebook
- `docs/`: task results (`lab2_results.md`) and prompts documents (`prompts/`)