"""Controller tests: TestClient; the layers below are replaced through dependency_overrides.

The page tests use a service with pages of four rows, so the nine seeded rows span three pages.
"""
import re

import pytest

from app.dependencies import get_observation_service
from app.main import app
from app.repositories.observation_repository import ObservationRepository
from app.services.observation_service import ObservationService


def _visible_text(response) -> str:
    """The page text as a browser shows it: runs of whitespace count as one space."""
    return " ".join(response.text.split())


@pytest.fixture
def page_client(client, session, seeded):
    service = ObservationService(ObservationRepository(session), page_size=4)
    app.dependency_overrides[get_observation_service] = lambda: service
    return client


def test_first_page_shows_the_totals_and_a_next_link(page_client) -> None:
    response = page_client.get("/")

    assert response.status_code == 200
    assert "9 rows" in response.text
    assert "page 1 of 3" in _visible_text(response)
    assert "page=2" in response.text
    assert "Previous" not in response.text


def test_last_page_has_a_previous_link_and_no_next_link(page_client) -> None:
    response = page_client.get("/?page=3")

    assert "page 3 of 3" in _visible_text(response)
    assert "Previous" in response.text
    assert "Next" not in response.text


def test_page_zero_is_rejected_before_the_service_is_called(page_client) -> None:
    assert page_client.get("/?page=0").status_code == 422


def test_filters_are_applied(page_client) -> None:
    assert "4 rows" in page_client.get("/?country=ROU").text
    assert "6 rows" in page_client.get("/?region=Europe+%26+Central+Asia").text


def test_the_filter_is_kept_on_the_next_page(page_client) -> None:
    response = page_client.get("/?region=Europe+%26+Central+Asia")

    assert "page 1 of 2" in _visible_text(response)
    assert re.search(r"region=Europe\+%26\+Central\+Asia(&amp;|&)page=2", response.text)


def test_invalid_or_blank_values_are_ignored(page_client) -> None:
    response = page_client.get("/?year_from=abc&country=&indicator=")

    assert response.status_code == 200
    assert "9 rows" in response.text


def test_the_chosen_option_stays_selected(page_client) -> None:
    response = page_client.get("/?country=ROU")

    assert re.search(r'value="ROU"\s+selected', response.text)


def test_a_filter_without_matches_shows_a_message(page_client) -> None:
    response = page_client.get("/?country=XXX")

    assert "No data matches these filters." in response.text


def test_the_sex_filter_shows_exactly_one_row(page_client) -> None:
    response = page_client.get("/?sex=MLE&country=ROU")

    assert "1 rows" in _visible_text(response)
    assert re.search(r'value="MLE"\s+selected', response.text)
    assert "<td>MLE</td>" in response.text


def test_the_sex_dropdown_lists_the_three_codes(page_client) -> None:
    response = page_client.get("/")

    for code in ("BTSX", "MLE", "FMLE"):
        assert f'<option value="{code}"' in response.text


def test_an_unknown_sex_code_is_ignored(page_client) -> None:
    response = page_client.get("/?sex=XXX")

    assert response.status_code == 200
    assert "9 rows" in _visible_text(response)