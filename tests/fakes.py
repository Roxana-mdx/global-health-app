"""Test doubles shared by the service and controller tests."""
from __future__ import annotations

from decimal import Decimal

from app.domain import (
    FilterOptions,
    ObservationCriteria,
    ObservationListItem,
    Option,
)
from app.models import Sex
from etl.step_result import StepResult


def make_item(year: int) -> ObservationListItem:
    return ObservationListItem(
        country_name="Romania",
        country_iso3="ROU",
        region="Europe & Central Asia",
        indicator_code="SH.XPD.CHEX.GD.ZS",
        indicator_name="Current health expenditure (% of GDP)",
        unit="% of GDP",
        year=year,
        sex=Sex.BOTH,
        value=Decimal("5.70"),
    )


class FakeRepository:
    """Holds list items in memory and records the queries it receives."""

    def __init__(self, total_items: int) -> None:
        self.items = [make_item(2000 + index) for index in range(total_items)]
        self.find_calls: list[tuple[ObservationCriteria, int, int]] = []

    def find(self, criteria, *, limit, offset):
        self.find_calls.append((criteria, limit, offset))
        return self.items[offset : offset + limit]

    def count(self, criteria) -> int:
        return len(self.items)

    def get_filter_options(self) -> FilterOptions:
        return FilterOptions(
            countries=(Option("ROU", "Romania"),),
            indicators=(Option("SH.XPD.CHEX.GD.ZS", "Health expenditure"),),
            regions=(Option("Europe & Central Asia", "Europe & Central Asia"),),
        )


class FakeEtlService:
    """Returns prepared results and records which action was called."""

    def __init__(self, results: list[StepResult]) -> None:
        self._results = results
        self.calls: list[str] = []

    def extract_all(self) -> list[StepResult]:
        self.calls.append("extract")
        return self._results

    def transform_and_load_all(self) -> list[StepResult]:
        self.calls.append("transform_and_load")
        return self._results
