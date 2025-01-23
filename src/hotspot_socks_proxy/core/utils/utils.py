"""Common utility functions."""

from typing import Final

# Size constants
BYTES_PER_KB: Final = 1024
BYTES_PER_MB: Final = BYTES_PER_KB * 1024
BYTES_PER_GB: Final = BYTES_PER_MB * 1024
BYTES_PER_TB: Final = BYTES_PER_GB * 1024

# Size units
SIZE_UNITS: Final = [
    ("B", 1),
    ("KB", BYTES_PER_KB),
    ("MB", BYTES_PER_MB),
    ("GB", BYTES_PER_GB),
    ("TB", BYTES_PER_TB),
]


def format_bytes(bytes_: float) -> str:
    """Format bytes into human readable format.

    Args:
        bytes_: Number of bytes to format

    Returns:
        str: Formatted string with appropriate unit
    """
    for unit, divisor in SIZE_UNITS:
        if bytes_ < divisor * BYTES_PER_KB:
            return f"{bytes_ / divisor:.1f} {unit}"
    return f"{bytes_ / BYTES_PER_TB:.1f} TB"
