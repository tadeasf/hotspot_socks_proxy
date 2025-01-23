"""Command-line interface for the SOCKS proxy server.

This module provides the main command-line interface for the proxy server, handling:
- Command-line argument parsing
- Server initialization
- Process management
- Root privilege checking
- Error reporting
- Interface selection

The CLI is built using Typer and provides a user-friendly interface for:
- Starting the proxy server
- Configuring the number of worker processes
- Setting the listening port
- Managing server lifecycle

Example:
    # Run from command line:
    $ python -m hotspot_socks_proxy proxy --port 9050 --processes 4
"""

import os
import sys

import typer
from loguru import logger
from rich.console import Console

from hotspot_socks_proxy import __version__
from hotspot_socks_proxy.core.network import scan_interfaces
from hotspot_socks_proxy.core.proxy import create_proxy_server
from hotspot_socks_proxy.core.utils.log_config import LOG_DIR

console = Console()
app = typer.Typer(help="SOCKS proxy for routing traffic through WiFi interface")


def check_root() -> bool:
    """Check if the script is running with root privileges."""
    if os.name == "nt":  # Windows
        try:
            import ctypes

            return ctypes.windll.shell32.IsUserAnAdmin()
        except Exception:
            return False
    else:  # Unix-like
        return os.geteuid() == 0


@app.callback(invoke_without_command=True)
def version_callback():
    """Show version information."""
    console.print(f"[cyan]Hotspot SOCKS Proxy v{__version__}[/cyan]")


@app.command(name="proxy")
def start_proxy(
    processes: int | None = typer.Option(
        None, "--processes", "-p", help="Number of CPU processes (default: CPU count)"
    ),
    port: int = typer.Option(9050, "--port", help="Port to listen on"),
    debug: bool = typer.Option(
        default=False,
        help="Enable debug logging",
    ),
):
    """Start the SOCKS proxy server."""
    if debug:
        logger.remove()
        logger.add(sys.stderr, level="DEBUG")
        logger.add(
            LOG_DIR / "proxy.log",
            level="DEBUG",
        )

    logger.info("Starting SOCKS proxy server")

    if not check_root():
        logger.error("Root privileges required")
        console.print("[red]This program requires root privileges to run properly.")
        console.print("[yellow]Please run with sudo or as root.")
        sys.exit(1)

    # Get available interfaces
    interface = scan_interfaces()
    if not interface:
        logger.error("No suitable network interface found")
        console.print("[red]No suitable network interface found")
        return

    try:
        process_count = processes if processes is not None else os.cpu_count() or 1
        logger.info(f"Starting proxy server on {interface.ip}:{port} with {process_count} processes")
        create_proxy_server(interface.ip, port, process_count)
    except KeyboardInterrupt:
        logger.info("Shutting down proxy server")
    except Exception as e:
        logger.exception("Error starting proxy server")
        console.print(f"[red]Error: {e}")


if __name__ == "__main__":
    app()
