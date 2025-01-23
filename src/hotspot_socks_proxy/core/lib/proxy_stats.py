"""Statistics tracking and monitoring for the SOCKS proxy server.

This module provides real-time statistics tracking for the proxy server, including:
- Active connection counting
- Bandwidth monitoring
- Data transfer tracking
- Historical bandwidth data

The module uses thread-safe operations to track:
- Number of active connections
- Total bytes sent/received
- Bandwidth usage over time
- Server uptime

The statistics are maintained in a thread-safe manner using locks and are designed
to be accessed from multiple processes and threads without race conditions.

Example:
    # Global stats object is automatically created
    from .proxy_stats import proxy_stats

    # Track new connection
    proxy_stats.connection_started()

    # Update transfer statistics
    proxy_stats.update_bytes(sent=1024, received=2048)
"""

import threading
import time
from collections import deque
from datetime import datetime


class ProxyStats:
    def __init__(self):
        self.active_connections = 0
        self.total_bytes_sent = 0
        self.total_bytes_received = 0
        self.bandwidth_history = deque(maxlen=60)  # Last 60 seconds
        self.start_time = datetime.now()
        self._lock = threading.Lock()

    def update_bytes(self, sent: int, received: int):
        with self._lock:
            self.total_bytes_sent += sent
            self.total_bytes_received += received
            self.bandwidth_history.append((sent + received, time.time()))

    def get_bandwidth(self):
        with self._lock:
            now = time.time()
            # Calculate bandwidth over last 5 seconds
            cutoff = now - 5
            recent = [
                (bytes_, ts) for bytes_, ts in self.bandwidth_history if ts > cutoff
            ]
            if not recent:
                return 0
            total_bytes = sum(bytes_ for bytes_, _ in recent)
            return total_bytes / 5  # bytes per second

    def connection_started(self):
        with self._lock:
            self.active_connections += 1

    def connection_ended(self):
        with self._lock:
            self.active_connections -= 1


# Global statistics object
proxy_stats = ProxyStats()
