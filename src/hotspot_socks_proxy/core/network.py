"""Network interface detection and management.

This module provides functionality for:
- Scanning available network interfaces
- Detecting wireless interfaces
- Validating interface status
- IP address management
- Interface filtering

The module prioritizes wireless interfaces and provides detailed information about
each interface including:
- IP address
- Interface status
- Wireless capability
- Interface name

Example:
    interface = scan_interfaces()
    if interface and interface.is_wireless:
        print(f"Found wireless interface {interface.name} with IP {interface.ip}")
"""

import socket
from dataclasses import dataclass

import psutil
from rich.console import Console

console = Console()


@dataclass
class NetworkInterface:
    """Network interface representation with its key properties.

    Attributes:
        name: Interface name (e.g., 'en0', 'eth0')
        ip: IPv4 address assigned to the interface
        is_up: Boolean indicating if the interface is up and running
        is_wireless: Boolean indicating if this is a wireless interface
    """

    name: str
    ip: str
    is_up: bool
    is_wireless: bool


def get_active_interfaces() -> list[NetworkInterface]:
    """Get all active network interfaces."""
    interfaces = []
    for name, addrs in psutil.net_if_addrs().items():
        # Skip loopback and virtual interfaces
        if name.startswith(("lo", "vmnet", "docker", "veth", "bridge", "utun")):
            continue

        # Get IPv4 address
        ipv4 = next((addr.address for addr in addrs if addr.family == socket.AF_INET), None)
        if not ipv4:
            continue

        # Check if interface is up
        stats = psutil.net_if_stats().get(name)
        if not stats or not stats.isup:
            continue

        interfaces.append(NetworkInterface(name=name, ip=ipv4, is_up=True, is_wireless=False))

    return interfaces


def select_interface() -> NetworkInterface | None:
    """Let user select the network interface."""
    interfaces = get_active_interfaces()

    if not interfaces:
        console.print("[red]No active network interfaces found")
        return None

    console.print("\n[bold cyan]Available Network Interfaces:")
    for i, iface in enumerate(interfaces, 1):
        console.print(f"[green]{i}.[/green] {iface.name} - {iface.ip}")

    while True:
        try:
            choice = console.input("\n[bold yellow]Select interface number (or 'q' to quit): ")
            if choice.lower() == "q":
                return None

            idx = int(choice) - 1
            if 0 <= idx < len(interfaces):
                return interfaces[idx]

            console.print("[red]Invalid selection. Please try again.")
        except ValueError:
            console.print("[red]Please enter a valid number.")
