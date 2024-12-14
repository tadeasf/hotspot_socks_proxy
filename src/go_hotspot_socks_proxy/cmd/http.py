"""HTTP proxy functionality"""
from rich.console import Console
import socket
import select
import threading
from typing import Optional
from prompt_toolkit.shortcuts import ProgressBar

console = Console()

class HTTPProxy:
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    def handle_client(self, client_socket: socket.socket, client_address: tuple):
        try:
            request = client_socket.recv(4096)
            if not request:
                return

            # Parse the first line of the request
            first_line = request.split(b'\n')[0].decode('utf-8')
            url = first_line.split(' ')[1]

            # Extract hostname and port from URL
            http_pos = url.find("://")
            if http_pos == -1:
                temp = url
            else:
                temp = url[(http_pos + 3):]

            port_pos = temp.find(":")
            webserver_pos = temp.find("/")
            if webserver_pos == -1:
                webserver_pos = len(temp)

            if port_pos == -1 or webserver_pos < port_pos:
                port = 80
                webserver = temp[:webserver_pos]
            else:
                port = int(temp[(port_pos + 1):webserver_pos])
                webserver = temp[:port_pos]

            # Connect to remote server
            remote_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            remote_socket.connect((webserver, port))
            remote_socket.send(request)

            # Forward data between client and remote server
            while True:
                r, w, e = select.select([client_socket, remote_socket], [], [], 3)
                if not r:
                    break

                for sock in r:
                    other = remote_socket if sock is client_socket else client_socket
                    try:
                        data = sock.recv(4096)
                        if not data:
                            return
                        other.send(data)
                    except:
                        return

        except Exception as e:
            console.print(f"[red]Error handling client: {e}")
        finally:
            client_socket.close()

    def start(self):
        try:
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            console.print(f"[green]HTTP proxy server started on {self.host}:{self.port}")

            while True:
                client_socket, client_address = self.server_socket.accept()
                console.print(f"[blue]Accepted connection from {client_address[0]}:{client_address[1]}")
                client_thread = threading.Thread(
                    target=self.handle_client,
                    args=(client_socket, client_address)
                )
                client_thread.setDaemon(True)
                client_thread.start()

        except KeyboardInterrupt:
            console.print("\n[yellow]Shutting down HTTP proxy server...")
        except Exception as e:
            console.print(f"[red]Error starting proxy: {e}")
        finally:
            self.server_socket.close()

def run_http_proxy(host: str, port: int = 8080):
    """Run HTTP proxy server"""
    with ProgressBar(title="Starting HTTP proxy...") as pb:
        for _ in pb(range(1)):
            proxy = HTTPProxy(host, port)
    
    try:
        proxy.start()
    except Exception as e:
        console.print(f"[red]Error running HTTP proxy: {e}")