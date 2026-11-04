# Global Health Data Platform: burden of endometriosis, 1990–2023

Lab 1 (CSP in Global Health). The project stores country-level estimates of the
burden of endometriosis in a PostgreSQL database, ready for a REST API,
analysis and machine learning in later labs.

## Data

- Source: IHME Global Burden of Disease Study 2023 (GBD 2023), downloaded
  from the GBD Results tool: https://vizhub.healthdata.org/gbd-results/
- Cause: Endometriosis; sex: female; 204 countries and territories; years 1990–2023
- Measures: incidence, prevalence, YLDs; as number, crude rate and
  age-standardized rate
- The CSV is not in this repository (see `.gitignore`). To reproduce, request the
  data with the settings above and save the CSV in `data/raw/`.

Citation: Global Burden of Disease Collaborative Network. Global Burden of
Disease Study 2023 (GBD 2023) Results. Seattle, United States: Institute for
Health Metrics and Evaluation (IHME), 2024. Available from
https://vizhub.healthdata.org/gbd-results/.

IHME data is free for non-commercial use; commercial use requires a licence.

## Setup

1. Install Python 3.12 and PostgreSQL 18.
2. Create the user and database:
   `CREATE USER gh_user WITH PASSWORD 'gh_pass';`
   `CREATE DATABASE global_health OWNER gh_user ENCODING 'UTF8';`
3. Create a virtual environment and install dependencies:
   `py -3.12 -m venv .venv`, activate it, then `pip install -r requirements.txt`
4. Create a `.env` file in the project root:
   `DATABASE_URL=postgresql+psycopg://gh_user:gh_pass@localhost:5432/global_health`
5. Create the tables: `python -m app.create_tables`
6. Load the data: `python -m etl.load_ihme`

## Structure

- `db/schema.sql`: design reference of the database
- `app/`: database connection and SQLAlchemy models
- `etl/`: import script (`load_ihme.py`)
- `schema_dump.sql`: schema exported with `pg_dump`