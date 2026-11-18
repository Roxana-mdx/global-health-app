"""Service tests: a fake repository, no database, no network."""
import pytest

from app.domain import ObservationCriteria
from app.models import Sex
from app.services.observation_service import ObservationPage, ObservationService
from tests.fakes import FakeRepository, make_item


def _service(total_items: int, page_size: int = 4):
    repository = FakeRepository(total_items)
    return ObservationService(repository, page_size=page_size), repository


@pytest.mark.parametrize("number, expected_offset", [(1, 0), (2, 4), (3, 8)])
def test_get_page_asks_the_repository_for_one_page(number, expected_offset) -> None:
    service, repository = _service(total_items=9)
    criteria = ObservationCriteria(country_iso3="ROU")

    service.get_page(criteria, number)

    assert repository.find_calls == [(criteria, 4, expected_offset)]


def test_get_page_reports_the_totals() -> None:
    service, _ = _service(total_items=9)

    page = service.get_page(ObservationCriteria(), 3)

    assert (page.number, page.size, page.total_items, page.total_pages) == (3, 4, 9, 3)
    assert len(page.items) == 1  # the last page holds the remaining row


@pytest.mark.parametrize("number", [0, -1])
def test_get_page_rejects_page_numbers_below_one(number) -> None:
    service, _ = _service(total_items=9)

    with pytest.raises(ValueError):
        service.get_page(ObservationCriteria(), number)


@pytest.mark.parametrize("page_size", [0, -5])
def test_page_size_must_be_at_least_one(page_size) -> None:
    with pytest.raises(ValueError):
        ObservationService(FakeRepository(0), page_size=page_size)


@pytest.mark.parametrize(
    "total_items, size, expected_pages", [(0, 4, 1), (4, 4, 1), (5, 4, 2), (9, 4, 3)]
)
def test_total_pages_rounds_up_and_is_at_least_one(total_items, size, expected_pages) -> None:
    page = ObservationPage(items=[], number=1, size=size, total_items=total_items)

    assert page.total_pages == expected_pages


def test_previous_and_next_flags() -> None:
    first = ObservationPage(items=[make_item(2000)], number=1, size=4, total_items=9)
    last = ObservationPage(items=[make_item(2008)], number=3, size=4, total_items=9)

    assert (first.has_previous, first.has_next) == (False, True)
    assert (last.has_previous, last.has_next) == (True, False)


def test_get_filter_options_comes_from_the_repository() -> None:
    service, repository = _service(total_items=0)

    assert service.get_filter_options() == repository.get_filter_options()


def test_the_sex_filter_is_passed_to_the_repository_unchanged() -> None:
    service, repository = _service(total_items=9)
    criteria = ObservationCriteria(sex=Sex.MALE)

    service.get_page(criteria, 1)

    assert repository.find_calls[0][0].sex is Sex.MALE