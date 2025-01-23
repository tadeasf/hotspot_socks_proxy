"""HTTP server implementation for proxy functionality."""

import socket

from rich.console import Console

console = Console()

# Constants
BUFFER_SIZE = 4096
HTTP_PREFIX = b"http://"
DEFAULT_HTTP_PORT = 80


class HTTPServer:
    """HTTP server implementation."""

    def __init__(self, host: str, port: int) -> None:
        """Initialize HTTP server.

        Args:
            host: Host address to bind to
            port: Port number to listen on
        """
        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.running = True

    def handle_client(self, client_socket: socket.socket, _: tuple[str, int]) -> None:
        """Handle client connection.

        Args:
            client_socket: Client socket connection
            _: Unused client address tuple
        """
        proxy_socket: socket.socket | None = None
        try:
            request = client_socket.recv(BUFFER_SIZE)
            if not request:
                return

            # Parse first line
            first_line = request.split(b"\n")[0]
            url = first_line.split()[1]

            # Extract host and port
            http_pos = url.find(HTTP_PREFIX)
            temp = url[http_pos + len(HTTP_PREFIX) :] if http_pos != -1 else url

            port_pos = temp.find(b":")
            webserver_pos = temp.find(b"/")
            if webserver_pos == -1:
                webserver_pos = len(temp)

            port = DEFAULT_HTTP_PORT
            webserver = temp[:webserver_pos].decode("utf-8")

            if port_pos != -1 and port_pos < webserver_pos:
                port = int(temp[port_pos + 1 : webserver_pos])
                webserver = temp[:port_pos].decode("utf-8")

            # Connect to destination
            proxy_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            proxy_socket.connect((webserver, port))
            proxy_socket.send(request)

            # Relay data
            while True:
                data = proxy_socket.recv(BUFFER_SIZE)
                if not data:
                    break
                client_socket.send(data)

        except OSError as e:
            console.print(f"[red]Socket error: {e}")
        except Exception as e:
            console.print(f"[red]Error handling client: {e}")
        finally:
            client_socket.close()
            if proxy_socket:
                proxy_socket.close()

    def start(self) -> None:
        """Start the HTTP server."""
        try:
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            console.print(f"[green]HTTP server listening on {self.host}:{self.port}")

            while self.running:
                client_socket, client_address = self.server_socket.accept()
                try:
                    self.handle_client(client_socket, client_address)
                except OSError:
                    # Log error but continue accepting connections
                    console.print("[yellow]Connection error occurred")
                    continue

        except KeyboardInterrupt:
            self.running = False
            console.print("\n[yellow]Shutting down HTTP server...")
        finally:
            self.server_socket.close()


def run_http_server(host: str, port: int = 8080) -> None:
    """Run HTTP server.

    Args:
        host: Host address to bind to
        port: Port number to listen on
    """
    server = HTTPServer(host, port)
    server.start()
