"""Base prompt handling and UI components."""

from rich.console import Console
from rich.live import Live
from rich.spinner import Spinner

console = Console()


class PromptHandler:
    """Base class for handling terminal prompts and UI."""

    def __init__(self) -> None:
        """Initialize the PromptHandler with default settings.

        Sets up the refresh rate and spinner style for terminal displays.
        """
        self._refresh_rate = 1.0
        self._spinner = Spinner("dots")

    def create_live_display(self, content, refresh_per_second: int = 2):
        """Create a live updating display."""
        return Live(
            content,
            console=console,
            refresh_per_second=refresh_per_second,
            transient=True,
        )
