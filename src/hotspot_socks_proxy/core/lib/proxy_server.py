"""SOCKS proxy server implementation with multi-process support.

This module implements a multi-process SOCKS proxy server with the following features:
- Process pool management for handling multiple connections
- Automatic process recovery on failure
- WiFi interface detection and validation
- Clean shutdown handling
- UI integration
- Clipboard integration for easy sharing

The server supports:
- Multiple simultaneous connections
- Process-level parallelism
- Automatic port reuse
- Privilege checking
- Interface validation

Example:
    # Create and start a proxy server with 4 processes
    create_proxy_server("192.168.1.100", 9050, 4)
"""

import contextlib
import multiprocessing
import os
import socket
import socketserver
import time

import psutil
import pyperclip
from rich.console import Console

from hotspot_socks_proxy.core.utils.prompt.proxy_ui import create_proxy_ui

from .socks_handler import SocksHandler

console = Console()

# Type aliases
ProcessList = list[multiprocessing.Process]

# Constants
BANDWIDTH_THRESHOLD = 100  # Bytes
PROCESS_JOIN_TIMEOUT = 1.0  # Seconds
STARTUP_DELAY = 0.1  # Seconds between process starts
CLIPBOARD_DELAY = 0.5  # Seconds to wait after clipboard copy


class SocksProxy(socketserver.ThreadingMixIn, socketserver.TCPServer):
    """SOCKS proxy server implementation."""

    allow_reuse_address = True
    daemon_threads = True
    request_queue_size = 100

    def server_bind(self) -> None:
        """Bind the server socket with reuse options."""
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if hasattr(socket, "SO_REUSEPORT"):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        super().server_bind()


def is_wifi_interface(ip: str) -> bool:
    """Verify if the IP belongs to the WiFi interface."""
    for interface, addrs in psutil.net_if_addrs().items():
        if interface.startswith(("en", "wlan", "wifi", "eth")):
            for addr in addrs:
                if addr.family == socket.AF_INET and addr.address == ip:
                    return True
    return False


def run_server(host: str, port: int) -> None:
    """Individual process server runner.

    Args:
        host: Host address to bind to
        port: Port number to listen on
    """
    server: SocksProxy | None = None
    try:
        if not is_wifi_interface(host):
            console.print(f"[red]Error: {host} is not the WiFi interface IP")
            return

        if os.name != "nt" and os.geteuid() != 0:
            console.print(
                """
            [yellow]Warning: Running without root privileges may limit functionality.
                """
            )

        server = SocksProxy((host, port), SocksHandler)
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        console.print(f"[red]Server error: {e}")
    finally:
        if server:
            with contextlib.suppress(Exception):
                server.server_close()


def create_proxy_server(host: str, port: int, num_processes: int) -> None:
    """Create and start a multi-process SOCKS proxy server.

    Args:
        host: Host address to bind to
        port: Port number to listen on
        num_processes: Number of worker processes to start
    """
    processes: ProcessList = []

    try:
        # Initialize UI
        ui_thread = create_proxy_ui(host, port)
        if ui_thread:
            ui_thread.start()

        # Copy address to clipboard
        try:
            proxy_address = f"{host}:{port}"
            pyperclip.copy(proxy_address)
            console.print("[bold green]Proxy address copied to clipboard")
            time.sleep(CLIPBOARD_DELAY)
        except Exception as e:
            console.print(f"[yellow]Could not copy to clipboard: {e}")

        # Start worker processes
        console.print(f"[bold green]Starting {num_processes} worker processes...")
        for _ in range(num_processes):
            process = multiprocessing.Process(target=run_server, args=(host, port))
            process.daemon = True
            processes.append(process)
            process.start()
            time.sleep(STARTUP_DELAY)

    except KeyboardInterrupt:
        console.print("\n[yellow]Shutting down proxy server...")
    finally:
        for process in processes:
            if process.is_alive():
                process.terminate()
                process.join(timeout=PROCESS_JOIN_TIMEOUT)
                if process.is_alive():
                    process.kill()
