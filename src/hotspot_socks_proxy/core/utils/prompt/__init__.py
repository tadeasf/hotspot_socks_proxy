"""Prompt and UI utilities."""

from hotspot_socks_proxy.core.utils.prompt.prompt import PromptHandler, console
from hotspot_socks_proxy.core.utils.prompt.proxy_ui import ProxyUI, create_proxy_ui
from hotspot_socks_proxy.core.utils.prompt.socks_ui import SocksUI

__all__ = ["console", "create_proxy_ui", "PromptHandler", "ProxyUI", "SocksUI"]
