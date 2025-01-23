"""SOCKS proxy for routing traffic through WiFi interface."""

import pathlib
import sys

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


def get_version() -> str:
    """Read version from pyproject.toml."""
    # Start from the current file's directory
    current_dir = pathlib.Path(__file__).parent
    # Look for pyproject.toml in parent directories
    for parent in [current_dir] + list(current_dir.parents):
        pyproject_path = parent / "pyproject.toml"
        if pyproject_path.exists():
            with pyproject_path.open("rb") as f:
                pyproject_data = tomllib.load(f)
            return pyproject_data["project"]["version"]
    
    # Fallback version if file not found
    return "0.0.0"


__version__ = get_version()
