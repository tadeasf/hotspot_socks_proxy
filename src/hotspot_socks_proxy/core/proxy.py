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
import dns.resolver
import dns.exception

console = Console()

class SocksProxy(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True
    request_queue_size = 100

    def __init__(self, server_address, RequestHandlerClass, bind_interface_ip):
        self.bind_interface_ip = bind_interface_ip  # Store the interface IP
        super().__init__(server_address, RequestHandlerClass)

    def server_bind(self):
        # Enable SO_REUSEPORT and bind to specific interface
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if hasattr(socket, 'SO_REUSEPORT'):
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
        
        return [
            ('class:title', f'\n SOCKS5 Proxy: {self.server_ip}:9050\n'),
            ('class:title', ' ' + '─' * 30 + '\n'),
            ('class:stats', f' Bandwidth: {self._format_bytes(bandwidth)}/s\n'),
            ('class:stats', f' Active Connections: {stats.active_connections}\n'),
            ('class:footer', '\n Press Ctrl-C to exit')
        ]

    def _format_bytes(self, bytes_):
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_ < 1024:
                return f"{bytes_:.1f} {unit}"
            bytes_ /= 1024
        return f"{bytes_:.1f} TB"

    def run(self):
        self.app.run()

class SocksHandler(socketserver.BaseRequestHandler):
    def resolve_dns(self, domain: str) -> str:
        """Resolve DNS using explicit DNS resolvers"""
        # Create custom resolver
        resolver = dns.resolver.Resolver()
        
        # Set custom DNS servers
        resolver.nameservers = [
            '8.8.8.8',      # Google DNS
            '8.8.4.4',      # Google DNS Secondary
            '1.1.1.1',      # Cloudflare
            '1.0.0.1',      # Cloudflare Secondary
        ]
        
        # Set timeout values
        resolver.timeout = 3
        resolver.lifetime = 5
        
        try:
            # Perform DNS query
            answers = resolver.resolve(domain, 'A')
            if answers:
                # Return the first IP address
                return str(answers[0])
            raise Exception(f"No A records found for {domain}")
            
        except dns.exception.DNSException as e:
            console.print(f"[yellow]DNS resolution failed for {domain}: {str(e)}")
            # Try system resolver as fallback
            try:
                ip = socket.gethostbyname(domain)
                console.print(f"[green]Resolved {domain} using system resolver: {ip}")
                return ip
            except socket.gaierror as e:
                raise Exception(f"Both custom and system DNS resolution failed: {str(e)}")

    def handle(self):
        proxy_stats.connection_started()
        try:
            # SOCKS5 initialization
            version = self.request.recv(1)
            
            if version != b'\x05':
                return
            
            # Get number of authentication methods
            nmethods = self.request.recv(1)
            methods = self.request.recv(int.from_bytes(nmethods, 'big'))
            
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
                length = int.from_bytes(self.request.recv(1), 'big')
                addr = self.request.recv(length)
                addr = addr.decode('utf-8')
            else:
                return
            
            port = struct.unpack('>H', self.request.recv(2))[0]
            
            try:
                if cmd == b'\x01':  # CONNECT
                    remote = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    remote.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    
                    # Get the interface IP from the server
                    bind_ip = self.server.bind_interface_ip
                    
                    # Explicitly bind to the selected interface
                    remote.bind((bind_ip, 0))
                    
                    # Resolve address if it's a domain
                    if atyp == b'\x03':
                        try:
                            resolved_ip = self.resolve_dns(addr)
                            addr = resolved_ip
                        except Exception as e:
                            console.print(f"[red]DNS resolution failed for {addr}: {e}")
                            return
                    
                    try:
                        remote.settimeout(10)
                        remote.connect((addr, port))
                        remote.settimeout(None)
                        
                        # Verify the connection is using the correct interface
                        actual_ip = remote.getsockname()[0]
                        if not actual_ip.startswith(bind_ip.rsplit('.', 1)[0]):
                            console.print(f"[red]Warning: Connection not using selected interface")
                            console.print(f"[red]Expected: {bind_ip}, Got: {actual_ip}")
                            remote.close()
                            return
                            
                        console.print(f"[green]Connected to {addr}:{port} via {bind_ip}")
                    except Exception as e:
                        console.print(f"[red]Connection failed to {addr}:{port}: {e}")
                        return
                    
                    # Send success response
                    bound_addr = remote.getsockname()[0]
                    bound_port = remote.getsockname()[1]
                    reply = struct.pack("!BBBB", 5, 0, 0, 1)
                    reply += socket.inet_aton(bound_addr) + struct.pack(">H", bound_port)
                    self.request.send(reply)
                    
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

def get_interface_name(ip):
    """Get interface name from IP address"""
    import psutil
    for interface, addrs in psutil.net_if_addrs().items():
        for addr in addrs:
            if addr.family == socket.AF_INET and addr.address == ip:
                return interface
    return None

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
        
        server = SocksProxy((host, port), SocksHandler, host)
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
    """Create and start the proxy server"""
    try:
        # Create server instance with interface IP
        server = SocksProxy((host, port), SocksHandler, host)
        console.print(f"[green]SOCKS5 proxy started on {host}:{port}")
        console.print(f"[green]Routing traffic through interface: {host}")
        
        server.serve_forever()
    except Exception as e:
        console.print(f"[red]Server error: {e}")
    finally:
        try:
            server.server_close()
        except:
            pass