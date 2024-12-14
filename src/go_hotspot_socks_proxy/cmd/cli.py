import typer
from typing import Optional
import multiprocessing
from . import find_wifi, socks
from rich.console import Console

app = typer.Typer(help="SOCKS proxy for routing traffic through WiFi interface")
console = Console()

@app.command()
def wifi():
    """Show WiFi interface information"""
    find_wifi.show_wifi_info()

@app.command()
def proxy(
    port: int = typer.Option(9050, help="Port to run the proxy on"),
    processes: int = typer.Option(None, help="Number of processes (default: CPU count)")
):
    """Start SOCKS proxy server"""
    try:
        info = find_wifi.get_interface_info()
        if info['status'].lower() != 'active':
            console.print("[red]WiFi interface is not active!")
            raise typer.Exit(1)
        
        socks.run_socks_proxy(info['ip'], port, processes)
    except Exception as e:
        console.print(f"[red]Error: {e}")
        raise typer.Exit(1)

if __name__ == "__main__":
    app()