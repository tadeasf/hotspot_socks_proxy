"""DNS resolution using dnspython."""

import socket
from typing import TYPE_CHECKING, ClassVar, NoReturn, cast

import dns.resolver
from loguru import logger
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

    def _try_system_dns(self, domain: str) -> str | None:
        """Try resolving using system DNS."""
        try:
            ip = socket.gethostbyname(domain)
            self._resolve_cache[domain] = ip
            return ip
        except socket.gaierror as e:
            logger.debug(f"System DNS resolution failed for {domain}: {e}")
            return None

    def _try_configured_resolver(self, domain: str) -> str | None:
        """Try resolving using configured resolver."""
        try:
            answer = self.resolver.resolve(domain, "A")
            ip = str(answer[0])
            self._resolve_cache[domain] = ip
            return ip
        except Exception as e:
            logger.debug(f"Configured resolver failed for {domain}: {e}")
            return None

    def _try_alternative_nameservers(self, domain: str) -> str | None:
        """Try resolving using alternative nameservers."""
        for nameserver in DEFAULT_NAMESERVERS:
            try:
                self.resolver.nameservers = [nameserver]
                answer = self.resolver.resolve(domain, "A")
                ip = str(answer[0])
                self._resolve_cache[domain] = ip
                return ip
            except Exception as e:
                logger.debug(f"Alternative nameserver {nameserver} failed for {domain}: {e}")
        return None

    def _raise_dns_error(self, msg: str) -> NoReturn:
        """Raise a DNS resolution error.

        Args:
            msg: Error message

        Raises:
            DNSResolutionError: Always raised with the given message
        """
        raise DNSResolutionError(msg)

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
            # Try each resolution method in order
            if ip := self._try_system_dns(domain):
                return ip

            if ip := self._try_configured_resolver(domain):
                return ip

            if ip := self._try_alternative_nameservers(domain):
                return ip

            error_msg = f"Could not resolve {domain} using any available method"
            logger.error(error_msg)
            self._raise_dns_error(error_msg)

        except Exception:
            error_msg = f"DNS resolution failed for {domain}"
            logger.exception(error_msg)
            self._raise_dns_error(error_msg)


# Global resolver instance
dns_resolver = DNSResolver()
