"""User interface component for the SOCKS proxy server.

This module implements a real-time terminal user interface for the SOCKS proxy server
using prompt_toolkit. It provides:
- Live bandwidth monitoring
- Active connection counting
- Clean terminal UI with borders
- Keyboard control (Ctrl-C to exit)
- Auto-updating statistics display

The UI is designed to be non-blocking and run in a separate thread, allowing the proxy
server to operate independently while providing real-time feedback to the user.

The interface uses box-drawing characters to create a bordered display that shows:
- Current server address and port
- Real-time bandwidth usage with automatic unit scaling
- Number of active connections
- Status line with keyboard controls

Example:
    ui = ProxyUI(server_ip="192.168.1.100")
    ui_thread = threading.Thread(target=ui.run, daemon=True)
    ui_thread.start()
"""

import threading
import time
from typing import Optional

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.spinner import Spinner
from rich.table import Table
from rich.text import Text

from .proxy_stats import proxy_stats

console = Console()

class ProxyUI:
    def __init__(self, server_ip: str, port: int = 9050):
        self.server_ip = server_ip
        self.port = port
        self.running = True
        self._refresh_rate = 1.0  # Refresh every second instead of constantly
        self._last_bandwidth = 0
        self._spinner = Spinner('dots')
        
    def _format_bytes(self, bytes_: float) -> str:
        for unit in ["B", "KB", "MB", "GB"]:
            if bytes_ < 1024:
                return f"{bytes_:.1f} {unit}"
            bytes_ /= 1024
        return f"{bytes_:.1f} TB"

    def _generate_table(self) -> Table:
        table = Table(show_header=False, box=None)
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="green")

        bandwidth = proxy_stats.get_bandwidth()
        # Only update bandwidth if it changed significantly (avoid jitter)
        if abs(bandwidth - self._last_bandwidth) > 100:
            self._last_bandwidth = bandwidth

        table.add_row(
            "Bandwidth",
            f"{self._spinner.render()} {self._format_bytes(self._last_bandwidth)}/s"
        )
        table.add_row(
            "Active Connections",
            str(proxy_stats.active_connections)
        )
        table.add_row(
            "Total Data Transferred",
            self._format_bytes(proxy_stats.total_bytes_sent + proxy_stats.total_bytes_received)
        )
        return table

    def _generate_display(self) -> Panel:
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
            with Live(
                self._generate_display(),
                refresh_per_second=2,  # Limit refresh rate
                transient=True
            ) as live:
                while self.running:
                    live.update(self._generate_display())
                    time.sleep(self._refresh_rate)
        except KeyboardInterrupt:
            self.running = False

def create_ui(host: str, port: int) -> Optional[threading.Thread]:
    """Create and return UI thread."""
    ui = ProxyUI(host, port)
    thread = threading.Thread(target=ui.run, daemon=True)
    return thread
