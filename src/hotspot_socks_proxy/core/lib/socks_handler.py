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

    def _send_response(self, status: int, bind_addr: str = "127.0.0.1", bind_port: int = 0) -> None:
        """Send SOCKS5 response."""
        # Convert bind address to bytes
        addr_bytes = socket.inet_aton(bind_addr)

        # Create response packet
        response = struct.pack("!BBBB", SOCKS_VERSION, status, 0, ADDR_TYPE_IPV4)
        response += addr_bytes + struct.pack("!H", bind_port)

        self.request.send(response)

    def handle_domain_connection(self, domain: str, port: int) -> socket.socket | None:
        """Handle connection to domain name address."""
        try:
            # Simple direct resolution using socket.getaddrinfo
            addrinfo = socket.getaddrinfo(domain, port, socket.AF_INET, socket.SOCK_STREAM)
            if not addrinfo:
                return None

            # Try each resolved address
            for af, socktype, proto, _, addr in addrinfo:
                try:
                    remote = socket.socket(af, socktype, proto)
                    remote.settimeout(10)
                    remote.connect(addr)
                    return remote
                except OSError:
                    continue
            return None
        except socket.gaierror:
            return None

    def handle(self) -> None:
        """Handle incoming SOCKS5 connection."""
        client_addr = self.client_address
        socks_ui.connection_started(client_addr)
        try:
            # SOCKS5 initialization
            if not self._negotiate():
                return

            # Get command and address
            version, cmd, _, addr_type = struct.unpack("!BBBB", self.request.recv(4))

            if version != SOCKS_VERSION or cmd != CONNECT_CMD:
                self._send_response(RESP_CMD_NOT_SUPPORTED)
                return

            # Handle different address types
            remote = None
            try:
                if addr_type == ADDR_TYPE_IPV4:  # IPv4
                    addr = socket.inet_ntoa(self.request.recv(4))
                    port = struct.unpack("!H", self.request.recv(2))[0]
                    remote = socket.create_connection((addr, port), timeout=10)
                elif addr_type == ADDR_TYPE_DOMAIN:  # Domain name
                    domain_len = self.request.recv(1)[0]
                    domain = self.request.recv(domain_len).decode()
                    port = struct.unpack("!H", self.request.recv(2))[0]
                    remote = self.handle_domain_connection(domain, port)

                if not remote:
                    self._send_response(RESP_HOST_UNREACHABLE)
                    return

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
            socks_ui.connection_ended(client_addr)
            proxy_stats.connection_ended()

    def forward(self, local: socket.socket, remote: socket.socket) -> None:
        """Forward data between local and remote sockets."""
        while True:
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
