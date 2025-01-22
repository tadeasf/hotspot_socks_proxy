# hotspot-socks-proxy

A high-performance SOCKS5 proxy server designed to route traffic through WiFi interfaces. Perfect for scenarios where you need to ensure traffic goes through a specific network interface.

## Features

- SOCKS5 proxy server with multi-process support
- Automatic WiFi interface detection
- Built-in DNS resolution with fallback options
- Real-time monitoring interface
- Clipboard integration for easy proxy configuration sharing
- Support for both Windows and Unix-like systems

## Installation

```bash
pip install hotspot-socks-proxy
```

## Usage

Run the proxy server (requires root/admin privileges):

Options:

- `--processes/-p`: Number of proxy processes (default: CPU count)
- `--port`: Port to listen on (default: 9050)

## Requirements

- Python >= 3.12
- Root/Administrator privileges for proper operation

## License

This project is licensed under the GPL-3.0 License.
