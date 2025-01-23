"""DNS resolution using dnspython."""

import socket
from typing import TYPE_CHECKING, ClassVar, cast

import dns.resolver
from rich.console import Console

from hotspot_socks_proxy.core.exceptions import DNSResolutionError

if TYPE_CHECKING:
    from dns.resolver import Resolver

console = Console()

# DNS resolver constants
DEFAULT_TIMEOUT = 1.0  # seconds
DEFAULT_LIFETIME = 3.0  # seconds
DEFAULT_NAMESERVERS = [
    "1.1.1.1",  # Cloudflare
    "8.8.8.8",  # Google
    "9.9.9.9",  # Quad9
]


class DNSResolver:
    """Simple DNS resolver using dnspython."""

    # Class-level cache to avoid memory leaks
    _resolve_cache: ClassVar[dict[str, str]] = {}

    def __init__(self) -> None:
        """Initialize the DNS resolver with default settings."""
        self.resolver = cast("Resolver", dns.resolver.Resolver())
        self.resolver.timeout = DEFAULT_TIMEOUT
        self.resolver.lifetime = DEFAULT_LIFETIME
        self.resolver.nameservers = DEFAULT_NAMESERVERS

    def resolve(self, domain: str) -> str:
        """Resolve domain name to IP address.

        Args:
            domain: Domain name to resolve

        Returns:
            str: Resolved IP address

        Raises:
            DNSResolutionError: If resolution fails
        """
        if domain in self._resolve_cache:
            return self._resolve_cache[domain]

        try:
            # Try system DNS first (fastest when it works)
            ip = socket.gethostbyname(domain)
            self._resolve_cache[domain] = ip
            return ip
        except socket.gaierror:
            try:
                # Fallback to our configured resolver
                answer = self.resolver.resolve(domain, "A")
                ip = str(
                    answer[0]
                )  # DNS record objects have proper string representation
                self._resolve_cache[domain] = ip
                return ip
            except Exception as dns_error:
                error_msg = f"Failed to resolve {domain}"
                raise DNSResolutionError(error_msg) from dns_error


# Global resolver instance
dns_resolver = DNSResolver()
