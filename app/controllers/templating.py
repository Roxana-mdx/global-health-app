"""The Jinja2 templates, found relative to this file, not to the working directory."""
from pathlib import Path

from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory=Path(__file__).resolve().parent.parent / "templates")