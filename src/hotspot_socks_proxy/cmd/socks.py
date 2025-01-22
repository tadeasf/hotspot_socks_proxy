from ..core.proxy import create_proxy_server
from rich.console import Console
from prompt_toolkit.shortcuts import ProgressBar
import multiprocessing

console = Console()

def run_socks_proxy(host: str, port: int = 9050, processes: int = None):
    """Run multi-process SOCKS proxy server"""
    if not processes:
        processes = multiprocessing.cpu_count()
    
    with ProgressBar(title=f"Starting SOCKS proxy with {processes} processes...") as pb:
        for _ in pb(range(1)):
            pass  # Preparation step
    
    console.print(f"[green]SOCKS5 proxy server started on {host}:{port} with {processes} processes")
    
    try:
        create_proxy_server(host, port, processes)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        console.print(f"[red]Error: {e}")