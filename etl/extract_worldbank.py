"""Download raw World Bank data and save it under data/raw/worldbank/.

This module only downloads and saves. Turning the saved files into a table
is done in etl/transform_worldbank.py.
"""
import json
import time
from pathlib import Path

import requests

API = "https://api.worldbank.org/v2"
DEFAULT_RAW_DIR = Path("data/raw/worldbank")
HTTP_TIMEOUT_S = 60
PER_PAGE = 1000


class WorldBankApiError(Exception):
    """The World Bank API returned something other than the documented shape."""


def _get_json(url: str, params: dict) -> object:
    """One HTTP request; tries up to 3 times if the network fails."""
    for attempt in range(3):
        try:
            response = requests.get(url, params=params, timeout=HTTP_TIMEOUT_S)
            response.raise_for_status()
            return response.json()
        except requests.RequestException:
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)


def _get_all_pages(url: str, params: dict) -> list[dict]:
    """Follow the pages of a response. Every response is [paging info, records]."""
    records: list[dict] = []
    page = 1
    while True:
        body = _get_json(
            url, {**params, "format": "json", "per_page": PER_PAGE, "page": page}
        )
        # Errors (for example an unknown indicator) come back with HTTP 200
        # and a different shape, so check the shape before using the records.
        if not (isinstance(body, list) and len(body) == 2):
            raise WorldBankApiError(f"{url}: unexpected response {body!r}")
        meta, data = body
        if not isinstance(meta, dict) or "pages" not in meta:
            raise WorldBankApiError(f"{url}: missing page metadata in {meta!r}")
        records.extend(data or [])
        if page >= int(meta["pages"]):
            return records
        page += 1


def _save_raw(output_dir: Path, filename: str, rows: list[dict]) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / filename
    path.write_text(json.dumps(rows), encoding="utf-8")
    return path


def download_worldbank_indicator(
    code: str,
    year_from: int = 1990,
    year_to: int = 2023,
    *,
    output_dir: Path | None = None,
) -> tuple[Path, str]:
    """Download one indicator for all countries; returns (saved file, request URL)."""
    url = f"{API}/country/all/indicator/{code}"
    rows = _get_all_pages(url, {"date": f"{year_from}:{year_to}"})
    path = _save_raw(
        output_dir or DEFAULT_RAW_DIR, f"{code}_{year_from}-{year_to}.json", rows
    )
    return path, f"{url}?format=json&date={year_from}:{year_to}"


def download_worldbank_countries(*, output_dir: Path | None = None) -> tuple[Path, str]:
    """Download the country list (with region and income group)."""
    url = f"{API}/country"
    rows = _get_all_pages(url, {})
    path = _save_raw(output_dir or DEFAULT_RAW_DIR, "countries.json", rows)
    return path, f"{url}?format=json"
