"""Business rules for browsing observations: paging.

The service knows nothing about HTTP: it raises ValueError, not status codes.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from app.domain import FilterOptions, ObservationCriteria, ObservationListItem
from app.repositories.observation_repository import ObservationRepository

DEFAULT_PAGE_SIZE = 50


@dataclass(frozen=True)
class ObservationPage:
    """One page of results; computes what the view needs, so templates do no arithmetic."""

    items: list[ObservationListItem]
    number: int
    size: int
    total_items: int

    @property
    def total_pages(self) -> int:
        # An empty result is still shown as "page 1 of 1".
        return max(1, math.ceil(self.total_items / self.size))

    @property
    def has_previous(self) -> bool:
        return self.number > 1

    @property
    def has_next(self) -> bool:
        return self.number < self.total_pages


class ObservationService:
    def __init__(
        self,
        repository: ObservationRepository,
        page_size: int = DEFAULT_PAGE_SIZE,
    ) -> None:
        if page_size < 1:
            raise ValueError(f"page_size must be at least 1, got {page_size}")
        self._repository = repository
        self._page_size = page_size

    def get_page(self, criteria: ObservationCriteria, number: int) -> ObservationPage:
        """Page ``number`` (1-based) of the matching observations."""
        if number < 1:
            raise ValueError(f"page numbers start at 1, got {number}")

        items = self._repository.find(
            criteria,
            limit=self._page_size,
            offset=(number - 1) * self._page_size,
        )
        return ObservationPage(
            items=items,
            number=number,
            size=self._page_size,
            total_items=self._repository.count(criteria),
        )

    def get_filter_options(self) -> FilterOptions:
        """The lists shown in the filter form."""
        return self._repository.get_filter_options()
