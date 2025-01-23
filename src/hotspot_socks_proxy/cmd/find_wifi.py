"""WiFi interface detection and information display.

This module provides functionality for:
- Detecting WiFi interfaces
- Gathering interface information
- Displaying interface details
- MAC address lookup
- Status checking

The module uses system commands to gather detailed information about
WiFi interfaces and presents it in a formatted table using Rich.

Example:
    # Show information about the WiFi interface
    show_wifi_info()
"""

import re
import subprocess
from pathlib import Path

from rich.console import Console
from rich.table import Table

console = Console()


def get_interface_info() -> dict[str, str]:
    """Get information about the network interface.

    Returns:
        dict[str, str]: Dictionary containing interface information with keys:
            - ip: IP address
            - mac: MAC address
            - status: Interface status
    """
    result = subprocess.run(
        [str(Path("/sbin/ifconfig")), "en0"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return {"ip": "Not found", "mac": "Not found", "status": "Error"}

    output = result.stdout

    # Parse interface information
    ip_match = re.search(r"inet (\d+\.\d+\.\d+\.\d+)", output)
    mac_match = re.search(r"ether (\w\w:\w\w:\w\w:\w\w:\w\w:\w\w)", output)
    status_match = re.search(r"status: (\w+)", output)

    return {
        "ip": ip_match.group(1) if ip_match else "Not found",
        "mac": mac_match.group(1) if mac_match else "Not found",
        "status": status_match.group(1) if status_match else "Unknown",
    }


def show_wifi_info() -> dict[str, str]:
    """Display WiFi interface information and return the interface details.

    Returns:
        dict[str, str]: Dictionary containing interface information with keys:
            - ip: IP address
            - mac: MAC address
            - status: Interface status
    """
    info = get_interface_info()

    table = Table(title="WiFi Interface (en0) Information")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("IP Address", info["ip"])
    table.add_row("MAC Address", info["mac"])
    table.add_row("Status", info["status"])

    console.print(table)
    return info
