"""SOCKS-specific UI components."""

import time

from rich.console import Console
from rich.panel import Panel
from rich.spinner import Spinner
from rich.table import Table
from rich.text import Text

from hotspot_socks_proxy.core.utils.prompt.prompt import PromptHandler

console = Console()


class SocksUI(PromptHandler):
    """UI handler for SOCKS connections."""

    def __init__(self) -> None:
        """Initialize the SOCKS UI handler.

        Sets up the spinner, start time, and active connections tracking.
        """
        super().__init__()
        self._spinner = Spinner("dots", text="")
        self._start_time = time.monotonic()
        self._active_connections = {}  # addr: start_time

    def connection_started(self, addr: tuple):
        """Log new connection."""
        self._active_connections[addr] = time.monotonic()

    def connection_ended(self, addr: tuple):
        """Log connection end."""
        self._active_connections.pop(addr, None)

    def _generate_table(self) -> Table:
        """Generate SOCKS statistics table."""
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("Property", style="cyan", no_wrap=True)
        table.add_column("Value", style="green", no_wrap=True)

        # Active connections
        for addr, start_time in self._active_connections.items():
            duration = time.monotonic() - start_time
            table.add_row(f"Connection {addr[0]}:{addr[1]}", f"{duration:.1f}s")

        # Connection stats
        table.add_row("Total Connections", str(len(self._active_connections)))

        return table

    def _generate_display(self) -> Panel:
        """Generate the main display panel."""
        title = Text("SOCKS Connection Statistics", style="bold cyan")
        table = self._generate_table()
        return Panel(table, title=title, border_style="blue", padding=(1, 2))


# Global UI instance
socks_ui = SocksUI()
