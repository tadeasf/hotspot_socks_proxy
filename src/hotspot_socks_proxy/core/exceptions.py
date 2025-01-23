"""Custom exceptions for the proxy server.

This module defines custom exceptions used throughout the proxy server implementation.
These exceptions provide more specific error handling for:
- DNS resolution failures
- Proxy connection errors
- Network interface issues

The exceptions are designed to be caught and handled appropriately by the proxy
server components, providing meaningful error messages to the user.

Example:
    try:
        resolved_ip = resolve_dns("example.com")
    except DNSResolutionError as e:
        console.print(f"[red]Failed to resolve domain: {e}")
"""


class ProxyError(Exception):
    """Base exception for proxy errors."""


class DNSResolutionError(ProxyError):
    """Raised when DNS resolution fails."""
