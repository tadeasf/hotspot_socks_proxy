# hotspot-socks-proxy

A high-performance SOCKS5 proxy server designed to route traffic through WiFi interfaces. Perfect for scenarios where you need to ensure traffic goes through a specific network interface.

## Features

### Core Functionality

- SOCKS5 proxy server with multi-process support
- Automatic WiFi interface detection and validation
- Built-in DNS resolution with multiple fallback options
- Process pool management with automatic recovery
- Clean shutdown handling

### Performance & Reliability

- Multi-process architecture for optimal performance
- Thread-safe statistics tracking
- Automatic process recovery on failure
- Configurable DNS resolvers with fallback mechanisms
- Connection pooling and timeout handling

### User Interface

- Real-time terminal UI with bandwidth monitoring
- Live connection statistics
- Clean terminal interface with borders
- Keyboard controls (Ctrl-C to exit)
- Automatic unit scaling for bandwidth display

### Network Management

- Automatic WiFi interface detection
- Interface validation and filtering
- IP address management
- Support for both wireless and fallback interfaces

### Additional Features

- Clipboard integration for easy proxy configuration sharing
- Support for both Windows and Unix-like systems
- Root privilege checking
- Comprehensive error handling and reporting

## Installation

```bash
pip install hotspot-socks-proxy
```

## Usage

Run the proxy server (requires root/admin privileges):

```bash
# Basic usage
sudo hotspot-proxy proxy

# Custom port and processes
sudo hotspot-proxy proxy --port 9050 --processes 4
```

### Options

- `--processes/-p`: Number of proxy processes (default: CPU count)
- `--port`: Port to listen on (default: 9050)

### Example Code

```python
from hotspot_socks_proxy.core.proxy import create_proxy_server

# Start a SOCKS proxy server on localhost:9050 with 4 processes
create_proxy_server("127.0.0.1", 9050, 4)
```

## Requirements

- Python >= 3.12
- Root/Administrator privileges for proper operation
- Required packages (automatically installed):
    - typer: CLI interface
    - prompt-toolkit: Terminal UI
    - rich: Pretty output formatting
    - psutil: System and process utilities
    - pyperclip: Clipboard integration
    - dnspython: DNS resolution

## Development

### Project Structure

```bash
src/hotspot_socks_proxy/
├── cmd/                 # Command-line interface modules
│   ├── cli.py          # Main CLI entry point
│   ├── find_wifi.py    # WiFi interface detection
│   ├── http.py         # HTTP proxy implementation
│   └── socks.py        # SOCKS proxy interface
├── core/               # Core functionality
│   ├── lib/            # Core library components
│   │   ├── proxy_server.py    # Multi-process server
│   │   ├── proxy_stats.py     # Statistics tracking
│   │   ├── proxy_ui.py        # Terminal UI
│   │   └── socks_handler.py   # SOCKS protocol handler
│   ├── exceptions.py   # Custom exceptions
│   ├── network.py      # Network interface management
│   └── proxy.py        # Main entry point
```

## Documentation

Full documentation is available at [[GitHub Pages URL](https://tadeasf.github.io/hotspot_socks_proxy)].

## License

This project is licensed under the GPL-3.0 License.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
