import socket
import socketserver
import struct
import select
import multiprocessing
from rich.console import Console
from prompt_toolkit.application import Application
from prompt_toolkit.layout.containers import VSplit, HSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.key_binding import KeyBindings
from collections import deque
from datetime import datetime
import threading
import time
import psutil
import sys
import os

console = Console()

class SocksProxy(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True
    request_queue_size = 100

    def server_bind(self):
        # Enable SO_REUSEPORT
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if hasattr(socket, 'SO_REUSEPORT'):  # Not available on all platforms
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        self.socket.bind(self.server_address)
        self.server_address = self.socket.getsockname()

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
            recent = [(bytes_, ts) for bytes_, ts in self.bandwidth_history if ts > cutoff]
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

class ProxyUI:
    def __init__(self, server_ip: str):
        self.server_ip = server_ip
        self.kb = KeyBindings()
        
        @self.kb.add('c-c')
        def _(event):
            event.app.exit()

        self.output = Window(
            content=FormattedTextControl(self._get_stats_text),
            always_hide_cursor=True
        )

        self.container = HSplit([
            self.output
        ])

        self.layout = Layout(self.container)
        self.app = Application(
            layout=self.layout,
            key_bindings=self.kb,
            full_screen=True,
            mouse_support=True
        )

    def _get_stats_text(self):
        stats = proxy_stats
        bandwidth = stats.get_bandwidth()
        uptime = datetime.now() - stats.start_time
        
        cpu_percent = psutil.cpu_percent(interval=None)
        memory = psutil.Process().memory_info()
        
        # Get interface info
        interface_info = "Unknown"
        for interface, addrs in psutil.net_if_addrs().items():
            for addr in addrs:
                if addr.family == socket.AF_INET and addr.address == self.server_ip:
                    interface_info = f"{interface} ({addr.address})"
                    break
        
        # Adjust the box width based on interface info length
        box_width = max(50, len(interface_info) + 10)
        border = "═" * (box_width - 2)
        
        return [
            ('class:title', f'\n╔{border}╗\n'),
            ('class:stats', f'║ Interface: {interface_info:<{box_width-13}} ║\n'),
            ('class:stats', f'║ Active Connections: {stats.active_connections:<{box_width-22}} ║\n'),
            ('class:stats', f'║ Current Bandwidth: {self._format_bytes(bandwidth)}/s{" "*(box_width-25)} ║\n'),
            ('class:stats', f'║ Total Data Sent: {self._format_bytes(stats.total_bytes_sent)}{" "*(box_width-23)} ║\n'),
            ('class:stats', f'║ Total Data Received: {self._format_bytes(stats.total_bytes_received)}{" "*(box_width-27)} ║\n'),
            ('class:stats', f'║ Uptime: {str(uptime).split(".")[0]}{" "*(box_width-12)} ║\n'),
            ('class:stats', f'║ CPU Usage: {cpu_percent}%{" "*(box_width-15)} ║\n'),
            ('class:stats', f'║ Memory Usage: {self._format_bytes(memory.rss)}{" "*(box_width-20)} ║\n'),
            ('class:title', f'╚{border}╝\n'),
            ('class:footer', '\nPress Ctrl-C to exit')
        ]

    def _format_bytes(self, bytes_):
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_ < 1024:
                return f"{bytes_:.2f} {unit}"
            bytes_ /= 1024
        return f"{bytes_:.2f} TB"

    def run(self):
        self.app.run()

class SocksHandler(socketserver.BaseRequestHandler):
    def handle(self):
        proxy_stats.connection_started()
        try:
            # SOCKS5 initialization
            version = self.request.recv(1)
            
            if version != b'\x05':
                return
            
            # Get number of authentication methods
            nmethods = self.request.recv(1)
            methods = self.request.recv(ord(nmethods))
            
            # Send authentication method (no authentication required)
            self.request.send(b'\x05\x00')
            
            # Get request details
            version = self.request.recv(1)
            cmd = self.request.recv(1)
            rsv = self.request.recv(1)
            atyp = self.request.recv(1)
            
            if atyp == b'\x01':  # IPv4
                addr = socket.inet_ntoa(self.request.recv(4))
            elif atyp == b'\x03':  # Domain name
                length = ord(self.request.recv(1))
                addr = self.request.recv(length)
                addr = addr.decode('utf-8')
            else:
                return
            
            port = struct.unpack('>H', self.request.recv(2))[0]
            
            try:
                if cmd == b'\x01':  # CONNECT
                    remote = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    # Set socket options to prevent using default route
                    remote.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    remote.setsockopt(socket.SOL_SOCKET, socket.SO_DONTROUTE, 0)
                    remote.setsockopt(socket.IPPROTO_IP, socket.IP_TTL, 64)
                    
                    # Explicitly bind to WiFi interface IP
                    wifi_ip = self.server.server_address[0]
                    remote.bind((wifi_ip, 0))
                    
                    # Log connection details
                    console.print(f"[blue]Connecting to {addr}:{port} via {wifi_ip}")
                    
                    # Resolve address if it's a domain
                    if atyp == b'\x03':
                        try:
                            addr = socket.gethostbyname(addr)
                        except socket.gaierror as e:
                            console.print(f"[red]DNS resolution failed: {e}")
                            return
                    
                    remote.connect((addr, port))
                    local = remote.getsockname()
                    
                    # Verify the binding worked
                    actual_ip = local[0]
                    if actual_ip != wifi_ip:
                        console.print(f"[red]Warning: Connection using {actual_ip} instead of {wifi_ip}")
                        remote.close()
                        return
                    
                    reply = struct.pack("!BBBB", 5, 0, 0, 1)
                    reply += socket.inet_aton(local[0]) + struct.pack(">H", local[1])
                    self.request.send(reply)
                    
                    # Start forwarding with improved buffer size
                    self.forward(self.request, remote)
                else:
                    return
                    
            except Exception as e:
                console.print(f"[red]Connection error: {e}")
                reply = struct.pack("!BBBB", 5, 5, 0, 1)
                reply += socket.inet_aton('0.0.0.0') + struct.pack(">H", 0)
                self.request.send(reply)
                
        finally:
            proxy_stats.connection_ended()

    def forward(self, local, remote):
        buffer_size = 32768
        bytes_sent = 0
        bytes_received = 0
        
        while True:
            r, w, e = select.select([local, remote], [], [])
            
            if local in r:
                data = local.recv(buffer_size)
                if not data:
                    break
                remote.send(data)
                bytes_sent += len(data)
                
            if remote in r:
                data = remote.recv(buffer_size)
                if not data:
                    break
                local.send(data)
                bytes_received += len(data)
            
            proxy_stats.update_bytes(bytes_sent, bytes_received)
            bytes_sent = bytes_received = 0
        
        local.close()
        remote.close()

def run_server(host: str, port: int):
    """Individual process server runner"""
    try:
        # Verify we're binding to the WiFi interface
        if not is_wifi_interface(host):
            console.print(f"[red]Error: {host} is not the WiFi interface IP")
            return
            
        # Check if running as root (needed for some socket options)
        if os.name != 'nt' and os.geteuid() != 0:
            console.print("[yellow]Warning: Running without root privileges might limit some functionality")
        
        server = SocksProxy((host, port), SocksHandler)
        console.print(f"[green]Server bound to WiFi interface {host}")
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        console.print(f"[red]Server error: {e}")
    finally:
        try:
            server.server_close()
        except:
            pass

def is_wifi_interface(ip: str) -> bool:
    """Verify if the IP belongs to the WiFi interface"""
    import psutil
    for interface, addrs in psutil.net_if_addrs().items():
        if interface.startswith(('en', 'wlan', 'wifi', 'eth')):  # Common WiFi interface names
            for addr in addrs:
                if addr.family == socket.AF_INET and addr.address == ip:
                    return True
    return False

def create_proxy_server(host: str, port: int, num_processes: int):
    processes = []
    ui = ProxyUI(server_ip=host)
    
    def run_ui():
        ui.run()
    
    # Start UI in a separate thread
    ui_thread = threading.Thread(target=run_ui, daemon=True)
    ui_thread.start()
    
    try:
        # Create and start processes
        for _ in range(num_processes):
            process = multiprocessing.Process(
                target=run_server,
                args=(host, port)
            )
            process.daemon = True
            processes.append(process)
            process.start()
        
        # Wait for processes
        while processes:
            for process in list(processes):
                if not process.is_alive():
                    processes.remove(process)
                    console.print("[red]A proxy process has died unexpectedly")
                process.join(timeout=0.1)
                
    except KeyboardInterrupt:
        console.print("\n[yellow]Shutting down proxy server...")
    finally:
        for process in processes:
            if process.is_alive():
                process.terminate()
                process.join(timeout=1.0)
                if process.is_alive():
                    process.kill()