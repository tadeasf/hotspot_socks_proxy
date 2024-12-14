import socket
import socketserver
import struct
import select
import multiprocessing
from rich.console import Console

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

class SocksHandler(socketserver.BaseRequestHandler):
    def handle(self):
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
                remote.connect((addr, port))
                local = remote.getsockname()
                reply = struct.pack("!BBBB", 5, 0, 0, 1)
                reply += socket.inet_aton(local[0]) + struct.pack(">H", local[1])
                self.request.send(reply)
                
                # Start forwarding with improved buffer size
                self.forward(self.request, remote)
            else:
                return
                
        except Exception as e:
            reply = struct.pack("!BBBB", 5, 5, 0, 1)
            reply += socket.inet_aton('0.0.0.0') + struct.pack(">H", 0)
            self.request.send(reply)
            
    def forward(self, local, remote):
        buffer_size = 32768  # 32KB buffer
        
        while True:
            r, w, e = select.select([local, remote], [], [])
            
            if local in r:
                data = local.recv(buffer_size)
                if not data:
                    break
                remote.send(data)
                
            if remote in r:
                data = remote.recv(buffer_size)
                if not data:
                    break
                local.send(data)
        
        local.close()
        remote.close()

def run_server(host: str, port: int):
    """Individual process server runner"""
    try:
        server = SocksProxy((host, port), SocksHandler)
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

def create_proxy_server(host: str, port: int, num_processes: int):
    """Create and manage multiple proxy server processes"""
    processes = []
    
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
        
        # Wait for processes and monitor them
        while processes:
            for process in list(processes):
                if not process.is_alive():
                    processes.remove(process)
                    console.print("[red]A proxy process has died unexpectedly")
                process.join(timeout=0.1)
                
    except KeyboardInterrupt:
        console.print("\n[yellow]Shutting down proxy server...")
    finally:
        # Clean shutdown
        for process in processes:
            if process.is_alive():
                process.terminate()
                process.join(timeout=1.0)
                if process.is_alive():
                    process.kill()