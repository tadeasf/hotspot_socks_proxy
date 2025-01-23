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

        # Get all network interfaces
        interfaces = []
        for name, addrs in psutil.net_if_addrs().items():
            # Skip loopback and virtual interfaces
            if name.startswith(
                (
                    "lo",
                    "vmnet",
                    "docker",
                    "veth",
                    "bridge",
                    "utun",
                    "llw",
                    "awdl",
                    "anpi",
                    "stf",
                    "gif",
                    "ap",
                )
            ):
                continue

            # Get IPv4 address
            ipv4 = next(
                (addr.address for addr in addrs if addr.family == socket.AF_INET), None
            )
            if not ipv4:
                continue

            # Check if interface is up
            stats = psutil.net_if_stats().get(name)
            if not stats or not stats.isup:
                continue

            # Get interface status
            try:
                import shutil
                import subprocess

                ifconfig_path = shutil.which("ifconfig")
                if not ifconfig_path:
                    console.log("ifconfig not found")
                    continue

                result = subprocess.run(
                    [ifconfig_path, name], capture_output=True, text=True, check=False
                )
                is_active = "status: active" in result.stdout
                if not is_active:
                    continue
            except Exception as e:
                console.log(f"Error checking interface {name}: {e!s}")
                continue

            # Determine if it's a wireless interface (macOS specific)
            is_wireless = name == "en0"  # On macOS, en0 is typically the built-in WiFi

            interfaces.append(
                NetworkInterface(
                    name=name, ip=ipv4, is_up=True, is_wireless=is_wireless
                )
            )

        progress.update(task, advance=1)

        # First try to find en0 (WiFi on macOS)
        wifi = next((iface for iface in interfaces if iface.name == "en0"), None)
        if wifi:
            return wifi

        # Then try other wireless interfaces
        wireless = [iface for iface in interfaces if iface.is_wireless]
        if wireless:
            return wireless[0]

        # Finally, fall back to any available interface
        if interfaces:
            return interfaces[0]

        return None
