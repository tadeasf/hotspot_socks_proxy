"""SOCKS proxy for routing traffic through WiFi interface."""

import pathlib
import sys

# Update version check to use newer Python version
if sys.version_info >= (3, 10):  # Update to match pyproject.toml requirement
    import tomllib
else:
    import tomli as tomllib


def get_version() -> str:
    """Read version from pyproject.toml."""
    current_dir = pathlib.Path(__file__).parent
    parents = [current_dir, *list(current_dir.parents)]  # Use list unpacking

    for parent in parents:
        pyproject_path = parent / "pyproject.toml"
        if pyproject_path.exists():
            with pyproject_path.open("rb") as f:
                pyproject_data = tomllib.load(f)
            return pyproject_data["project"]["version"]

    return "0.0.0"


__version__ = get_version()
