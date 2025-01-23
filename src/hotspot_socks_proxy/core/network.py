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

import os
import socket
from dataclasses import dataclass
from pathlib import Path

import psutil
from rich.console import Console
from rich.progress import Progress

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


def scan_interfaces() -> NetworkInterface | None:
    """Scan for available network interfaces and return the most suitable one."""
    with Progress() as progress:
        task = progress.add_task("Scanning network interfaces...", total=1)

        interfaces = []
        for name, addrs in psutil.net_if_addrs().items():
            # Skip loopback and virtual interfaces
            if name.startswith(("lo", "vmnet", "docker", "veth", "bridge", "utun")):
                continue

            # Get IPv4 address
            ipv4 = next((addr.address for addr in addrs if addr.family == socket.AF_INET), None)
            if not ipv4:
                continue

            # Check if interface is up and has valid IP
            stats = psutil.net_if_stats().get(name)
            if not stats or not stats.isup:
                continue

            # More comprehensive wireless detection
            is_wireless = (
                name.startswith(("wlan", "wifi", "en", "wlp", "wl"))
                or "802.11" in str(stats.flags)  # Check for WiFi flags
                or any(name.startswith(prefix) for prefix in ("ap", "wifi", "wlan"))
                or (Path(f"/sys/class/net/{name}/wireless").exists() if os.name != "nt" else False)
            )

            interfaces.append(NetworkInterface(name=name, ip=ipv4, is_up=True, is_wireless=is_wireless))

        progress.update(task, advance=1)

        # First try to find wireless interfaces that are actually connected
        wireless = [iface for iface in interfaces if iface.is_wireless]
        if wireless:
            # Prioritize interfaces with non-local IPs
            connected = [iface for iface in wireless if not iface.ip.startswith(("127.", "169.254."))]
            if connected:
                return connected[0]
            return wireless[0]

        # Fall back to any available interface with a valid IP
        valid_interfaces = [iface for iface in interfaces if not iface.ip.startswith(("127.", "169.254."))]
        if valid_interfaces:
            return valid_interfaces[0]

        return None
