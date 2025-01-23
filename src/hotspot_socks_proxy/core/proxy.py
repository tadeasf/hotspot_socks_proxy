"""Core proxy functionality and main entry point for the SOCKS proxy server.

This module serves as the main entry point for the SOCKS proxy server functionality.
It provides a clean interface to the underlying proxy implementation by exposing
only the necessary components through its public API.

The module abstracts away the complexity of:
- Multi-process SOCKS server management
- User interface handling
- Statistics tracking
- Connection management

Example:
    from hotspot_socks_proxy.core.proxy import create_proxy_server

    # Start a SOCKS proxy server on localhost:9050 with 4 processes
    create_proxy_server("127.0.0.1", 9050, 4)

Attributes:
    __all__ (list): List of public components exposed by this module
"""

from .lib import create_proxy_server

__all__ = ["create_proxy_server"]
