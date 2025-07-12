from SystemSage.server import mcp

# Get system metrics
print(mcp.get_cpu_usage())
print(mcp.get_memory_usage())
print(mcp.get_disk_usage())

# Monitor system resources
print(mcp.monitor_system_resources(duration=10))

# Get system alerts
print(mcp.get_system_alerts())