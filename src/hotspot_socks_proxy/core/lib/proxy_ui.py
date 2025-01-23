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

from prompt_toolkit.application import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout.containers import HSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.layout import Layout

from .proxy_stats import proxy_stats


class ProxyUI:
    def __init__(self, server_ip: str):
        self.server_ip = server_ip
        self.kb = KeyBindings()

        @self.kb.add("c-c")
        def _(event):
            event.app.exit()

        # Add a status line at the top
        self.status_line = Window(
            height=1,
            content=FormattedTextControl(lambda: [("class:status", " Press Ctrl-C to exit")])
        )

        # Main stats display
        self.output = Window(
            content=FormattedTextControl(self._get_stats_text),
            always_hide_cursor=True,
            wrap_lines=True,
        )

        # Create a cleaner layout with proper spacing
        self.container = HSplit([
            Window(height=1),  # Top padding
            self.output,
            Window(height=1),  # Bottom padding
            self.status_line,
        ])

        self.layout = Layout(self.container)
        self.app = Application(
            layout=self.layout,
            key_bindings=self.kb,
            full_screen=True,
            mouse_support=True,
        )

    def _get_stats_text(self):
        stats = proxy_stats
        bandwidth = stats.get_bandwidth()
        
        return [
            ("class:title", "╔══════════════════════════════════════╗\n"),
            ("class:title", f"║  SOCKS5 Proxy: {self.server_ip}:9050  ║\n"),
            ("class:title", "╠══════════════════════════════════════╣\n"),
            ("class:stats", f"║  Bandwidth: {self._format_bytes(bandwidth)}/s" + " " * (31 - len(self._format_bytes(bandwidth))) + "║\n"),
            ("class:stats", f"║  Active Connections: {stats.active_connections}" + " " * (27 - len(str(stats.active_connections))) + "║\n"),
            ("class:title", "╚══════════════════════════════════════╝\n"),
        ]

    def _format_bytes(self, bytes_):
        for unit in ["B", "KB", "MB", "GB"]:
            if bytes_ < 1024:
                return f"{bytes_:.1f} {unit}"
            bytes_ /= 1024
        return f"{bytes_:.1f} TB"

    def run(self):
        self.app.run()
