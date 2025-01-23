"""SOCKS proxy server command interface.

This module provides a high-level interface for:
- Starting the SOCKS proxy server
- Managing worker processes
- Handling server lifecycle
- Progress reporting
- Error handling

The module integrates with the core proxy implementation and provides
a user-friendly way to start and manage the proxy server.

Example:
    # Start a SOCKS proxy with default settings
    run_socks_proxy("192.168.1.100")
"""

import multiprocessing

from prompt_toolkit.shortcuts import ProgressBar
from rich.console import Console

from hotspot_socks_proxy.core.proxy import create_proxy_server

console = Console()


def run_socks_proxy(host: str, port: int = 9050, processes: int | None = None) -> None:
    """Run multi-process SOCKS proxy server."""
    if not processes:
        processes = multiprocessing.cpu_count()

    with ProgressBar(title=f"Starting SOCKS proxy with {processes} processes...") as pb:
        for _ in pb(range(1)):
            pass  # Preparation step

    console.print(
        f"[green]SOCKS5 proxy server started on {host}:{port} "
        f"with {processes} processes"
    )

    try:
        create_proxy_server(host, port, processes)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        console.print(f"[red]Error: {e}")
