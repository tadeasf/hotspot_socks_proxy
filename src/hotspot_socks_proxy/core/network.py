import psutil
import socket
from dataclasses import dataclass
from typing import List, Optional
from rich.progress import Progress
from rich.console import Console
from prompt_toolkit import prompt
from prompt_toolkit.completion import WordCompleter

console = Console()

@dataclass
class NetworkInterface:
    name: str
    ip: str
    is_up: bool
    is_wireless: bool
    description: str = ""  # Added for better user feedback

def get_all_interfaces() -> List[NetworkInterface]:
    """Get all available network interfaces"""
    interfaces = []
    
    for name, addrs in psutil.net_if_addrs().items():
        # Skip loopback and virtual interfaces
        if name.startswith(('lo', 'vmnet', 'docker', 'veth', 'utun', 'llw', 'awdl', 'bridge')):
            continue
            
        # Get IPv4 address
        ipv4 = next((addr.address for addr in addrs 
                    if addr.family == socket.AF_INET), None)
        if not ipv4:
            continue
            
        # Check if interface is up
        stats = psutil.net_if_stats().get(name)
        if not stats or not stats.isup:
            continue
            
        # Determine if it's likely a wireless interface
        is_wireless = name.startswith(('wlan', 'wifi', 'en0'))
        
        # Create description
        description = f"{name} ({ipv4})"
        if is_wireless:
            description += " [WiFi]"
        
        interfaces.append(NetworkInterface(
            name=name,
            ip=ipv4,
            is_up=True,
            is_wireless=is_wireless,
            description=description
        ))
    
    return interfaces

def select_interface() -> Optional[NetworkInterface]:
    """Let user select network interface"""
    interfaces = get_all_interfaces()
    
    if not interfaces:
        console.print("[red]No suitable network interfaces found")
        return None
        
    # Create interface completer
    descriptions = [iface.description for iface in interfaces]
    completer = WordCompleter(descriptions, sentence=True)
    
    # Show available interfaces
    console.print("\n[cyan]Available network interfaces:")
    for i, iface in enumerate(interfaces, 1):
        console.print(f"[green]{i}.[/green] {iface.description}")
    
    try:
        # Get user selection
        selection = prompt("\nSelect interface (enter number or start typing): ", 
                         completer=completer)
        
        # Handle numeric selection
        if selection.isdigit():
            idx = int(selection) - 1
            if 0 <= idx < len(interfaces):
                return interfaces[idx]
        else:
            # Handle description selection
            for iface in interfaces:
                if iface.description == selection:
                    return iface
                    
        console.print("[red]Invalid selection")
        return None
        
    except (KeyboardInterrupt, EOFError):
        return None 