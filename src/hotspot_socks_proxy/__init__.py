"""SOCKS proxy for routing traffic through WiFi interface."""

import pathlib

# For Python < 3.11, use tomli instead of tomllib
try:
    import tomllib
except ImportError:
    import tomli as tomllib


def get_version() -> str:
    """Read version from pyproject.toml."""
    current_dir = pathlib.Path(__file__).parent
    parents = [current_dir, *list(current_dir.parents)]

    for parent in parents:
        pyproject_path = parent / "pyproject.toml"
        if pyproject_path.exists():
            with pyproject_path.open("rb") as f:
                pyproject_data = tomllib.load(f)
            return pyproject_data["project"]["version"]

    return "0.0.0"


__version__ = get_version()
