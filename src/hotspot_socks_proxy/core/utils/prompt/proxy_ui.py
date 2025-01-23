"""Proxy-specific UI components."""

import threading
import time

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.spinner import Spinner
from rich.table import Table
from rich.text import Text

from hotspot_socks_proxy.core.lib.proxy_stats import proxy_stats
from hotspot_socks_proxy.core.utils.utils import format_bytes

from .prompt import PromptHandler

console = Console()

# Add this constant at module level, after the imports
BANDWIDTH_THRESHOLD = 100  # bytes


class ProxyUI(PromptHandler):
    """UI handler for the proxy server."""

    def __init__(self, server_ip: str, port: int = 9050) -> None:
        """Initialize the proxy UI handler.

        Args:
            server_ip: IP address of the proxy server
            port: Port number the proxy server is listening on (default: 9050)
        """
        super().__init__()
        self.server_ip = server_ip
        self.port = port
        self.running = True
        self._last_bandwidth = 0
        self._start_time = time.monotonic()
        self._refresh_rate = 0.5
        self._spinner = Spinner("dots", text="")

    def _generate_table(self) -> Table:
        """Generate statistics table."""
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("Property", style="cyan", no_wrap=True)
        table.add_column("Value", style="green", no_wrap=True)

        bandwidth = proxy_stats.get_bandwidth()
        if abs(bandwidth - self._last_bandwidth) > BANDWIDTH_THRESHOLD:
            self._last_bandwidth = bandwidth

        elapsed = time.monotonic() - self._start_time
        spinner_text = self._spinner.render(elapsed)

        table.add_row(
            "Bandwidth", f"{spinner_text} {format_bytes(self._last_bandwidth)}/s"
        )
        table.add_row("Active Connections", str(proxy_stats.active_connections))
        table.add_row(
            "Total Data Transferred",
            format_bytes(
                proxy_stats.total_bytes_sent + proxy_stats.total_bytes_received
            ),
        )
        return table

    def _generate_display(self) -> Panel:
        """Generate the main display panel."""
        title = Text(f"SOCKS5 Proxy: {self.server_ip}:{self.port}", style="bold cyan")
        table = self._generate_table()
        return Panel(
            table,
            title=title,
            subtitle="Press Ctrl+C to exit",
            border_style="blue",
            padding=(1, 2),
        )

    def run(self):
        """Run the UI with efficient updates."""
        try:
            # Clear the screen once at start
            console.clear()

            # Create live display with higher refresh rate and auto refresh disabled
            with Live(
                self._generate_display(),
                console=console,
                refresh_per_second=4,  # Increased refresh rate
                transient=False,  # Keep the display on screen
                auto_refresh=False,  # Manual refresh control
            ) as live:
                while self.running:
                    live.update(self._generate_display())
                    time.sleep(self._refresh_rate)
        except KeyboardInterrupt:
            self.running = False


def create_proxy_ui(host: str, port: int) -> threading.Thread | None:
    """Create and return UI thread."""
    ui = ProxyUI(host, port)
    return threading.Thread(target=ui.run, daemon=True)
