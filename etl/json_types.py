"""Helpers for reading saved JSON files and checking their shape."""
import json
from pathlib import Path


def read_json_records(path: Path) -> list[dict]:
    """Read a saved JSON file and return it as a list of dictionaries."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"{path}: expected a JSON list, got {type(data).__name__}")
    for item in data:
        if not isinstance(item, dict):
            raise ValueError(f"{path}: expected every item to be an object, got {item!r}")
    return data


def require_keys(record: dict, keys: list[str], source: str) -> None:
    """Stop with a clear message if a record lacks one of the expected fields."""
    missing = [key for key in keys if key not in record]
    if missing:
        raise ValueError(f"{source}: record is missing {missing}: {record!r}")