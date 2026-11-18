"""Fixtures: a temporary PostgreSQL schema with seed data, and a TestClient with a safety net."""
from __future__ import annotations

import os
import uuid

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_etl_service
from app.main import app
from app.models import Base, Country, Indicator, Observation, Sex, Source

load_dotenv()


@pytest.fixture(scope="session")
def engine():
    """An engine on a temporary schema test_<random>, dropped at the end of the session.

    The database comes from TEST_DATABASE_URL, or DATABASE_URL if that is not set.
    The tests use only the temporary schema: the application data is never touched.
    Without a reachable database, the tests that need it are skipped.
    """
    url = os.environ.get("TEST_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not url:
        pytest.skip("no TEST_DATABASE_URL or DATABASE_URL")

    schema = f"test_{uuid.uuid4().hex[:8]}"
    admin = create_engine(url)
    try:
        with admin.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    except SQLAlchemyError as error:
        admin.dispose()
        pytest.skip(f"database not reachable: {type(error).__name__}")

    test_engine = create_engine(url, connect_args={"options": f"-csearch_path={schema}"})
    Base.metadata.create_all(test_engine)
    yield test_engine

    test_engine.dispose()
    with admin.begin() as connection:
        connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
    admin.dispose()


@pytest.fixture
def session(engine):
    """A session whose changes are rolled back after every test."""
    connection = engine.connect()
    transaction = connection.begin()
    db = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield db
    finally:
        db.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def seeded(session):
    """Four countries, two indicators and nine observations."""
    source = Source(name="Test source")
    session.add(source)
    session.flush()

    session.add_all(
        [
            Country(iso3="FRA", name="France", region="Europe & Central Asia"),
            Country(iso3="ROU", name="Romania", region="Europe & Central Asia"),
            Country(iso3="KEN", name="Kenya", region="Sub-Saharan Africa"),
            Country(iso3="BRA", name="Brazil", region="Latin America & Caribbean"),
        ]
    )
    health = Indicator(
        code="SH.XPD.CHEX.GD.ZS",
        name="Current health expenditure (% of GDP)",
        unit="% of GDP",
        source_id=source.source_id,
    )
    endo = Indicator(
        code="ENDO_PREV_ASR",
        name="Endometriosis - Prevalence (age-standardized rate)",
        unit="per 100,000",
        source_id=source.source_id,
    )
    session.add_all([health, endo])
    session.flush()

    both, female, male = Sex.BOTH.value, Sex.FEMALE.value, Sex.MALE.value
    rows = [
        ("FRA", health, 2015, both, 11.0),
        ("FRA", health, 2020, both, 12.2),
        ("ROU", health, 2019, both, 5.7),
        ("ROU", health, 2020, both, 6.2),
        ("ROU", endo, 2019, female, 474.67),
        ("ROU", endo, 2019, male, 1.5),  # a male row, only to test the sex filter
        ("KEN", health, 2019, both, 4.5),
        ("KEN", endo, 2019, female, 300.1),
        ("BRA", endo, 2019, female, 420.8),
    ]
    session.add_all(
        Observation(
            country_iso3=iso3,
            indicator_id=indicator.indicator_id,
            year=year,
            sex=sex,
            value=value,
        )
        for iso3, indicator, year, sex, value in rows
    )
    session.flush()


def _forbidden(*args, **kwargs):
    raise AssertionError("this test reached a real dependency: override it")


@pytest.fixture
def client():
    """A TestClient. As a safety net, the real database and the real ETL are replaced by
    functions that fail the test: a test that reaches them by mistake fails instead of
    changing data."""
    app.dependency_overrides[get_db] = _forbidden
    app.dependency_overrides[get_etl_service] = _forbidden
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
