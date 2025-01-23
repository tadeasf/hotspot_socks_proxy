"""SOCKS protocol handler implementation for the proxy server.

This module implements the SOCKS5 protocol according to RFC 1928, providing:
- Protocol negotiation and handshaking
- Authentication methods (currently no-auth)
- Address type handling (IPv4 and domain names)
- DNS resolution with fallback mechanisms
- Bi-directional data forwarding
- Connection tracking
- Error handling and reporting

The handler supports:
- CONNECT method
- IPv4 addresses
- Domain name resolution
- Configurable DNS resolvers
- Connection statistics tracking
- Timeout handling

Example:
    # The handler is automatically used by the SocksProxy server class
    server = SocksProxy((host, port), SocksHandler)
    server.serve_forever()
"""

import select
import socket
import socketserver
import struct
from typing import Final

from rich.console import Console

from hotspot_socks_proxy.core.lib.proxy_stats import proxy_stats
from hotspot_socks_proxy.core.utils.prompt.socks_ui import socks_ui

console = Console()

# SOCKS protocol constants
SOCKS_VERSION: Final = 5
CONNECT_CMD: Final = 1
ADDR_TYPE_IPV4: Final = 1
ADDR_TYPE_DOMAIN: Final = 3

# Response codes
RESP_SUCCESS: Final = 0
RESP_CMD_NOT_SUPPORTED: Final = 5
RESP_ADDR_NOT_SUPPORTED: Final = 8
RESP_HOST_UNREACHABLE: Final = 4

# Default bind address for responses
DEFAULT_BIND_ADDR: Final = "127.0.0.1"  # Changed from 0.0.0.0 for security


class SocksHandler(socketserver.BaseRequestHandler):
    """Handle incoming SOCKS5 connections."""

    def _negotiate(self) -> bool:
        """Perform SOCKS5 protocol negotiation."""
        # Get auth methods
        version, nmethods = struct.unpack("!BB", self.request.recv(2))
        if version != SOCKS_VERSION:
            return False

        # Get available methods and ignore them since we only support no-auth
        self.request.recv(nmethods)

        # Send auth method choice (0 = no auth)
        self.request.send(struct.pack("!BB", SOCKS_VERSION, 0))
        return True

    def _send_response(self, status: int, bind_addr: str = DEFAULT_BIND_ADDR, bind_port: int = 0) -> None:
        """Send SOCKS5 response."""
        # Convert bind address to bytes
        addr_bytes = socket.inet_aton(bind_addr)

        # Create response packet
        response = struct.pack("!BBBB", SOCKS_VERSION, status, 0, ADDR_TYPE_IPV4)
        response += addr_bytes + struct.pack("!H", bind_port)

        self.request.send(response)

    def _create_outbound_socket(self) -> socket.socket:
        """Create a socket bound to our chosen interface."""
        remote = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        remote.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # Set IP_TRANSPARENT to allow binding to a specific interface
        if hasattr(socket, "IP_TRANSPARENT"):
            remote.setsockopt(socket.SOL_IP, socket.IP_TRANSPARENT, 1)

        # Bind to the interface IP
        remote.bind((self.server.server_address[0], 0))

        # Set source routing if available
        if hasattr(socket, "SO_BINDTODEVICE"):
            # Get interface name from server
            iface_name = self.server.interface_name if hasattr(self.server, "interface_name") else None
            if iface_name:
                remote.setsockopt(socket.SOL_SOCKET, socket.SO_BINDTODEVICE, iface_name.encode())

        return remote

    def handle_domain_connection(self, domain: str, port: int) -> socket.socket | None:
        """Handle connection to domain name address."""
        try:
            remote = self._create_outbound_socket()

            # Resolve domain
            addrinfo = socket.getaddrinfo(domain, port, socket.AF_INET, socket.SOCK_STREAM)
            if not addrinfo:
                return None

            # Try each resolved address
            for *_, addr in addrinfo:
                try:
                    remote.connect(addr)
                    return remote
                except OSError:
                    continue
            return None
        except socket.gaierror:
            return None

    def handle_connect(self, address: str, port: int) -> None:
        """Handle CONNECT command."""
        try:
            remote = self._create_outbound_socket()

            try:
                remote.connect((address, port))
                bound_addr = remote.getsockname()
                self._send_response(RESP_SUCCESS, bound_addr[0], bound_addr[1])
                self.forward(self.request, remote)
            except OSError:
                if remote:
                    remote.close()
                self._send_response(RESP_HOST_UNREACHABLE)
                return
        except Exception as exc:
            console.print(f"[red]Error handling SOCKS connection: {exc}")
        finally:
            proxy_stats.connection_ended()

    def handle(self) -> None:
        """Handle incoming SOCKS5 connection."""
        client_addr = self.client_address
        socks_ui.connection_started(client_addr)
        try:
            # SOCKS5 initialization
            if not self._negotiate():
                return

            # Get command and address type
            header = self.request.recv(4)
            version, cmd, _, addr_type = struct.unpack("!BBBB", header)

            if version != SOCKS_VERSION:
                self._send_response(RESP_CMD_NOT_SUPPORTED)
                return

            if cmd != CONNECT_CMD:
                self._send_response(RESP_CMD_NOT_SUPPORTED)
                return

            # Handle different address types
            try:
                if addr_type == ADDR_TYPE_IPV4:
                    # IPv4
                    addr_bytes = self.request.recv(4)
                    addr = socket.inet_ntoa(addr_bytes)
                    port_data = self.request.recv(2)
                    port = struct.unpack("!H", port_data)[0]
                    self.handle_connect(addr, port)
                elif addr_type == ADDR_TYPE_DOMAIN:
                    # Domain name
                    domain_len_bytes = self.request.recv(1)
                    domain_len = struct.unpack("!B", domain_len_bytes)[0]  # Properly unpack the byte
                    domain = self.request.recv(domain_len).decode()
                    port_data = self.request.recv(2)
                    port = struct.unpack("!H", port_data)[0]

                    remote = self.handle_domain_connection(domain, port)
                    if remote:
                        bound_addr = remote.getsockname()
                        self._send_response(RESP_SUCCESS, bound_addr[0], bound_addr[1])
                        self.forward(self.request, remote)
                    else:
                        self._send_response(RESP_HOST_UNREACHABLE)
                else:
                    self._send_response(RESP_ADDR_NOT_SUPPORTED)

            except OSError:
                self._send_response(RESP_HOST_UNREACHABLE)

        except Exception as exc:
            console.print(f"[red]Error handling SOCKS connection: {exc}")
        finally:
            socks_ui.connection_ended(client_addr)
            proxy_stats.connection_ended()

    def forward(self, local: socket.socket, remote: socket.socket) -> None:
        """Forward data between local and remote sockets."""
        while True:
            # Wait for data on either socket
            r, w, e = select.select([local, remote], [], [], 60)

            if not r:  # Timeout
                break

            for sock in r:
                other = remote if sock is local else local
                try:
                    data = sock.recv(4096)
                    if not data:
                        return
                    other.send(data)
                    proxy_stats.update_bytes(len(data), 0 if sock is local else len(data))
                except OSError as sock_error:
                    console.print(f"[red]Forward error: {sock_error}")
                    return
