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

import typer
import sys
import os
from rich.console import Console
from ..core.network import select_interface
from ..core.proxy import create_proxy_server

console = Console()
app = typer.Typer(help="SOCKS proxy for routing traffic through selected network interface")

def check_root():
    """Check if the script is running with root privileges"""
    if os.name == 'nt':  # Windows
        try:
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False
    else:  # Unix-like
        return os.geteuid() == 0

@app.command(name="proxy")
def start_proxy(
    processes: int | None = typer.Option(None, "--processes", "-p", help="Number of proxy processes (default: CPU count)"),
    port: int = typer.Option(9050, "--port", help="Port to listen on")
):
    """Start the SOCKS proxy server"""
    if not check_root():
        console.print("[red]This program requires root privileges to run properly.")
        console.print("[yellow]Please run with sudo or as root.")
        sys.exit(1)
    
    # Let user select interface
    interface = select_interface()
    if not interface:
        console.print("[red]No interface selected. Exiting.")
        return
    
    actual_processes = processes if processes is not None else os.cpu_count()
    if actual_processes is None:
        actual_processes = 1
        
    try:
        create_proxy_server(interface.ip, port, actual_processes)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        console.print(f"[red]Error: {e}")

if __name__ == "__main__":
    app()