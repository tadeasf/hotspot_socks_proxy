"""HTTP proxy server implementation."""

import socket

from rich.console import Console

console = Console()


class HTTPProxy:
    """HTTP proxy server implementation."""

    def __init__(self, host: str, port: int) -> None:
        """Initialize the HTTP proxy server.

        Args:
            host: Host address to bind to
            port: Port number to listen on
        """
        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.running = True

    def handle_client(
        self, client_socket: socket.socket, _client_address: tuple[str, int]
    ) -> None:
        """Handle an incoming client connection.

        Args:
            client_socket: Client socket connection
            _client_address: Client address tuple (unused)
        """
        proxy_socket: socket.socket | None = None
        try:
            request = client_socket.recv(4096)
            if not request:
                return

            # Parse the first line
            first_line = request.split(b"\n")[0]
            url = first_line.split()[1]

            http_pos = url.find(b"http://")
            temp = url[http_pos + 7 :] if http_pos != -1 else url

            port_pos = temp.find(b":")
            webserver_pos = temp.find(b"/")
            if webserver_pos == -1:
                webserver_pos = len(temp)

            webserver = temp[:webserver_pos].decode("utf-8")
            port = 80

            if port_pos != -1 and port_pos < webserver_pos:
                port = int(temp[port_pos + 1 : webserver_pos])
                webserver = temp[:port_pos].decode("utf-8")

            proxy_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            proxy_socket.connect((webserver, port))
            proxy_socket.send(request)

            while self.running:
                data = proxy_socket.recv(4096)
                if not data:
                    break
                client_socket.send(data)

        except OSError as e:
            console.print(f"[red]Socket error: {e}")
        finally:
            client_socket.close()
            if proxy_socket:
                proxy_socket.close()

    def start(self) -> None:
        """Start the HTTP proxy server."""
        try:
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            console.print(
                f"[green]HTTP proxy server started on {self.host}:{self.port}"
            )

            while self.running:
                try:
                    client_socket, client_address = self.server_socket.accept()
                    self.handle_client(client_socket, client_address)
                except OSError:
                    continue

        except KeyboardInterrupt:
            self.running = False
            console.print("\n[yellow]Shutting down HTTP proxy server...")
        except Exception as e:
            console.print(f"[red]Error starting proxy: {e}")
        finally:
            self.server_socket.close()


def run_http_proxy(host: str, port: int = 8080) -> None:
    """Run HTTP proxy server.

    Args:
        host: Host address to bind to
        port: Port number to listen on
    """
    proxy = HTTPProxy(host, port)
    try:
        proxy.start()
    except Exception as e:
        console.print(f"[red]Error running HTTP proxy: {e}")
