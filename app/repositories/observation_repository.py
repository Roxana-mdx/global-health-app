"""Data access: every query on observations lives here.

The repository receives its session, returns domain types and never commits:
the transaction belongs to the caller.
"""
from __future__ import annotations

from sqlalchemy import ColumnElement, Select, func, select
from sqlalchemy.orm import Session

from app.domain import FilterOptions, ObservationCriteria, ObservationListItem, Option
from app.models import Country, Indicator, Observation, Sex

# Ends with the primary key so that the order is total: with LIMIT and OFFSET,
# rows that tie on country and year cannot repeat or disappear between pages.
_STABLE_ORDER = (
    Country.name,
    Observation.year.desc(),
    Indicator.code,
    Observation.sex,
    Observation.observation_id,
)


def _conditions(criteria: ObservationCriteria) -> list[ColumnElement[bool]]:
    """One condition per filter that is set. Values are sent as parameters."""
    conditions: list[ColumnElement[bool]] = []
    if criteria.country_iso3 is not None:
        conditions.append(Country.iso3 == criteria.country_iso3)
    if criteria.indicator_code is not None:
        conditions.append(Indicator.code == criteria.indicator_code)
    if criteria.region is not None:
        conditions.append(Country.region == criteria.region)
    if criteria.year_from is not None:
        conditions.append(Observation.year >= criteria.year_from)
    if criteria.year_to is not None:
        conditions.append(Observation.year <= criteria.year_to)
    return conditions


def _matching_observations(criteria: ObservationCriteria) -> Select:
    """Observations joined with country and indicator, columns named like
    the fields of ObservationListItem."""
    return (
        select(
            Country.name.label("country_name"),
            Country.iso3.label("country_iso3"),
            Country.region.label("region"),
            Indicator.code.label("indicator_code"),
            Indicator.name.label("indicator_name"),
            Indicator.unit.label("unit"),
            Observation.year.label("year"),
            Observation.sex.label("sex"),
            Observation.value.label("value"),
        )
        .select_from(Observation)
        .join(Country, Observation.country_iso3 == Country.iso3)
        .join(Indicator, Observation.indicator_id == Indicator.indicator_id)
        .where(*_conditions(criteria))
    )


class ObservationRepository:
    """Reads observations and the lookup values used to filter them."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def find(
        self, criteria: ObservationCriteria, *, limit: int, offset: int
    ) -> list[ObservationListItem]:
        query = (
            _matching_observations(criteria)
            .order_by(*_STABLE_ORDER)
            .limit(limit)
            .offset(offset)
        )
        return [
            ObservationListItem(**{**row, "sex": Sex(row["sex"])})
            for row in self._session.execute(query).mappings()
        ]

    def count(self, criteria: ObservationCriteria) -> int:
        query = select(func.count()).select_from(
            _matching_observations(criteria).subquery()
        )
        return self._session.scalar(query) or 0

    def list_countries(self) -> tuple[Option, ...]:
        rows = self._session.execute(
            select(Country.iso3, Country.name).order_by(Country.name)
        )
        return tuple(Option(value=iso3, label=name) for iso3, name in rows)

    def list_indicators(self) -> tuple[Option, ...]:
        rows = self._session.execute(
            select(Indicator.code, Indicator.name).order_by(Indicator.code)
        )
        return tuple(Option(value=code, label=f"{name} ({code})") for code, name in rows)

    def list_regions(self) -> tuple[Option, ...]:
        rows = self._session.scalars(
            select(Country.region)
            .where(Country.region.is_not(None))
            .distinct()
            .order_by(Country.region)
        )
        return tuple(Option(value=region, label=region) for region in rows)

    def get_filter_options(self) -> FilterOptions:
        return FilterOptions(
            countries=self.list_countries(),
            indicators=self.list_indicators(),
            regions=self.list_regions(),
        )
