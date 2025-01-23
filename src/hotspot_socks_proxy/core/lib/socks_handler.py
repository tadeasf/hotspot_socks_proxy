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

import dns.exception
import dns.resolver
from rich.console import Console

from ..exceptions import DNSResolutionError
from .proxy_stats import proxy_stats

console = Console()


class SocksHandler(socketserver.BaseRequestHandler):
    def resolve_dns(self, domain: str) -> str:
        """Resolve DNS using explicit DNS resolvers with fallback"""
        resolver = dns.resolver.Resolver()
        resolver.nameservers = [
            "8.8.8.8",  # Google DNS
            "8.8.4.4",  # Google DNS Secondary
            "1.1.1.1",  # Cloudflare
            "1.0.0.1",  # Cloudflare Secondary
        ]
        resolver.timeout = 3
        resolver.lifetime = 5

        try:
            answers = resolver.resolve(domain, "A")
            if answers:
                return str(answers[0])
            raise DNSResolutionError(f"No A records found for {domain}")

        except dns.exception.DNSException as e:
            console.print(f"[yellow]DNS resolution failed for {domain}: {e!s}")
            try:
                ip = socket.gethostbyname(domain)
                console.print(f"[green]Resolved {domain} using system resolver: {ip}")
                return ip
            except socket.gaierror as e:
                raise DNSResolutionError(
                    f"Both custom and system DNS resolution failed: {e!s}"
                )

    def handle(self):
        """Handle incoming SOCKS5 connection"""
        proxy_stats.connection_started()
        try:
            # SOCKS5 initialization
            version, nmethods = struct.unpack("!BB", self.request.recv(2))
            methods = self.request.recv(nmethods)

            # We only support no authentication (0x00) for now
            self.request.send(struct.pack("!BB", 5, 0))

            # SOCKS5 connection request
            version, cmd, _, address_type = struct.unpack("!BBBB", self.request.recv(4))

            if cmd != 1:  # Only support CONNECT method
                self.request.send(struct.pack("!BBBBIH", 5, 7, 0, 1, 0, 0))
                return

            if address_type == 1:  # IPv4
                address = socket.inet_ntoa(self.request.recv(4))
            elif address_type == 3:  # Domain name
                domain_length = ord(self.request.recv(1))
                address = self.request.recv(domain_length)
                address = self.resolve_dns(address.decode())
            else:  # Unsupported address type
                self.request.send(struct.pack("!BBBBIH", 5, 8, 0, 1, 0, 0))
                return

            port = struct.unpack("!H", self.request.recv(2))[0]

            try:
                remote = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                remote.connect((address, port))
                bind_address = remote.getsockname()
                self.request.send(
                    struct.pack(
                        "!BBBBIH",
                        5,
                        0,
                        0,
                        1,
                        int(bind_address[0].replace(".", "")),
                        bind_address[1],
                    )
                )
            except Exception as e:
                console.print(f"[red]Connection failed: {e}")
                self.request.send(struct.pack("!BBBBIH", 5, 5, 0, 1, 0, 0))
                return

            self.forward(self.request, remote)

        except Exception as e:
            console.print(f"[red]Error handling SOCKS connection: {e}")
        finally:
            proxy_stats.connection_ended()

    def forward(self, local: socket.socket, remote: socket.socket):
        """Forward data between local and remote sockets"""
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
                    proxy_stats.update_bytes(
                        len(data), 0 if sock is local else len(data)
                    )
                except Exception as e:
                    console.print(f"[red]Forward error: {e}")
                    return
