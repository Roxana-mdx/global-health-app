"""Locate the IHME GBD CSV export in data/raw/ihme/.

IHME has no API: the data is requested in the GBD Results tool and downloaded
by hand, so this module does not download anything. It only finds the file and
returns it with a description of where it came from (written to import_log).
"""
from pathlib import Path

DEFAULT_RAW_DIR = Path("data/raw/ihme")
SOURCE_URL = "https://vizhub.healthdata.org/gbd-results/"


def locate_ihme_csv(
    filename: str | None = None, *, raw_dir: Path | None = None
) -> tuple[Path, str]:
    """Return (path of the CSV, source description).

    Without a filename, the folder must contain exactly one .csv file.
    """
    folder = raw_dir or DEFAULT_RAW_DIR
    if filename:
        path = folder / filename
        if not path.exists():
            raise FileNotFoundError(f"{path} not found")
    else:
        files = sorted(folder.glob("*.csv"))
        if not files:
            raise FileNotFoundError(
                f"No CSV in {folder}. Unzip the IHME download and copy the .csv here."
            )
        if len(files) > 1:
            names = ", ".join(f.name for f in files)
            raise ValueError(f"More than one CSV in {folder} ({names}); pass a filename.")
        path = files[0]
    return path, f"{SOURCE_URL} (file: {path.name})"
