# SystemSage

[![MCP Server](https://badge.mcpx.dev?type=server)](https://badge.mcpx.dev?type=server)
[![PyPI](https://img.shields.io/pypi/v/systemsage.svg)](https://pypi.org/project/systemsage/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

A powerful cross-platform system management and monitoring tool that provides comprehensive system insights and management capabilities through Model Context Protocol (MCP).

## At a Glance

* Monitor system resources in real-time (CPU, Memory, Disk)
* Manage processes and services across different operating systems
* Track network interfaces and performance
* Monitor Docker containers and Kubernetes clusters
* Get instant system alerts and diagnostics
* Perform security checks and monitoring
* Manage system services efficiently

## Available Tools

| Tool | Description | Parameters |
|----------|-------------|------------|
| get_cpu_usage() | Get current CPU usage percentage | None |
| get_memory_usage() | Get current memory usage statistics | None |
| get_disk_usage() | Get disk usage statistics | None |
| get_network_interfaces() | Get detailed network interface information | None |
| monitor_system_resources() | Monitor system resources over time | duration: int = 10 |
| get_process_details() | Get detailed information about a process | pid: int |
| find_processes_by_name() | Find processes by name pattern | name: str |
| get_system_alerts() | Check for system alerts and issues | None |
| cleanup_temp_files() | Clean up temporary files | None |
| get_security_status() | Check system security status | None |
| get_startup_programs() | List programs that start with system | None |
| check_disk_health() | Check disk health and SMART status | None |
| get_environment_variables() | Get system environment variables | None |
| system_health_check() | Comprehensive system health check | None |
| manage_docker_containers() | Manage Docker containers | action: str, container_name: str |

## Installation

### Using pip (recommended)

```bash
# Basic installation
pip install systemsage

# With cloud features (Docker, Kubernetes)
pip install systemsage[cloud]
```

### Using uv

```bash
# Install uv first
pip install uv

# Then install systemsage
uv pip install systemsage
```


## Configuration

### Claude Desktop Setup

#### Using uvx (recommended)

```json
{
    "mcpServers": {
        "apple-books-mcp": {
            "command": "uvx",
            "args": [ "systemsage@latest" ]
        }
    }
}
```

#### Using python


```json
{
    "mcpServers": {
        "systemsage": {
            "command": "python",
            "args": ["-m", "SystemSage"]
        }
    }
}
```


### Debugging

If you cloned this repository, you can test it using Claude Desktop with below configuration:

**With Claude Desktop**

{
    "mcpServers": {
        "systemsage": {
            "command": "uv",
            "args": [
                "--directory",
                "C:/Users/sharm/Downloads/SystemSage/",
                "run",
                "systemsage"
            ]
        }
    }
}

## Features in Detail

### System Monitoring
- Real-time CPU, Memory, and Disk usage tracking
- Network interface monitoring
- Process management and tracking
- System alerts and diagnostics

### Service Management
- Start/Stop/Restart system services
- Monitor service status
- Enable/Disable services on boot
- Service health checks

### Security Features
- System security status checks
- Failed login attempts monitoring
- Open ports scanning
- File system monitoring

### Cloud Integration
- Docker container management
- Kubernetes cluster monitoring
- Cloud services status checking
- Database service monitoring

### Performance Analysis
- System bottleneck detection
- Performance history tracking
- Resource usage trends
- System health scoring

## Requirements

- Python 3.10 or higher
- psutil>=5.9.0
- fastmcp>=1.0.0
- click>=8.1.0

### Optional Dependencies

- requests>=2.31.0 (for cloud services)
- docker>=6.1.0 (for Docker management)
- kubernetes>=28.1.0 (for Kubernetes monitoring)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.