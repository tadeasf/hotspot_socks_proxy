"""HTTP handler implementation."""

import select
import socket
import threading
from typing import cast

from prompt_toolkit.shortcuts import ProgressBar
from rich.console import Console

console = Console()


class HTTPProxy:
    """HTTP proxy server implementation."""

    def __init__(self, host: str, port: int) -> None:
        """Initialize the HTTP proxy server."""
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
            client_socket: The connected client socket
            _client_address: Tuple of (host, port) representing client address
        """
        remote_socket = None
        try:
            request = client_socket.recv(4096)
            if not request:
                return

            # Parse the first line
            first_line = request.split(b"\n")[0].decode("utf-8")
            url = first_line.split(" ")[1]

            # Extract hostname and port
            http_pos = url.find("://")
            temp = url if http_pos == -1 else url[(http_pos + 3) :]

            port_pos = temp.find(":")
            webserver_pos = temp.find("/")
            if webserver_pos == -1:
                webserver_pos = len(temp)

            if port_pos == -1 or webserver_pos < port_pos:
                port = 80
                webserver = temp[:webserver_pos]
            else:
                port = int(temp[(port_pos + 1) : webserver_pos])
                webserver = temp[:port_pos]

            # Connect to remote server
            remote_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            remote_socket.connect((webserver, port))
            remote_socket.send(request)

            # Forward data between client and remote server
            while True:
                # Use proper type hints for select results
                readable_sockets, _, _ = cast(
                    tuple[
                        list[socket.socket], list[socket.socket], list[socket.socket]
                    ],
                    select.select([client_socket, remote_socket], [], [], 3),
                )
                if not readable_sockets:
                    break

                for sock in readable_sockets:
                    other = remote_socket if sock is client_socket else client_socket
                    try:
                        data = sock.recv(4096)
                        if not data:
                            return
                        other.send(data)
                    except OSError:
                        return

        except OSError as e:
            console.print(f"[red]Error handling client: {e}")
        finally:
            client_socket.close()
            if remote_socket:
                remote_socket.close()

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
                    thread = threading.Thread(
                        target=self.handle_client,
                        args=(client_socket, client_address),
                        daemon=True,
                    )
                    thread.start()
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
    with ProgressBar(title="Starting HTTP proxy...") as pb:
        for _ in pb(range(1)):
            proxy = HTTPProxy(host, port)

    try:
        proxy.start()
    except Exception as e:
        console.print(f"[red]Error running HTTP proxy: {e}")
