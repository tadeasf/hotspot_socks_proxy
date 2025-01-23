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

import multiprocessing
import os
import socket
import socketserver
import threading
import time

import psutil
import pyperclip
from rich.console import Console

from ..utils.prompt.proxy_ui import create_proxy_ui
from .socks_handler import SocksHandler

console = Console()


class SocksProxy(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True
    request_queue_size = 100

    def server_bind(self):
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if hasattr(socket, "SO_REUSEPORT"):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        self.socket.bind(self.server_address)
        self.server_address = self.socket.getsockname()


def is_wifi_interface(ip: str) -> bool:
    """Verify if the IP belongs to the WiFi interface"""
    for interface, addrs in psutil.net_if_addrs().items():
        if interface.startswith(("en", "wlan", "wifi", "eth")):
            for addr in addrs:
                if addr.family == socket.AF_INET and addr.address == ip:
                    return True
    return False


def run_server(host: str, port: int):
    """Individual process server runner"""
    try:
        if not is_wifi_interface(host):
            console.print(f"[red]Error: {host} is not the WiFi interface IP")
            return

        if os.name != "nt" and os.geteuid() != 0:
            console.print(
                "[yellow]Warning: Running without root privileges might limit some functionality"
            )

        server = SocksProxy((host, port), SocksHandler)
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        console.print(f"[red]Server error: {e}")
    finally:
        try:
            server.server_close()
        except:
            pass


def create_proxy_server(host: str, port: int, num_processes: int):
    """Create and run the proxy server with UI"""
    processes = []

    # Clear screen once at start
    console.clear()
    
    with console.status("[bold green]Starting proxy server...", spinner="dots") as status:
        # Initialize UI
        ui_thread = create_proxy_ui(host, port)
        ui_thread.start()

        # Copy address to clipboard
        try:
            proxy_address = f"{host}:{port}"
            pyperclip.copy(proxy_address)
            status.update("[bold green]Proxy address copied to clipboard")
            time.sleep(0.5)
        except Exception:
            pass

        # Start worker processes
        status.update(f"[bold green]Starting {num_processes} worker processes...")
        for _ in range(num_processes):
            process = multiprocessing.Process(target=run_server, args=(host, port))
            process.daemon = True
            processes.append(process)
            process.start()
            time.sleep(0.1)  # Small delay between process starts

    try:
        # Monitor processes
        while processes:
            for process in list(processes):
                if not process.is_alive():
                    processes.remove(process)
                    new_process = multiprocessing.Process(
                        target=run_server, args=(host, port)
                    )
                    new_process.daemon = True
                    processes.append(new_process)
                    new_process.start()
                process.join(timeout=0.1)

    except KeyboardInterrupt:
        console.print("\n[yellow]Shutting down proxy server...")
    finally:
        for process in processes:
            if process.is_alive():
                process.terminate()
                process.join(timeout=1.0)
                if process.is_alive():
                    process.kill()
