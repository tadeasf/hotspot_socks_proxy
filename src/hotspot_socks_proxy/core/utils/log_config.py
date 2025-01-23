"""Logging configuration for the proxy server.

This module provides centralized logging configuration using Loguru.
It sets up logging to both file and console with proper formatting
and log rotation.
"""

import sys
from pathlib import Path

from loguru import logger

# Create logs directory in user's home directory
LOG_DIR = Path.home() / ".hotspot-socks-proxy" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Configure loguru
logger.remove()  # Remove default handler

# Add console handler with custom format
logger.add(
    sys.stderr,
    format=(
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    ),
    level="INFO",
    backtrace=True,
    diagnose=True,
)

# Add file handler with rotation
logger.add(
    LOG_DIR / "proxy.log",
    rotation="10 MB",
    retention="1 week",
    compression="zip",
    format=(
        "{time:YYYY-MM-DD HH:mm:ss} | "
        "{level: <8} | "
        "{name}:{function}:{line} - "
        "{message}"
    ),
    level="DEBUG",
    backtrace=True,
    diagnose=True,
)

__all__ = ["logger", "LOG_DIR"]
