"""Proxy-specific UI components."""

import threading
import time
from typing import Optional

from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ...lib.proxy_stats import proxy_stats
from ..utils import format_bytes
from .prompt import PromptHandler, console

class ProxyUI(PromptHandler):
    """UI handler for the proxy server."""
    
    def __init__(self, server_ip: str, port: int = 9050):
        super().__init__()
        self.server_ip = server_ip
        self.port = port
        self.running = True
        self._last_bandwidth = 0

    def _generate_table(self) -> Table:
        """Generate statistics table."""
        table = Table(show_header=False, box=None)
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="green")

        bandwidth = proxy_stats.get_bandwidth()
        if abs(bandwidth - self._last_bandwidth) > 100:
            self._last_bandwidth = bandwidth

        table.add_row(
            "Bandwidth",
            f"{self._spinner.render()} {format_bytes(self._last_bandwidth)}/s"
        )
        table.add_row(
            "Active Connections",
            str(proxy_stats.active_connections)
        )
        table.add_row(
            "Total Data Transferred",
            format_bytes(proxy_stats.total_bytes_sent + proxy_stats.total_bytes_received)
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
            border_style="blue"
        )

    def run(self):
        """Run the UI with efficient updates."""
        try:
            with self.create_live_display(self._generate_display()) as live:
                while self.running:
                    live.update(self._generate_display())
                    time.sleep(self._refresh_rate)
        except KeyboardInterrupt:
            self.running = False

def create_proxy_ui(host: str, port: int) -> Optional[threading.Thread]:
    """Create and return UI thread."""
    ui = ProxyUI(host, port)
    thread = threading.Thread(target=ui.run, daemon=True)
    return thread
