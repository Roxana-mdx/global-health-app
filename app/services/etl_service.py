"""The service behind the two action buttons: it runs the pipeline of lab 2.

It runs a list of jobs and turns each outcome into a StepResult. Only the expected
errors become a failed result; any other exception is a bug and is not hidden.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import Callable, Sequence

import requests

from etl import import_ihme, import_worldbank
from etl.extract_ihme import locate_ihme_csv
from etl.extract_worldbank import (
    WorldBankApiError,
    download_worldbank_countries,
    download_worldbank_indicator,
)
from etl.step_result import StepResult

logger = logging.getLogger(__name__)

EXTRACT_ERRORS = (WorldBankApiError, requests.RequestException, OSError, ValueError)


@dataclass(frozen=True)
class ExtractJob:
    """One download: returns the path of the saved file and the request URL."""

    source: str
    item: str
    download: Callable[[], tuple[Path, str]]


@dataclass(frozen=True)
class ImportJob:
    """One source import: returns one result per step."""

    source: str
    run: Callable[[], list[StepResult]]


# The World Bank import runs first: it loads the countries the IHME import refers to.
DEFAULT_IMPORT_JOBS = (
    ImportJob(import_worldbank.SOURCE.name, import_worldbank.import_all),
    ImportJob(import_ihme.SOURCE.name, import_ihme.import_all),
)


def default_extract_jobs() -> tuple[ExtractJob, ...]:
    """Built from the same indicator lists the imports use, so Extract downloads
    exactly the files that Transform & load reads."""
    world_bank = import_worldbank.SOURCE.name
    jobs = [ExtractJob(world_bank, "countries", download_worldbank_countries)]
    jobs += [
        ExtractJob(world_bank, spec.code, partial(download_worldbank_indicator, spec.remote_id))
        for spec in import_worldbank.INDICATORS
    ]
    # IHME has no API: the CSV is requested by hand, so this step only checks that it is there.
    jobs.append(ExtractJob(import_ihme.SOURCE.name, "IHME CSV", locate_ihme_csv))
    return tuple(jobs)


class EtlService:
    def __init__(
        self,
        extract_jobs: Sequence[ExtractJob] | None = None,
        import_jobs: Sequence[ImportJob] = DEFAULT_IMPORT_JOBS,
    ) -> None:
        self._extract_jobs = (
            tuple(extract_jobs) if extract_jobs is not None else default_extract_jobs()
        )
        self._import_jobs = tuple(import_jobs)

    def extract_all(self) -> list[StepResult]:
        """Download every source into data/raw/; one result per file."""
        return [_run_extract(job) for job in self._extract_jobs]

    def transform_and_load_all(self) -> list[StepResult]:
        """Transform, clean and load every source."""
        return [result for job in self._import_jobs for result in job.run()]


def _run_extract(job: ExtractJob) -> StepResult:
    try:
        path, _ = job.download()
    except EXTRACT_ERRORS as error:
        logger.exception("%s %s: extract failed", job.source, job.item)
        return StepResult.from_error(job.source, job.item, error)

    size = path.stat().st_size
    return StepResult.ok(job.source, job.item, f"{path.name} ({size:,} bytes)")
