"""The dependency rule, checked automatically: dependencies point one way only.

The domain types, the repositories and the services are lower layers: they must not
import FastAPI, the controllers or the wiring in app/dependencies.py.
"""
import ast
from pathlib import Path

import pytest

APP = Path(__file__).resolve().parent.parent / "app"
FORBIDDEN = ("fastapi", "app.controllers", "app.dependencies")

LOWER_LAYER_FILES = [
    APP / "domain.py",
    *sorted((APP / "repositories").glob("*.py")),
    *sorted((APP / "services").glob("*.py")),
]


def imported_modules(path: Path) -> set[str]:
    """Names of the modules imported by one Python file."""
    modules = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def forbidden_imports(path: Path) -> list[str]:
    """The imports of ``path`` that a lower layer must not have."""
    return sorted(
        module
        for module in imported_modules(path)
        if any(module == name or module.startswith(name + ".") for name in FORBIDDEN)
    )


def test_there_are_lower_layer_files_to_check() -> None:
    # Guards against a typo in a path: an empty list would make the test below pass for nothing.
    assert APP / "domain.py" in LOWER_LAYER_FILES
    assert len(LOWER_LAYER_FILES) >= 5


@pytest.mark.parametrize(
    "path", LOWER_LAYER_FILES, ids=lambda path: path.relative_to(APP).as_posix()
)
def test_lower_layers_do_not_import_from_upper_layers(path: Path) -> None:
    assert forbidden_imports(path) == [], f"{path.name} imports from an upper layer"


def test_the_check_detects_a_forbidden_import(tmp_path) -> None:
    bad_file = tmp_path / "bad.py"
    bad_file.write_text(
        "from fastapi import Request\n"
        "import app.controllers.observation_controller\n"
        "from app.dependencies import get_db\n"
        "from app.domain import ObservationCriteria\n",
        encoding="utf-8",
    )

    assert forbidden_imports(bad_file) == [
        "app.controllers.observation_controller",
        "app.dependencies",
        "fastapi",
    ]
