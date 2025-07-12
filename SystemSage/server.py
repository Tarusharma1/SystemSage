import subprocess
import shutil
import re
import platform
import os
from mcp.server.fastmcp import FastMCP
import json
import datetime
import subprocess
import shutil
import platform
import urllib.request
import urllib.error
import psutil
import tempfile
import time

# Detect operating system
IS_WINDOWS = platform.system() == "Windows"
IS_LINUX = platform.system() == "Linux"
IS_MACOS = platform.system() == "Darwin"

def is_admin() -> bool:
    """Check if the script is running with administrative privileges."""
    try:
        if IS_WINDOWS:
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        else: # Linux/macOS
            return os.geteuid() == 0
    except Exception:
        return False

# Global admin status
IS_ADMIN = is_admin()

mcp = FastMCP("Cross-Platform System Management MCP",
              description="Manage services and logs on Windows and Linux via MCP server")

# ------------------ System Metrics ------------------

@mcp.tool()
def get_cpu_usage() -> str:
    """Get current CPU usage percentage."""
    usage = psutil.cpu_percent(interval=1)
    return f"Current CPU usage: {usage}%"

@mcp.tool()
def get_memory_usage() -> str:
    """Get current memory usage statistics."""
    mem = psutil.virtual_memory()
    return f"Memory usage: {mem.percent}% used ({mem.used // (1024**2)} MB of {mem.total // (1024**2)} MB)"

@mcp.tool()
def get_disk_usage() -> str:
    """Get disk usage statistics for the main system drive."""
    if IS_WINDOWS:
        disk = psutil.disk_usage('C:')
    else:
        disk = psutil.disk_usage('/')
    return f"Disk usage: {disk.percent}% used ({disk.used // (1024**3)} GB of {disk.total // (1024**3)} GB)"



@mcp.tool()
def get_network_interfaces() -> str:
    """Get detailed network interface information."""
    try:
        interfaces = psutil.net_if_addrs()
        stats = psutil.net_if_stats()
        
        result = "=== NETWORK INTERFACES ===\n"
        for interface, addresses in interfaces.items():
            result += f"\nInterface: {interface}\n"
            if interface in stats:
                stat = stats[interface]
                result += f"  Status: {'UP' if stat.isup else 'DOWN'}\n"
                result += f"  Speed: {stat.speed} Mbps\n"
                result += f"  MTU: {stat.mtu}\n"
            
            for addr in addresses:
                result += f"  {addr.family.name}: {addr.address}\n"
                if addr.netmask:
                    result += f"    Netmask: {addr.netmask}\n"
                if addr.broadcast:
                    result += f"    Broadcast: {addr.broadcast}\n"
        
        return result
    except Exception as e:
        return f"Failed to get network interfaces: {e}"

@mcp.tool()
def monitor_system_resources(duration: int = 10) -> str:
    """Monitor system resources over a specified duration (seconds)."""
    try:
        samples = []
        for i in range(duration):
            sample = {
                'time': datetime.datetime.now().strftime('%H:%M:%S'),
                'cpu': psutil.cpu_percent(interval=1),
                'memory': psutil.virtual_memory().percent,
                'disk': psutil.disk_usage('/').percent if not IS_WINDOWS else psutil.disk_usage('C:').percent
            }
            samples.append(sample)
        
        result = f"=== SYSTEM MONITORING ({duration} seconds) ===\n"
        result += "Time     CPU%   Memory%   Disk%\n"
        result += "--------------------------------\n"
        for sample in samples:
            result += f"{sample['time']}   {sample['cpu']:5.1f}   {sample['memory']:7.1f}   {sample['disk']:5.1f}\n"
        
        # Calculate averages
        avg_cpu = sum(s['cpu'] for s in samples) / len(samples)
        avg_mem = sum(s['memory'] for s in samples) / len(samples)
        avg_disk = sum(s['disk'] for s in samples) / len(samples)
        
        result += f"\nAverages: CPU {avg_cpu:.1f}%, Memory {avg_mem:.1f}%, Disk {avg_disk:.1f}%\n"
        
        return result
    except Exception as e:
        return f"Failed to monitor resources: {e}"

@mcp.tool()
def get_process_details(pid: int) -> str:
    """Get detailed information about a specific process."""
    try:
        process = psutil.Process(pid)
        
        # Get process info
        info = process.as_dict(attrs=[
            'pid', 'name', 'exe', 'cmdline', 'create_time', 'status',
            'cpu_percent', 'memory_percent', 'memory_info', 'num_threads',
            'username', 'cwd'
        ])
        
        # Format the output
        result = f"=== PROCESS DETAILS (PID: {pid}) ===\n"
        result += f"Name: {info['name']}\n"
        result += f"Executable: {info['exe']}\n"
        result += f"Command: {' '.join(info['cmdline']) if info['cmdline'] else 'N/A'}\n"
        result += f"Status: {info['status']}\n"
        result += f"User: {info['username']}\n"
        result += f"Working Directory: {info['cwd']}\n"
        result += f"Created: {datetime.datetime.fromtimestamp(info['create_time']).strftime('%Y-%m-%d %H:%M:%S')}\n"
        result += f"CPU Usage: {info['cpu_percent']}%\n"
        result += f"Memory Usage: {info['memory_percent']:.2f}%\n"
        result += f"Memory (RSS): {info['memory_info'].rss // (1024**2)} MB\n"
        result += f"Memory (VMS): {info['memory_info'].vms // (1024**2)} MB\n"
        result += f"Threads: {info['num_threads']}\n"
        
        # Get open files
        try:
            open_files = process.open_files()
            if open_files:
                result += f"\nOpen Files ({len(open_files)}):\n"
                for file in open_files[:10]:  # Show first 10
                    result += f"  {file.path}\n"
                if len(open_files) > 10:
                    result += f"  ... and {len(open_files) - 10} more\n"
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            result += "\nOpen Files: Access denied\n"
        
        return result
    except psutil.NoSuchProcess:
        return f"Process {pid} not found"
    except Exception as e:
        return f"Failed to get process details: {e}"

@mcp.tool()
def find_processes_by_name(name: str) -> str:
    """Find processes by name pattern."""
    try:
        matching_processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'status']):
            if name.lower() in proc.info['name'].lower():
                matching_processes.append(proc.info)
        
        if not matching_processes:
            return f"No processes found matching '{name}'"
        
        result = f"=== PROCESSES MATCHING '{name}' ===\n"
        result += "PID     Name                CPU%   Memory%   Status\n"
        result += "------------------------------------------------\n"
        
        for proc in matching_processes:
            result += f"{proc['pid']:<8} {proc['name']:<15} {proc['cpu_percent']:<6} {proc['memory_percent']:<9.2f} {proc['status']}\n"
        
        return result
    except Exception as e:
        return f"Failed to find processes: {e}"

@mcp.tool()
def get_system_alerts() -> str:
    """Check for system alerts and potential issues."""
    alerts = []
    
    try:
        # Check CPU usage
        cpu_usage = psutil.cpu_percent(interval=1)
        if cpu_usage > 80:
            alerts.append(f"HIGH CPU USAGE: {cpu_usage}%")
        
        # Check memory usage
        mem = psutil.virtual_memory()
        if mem.percent > 85:
            alerts.append(f"HIGH MEMORY USAGE: {mem.percent}%")
        
        # Check disk usage
        if IS_WINDOWS:
            disk = psutil.disk_usage('C:')
        else:
            disk = psutil.disk_usage('/')
        
        if disk.percent > 90:
            alerts.append(f"HIGH DISK USAGE: {disk.percent}%")
        
        # Check for zombie processes
        zombie_count = 0
        for proc in psutil.process_iter(['status']):
            if proc.info['status'] == psutil.STATUS_ZOMBIE:
                zombie_count += 1
        
        if zombie_count > 0:
            alerts.append(f"ZOMBIE PROCESSES: {zombie_count} found")
        
        # Check swap usage
        swap = psutil.swap_memory()
        if swap.percent > 50:
            alerts.append(f"HIGH SWAP USAGE: {swap.percent}%")
        
        # Check load average (Linux/macOS)
        if not IS_WINDOWS:
            try:
                load_avg = os.getloadavg()
                cpu_count = psutil.cpu_count()
                if load_avg[0] > cpu_count * 0.8:
                    alerts.append(f"HIGH LOAD AVERAGE: {load_avg[0]:.2f} (threshold: {cpu_count * 0.8:.2f})")
            except:
                pass
        
        if alerts:
            return "=== SYSTEM ALERTS ===\n" + "\n".join(f"[WARNING] {alert}" for alert in alerts)
        else:
            return "[OK] No system alerts - all metrics within normal ranges"
            
    except Exception as e:
        return f"Failed to check system alerts: {e}"

@mcp.tool()
def cleanup_temp_files() -> str:
    """Clean up temporary files to free disk space."""
    try:
        cleaned_files = 0
        freed_space = 0
        
        if IS_WINDOWS:
            temp_dirs = [
                os.environ.get('TEMP', 'C:\\temp'),
                os.environ.get('TMP', 'C:\\tmp'),
                'C:\\Windows\\Temp'
            ]
        else:
            temp_dirs = ['/tmp', '/var/tmp']
        
        for temp_dir in temp_dirs:
            if os.path.exists(temp_dir):
                for root, dirs, files in os.walk(temp_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        try:
                            # Only delete files older than 24 hours
                            if os.path.getmtime(file_path) < (datetime.datetime.now() - datetime.timedelta(hours=24)).timestamp():
                                file_size = os.path.getsize(file_path)
                                os.remove(file_path)
                                cleaned_files += 1
                                freed_space += file_size
                        except (OSError, PermissionError):
                            continue
        
        freed_mb = freed_space / (1024 * 1024)
        return f"Cleanup completed: {cleaned_files} files removed, {freed_mb:.2f} MB freed"
        
    except Exception as e:
        return f"Failed to cleanup temp files: {e}"

@mcp.tool()
def get_security_status() -> str:
    """Check system security status and potential vulnerabilities."""
    if not IS_ADMIN:
        return "[WARNING] Permission Denied: Full security status check requires administrator privileges."
    
    try:
        security_report = []
        
        # Check for processes running as root/admin
        privileged_processes = []
        for proc in psutil.process_iter(['pid', 'name', 'username']):
            try:
                if proc.info['username'] in ['root', 'SYSTEM', 'Administrator']:
                    privileged_processes.append(f"{proc.info['pid']}: {proc.info['name']}")
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                continue
        
        if privileged_processes:
            security_report.append(f"Privileged processes ({len(privileged_processes)}):")
            for proc in privileged_processes[:10]:
                security_report.append(f"  {proc}")
            if len(privileged_processes) > 10:
                security_report.append(f"  ... and {len(privileged_processes) - 10} more")
        
        # Check for unusual network connections
        connections = psutil.net_connections()
        listening_ports = [conn.laddr.port for conn in connections if conn.status == 'LISTEN']
        
        # Common suspicious ports
        suspicious_ports = [1337, 31337, 4444, 5555, 6666, 7777, 8888, 9999]
        found_suspicious = [port for port in listening_ports if port in suspicious_ports]
        
        if found_suspicious:
            security_report.append(f"Suspicious listening ports: {found_suspicious}")
        
        # Check for high resource usage processes
        high_cpu_processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent']):
            try:
                if proc.info['cpu_percent'] > 50:
                    high_cpu_processes.append(f"{proc.info['pid']}: {proc.info['name']} ({proc.info['cpu_percent']}%)")
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                continue
        
        if high_cpu_processes:
            security_report.append(f"High CPU usage processes:")
            for proc in high_cpu_processes:
                security_report.append(f"  {proc}")
        
        # Check system uptime (very low uptime might indicate recent compromise)
        boot_time = psutil.boot_time()
        uptime_hours = (datetime.datetime.now().timestamp() - boot_time) / 3600
        if uptime_hours < 1:
            security_report.append(f"[WARNING] System recently rebooted ({uptime_hours:.1f} hours ago)")
        
        if security_report:
            return "=== SECURITY STATUS ===\n" + "\n".join(security_report)
        else:
            return "[OK] No obvious security concerns detected"
            
    except Exception as e:
        return f"Failed to check security status: {e}"

@mcp.tool()
def get_startup_programs() -> str:
    """List programs that start automatically with the system."""
    try:
        if IS_WINDOWS:
            # Use PowerShell to get startup commands
            result = subprocess.run([
                "powershell", "-Command",
                "Get-CimInstance Win32_StartupCommand | Select-Object Name, Command, Location | ConvertTo-Json -Depth 2"
            ], capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                return f"Failed to get Windows startup programs:\n{result.stderr.strip()}"
            return f"=== WINDOWS STARTUP PROGRAMS ===\n{result.stdout.strip()}"

        else:
            # Use systemctl to list enabled services
            result = subprocess.run([
                "systemctl", "list-unit-files", "--type=service", "--state=enabled", "--no-pager"
            ], capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                return f"Failed to get system services:\n{result.stderr.strip()}"
            return f"=== ENABLED SYSTEM SERVICES ===\n{result.stdout.strip()}"

    except Exception as e:
        return f"Failed to get startup programs: {e}"

@mcp.tool()
def check_disk_health() -> str:
    """Check disk health and SMART status (where available)."""
    try:
        disk_info = []
        
        # Get disk usage for all partitions
        for partition in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                disk_info.append(f"""
Partition: {partition.device}
  Mountpoint: {partition.mountpoint}
  File system: {partition.fstype}
  Total: {usage.total // (1024**3)} GB
  Used: {usage.used // (1024**3)} GB ({usage.percent}%)
  Free: {usage.free // (1024**3)} GB
""")
            except PermissionError:
                disk_info.append(f"Partition: {partition.device} - Permission denied")
        
        result = "=== DISK HEALTH STATUS ===\n" + "\n".join(disk_info)
        
        # Try to get SMART data (Linux only)
        if not IS_WINDOWS:
            try:
                smart_result = subprocess.run(["smartctl", "--scan"], capture_output=True, text=True, timeout=10)
                if smart_result.returncode == 0:
                    result += "\n=== SMART STATUS ===\n"
                    result += "SMART monitoring available. Use 'smartctl -a /dev/sdX' for detailed info.\n"
                else:
                    result += "\n=== SMART STATUS ===\nSMART tools not available or no SMART-capable drives found.\n"
            except FileNotFoundError:
                result += "\n=== SMART STATUS ===\nSMART tools (smartctl) not installed.\n"
        
        return result
    except Exception as e:
        return f"Failed to check disk health: {e}"

@mcp.tool()
def get_environment_variables() -> str:
    """Get system environment variables (filtered for security)."""
    try:
        env_vars = dict(os.environ)
        
        # Filter out sensitive variables
        sensitive_keywords = ['password', 'key', 'secret', 'token', 'auth', 'credential']
        filtered_vars = {}
        
        for key, value in env_vars.items():
            if any(keyword in key.lower() for keyword in sensitive_keywords):
                filtered_vars[key] = "[FILTERED]"
            else:
                filtered_vars[key] = value
        
        result = "=== ENVIRONMENT VARIABLES ===\n"
        for key, value in sorted(filtered_vars.items()):
            result += f"{key}={value}\n"
        
        return result
    except Exception as e:
        return f"Failed to get environment variables: {e}"

@mcp.tool()
def system_health_check() -> str:
    """Comprehensive system health check combining multiple metrics."""
    try:
        health_report = []
        
        # System load - these usually work without admin
        cpu_usage = psutil.cpu_percent(interval=1)
        mem_usage = psutil.virtual_memory().percent
        
        health_report.append(f"=== SYSTEM HEALTH SUMMARY ===")
        health_report.append(f"CPU Usage: {cpu_usage}% {'[WARNING]' if cpu_usage > 80 else '[OK]'}")
        health_report.append(f"Memory Usage: {mem_usage}% {'[WARNING]' if mem_usage > 85 else '[OK]'}")
        
        # Disk usage - try to get what we can access
        try:
            if IS_WINDOWS:
                disk_usage = psutil.disk_usage('C:\\').percent

            else:
                disk_usage = psutil.disk_usage('/').percent
            health_report.append(f"Disk Usage: {disk_usage}% {'[WARNING]' if disk_usage > 90 else '[OK]'}")
        except (PermissionError, OSError):
            health_report.append("Disk Usage: Permission denied")
        
        # Process count - this usually works without admin
        process_count = len(psutil.pids())
        health_report.append(f"Running Processes: {process_count}")
        
        # Admin-only checks
        if IS_ADMIN:
            # Check for failed services
            try:
                if IS_WINDOWS:
                    result = subprocess.run([
                        "powershell", "-Command", 
                        "Get-Service | Where-Object {$_.Status -eq 'Stopped' -and $_.StartType -eq 'Automatic'} | Select-Object Name"
                    ], capture_output=True, text=True, timeout=15)
                    failed_count = max(0, len([line for line in result.stdout.strip().split('\n') if line.strip() and not line.startswith('Name')]) - 1)
                else:
                    result = subprocess.run(["systemctl", "--failed", "--no-legend"], capture_output=True, text=True, timeout=15)
                    failed_count = len([line for line in result.stdout.strip().split('\n') if line.strip()])
                
                health_report.append(f"Failed Services: {failed_count} {'[WARNING]' if failed_count > 0 else '[OK]'}")
            except:
                health_report.append("Failed Services: Unable to check")
        else:
            health_report.append("Failed Services: Requires admin access")
        
        # Overall health score based on available metrics
        issues = sum([
            1 if cpu_usage > 80 else 0,
            1 if mem_usage > 85 else 0,
            1 if 'disk_usage' in locals() and disk_usage > 90 else 0
        ])
        
        if issues == 0:
            health_report.append("\n[GOOD] OVERALL HEALTH: GOOD")
        elif issues <= 2:
            health_report.append("\n[MODERATE] OVERALL HEALTH: MODERATE - Some issues detected")
        else:
            health_report.append("\n[POOR] OVERALL HEALTH: POOR - Multiple issues detected")
        
        if not IS_ADMIN:
            health_report.append("\nNote: Some health checks were skipped due to insufficient privileges.")
        
        return "\n".join(health_report)
        
    except Exception as e:
        return f"Failed to perform health check: {e}"

# ------------------ PERFORMANCE PROFILING ------------------

@mcp.tool()
def get_performance_history(duration: int = 60) -> str:
    """Get performance metrics history over specified duration (seconds)."""
    try:
        history = []
        interval = max(1, duration // 60)  # Sample every second for up to 60 samples
        
        for i in range(0, duration, interval):
            timestamp = datetime.datetime.now()
            cpu_percent = psutil.cpu_percent(interval=interval)
            memory = psutil.virtual_memory()
            disk_io = psutil.disk_io_counters()
            net_io = psutil.net_io_counters()
            
            history.append({
                'time': timestamp.strftime('%H:%M:%S'),
                'cpu': cpu_percent,
                'memory': memory.percent,
                'disk_read': disk_io.read_bytes if disk_io else 0,
                'disk_write': disk_io.write_bytes if disk_io else 0,
                'net_sent': net_io.bytes_sent if net_io else 0,
                'net_recv': net_io.bytes_recv if net_io else 0
            })
        
        result = f"=== PERFORMANCE HISTORY ({duration}s) ===\n"
        result += "Time     CPU%   Memory%   Disk R/W (MB)   Net S/R (MB)\n"
        result += "--------------------------------------------------------\n"
        
        for i, sample in enumerate(history):
            if i > 0:
                disk_read_mb = (sample['disk_read'] - history[i-1]['disk_read']) / (1024**2)
                disk_write_mb = (sample['disk_write'] - history[i-1]['disk_write']) / (1024**2)
                net_sent_mb = (sample['net_sent'] - history[i-1]['net_sent']) / (1024**2)
                net_recv_mb = (sample['net_recv'] - history[i-1]['net_recv']) / (1024**2)
            else:
                disk_read_mb = disk_write_mb = net_sent_mb = net_recv_mb = 0
            
            result += f"{sample['time']}   {sample['cpu']:5.1f}   {sample['memory']:7.1f}   {disk_read_mb:4.1f}/{disk_write_mb:4.1f}   {net_sent_mb:4.1f}/{net_recv_mb:4.1f}\n"
        
        return result
    except Exception as e:
        return f"Failed to get performance history: {e}"

@mcp.tool()
def detect_performance_bottlenecks() -> str:
    """Detect system performance bottlenecks."""
    try:
        bottlenecks = []
        
        # CPU bottleneck detection
        cpu_usage = psutil.cpu_percent(interval=2)
        if cpu_usage > 90:
            bottlenecks.append(f"[CRITICAL] CPU BOTTLENECK: {cpu_usage}% usage")
            
            # Find top CPU consumers
            top_processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent']):
                try:
                    if proc.info['cpu_percent'] > 10:
                        top_processes.append((proc.info['pid'], proc.info['name'], proc.info['cpu_percent']))
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            if top_processes:
                top_processes.sort(key=lambda x: x[2], reverse=True)
                bottlenecks.append("  Top CPU consumers:")
                for pid, name, cpu in top_processes[:5]:
                    bottlenecks.append(f"    {pid}: {name} ({cpu}%)")
        
        # Memory bottleneck detection
        memory = psutil.virtual_memory()
        if memory.percent > 90:
            bottlenecks.append(f"[CRITICAL] MEMORY BOTTLENECK: {memory.percent}% usage")
            
            # Find top memory consumers
            top_processes = []
            for proc in psutil.process_iter(['pid', 'name', 'memory_percent']):
                try:
                    if proc.info['memory_percent'] > 5:
                        top_processes.append((proc.info['pid'], proc.info['name'], proc.info['memory_percent']))
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            if top_processes:
                top_processes.sort(key=lambda x: x[2], reverse=True)
                bottlenecks.append("  Top memory consumers:")
                for pid, name, mem in top_processes[:5]:
                    bottlenecks.append(f"    {pid}: {name} ({mem:.1f}%)")
        
        # Disk I/O bottleneck detection
        disk_io = psutil.disk_io_counters()
        if disk_io:
            # Check disk utilization (simplified)
            disk_usage = psutil.disk_usage('/').percent if not IS_WINDOWS else psutil.disk_usage('C:').percent
            if disk_usage > 95:
                bottlenecks.append(f"[CRITICAL] DISK SPACE BOTTLENECK: {disk_usage}% full")
        
        # Network bottleneck detection
        net_connections = psutil.net_connections()
        active_connections = len([conn for conn in net_connections if conn.status == 'ESTABLISHED'])
        if active_connections > 1000:
            bottlenecks.append(f"[WARNING] NETWORK BOTTLENECK: {active_connections} active connections")
        
        # Load average bottleneck (Linux/macOS)
        if not IS_WINDOWS:
            try:
                load_avg = os.getloadavg()
                cpu_count = psutil.cpu_count()
                if load_avg[0] > cpu_count * 2:
                    bottlenecks.append(f"[CRITICAL] LOAD AVERAGE BOTTLENECK: {load_avg[0]:.2f} (CPUs: {cpu_count})")
            except:
                pass
        
        if bottlenecks:
            return "=== PERFORMANCE BOTTLENECKS ===\n" + "\n".join(bottlenecks)
        else:
            return "[OK] No performance bottlenecks detected"
            
    except Exception as e:
        return f"Failed to detect bottlenecks: {e}"

# ------------------ BACKUP & RECOVERY ------------------

@mcp.tool()
def check_backup_status() -> str:
    """Check system backup status and recent backup jobs."""
    try:
        backup_info = []
        
        if IS_WINDOWS:
            # Check Windows Backup status
            result = subprocess.run([
                "powershell", "-Command", 
                "Get-WBSummary | Select-Object LastBackupTime, LastBackupResultHR, NextBackupTime | Format-List"
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                backup_info.append("=== WINDOWS BACKUP STATUS ===")
                backup_info.append(result.stdout)
            else:
                backup_info.append("=== WINDOWS BACKUP STATUS ===")
                backup_info.append("Windows Backup not configured or accessible")
            
            # Check System Restore points
            restore_result = subprocess.run([
                "powershell", "-Command", 
                "Get-ComputerRestorePoint | Select-Object CreationTime, Description, RestorePointType | Format-Table -AutoSize"
            ], capture_output=True, text=True, timeout=30)
            
            if restore_result.returncode == 0:
                backup_info.append("\n=== SYSTEM RESTORE POINTS ===")
                backup_info.append(restore_result.stdout)
        else:
            # Check common Linux backup tools
            backup_tools = {
                'rsync': 'rsync --version',
                'tar': 'tar --version',
                'duplicity': 'duplicity --version',
                'borgbackup': 'borg --version'
            }
            
            backup_info.append("=== BACKUP TOOLS STATUS ===")
            for tool, command in backup_tools.items():
                try:
                    result = subprocess.run(command.split(), capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        version = result.stdout.split('\n')[0]
                        backup_info.append(f"[OK] {tool}: {version}")
                    else:
                        backup_info.append(f"❌ {tool}: Not available")
                except:
                    backup_info.append(f"❌ {tool}: Not installed")
            
            # Check for common backup directories
            backup_dirs = ['/backup', '/backups', '/var/backups', '/home/backup']
            backup_info.append("\n=== BACKUP DIRECTORIES ===")
            for backup_dir in backup_dirs:
                if os.path.exists(backup_dir):
                    try:
                        size = sum(os.path.getsize(os.path.join(dirpath, filename))
                                 for dirpath, dirnames, filenames in os.walk(backup_dir)
                                 for filename in filenames)
                        backup_info.append(f"[OK] {backup_dir}: {size // (1024**3)} GB")
                    except:
                        backup_info.append(f"[OK] {backup_dir}: Exists (size unknown)")
                else:
                    backup_info.append(f"❌ {backup_dir}: Not found")
        
        return "\n".join(backup_info)
    except Exception as e:
        return f"Failed to check backup status: {e}"

@mcp.tool()


def create_system_snapshot() -> str:
    """Create a system configuration snapshot."""
    try:
        is_windows = platform.system() == "Windows"
        snapshot_dir = os.path.join(tempfile.gettempdir(), 'mcp_snapshot')
        os.makedirs(snapshot_dir, exist_ok=True)

        snapshot_info = []
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')

        if is_windows:
            # Avoid deprecated WMIC
            commands = {
                'system_info': 'systeminfo',
                'installed_programs': (
                    "powershell Get-ItemProperty HKLM:\\Software\\Wow6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\* "
                    "| Select-Object DisplayName, DisplayVersion"
                ),
                'services': 'sc query',
                'network_config': 'ipconfig /all',
                'firewall_rules': 'netsh advfirewall show allprofiles'
            }
        else:
            commands = {
                'system_info': 'uname -a',
                'installed_packages': 'dpkg -l',
                'services': 'systemctl list-units --type=service',
                'network_config': 'ip addr show',
                'firewall_rules': 'iptables -L'
            }

        for name, command in commands.items():
            try:
                # Run through shell=True for complex PowerShell command on Windows
                result = subprocess.run(
                    command if is_windows else command.split(),
                    capture_output=True, text=True, timeout=60,
                    shell=is_windows
                )
                file_path = os.path.join(snapshot_dir, f"{name}_{timestamp}.txt")
                with open(file_path, 'w', encoding='utf-8', errors='ignore') as f:
                    f.write(result.stdout or f"[No output from {name}]\n")
                snapshot_info.append(f"[OK] {name}: {file_path}")
            except Exception as e:
                snapshot_info.append(f"❌ {name}: Failed - {e}")

        # Create summary
        summary_path = os.path.join(snapshot_dir, f"snapshot_summary_{timestamp}.txt")
        hostname = platform.node()
        os_info = f"{platform.system()} {platform.release()}"

        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write(f"System Snapshot Created: {datetime.datetime.now()}\n")
            f.write(f"Hostname: {hostname}\n")
            f.write(f"OS: {os_info}\n\n")
            f.write("Files created:\n")
            for info in snapshot_info:
                f.write(f"{info}\n")

        return (
            f"=== SYSTEM SNAPSHOT CREATED ===\n"
            f"Snapshot directory: {snapshot_dir}\n"
            f"Summary: {summary_path}\n\n"
            + "\n".join(snapshot_info)
        )

    except Exception as e:
        return f"❌ Failed to create system snapshot: {e}"


# ------------------ UPDATE MANAGEMENT ------------------

@mcp.tool()

def check_system_updates() -> str:
    """Check for available system updates on Windows or Linux."""
    try:
        is_windows = platform.system() == "Windows"

        if is_windows:
            # Try PowerShell PSWindowsUpdate module
            ps_command = (
                "if (Get-Module -ListAvailable -Name PSWindowsUpdate) { "
                "Import-Module PSWindowsUpdate; "
                "Get-WUList | Select-Object Title, Size, Description | Format-Table -AutoSize "
                "} else { Write-Output 'PSWindowsUpdate module not installed' }"
            )
            result = subprocess.run(
                ["powershell", "-Command", ps_command],
                capture_output=True, text=True, timeout=60
            )

            output = result.stdout.strip()
            if result.returncode == 0 and "PSWindowsUpdate module not installed" not in output and output:
                return f"=== WINDOWS UPDATES (PSWindowsUpdate) ===\n{output}"

            # Fallback: show installed updates using Get-HotFix
            alt_result = subprocess.run(
                ["powershell", "-Command",
                 "Get-HotFix | Sort-Object InstalledOn -Descending | Select-Object -First 10 | Format-Table -AutoSize"],
                capture_output=True, text=True, timeout=30
            )
            alt_output = alt_result.stdout.strip()
            alt_error = alt_result.stderr.strip()

            if alt_output:
                return f"=== RECENTLY INSTALLED WINDOWS UPDATES (Get-HotFix) ===\n{alt_output}"
            elif alt_result.returncode != 0 or alt_error:
                return f"❌ PowerShell Get-HotFix failed:\n{alt_error or '[Unknown error]'}"
            else:
                return "ℹ️ No installed updates found via Get-HotFix."

        else:
            # Linux: try known package managers
            update_commands = {
                'apt': ['apt', 'list', '--upgradable'],
                'yum': ['yum', 'check-update'],
                'dnf': ['dnf', 'check-update'],
                'pacman': ['pacman', '-Qu']
            }

            for manager, command in update_commands.items():
                if shutil.which(command[0]):
                    try:
                        result = subprocess.run(command, capture_output=True, text=True, timeout=30)
                        output = (result.stdout + result.stderr).strip()
                        if output:
                            return f"=== {manager.upper()} UPDATES ===\n{output}"
                    except Exception:
                        continue

            return "❌ No supported package manager found or no updates available."

    except Exception as e:
        return f"❌ Failed to check system updates: {e}"


@mcp.tool()
def install_system_updates(confirm: bool = False) -> str:
    """Install available system updates (requires confirmation)."""
    if not confirm:
        return "[WARNING] System updates can affect system stability. Set confirm=True to proceed."
    
    try:
        if IS_WINDOWS:
            # Install Windows Updates
            result = subprocess.run([
                "powershell", "-Command", 
                "Install-WindowsUpdate -AcceptAll -AutoReboot:$false"
            ], capture_output=True, text=True, timeout=300)
            
            return f"=== WINDOWS UPDATE INSTALLATION ===\n{result.stdout}"
        else:
            # Install Linux updates
            if shutil.which('apt'):
                result = subprocess.run(['sudo', 'apt', 'update'], capture_output=True, text=True, timeout=60)
                if result.returncode == 0:
                    install_result = subprocess.run(['sudo', 'apt', 'upgrade', '-y'], capture_output=True, text=True, timeout=600)
                    return f"=== APT UPDATE INSTALLATION ===\n{install_result.stdout}"
            elif shutil.which('yum'):
                result = subprocess.run(['sudo', 'yum', 'update', '-y'], capture_output=True, text=True, timeout=600)
                return f"=== YUM UPDATE INSTALLATION ===\n{result.stdout}"
            elif shutil.which('dnf'):
                result = subprocess.run(['sudo', 'dnf', 'update', '-y'], capture_output=True, text=True, timeout=600)
                return f"=== DNF UPDATE INSTALLATION ===\n{result.stdout}"
            
            return "No supported package manager found"
    except Exception as e:
        return f"Failed to install updates: {e}"

# ------------------ ADVANCED SECURITY ------------------

@mcp.tool()
def check_failed_logins() -> str:
    """Check for failed login attempts."""
    try:
        if IS_WINDOWS:
            result = subprocess.run([
                "powershell", "-Command",
                "Get-WinEvent -FilterHashtable @{LogName='Security'; ID=4625} -MaxEvents 20 | "
                "Select-Object TimeCreated, Message | Format-Table -Wrap -AutoSize | Out-String -Width 500"
            ], capture_output=True, text=True, timeout=30)

            output = result.stdout.strip()
            if result.returncode == 0 and output:
                return f"=== FAILED LOGIN ATTEMPTS (Windows) ===\n{output}"
            else:
                return "No failed login events found or access denied."

        else:
            # Linux: check for failed login attempts in known log files
            auth_logs = ['/var/log/auth.log', '/var/log/secure', '/var/log/messages']
            for log_file in auth_logs:
                if os.path.exists(log_file):
                    try:
                        result = subprocess.run([
                            'grep', '-Ei', 'failed|failure|invalid', log_file
                        ], capture_output=True, text=True, timeout=30)

                        if result.stdout:
                            lines = result.stdout.strip().split('\n')
                            recent_failures = lines[-20:]  # Show last 20 entries
                            return f"=== FAILED LOGIN ATTEMPTS ({log_file}) ===\n" + "\n".join(recent_failures)
                    except Exception as e:
                        continue
            return "No auth log files found or no failed login attempts."

    except Exception as e:
        return f"Failed to check failed logins: {e}"



@mcp.tool()
def scan_open_ports() -> str:
    """Scan for open ports and identify potential security risks."""
    try:
        connections = psutil.net_connections(kind='inet')
        listening_ports = {}
        
        for conn in connections:
            if conn.status == 'LISTEN':
                port = conn.laddr.port
                if port not in listening_ports:
                    listening_ports[port] = []
                
                try:
                    process = psutil.Process(conn.pid) if conn.pid else None
                    proc_name = process.name() if process else "Unknown"
                    listening_ports[port].append(proc_name)
                except:
                    listening_ports[port].append("Unknown")
        
        # Define port risk levels
        high_risk_ports = [21, 23, 25, 53, 135, 139, 445, 1433, 3389, 5432, 5900]
        medium_risk_ports = [80, 443, 993, 995, 110, 143, 465, 587, 636, 989, 990]
        
        result = "=== OPEN PORTS SECURITY SCAN ===\n"
        
        high_risk_found = []
        medium_risk_found = []
        other_ports = []
        
        for port, processes in sorted(listening_ports.items()):
            port_info = f"Port {port}: {', '.join(set(processes))}"
            
            if port in high_risk_ports:
                high_risk_found.append(f"[CRITICAL] {port_info}")
            elif port in medium_risk_ports:
                medium_risk_found.append(f"[WARNING] {port_info}")
            else:
                other_ports.append(f"[OK] {port_info}")
        
        if high_risk_found:
            result += "\nHIGH RISK PORTS:\n" + "\n".join(high_risk_found)
        
        if medium_risk_found:
            result += "\n\nMEDIUM RISK PORTS:\n" + "\n".join(medium_risk_found)
        
        if other_ports:
            result += "\n\nOTHER LISTENING PORTS:\n" + "\n".join(other_ports)
        
        # Add recommendations
        result += "\n\n=== RECOMMENDATIONS ===\n"
        if high_risk_found:
            result += "[CRITICAL] High-risk ports detected. Consider:\n"
            result += "  - Closing unnecessary services\n"
            result += "  - Using firewall rules to restrict access\n"
            result += "  - Enabling authentication and encryption\n"
        
        if not high_risk_found and not medium_risk_found:
            result += "[OK] No high-risk ports detected"
        
        return result
    except Exception as e:
        return f"Failed to scan ports: {e}"

@mcp.tool()
def monitor_file_changes(directory: str = "/etc", duration: int = 300) -> str:
    """Monitor file changes in critical directories."""
    if IS_WINDOWS:
        directory = "C:\\Windows\\System32\\config"
    
    try:
        if not os.path.exists(directory):
            return f"Directory {directory} does not exist"
        
        # Take initial snapshot
        initial_files = {}
        for root, dirs, files in os.walk(directory):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    stat = os.stat(file_path)
                    initial_files[file_path] = {
                        'size': stat.st_size,
                        'mtime': stat.st_mtime
                    }
                except (OSError, PermissionError):
                    continue
        
        # Wait for specified duration
        import time
        time.sleep(duration)
        
        # Take final snapshot
        changes = []
        for root, dirs, files in os.walk(directory):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    stat = os.stat(file_path)
                    current_info = {
                        'size': stat.st_size,
                        'mtime': stat.st_mtime
                    }
                    
                    if file_path not in initial_files:
                        changes.append(f"➕ NEW: {file_path}")
                    elif (initial_files[file_path]['size'] != current_info['size'] or 
                          initial_files[file_path]['mtime'] != current_info['mtime']):
                        changes.append(f"📝 MODIFIED: {file_path}")
                        
                except (OSError, PermissionError):
                    continue
        
        # Check for deleted files
        current_files = set()
        for root, dirs, files in os.walk(directory):
            for file in files:
                current_files.add(os.path.join(root, file))
        
        for file_path in initial_files:
            if file_path not in current_files:
                changes.append(f"🗑️ DELETED: {file_path}")
        
        result = f"=== FILE CHANGES MONITOR ({directory}) ===\n"
        result += f"Monitoring duration: {duration} seconds\n\n"
        
        if changes:
            result += f"Changes detected ({len(changes)}):\n"
            result += "\n".join(changes[:50])  # Show first 50 changes
            if len(changes) > 50:
                result += f"\n... and {len(changes) - 50} more changes"
        else:
            result += "[OK] No file changes detected"
        
        return result
    except Exception as e:
        return f"Failed to monitor file changes: {e}"

# ------------------ CLOUD INTEGRATION ------------------

@mcp.tool()

def check_cloud_services() -> str:
    cloud_tools = {
        'AWS CLI': 'aws --version',
        'Azure CLI': 'az --version',
        'Google Cloud CLI': 'gcloud --version',
        'kubectl': 'kubectl version --client',
        'docker': 'docker --version',
        'terraform': 'terraform --version',
        'ansible': 'ansible --version'
    }

    result = "=== CLOUD TOOLS STATUS ===\n"

    for tool, command in cloud_tools.items():
        exe = command.split()[0]
        cmd_path = shutil.which(exe)

        if cmd_path:
            try:
                cmd = [cmd_path] + command.split()[1:]
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                output = proc.stdout or proc.stderr
                version_line = output.splitlines()[0] if output else "Unknown version"
                result += f"[OK] {tool}: {version_line.strip()}\n"
            except subprocess.TimeoutExpired:
                result += f"❌ {tool}: Timed out\n"
            except Exception as e:
                result += f"❌ {tool}: Error - {str(e)}\n"
        else:
            result += f"❌ {tool}: Not installed or not in PATH\n"

    result += "\n=== CLOUD ENVIRONMENT DETECTION ===\n"
    cloud_metadata = {
        'AWS': 'http://169.254.169.254/latest/meta-data/',
        'Azure': 'http://169.254.169.254/metadata/instance?api-version=2021-02-01',
        'Google Cloud': 'http://metadata.google.internal/computeMetadata/v1/'
    }

    for provider, url in cloud_metadata.items():
        try:
            headers = {}
            if provider == 'Google Cloud':
                headers['Metadata-Flavor'] = 'Google'
            elif provider == 'Azure':
                headers['Metadata'] = 'true'

            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=2) as response:
                if response.status == 200:
                    result += f"[OK] Running on {provider}\n"
                else:
                    result += f"❌ Not running on {provider}\n"
        except:
            result += f"❌ Not running on {provider}\n"

    return result


# ------------------ DATABASE MANAGEMENT ------------------

@mcp.tool()
def check_database_services() -> str:
    """Check status of database services and connections."""
    try:
        db_services = {
            'MySQL': ['mysql', '--version'],
            'PostgreSQL': ['psql', '--version'],
            'MongoDB': ['mongod', '--version'],
            'Redis': ['redis-server', '--version'],
            'SQLite': ['sqlite3', '--version'],
            'MariaDB': ['mariadb', '--version']
        }
        
        result = "=== DATABASE SERVICES STATUS ===\n"
        
        for db_name, command in db_services.items():
            try:
                db_result = subprocess.run(command, capture_output=True, text=True, timeout=10)
                if db_result.returncode == 0:
                    version = db_result.stdout.split('\n')[0]
                    result += f"[OK] {db_name}: {version}\n"
                else:
                    result += f"❌ {db_name}: Not available\n"
            except (FileNotFoundError, subprocess.TimeoutExpired):
                result += f"❌ {db_name}: Not installed\n"
        
        # Check for running database processes
        result += "\n=== RUNNING DATABASE PROCESSES ===\n"
        db_processes = []
        
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                proc_name = proc.info['name'].lower()
                if any(db in proc_name for db in ['mysql', 'postgres', 'mongod', 'redis', 'sqlite', 'mariadb']):
                    db_processes.append(f"{proc.info['pid']}: {proc.info['name']} (CPU: {proc.info['cpu_percent']}%, Memory: {proc.info['memory_percent']:.1f}%)")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        if db_processes:
            result += "\n".join(db_processes)
        else:
            result += "No database processes found"
        
        # Check database ports
        result += "\n\n=== DATABASE PORTS ===\n"
        db_ports = {3306: 'MySQL', 5432: 'PostgreSQL', 27017: 'MongoDB', 6379: 'Redis'}
        
        connections = psutil.net_connections(kind='inet')
        for conn in connections:
            if conn.status == 'LISTEN' and conn.laddr.port in db_ports:
                result += f"[OK] {db_ports[conn.laddr.port]} listening on port {conn.laddr.port}\n"
        
        return result
    except Exception as e:
        return f"Failed to check database services: {e}"

@mcp.tool()
def get_database_performance() -> str:
    """Get database performance metrics."""
    try:
        result = "=== DATABASE PERFORMANCE METRICS ===\n"
        
        # MySQL performance
        if shutil.which('mysql'):
            try:
                mysql_result = subprocess.run([
                    'mysql', '-e', 'SHOW GLOBAL STATUS LIKE "Connections"; SHOW GLOBAL STATUS LIKE "Queries"; SHOW GLOBAL STATUS LIKE "Slow_queries";'
                ], capture_output=True, text=True, timeout=15)
                
                if mysql_result.returncode == 0:
                    result += "[OK] MYSQL PERFORMANCE\n"
                    result += mysql_result.stdout + "\n"
            except:
                result += "MySQL performance data unavailable\n"
        
        # PostgreSQL performance
        if shutil.which('psql'):
            try:
                pg_result = subprocess.run([
                    'psql', '-c', 'SELECT datname, numbackends, xact_commit, xact_rollback FROM pg_stat_database;'
                ], capture_output=True, text=True, timeout=15)
                
                if pg_result.returncode == 0:
                    result += "[OK] POSTGRESQL PERFORMANCE\n"
                    result += pg_result.stdout + "\n"
            except:
                result += "PostgreSQL performance data unavailable\n"
        
        # Redis performance
        if shutil.which('redis-cli'):
            try:
                redis_result = subprocess.run([
                    'redis-cli', 'INFO', 'stats'
                ], capture_output=True, text=True, timeout=10)
                
                if redis_result.returncode == 0:
                    result += "[OK] REDIS PERFORMANCE\n"
                    result += redis_result.stdout + "\n"
            except:
                result += "Redis performance data unavailable\n"
        
        # MongoDB performance
        if shutil.which('mongo'):
            try:
                mongo_result = subprocess.run([
                    'mongo', '--eval', 'db.serverStatus().connections'
                ], capture_output=True, text=True, timeout=15)
                
                if mongo_result.returncode == 0:
                    result += "[OK] MONGODB PERFORMANCE\n"
                    result += mongo_result.stdout + "\n"
            except:
                result += "MongoDB performance data unavailable\n"
        
        return result
    except Exception as e:
        return f"Failed to get database performance: {e}"

# ------------------ CONTAINER ORCHESTRATION ------------------

@mcp.tool()
def get_kubernetes_status() -> str:
    """Get Kubernetes cluster status and resources."""
    try:
        if not shutil.which('kubectl'):
            return "kubectl not found - Kubernetes management unavailable"
        
        result = "=== KUBERNETES CLUSTER STATUS ===\n"
        
        # Cluster info
        try:
            cluster_result = subprocess.run(['kubectl', 'cluster-info'], capture_output=True, text=True, timeout=20)
            result += "[OK] CLUSTER INFO\n"
            result += cluster_result.stdout + "\n"
        except:
            result += "Cluster info unavailable\n"
        
        # Node status
        try:
            nodes_result = subprocess.run(['kubectl', 'get', 'nodes', '-o', 'wide'], capture_output=True, text=True, timeout=20)
            result += "[OK] NODES\n"
            result += nodes_result.stdout + "\n"
        except:
            result += "Node info unavailable\n"
        
        # Pod status
        try:
            pods_result = subprocess.run(['kubectl', 'get', 'pods', '--all-namespaces'], capture_output=True, text=True, timeout=20)
            result += "[OK] PODS (ALL NAMESPACES)\n"
            result += pods_result.stdout + "\n"
        except:
            result += "Pod info unavailable\n"
        
        # Resource usage
        try:
            top_nodes = subprocess.run(['kubectl', 'top', 'nodes'], capture_output=True, text=True, timeout=20)
            result += "[OK] NODE RESOURCE USAGE\n"
            result += top_nodes.stdout + "\n"
        except:
            result += "Node resource usage unavailable (metrics-server may not be installed)\n"
        
        # Services
        try:
            services_result = subprocess.run(['kubectl', 'get', 'services', '--all-namespaces'], capture_output=True, text=True, timeout=20)
            result += "[OK] SERVICES\n"
            result += services_result.stdout + "\n"
        except:
            result += "Service info unavailable\n"
        
        return result
    except Exception as e:
        return f"Failed to get Kubernetes status: {e}"

@mcp.tool()
def manage_docker_containers(action: str, container_name: str = "") -> str:
    """Manage Docker containers (list, start, stop, restart)."""
    try:
        if not shutil.which('docker'):
            return "Docker not found"
        
        if action == "list":
            result = subprocess.run(['docker', 'ps', '-a'], capture_output=True, text=True, timeout=30)
            return f"=== DOCKER CONTAINERS ===\n{result.stdout}"
        
        elif action == "stats":
            result = subprocess.run(['docker', 'stats', '--no-stream'], capture_output=True, text=True, timeout=30)
            return f"=== DOCKER CONTAINER STATS ===\n{result.stdout}"
        
        elif action == "images":
            result = subprocess.run(['docker', 'images'], capture_output=True, text=True, timeout=30)
            return f"=== DOCKER IMAGES ===\n{result.stdout}"
        
        elif action in ["start", "stop", "restart"] and container_name:
            result = subprocess.run(['docker', action, container_name], capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                return f"[OK] Container {container_name} {action}ed successfully"
            else:
                return f"❌ Failed to {action} container {container_name}: {result.stderr}"
        
        elif action == "logs" and container_name:
            result = subprocess.run(['docker', 'logs', '--tail', '50', container_name], capture_output=True, text=True, timeout=30)
            return f"=== DOCKER LOGS ({container_name}) ===\n{result.stdout}"
        
        else:
            return "Invalid action. Use: list, stats, images, start, stop, restart, logs"
        
    except Exception as e:
        return f"Failed to manage Docker containers: {e}"

@mcp.tool()
def get_container_resource_usage() -> str:
    """Get detailed container resource usage."""
    try:
        result = "=== CONTAINER RESOURCE USAGE ===\n"
        
        # Docker stats
        if shutil.which('docker'):
            try:
                docker_result = subprocess.run(['docker', 'stats', '--no-stream', '--format', 
                    'table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}'], 
                    capture_output=True, text=True, timeout=30)
                
                result += "[OK] DOCKER CONTAINER STATS\n"
                result += docker_result.stdout + "\n"
            except:
                result += "Docker stats unavailable\n"
        
        # Kubernetes pod resource usage
        if shutil.which('kubectl'):
            try:
                k8s_result = subprocess.run(['kubectl', 'top', 'pods', '--all-namespaces'], 
                    capture_output=True, text=True, timeout=30)
                
                result += "[OK] KUBERNETES POD RESOURCE USAGE\n"
                result += k8s_result.stdout + "\n"
            except:
                result += "Kubernetes pod stats unavailable\n"
        
        # Container process monitoring
        container_processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                proc_name = proc.info['name'].lower()
                if any(container in proc_name for container in ['docker', 'containerd', 'runc', 'kubelet']):
                    container_processes.append(f"{proc.info['pid']}: {proc.info['name']} (CPU: {proc.info['cpu_percent']}%, Memory: {proc.info['memory_percent']:.1f}%)")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        if container_processes:
            result += "\n=== CONTAINER RUNTIME PROCESSES ===\n"
            result += "\n".join(container_processes)
        
        return result
    except Exception as e:
        return f"Failed to get container resource usage: {e}"

@mcp.tool()
def enable_service(name: str) -> str:
    """Enable a system service to start on boot."""
    if not IS_ADMIN:
        return "Permission Denied: Enabling services requires administrator privileges."
    name = sanitize_service_name(name)
    try:
        if IS_WINDOWS:
            subprocess.run(["sc", "config", name, "start=", "auto"], check=True)
        else:
            subprocess.run(["sudo", "systemctl", "enable", name], check=True)
        return f"Service {name} enabled successfully."
    except Exception as e:
        return f"Failed to enable {name}: {e}"

@mcp.tool()
def disable_service(name: str) -> str:
    """Disable a system service from starting on boot."""
    if not IS_ADMIN:
        return "Permission Denied: Disabling services requires administrator privileges."
    name = sanitize_service_name(name)
    try:
        if IS_WINDOWS:
            subprocess.run(["sc", "config", name, "start=", "disabled"], check=True)
        else:
            subprocess.run(["sudo", "systemctl", "disable", name], check=True)
        return f"Service {name} disabled successfully."
    except Exception as e:
        return f"Failed to disable {name}: {e}"

@mcp.tool()
def list_installed_packages() -> str:
    """List all installed packages on the system."""
    try:
        IS_WINDOWS = platform.system() == "Windows"
        
        if IS_WINDOWS:
            powershell_cmd = (
                "Get-ItemProperty HKLM:\\Software\\Wow6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\* | "
                "Select-Object DisplayName, DisplayVersion | Format-Table -AutoSize"
            )
            result = subprocess.run([
                "powershell", "-Command", powershell_cmd
            ], capture_output=True, text=True, timeout=60)
            return result.stdout
        else:
            result = subprocess.run(["dpkg", "-l"], capture_output=True, text=True, timeout=30)
            return result.stdout
    except Exception as e:
        return f"Failed to list packages: {e}"



@mcp.tool()
def list_open_ports() -> str:
    """List all open network ports on the system."""
    try:
        if IS_WINDOWS:
            result = subprocess.run(["netstat", "-an"], capture_output=True, text=True)
        else:
            result = subprocess.run(["ss", "-tuln"], capture_output=True, text=True)
        return truncate(result.stdout)
    except Exception as e:
        return f"Failed to list open ports: {e}"

@mcp.tool()

def get_logged_in_users() -> str:
    """Get a list of currently logged-in users."""
    try:
        if IS_WINDOWS:
            # Run 'query user' via cmd.exe
            result = subprocess.run(["cmd", "/c", "query user"], capture_output=True, text=True)
        else:
            result = subprocess.run(["who"], capture_output=True, text=True)
        
        output = result.stdout.strip()
        return output if output else "No users currently logged in."
    
    except FileNotFoundError as e:
        return f"Command not found: {e}"
    except Exception as e:
        return f"Failed to retrieve user sessions: {e}"


@mcp.tool()
def list_cron_jobs(user: str = "root") -> str:
    try:
        is_windows = platform.system() == "Windows"

        if is_windows:
            result = subprocess.run([
                "powershell", "-Command", 
                "Get-ScheduledTask | Where-Object {$_.State -eq 'Ready'} | "
                "Select-Object TaskName, State | Format-Table -AutoSize"
            ], capture_output=True, text=True, timeout=30)

            output = result.stdout.strip()
            return output if output else "No scheduled tasks found."

        else:
            result = subprocess.run(
                ["crontab", "-l", "-u", user],
                capture_output=True, text=True, timeout=10
            )

            if result.returncode != 0 or not result.stdout.strip():
                return f"No crontab found for user '{user}'."

            return result.stdout.strip()

    except subprocess.CalledProcessError:
        return f"No crontab found for user '{user}'." if not is_windows else "No scheduled tasks found or access denied."

    except Exception as e:
        return f"Failed to fetch scheduled tasks/crontab: {e}"

@mcp.tool()
def system_diagnostic_summary() -> str:
    """Get a quick summary of system diagnostics including CPU, memory, and disk usage."""
    return "\n".join([
        get_cpu_usage(),
        get_memory_usage(),
        get_disk_usage(),
    ])

@mcp.tool()
def list_processes() -> str:
    """List all running processes with their PIDs."""
    processes = [f"{p.pid}: {p.name()}" for p in psutil.process_iter(['pid', 'name'])]
    return truncate("\n".join(processes), 3000)

@mcp.tool()
def kill_process(pid: int) -> str:
    """Kill a process by its PID."""
    try:
        if IS_WINDOWS:
            subprocess.run(["taskkill", "/F", "/PID", str(pid)], check=True)
        else:
            psutil.Process(pid).kill()
        return f"Process {pid} killed."
    except Exception as e:
        return f"Failed to kill process {pid}: {e}"

@mcp.tool()
def list_docker_containers() -> str:
    """List all Docker containers on the system."""
    try:
        result = subprocess.run(["docker", "ps", "-a"], capture_output=True, text=True)
        return truncate(result.stdout)
    except Exception as e:
        return f"Docker not available or failed: {e}"

@mcp.tool()
def get_system_info() -> str:
    """Get basic system information including hostname, OS, architecture, and Python version."""
    import socket
    return (
        f"Hostname: {socket.gethostname()}\n"
        f"OS: {platform.system()} {platform.release()}\n"
        f"Architecture: {platform.machine()}\n"
        f"Python version: {platform.python_version()}\n"
    )

@mcp.tool()
def list_sudo_users() -> str:
    """List all users with administrative (sudo/admin) privileges."""
    try:
        if IS_WINDOWS:
            result = subprocess.run([
                "powershell", "-Command", 
                "Get-LocalGroupMember -Group 'Administrators' | Select-Object Name | Format-Table -AutoSize"
            ], capture_output=True, text=True)
            return f"Administrator users:\n{result.stdout}"
        else:
            result = subprocess.run(["getent", "group", "sudo"], capture_output=True, text=True)
            members = result.stdout.strip().split(":")[-1].split(",")
            return f"Sudo users: {', '.join(user.strip() for user in members if user)}"
    except Exception as e:
        return f"Failed to list admin/sudo users: {e}"

# ------------------ Network Diagnostics ------------------

@mcp.tool()
def ping_host(host: str = "8.8.8.8") -> str:
    """Ping a host to check network connectivity."""
    try:
        if IS_WINDOWS:
            result = subprocess.run(["ping", "-n", "4", host], capture_output=True, text=True, timeout=10)
        else:
            result = subprocess.run(["ping", "-c", "4", host], capture_output=True, text=True, timeout=10)
        return result.stdout
    except Exception as e:
        return f"Ping failed: {e}"

@mcp.tool()
def traceroute_host(host: str = "8.8.8.8") -> str:
    """Trace the network route to a host."""
    try:
        if IS_WINDOWS:
            result = subprocess.run(["tracert", host], capture_output=True, text=True, timeout=20)
        else:
            traceroute_cmd = shutil.which("traceroute")
            if not traceroute_cmd:
                return "Traceroute not installed."
            result = subprocess.run([traceroute_cmd, host], capture_output=True, text=True, timeout=20)
        return result.stdout
    except Exception as e:
        return f"Traceroute failed: {e}"

def sanitize_service_name(name: str) -> str:
    # Allow alphanumeric, hyphens, dots, and underscores for service names
    if not re.match(r'^[a-zA-Z0-9._-]+$', name):
        raise ValueError(f"Invalid service name: {name}")
    return name

@mcp.tool()
def restart_service(name: str) -> str:
    """Restart a system service."""
    if not IS_ADMIN:
        return "[WARNING] Permission Denied: Restarting services requires administrator privileges."
    name = sanitize_service_name(name)
    try:
        if IS_WINDOWS:
            subprocess.run(["sc", "stop", name], check=True, timeout=30)
            subprocess.run(["sc", "start", name], check=True, timeout=30)
            return f"Service {name} restarted successfully."
        else:
            subprocess.run(["sudo", "systemctl", "restart", name], check=True, timeout=30)
            return f"Service {name} restarted successfully."
    except subprocess.CalledProcessError as e:
        return f"Failed to restart {name}: {e}"
    except PermissionError:
        return f"Permission denied — admin privileges required."

@mcp.tool()
def confirm_restart_service(name: str, confirm: bool = False) -> str:
    """Safely restart a service with confirmation."""
    name = sanitize_service_name(name)
    if not confirm:
        return f"Are you sure you want to restart {name}? Set confirm=True."
    return restart_service(name)

@mcp.tool()
def stop_service(name: str) -> str:
    """Stop a system service."""
    if not IS_ADMIN:
        return "[WARNING] Permission Denied: Stopping services requires administrator privileges."
    name = sanitize_service_name(name)
    try:
        if IS_WINDOWS:
            subprocess.run(["sc", "stop", name], check=True, timeout=30)
        else:
            subprocess.run(["sudo", "systemctl", "stop", name], check=True, timeout=30)
        return f"Service {name} stopped successfully."
    except Exception as e:
        return f"Failed to stop {name}: {e}"

@mcp.tool()
def start_service(name: str) -> str:
    """Start a system service."""
    if not IS_ADMIN:
        return "[WARNING] Permission Denied: Starting services requires administrator privileges."
    name = sanitize_service_name(name)
    try:
        if IS_WINDOWS:
            subprocess.run(["sc", "start", name], check=True, timeout=30)
        else:
            subprocess.run(["sudo", "systemctl", "start", name], check=True, timeout=30)
        return f"Service {name} started successfully."
    except Exception as e:
        return f"Failed to start {name}: {e}"

@mcp.tool()
def check_service_status(name: str) -> str:
    """Check the current status of a system service."""
    name = sanitize_service_name(name)
    try:
        if IS_WINDOWS:
            result = subprocess.run(["sc", "query", name], capture_output=True, text=True, timeout=10)
            return result.stdout
        else:
            result = subprocess.run(["systemctl", "status", name], capture_output=True, text=True, timeout=10)
            return result.stdout
    except Exception as e:
        return f"Failed to get status of {name}: {e}"

@mcp.tool()
def get_firewall_status() -> str:
    """Get the current status of the system firewall."""
    try:
        if IS_WINDOWS:
            result = subprocess.run(
                ["powershell", "-Command", "Get-NetFirewallProfile | Select-Object Name,Enabled"],
                capture_output=True, text=True, timeout=10
            )
            output = result.stdout.strip()
            error = result.stderr.strip()
            if output:
                return f"[OK] Windows Firewall Status:\n{output}"
            elif error:
                return f"❌ PowerShell Error:\n{error}"
            else:
                return "[WARNING] No firewall data returned."

        else:
            result = subprocess.run(["ufw", "status"], capture_output=True, text=True, timeout=10)
            output = result.stdout.strip()
            error = result.stderr.strip()
            if output:
                return f"[OK] UFW Firewall Status:\n{output}"
            elif error:
                return f"❌ Error checking UFW:\n{error}"
            else:
                return "[WARNING] No UFW output returned."

    except Exception as e:
        return f"Failed to get firewall status: {e}"

@mcp.resource("services://all")
def list_services() -> str:
    try:
        if IS_WINDOWS:
            result = subprocess.run([
                "powershell", "-Command", 
                "Get-Service | Select-Object Name, Status, StartType | Format-Table -AutoSize"
            ], capture_output=True, text=True, timeout=30)
        else:
            result = subprocess.run(["systemctl", "list-units", "--type=service", "--no-pager"], 
                                  capture_output=True, text=True, timeout=30)
        return result.stdout
    except Exception as e:
        return f"Failed to list services: {e}"

@mcp.resource("services://failed")
def list_failed_services() -> str:
    try:
        if IS_WINDOWS:
            result = subprocess.run([
                "powershell", "-Command", 
                "Get-Service | Where-Object {$_.Status -eq 'Stopped'} | Select-Object Name, Status | Format-Table -AutoSize"
            ], capture_output=True, text=True, timeout=30)
        else:
            result = subprocess.run(["systemctl", "--failed", "--no-pager"], 
                                  capture_output=True, text=True, timeout=30)
        return result.stdout
    except Exception as e:
        return f"Failed to list failed services: {e}"

@mcp.tool()
def install_package(package: str, confirm: bool = False) -> str:
    """Install a package using the system's package manager."""
    if not confirm:
        return f"Are you sure you want to install {package}? Set confirm=True to proceed."
    
    try:
        if IS_WINDOWS:
            # Try using winget
            result = subprocess.run(
                ["winget", "install", "--id", package, "-e", "--accept-source-agreements"],
                capture_output=True,
                text=True
            )
        else:
            # Try apt-get for Debian/Ubuntu
            result = subprocess.run(
                ["sudo", "apt-get", "install", "-y", package],
                capture_output=True,
                text=True
            )
        
        if result.returncode == 0:
            return f"Successfully installed {package}"
        else:
            return f"Failed to install {package}: {result.stderr}"
            
    except Exception as e:
        return f"Installation failed: {e}"

@mcp.resource("logs://{service}/export/{lines}")
def export_logs_to_file(service: str, lines: int = 100) -> str:
    """Export service logs to a file."""
    try:
        # Create logs directory if it doesn't exist
        os.makedirs("logs", exist_ok=True)
        
        # Generate filename with timestamp
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"logs/{service}_{timestamp}.log"
        
        if IS_WINDOWS:
            cmd = f"Get-EventLog -LogName Application -Source {service} -Newest {lines}"
            result = subprocess.run(["powershell", "-Command", cmd], 
                                capture_output=True, text=True)
        else:
            result = subprocess.run(["journalctl", "-u", service, "-n", str(lines)],
                                capture_output=True, text=True)
        
        with open(filename, 'w') as f:
            f.write(result.stdout)
        
        return f"Logs exported to {filename}"
    except Exception as e:
        return f"Failed to export logs: {e}"

@mcp.tool()
def list_all_available_tools() -> str:
    """List all available system management tools with descriptions."""
    tools = []
    for name, func in sorted(mcp.tools.items()):
        doc = func.__doc__ or "No description available"
        tools.append(f"{name}: {doc}")
    return "\n\n".join(tools)

# File: tools/log_tools.py

import tempfile

def clean_ansi(text):
    return re.sub(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])", "", text)

def truncate(text: str, limit: int = 5000) -> str:
    return text if len(text) < limit else text[:limit] + "\n... (truncated)"

@mcp.resource("logs://{service}/{lines}")
def get_logs(service: str, lines: int = 50) -> str:
    try:
        if IS_WINDOWS:
            result = subprocess.run([
                "powershell", "-Command", 
                f"Get-WinEvent -FilterHashtable @{{LogName='System'; ProviderName='{service}'}} -MaxEvents {lines} | Format-Table -AutoSize"
            ], capture_output=True, text=True, timeout=30)
            return truncate(clean_ansi(result.stdout))
        else:
            result = subprocess.run([
                "journalctl", "-u", service, "-n", str(lines), "--no-pager"
            ], capture_output=True, text=True, timeout=30)
            return truncate(clean_ansi(result.stdout))
    except subprocess.CalledProcessError as e:
        return f"Could not fetch logs for {service}: {e}"
    except FileNotFoundError:
        return f"Log retrieval tool not found on this system."

@mcp.resource("logs://{service}/since/{hours}")
def get_logs_since(service: str, hours: int = 1) -> str:
    try:
        if IS_WINDOWS:
            result = subprocess.run([
                "powershell", "-Command", 
                f"Get-WinEvent -FilterHashtable @{{LogName='System'; ProviderName='{service}'; StartTime=(Get-Date).AddHours(-{hours})}} | Format-Table -AutoSize"
            ], capture_output=True, text=True, timeout=30)
            return truncate(clean_ansi(result.stdout))
        else:
            result = subprocess.run([
                "journalctl", "-u", service, "--since", f"{hours} hour ago", "--no-pager"
            ], capture_output=True, text=True, timeout=30)
            return truncate(clean_ansi(result.stdout))
    except subprocess.CalledProcessError as e:
        return f"Could not fetch logs for {service}: {e}"

@mcp.resource("logs://{service}/filter/{keyword}")
def get_logs_filtered(service: str, keyword: str) -> str:
    try:
        if IS_WINDOWS:
            result = subprocess.run([
                "powershell", "-Command", 
                f"Get-WinEvent -FilterHashtable @{{LogName='System'; ProviderName='{service}'}} | Where-Object {{$_.Message -like '*{keyword}*'}} | Format-Table -AutoSize"
            ], capture_output=True, text=True, timeout=30)
            logs = result.stdout
            return logs or f"No logs found containing '{keyword}'"
        else:
            result = subprocess.run([
                "journalctl", "-u", service, "--no-pager"
            ], capture_output=True, text=True, timeout=30)
            logs = result.stdout
            filtered = "\n".join([line for line in logs.splitlines() if keyword.lower() in line.lower()])
            return filtered or f"No logs found containing '{keyword}'"
    except subprocess.CalledProcessError as e:
        return f"Could not filter logs for {service}: {e}"

@mcp.tool()


@mcp.resource("logs://{service}/export/{lines}")
def export_logs_to_file(service: str, lines: int = 100) -> str:
    try:
        if IS_WINDOWS:
            result = subprocess.run([
                "powershell", "-Command", 
                f"Get-WinEvent -FilterHashtable @{{LogName='System'; ProviderName='{service}'}} -MaxEvents {lines} | Format-Table -AutoSize"
            ], capture_output=True, text=True, timeout=30)
            log_dir = os.path.join(os.environ.get('TEMP', 'C:\\temp'), 'mcp_logs')
        else:
            result = subprocess.run([
                "journalctl", "-u", service, "-n", str(lines), "--no-pager"
            ], capture_output=True, text=True, timeout=30)
            log_dir = "/tmp/mcp_logs"
        
        os.makedirs(log_dir, exist_ok=True)
        file_path = os.path.join(log_dir, f"{service}.log")
        with open(file_path, 'w') as f:
            f.write(clean_ansi(result.stdout))
        return f"Logs saved to {file_path}"
    except subprocess.CalledProcessError as e:
        return f"Failed to export logs: {e}"


@mcp.tool()
def list_all_available_tools() -> str:
    """List all available MCP tools with descriptions."""
    tools = {
        "System Monitoring": [
            "get_cpu_usage - Get current CPU usage",
            "get_memory_usage - Get current memory usage", 
            "get_disk_usage - Get disk usage",
            "get_detailed_system_metrics - Comprehensive system metrics",
            "get_network_interfaces - Network interface details",
            "monitor_system_resources - Monitor resources over time",
            "get_system_info - Basic system information",
            "system_diagnostic_summary - Quick diagnostic summary",
            "get_system_alerts - Check for system alerts",
            "system_health_check - Comprehensive health check",
            "get_system_dashboard - Complete system dashboard"
        ],
        "Process Management": [
            "list_processes - List all running processes",
            "get_process_details - Detailed process information",
            "find_processes_by_name - Find processes by name",
            "kill_process - Kill a process by PID"
        ],
        "Performance Analysis": [
            "get_performance_history - Performance metrics over time",
            "detect_performance_bottlenecks - Identify bottlenecks",
            "monitor_system_resources - Real-time monitoring"
        ],
        "Service Management": [
            "list_services - List all services",
            "list_failed_services - List failed services",
            "check_service_status - Check service status",
            "start_service - Start a service",
            "stop_service - Stop a service", 
            "restart_service - Restart a service",
            "enable_service - Enable a service",
            "disable_service - Disable a service",
            "get_startup_programs - List startup programs"
        ],
        "Security & Monitoring": [
            "get_security_status - Security status check",
            "check_failed_logins - Check failed login attempts",
            "scan_open_ports - Scan and analyze open ports",
            "monitor_file_changes - Monitor file changes",
            "list_sudo_users - List admin/sudo users",
            "get_firewall_status - Get firewall status",
            "get_environment_variables - List environment variables"
        ],
        "Network Diagnostics": [
            "ping_host - Ping a host",
            "traceroute_host - Traceroute to host",
            "list_open_ports - List open ports",
            "get_network_interfaces - Network interface details",
            "get_logged_in_users - List logged in users"
        ],
        "System Maintenance": [
            "cleanup_temp_files - Clean temporary files",
            "check_disk_health - Check disk health",
            "install_package - Install packages",
            "list_installed_packages - List installed packages",
            "list_cron_jobs - List scheduled tasks/cron jobs"
        ],
        "Backup & Recovery": [
            "check_backup_status - Check backup status",
            "create_system_snapshot - Create system snapshot"
        ],
        "Update Management": [
            "check_system_updates - Check for updates",
            "install_system_updates - Install system updates"
        ],
        "Log Management": [
            "get_logs - Get service logs",
            "get_logs_since - Get logs since time",
            "get_logs_filtered - Get filtered logs",
            "export_logs_to_file - Export logs to file"
        ],
        "Cloud Integration": [
            "check_cloud_services - Check cloud tools status",
            "get_cloud_resource_usage - Get cloud resource usage"
        ],
        "Database Management": [
            "check_database_services - Check database services",
            "get_database_performance - Get database performance",
            "list_docker_containers - List Docker containers"
        ],
        "Container Orchestration": [
            "get_kubernetes_status - Get Kubernetes status",
            "manage_docker_containers - Manage Docker containers",
            "get_container_resource_usage - Container resource usage"
        ]
    }
    
    result = "🛠️  MCP SYSTEM MANAGEMENT TOOLS\n"
    result += "=" * 50 + "\n\n"
    
    for category, tool_list in tools.items():
        result += f"📂 {category}\n"
        result += "-" * len(category) + "\n"
        for tool in tool_list:
            result += f"  • {tool}\n"
        result += "\n"
    
    result += f"Total tools available: {sum(len(tools) for tools in tools.values())}\n"
    result += "=" * 50 + "\n"
    result += "Cross-platform support: Windows, Linux, macOS\n"
    result += "Use any tool name to get detailed information"
    
    return result

# File: main.py
# Validate system compatibility
print(f"Starting MCP Server on {platform.system()} {platform.release()}")

if IS_LINUX:
    if not shutil.which("systemctl"):
        print("WARNING: systemctl not found. Some Linux-specific features may not work.")
    if not shutil.which("journalctl"):
        print("WARNING: journalctl not found. Some logging features may not work.")

if IS_WINDOWS:
    print("Windows detected - using Windows-specific commands where applicable.")


def serve():
    mcp.run(transport="stdio")