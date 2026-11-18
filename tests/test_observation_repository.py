"""Repository tests: real PostgreSQL, in a temporary schema with seed data."""
import pytest

from app.domain import ObservationCriteria
from app.models import Sex
from app.repositories.observation_repository import ObservationRepository

ALL = ObservationCriteria()
HEALTH = "SH.XPD.CHEX.GD.ZS"
ENDO = "ENDO_PREV_ASR"


@pytest.fixture
def repository(session, seeded) -> ObservationRepository:
    return ObservationRepository(session)


def _keys(items):
    return [(i.country_iso3, i.indicator_code, i.year, i.sex) for i in items]


def test_find_returns_rows_in_stable_order(repository) -> None:
    items = repository.find(ALL, limit=100, offset=0)

    # country name, year descending, indicator code, sex
    assert _keys(items) == [
        ("BRA", ENDO, 2019, Sex.FEMALE),
        ("FRA", HEALTH, 2020, Sex.BOTH),
        ("FRA", HEALTH, 2015, Sex.BOTH),
        ("KEN", ENDO, 2019, Sex.FEMALE),
        ("KEN", HEALTH, 2019, Sex.BOTH),
        ("ROU", HEALTH, 2020, Sex.BOTH),
        ("ROU", ENDO, 2019, Sex.FEMALE),
        ("ROU", ENDO, 2019, Sex.MALE),
        ("ROU", HEALTH, 2019, Sex.BOTH),
    ]


def test_pages_neither_repeat_nor_skip_rows(repository) -> None:
    everything = repository.find(ALL, limit=100, offset=0)

    pages = [repository.find(ALL, limit=4, offset=offset) for offset in (0, 4, 8)]

    assert [len(page) for page in pages] == [4, 4, 1]
    assert [item for page in pages for item in page] == everything


@pytest.mark.parametrize(
    "criteria, expected_count",
    [
        (ALL, 9),
        (ObservationCriteria(country_iso3="ROU"), 4),
        (ObservationCriteria(region="Europe & Central Asia"), 6),
        (ObservationCriteria(indicator_code=ENDO), 4),
        (ObservationCriteria(indicator_code=HEALTH), 5),
        (ObservationCriteria(year_from=2020), 2),
        (ObservationCriteria(year_to=2015), 1),
        (ObservationCriteria(country_iso3="ROU", indicator_code=HEALTH, year_from=2019), 2),
        (ObservationCriteria(country_iso3="XXX"), 0),
        (ObservationCriteria(sex=Sex.FEMALE), 3),
        (ObservationCriteria(sex=Sex.BOTH), 5),
    ],
)
def test_count_applies_every_filter(repository, criteria, expected_count) -> None:
    assert repository.count(criteria) == expected_count


def test_find_with_filters_returns_only_matching_rows(repository) -> None:
    criteria = ObservationCriteria(country_iso3="ROU", indicator_code=HEALTH)

    items = repository.find(criteria, limit=100, offset=0)

    assert _keys(items) == [
        ("ROU", HEALTH, 2020, Sex.BOTH),
        ("ROU", HEALTH, 2019, Sex.BOTH),
    ]


def test_find_returns_ready_to_show_items(repository) -> None:
    item = repository.find(ObservationCriteria(country_iso3="KEN", indicator_code=ENDO), limit=1, offset=0)[0]

    assert item.country_name == "Kenya"
    assert item.region == "Sub-Saharan Africa"
    assert item.indicator_name.startswith("Endometriosis")
    assert item.unit == "per 100,000"
    assert float(item.value) == pytest.approx(300.1)


def test_lookup_lists_for_the_filter_form(repository) -> None:
    assert [o.label for o in repository.list_countries()] == [
        "Brazil", "France", "Kenya", "Romania",
    ]
    assert [o.value for o in repository.list_indicators()] == [ENDO, HEALTH]
    assert [o.value for o in repository.list_regions()] == [
        "Europe & Central Asia", "Latin America & Caribbean", "Sub-Saharan Africa",
    ]


def test_find_returns_only_the_rows_of_the_chosen_sex(repository) -> None:
    items = repository.find(ObservationCriteria(sex=Sex.MALE), limit=100, offset=0)

    assert _keys(items) == [("ROU", ENDO, 2019, Sex.MALE)]


def test_sex_can_be_combined_with_other_filters(repository) -> None:
    criteria = ObservationCriteria(country_iso3="ROU", sex=Sex.FEMALE)

    items = repository.find(criteria, limit=100, offset=0)

    assert _keys(items) == [("ROU", ENDO, 2019, Sex.FEMALE)]