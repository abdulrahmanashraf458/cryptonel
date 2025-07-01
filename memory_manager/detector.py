"""
System Detector Module
--------------------
Detects and monitors system capabilities such as CPU, memory, disk, and network resources.
Provides real-time information about available resources for decision-making.
"""

import os
import sys
import time
import platform
import logging
import threading
import psutil
import socket
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict, field

logger = logging.getLogger("memory_manager.detector")

@dataclass
class SystemInfo:
    """Information about the system hardware and resources"""
    # System identification
    hostname: str = ""
    platform: str = ""
    platform_release: str = ""
    python_version: str = ""
    cpu_architecture: str = ""
    process_id: int = 0
    
    # CPU
    cpu_count_physical: int = 0
    cpu_count_logical: int = 0
    cpu_frequency_mhz: float = 0.0
    cpu_frequency_max_mhz: float = 0.0
    
    # Memory
    total_memory_bytes: int = 0
    available_memory_bytes: int = 0
    total_memory_gb: float = 0.0
    available_memory_gb: float = 0.0
    
    # Swap
    swap_total_bytes: int = 0
    swap_available_bytes: int = 0
    swap_total_gb: float = 0.0
    swap_available_gb: float = 0.0
    
    # Disk
    disk_total_bytes: int = 0
    disk_available_bytes: int = 0
    disk_total_gb: float = 0.0
    disk_available_gb: float = 0.0
    disk_path: str = ""
    
    # Network interfaces
    network_interfaces: List[str] = field(default_factory=list)
    
    # Last update timestamp
    updated_at: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return asdict(self)
    
    def __str__(self) -> str:
        """String representation with key information"""
        return (
            f"System: {self.platform} {self.platform_release} ({self.cpu_architecture})\n"
            f"CPU: {self.cpu_count_logical} logical cores, {self.cpu_frequency_mhz:.0f}MHz\n"
            f"Memory: {self.total_memory_gb:.1f}GB total, {self.available_memory_gb:.1f}GB available\n"
            f"Swap: {self.swap_total_gb:.1f}GB total, {self.swap_available_gb:.1f}GB available\n"
            f"Disk: {self.disk_total_gb:.1f}GB total, {self.disk_available_gb:.1f}GB available on {self.disk_path}"
        )

@dataclass
class ResourceUsage:
    """Current resource usage snapshot"""
    # Timestamp
    timestamp: float = 0.0
    
    # CPU usage (percent)
    cpu_percent: float = 0.0
    cpu_percent_per_core: List[float] = field(default_factory=list)
    load_averages: List[float] = field(default_factory=list)
    
    # Memory usage
    memory_used_bytes: int = 0
    memory_available_bytes: int = 0
    memory_percent: float = 0.0
    memory_used_gb: float = 0.0
    memory_available_gb: float = 0.0
    
    # Swap usage
    swap_used_bytes: int = 0
    swap_percent: float = 0.0
    swap_used_gb: float = 0.0
    
    # Disk I/O
    disk_read_bytes_sec: int = 0
    disk_write_bytes_sec: int = 0
    disk_read_count_sec: int = 0
    disk_write_count_sec: int = 0
    
    # Network I/O
    net_sent_bytes_sec: int = 0
    net_recv_bytes_sec: int = 0
    net_packets_sent_sec: int = 0
    net_packets_recv_sec: int = 0
    
    # Process specific
    process_memory_bytes: int = 0
    process_memory_percent: float = 0.0
    process_cpu_percent: float = 0.0
    process_threads: int = 0
    process_open_files: int = 0
    
    # System summary
    system_uptime_seconds: float = 0.0
    process_uptime_seconds: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return asdict(self)


class SystemDetector:
    """Detects system capabilities and monitors resource usage in real-time"""
    
    def __init__(self, config=None):
        """Initialize the system detector"""
        self.config = config
        self.process = psutil.Process(os.getpid())
        self.process_start_time = self.process.create_time()
        
        # Initialize system info
        self.system_info = SystemInfo()
        self.refresh_system_info()
        
        # Initialize usage data
        self.current_usage = ResourceUsage()
        self.last_usage = ResourceUsage()
        self.last_check_time = 0.0
        self.last_io_counters = None
        self.last_net_counters = None
        
        # Initialize history tracking
        self.history_lock = threading.RLock()
        self.usage_history = []
        self.history_size = config.monitoring.history_size if config else 720
        
        # Background monitoring thread
        self.monitor_thread = None
        self.running = False
        
        logger.info(f"System detector initialized on {self.system_info.hostname}")
        logger.info(str(self.system_info))
    
    def refresh_system_info(self) -> SystemInfo:
        """Refresh system information (hardware capabilities)"""
        try:
            # System identification
            self.system_info.hostname = socket.gethostname()
            self.system_info.platform = platform.system()
            self.system_info.platform_release = platform.release()
            self.system_info.python_version = platform.python_version()
            self.system_info.cpu_architecture = platform.machine()
            self.system_info.process_id = os.getpid()
            
            # CPU information
            self.system_info.cpu_count_physical = psutil.cpu_count(logical=False) or 1
            self.system_info.cpu_count_logical = psutil.cpu_count(logical=True) or 1
            
            cpu_freq = psutil.cpu_freq()
            if cpu_freq:
                self.system_info.cpu_frequency_mhz = cpu_freq.current
                self.system_info.cpu_frequency_max_mhz = cpu_freq.max or cpu_freq.current
            
            # Memory information
            mem = psutil.virtual_memory()
            self.system_info.total_memory_bytes = mem.total
            self.system_info.available_memory_bytes = mem.available
            self.system_info.total_memory_gb = mem.total / (1024**3)
            self.system_info.available_memory_gb = mem.available / (1024**3)
            
            # Swap information
            swap = psutil.swap_memory()
            self.system_info.swap_total_bytes = swap.total
            self.system_info.swap_available_bytes = swap.total - swap.used
            self.system_info.swap_total_gb = swap.total / (1024**3)
            self.system_info.swap_available_gb = (swap.total - swap.used) / (1024**3)
            
            # Disk information - focused on the main disk where the application is running
            disk_path = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
            disk = psutil.disk_usage(disk_path)
            self.system_info.disk_total_bytes = disk.total
            self.system_info.disk_available_bytes = disk.free
            self.system_info.disk_total_gb = disk.total / (1024**3)
            self.system_info.disk_available_gb = disk.free / (1024**3)
            self.system_info.disk_path = disk_path
            
            # Network interfaces
            self.system_info.network_interfaces = list(psutil.net_if_addrs().keys())
            
            # Update timestamp
            self.system_info.updated_at = time.time()
            
            return self.system_info
            
        except Exception as e:
            logger.error(f"Error refreshing system info: {e}")
            return self.system_info
    
    def get_resource_usage(self) -> ResourceUsage:
        """Get current resource usage snapshot"""
        current_time = time.time()
        
        # Create new usage object
        usage = ResourceUsage()
        usage.timestamp = current_time
        
        try:
            # CPU usage
            usage.cpu_percent = psutil.cpu_percent(interval=None)
            usage.cpu_percent_per_core = psutil.cpu_percent(interval=None, percpu=True)
            
            if hasattr(os, 'getloadavg'):
                try:
                    usage.load_averages = list(os.getloadavg())
                except:
                    usage.load_averages = []
            
            # Memory usage
            mem = psutil.virtual_memory()
            usage.memory_used_bytes = mem.used
            usage.memory_available_bytes = mem.available
            usage.memory_percent = mem.percent
            usage.memory_used_gb = mem.used / (1024**3)
            usage.memory_available_gb = mem.available / (1024**3)
            
            # Swap usage
            swap = psutil.swap_memory()
            usage.swap_used_bytes = swap.used
            usage.swap_percent = swap.percent
            usage.swap_used_gb = swap.used / (1024**3)
            
            # Disk I/O rates
            io_counters = psutil.disk_io_counters()
            if io_counters and self.last_io_counters:
                time_diff = current_time - self.last_check_time
                if time_diff > 0:
                    usage.disk_read_bytes_sec = (io_counters.read_bytes - self.last_io_counters.read_bytes) / time_diff
                    usage.disk_write_bytes_sec = (io_counters.write_bytes - self.last_io_counters.write_bytes) / time_diff
                    usage.disk_read_count_sec = (io_counters.read_count - self.last_io_counters.read_count) / time_diff
                    usage.disk_write_count_sec = (io_counters.write_count - self.last_io_counters.write_count) / time_diff
            self.last_io_counters = io_counters
            
            # Network I/O rates
            net_counters = psutil.net_io_counters()
            if net_counters and self.last_net_counters:
                time_diff = current_time - self.last_check_time
                if time_diff > 0:
                    usage.net_sent_bytes_sec = (net_counters.bytes_sent - self.last_net_counters.bytes_sent) / time_diff
                    usage.net_recv_bytes_sec = (net_counters.bytes_recv - self.last_net_counters.bytes_recv) / time_diff
                    usage.net_packets_sent_sec = (net_counters.packets_sent - self.last_net_counters.packets_sent) / time_diff
                    usage.net_packets_recv_sec = (net_counters.packets_recv - self.last_net_counters.packets_recv) / time_diff
            self.last_net_counters = net_counters
            
            # Process-specific metrics
            try:
                proc = self.process
                proc_mem = proc.memory_info()
                usage.process_memory_bytes = proc_mem.rss
                usage.process_memory_percent = proc.memory_percent()
                usage.process_cpu_percent = proc.cpu_percent(interval=None)
                usage.process_threads = proc.num_threads()
                usage.process_open_files = len(proc.open_files())
            except:
                pass
            
            # System uptime
            usage.system_uptime_seconds = time.time() - psutil.boot_time()
            usage.process_uptime_seconds = time.time() - self.process_start_time
            
            # Store usage data
            self.last_usage = self.current_usage
            self.current_usage = usage
            self.last_check_time = current_time
            
            # Add to history
            with self.history_lock:
                self.usage_history.append(usage)
                while len(self.usage_history) > self.history_size:
                    self.usage_history.pop(0)
            
            return usage
            
        except Exception as e:
            logger.error(f"Error getting resource usage: {e}")
            return usage
    
    def start_monitoring(self, interval_seconds=5.0):
        """Start background monitoring thread"""
        if self.monitor_thread and self.monitor_thread.is_alive():
            logger.warning("Monitoring thread already running")
            return False
        
        self.running = True
        self.monitor_thread = threading.Thread(
            target=self._monitoring_loop,
            args=(interval_seconds,),
            daemon=True
        )
        self.monitor_thread.start()
        logger.info(f"System monitoring started with interval: {interval_seconds}s")
        return True
    
    def stop_monitoring(self):
        """Stop background monitoring thread"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2.0)
        logger.info("System monitoring stopped")
    
    def _monitoring_loop(self, interval_seconds):
        """Background thread for periodic resource monitoring"""
        counter = 0
        while self.running:
            try:
                # Get current resource usage
                self.get_resource_usage()
                
                # Refresh system info periodically (every 10 minutes)
                if counter % 120 == 0:  # 120 * 5 seconds = 10 minutes
                    self.refresh_system_info()
                
                # Increment counter
                counter += 1
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
            
            # Sleep for the interval
            time.sleep(interval_seconds)
    
    def get_historical_usage(self, minutes=5) -> List[ResourceUsage]:
        """Get historical resource usage data for the specified number of minutes"""
        with self.history_lock:
            # Calculate how many samples we need
            interval = self.config.monitoring.interval_seconds if self.config else 5.0
            num_samples = int(minutes * 60 / interval)
            
            # Return the most recent samples
            return self.usage_history[-num_samples:] if num_samples < len(self.usage_history) else self.usage_history[:]
    
    def detect_memory_pressure(self) -> Tuple[bool, float]:
        """Detect if the system is under memory pressure"""
        try:
            # Get current memory usage
            usage = self.get_resource_usage()
            
            # Check if memory usage is above warning threshold
            warning_threshold = 80.0  # Default 80%
            if self.config and hasattr(self.config, 'thresholds'):
                warning_threshold = self.config.thresholds.warning_percent
            
            is_under_pressure = usage.memory_percent > warning_threshold
            return is_under_pressure, usage.memory_percent
            
        except Exception as e:
            logger.error(f"Error detecting memory pressure: {e}")
            return False, 0.0
    
    def detect_cpu_pressure(self) -> Tuple[bool, float]:
        """Detect if the CPU is under pressure"""
        try:
            # Get current CPU usage
            usage = self.get_resource_usage()
            
            # Check if CPU usage is above threshold
            cpu_threshold = 80.0  # Default 80%
            if self.config and hasattr(self.config, 'stress_handling'):
                cpu_threshold = self.config.stress_handling.cpu_threshold_percent
            
            is_under_pressure = usage.cpu_percent > cpu_threshold
            return is_under_pressure, usage.cpu_percent
            
        except Exception as e:
            logger.error(f"Error detecting CPU pressure: {e}")
            return False, 0.0
    
    def get_memory_info(self) -> Dict[str, Any]:
        """Get memory information in a structured format for logs or API"""
        usage = self.current_usage
        return {
            'total_gb': self.system_info.total_memory_gb,
            'available_gb': usage.memory_available_gb,
            'used_gb': usage.memory_used_gb,
            'percent': usage.memory_percent,
            'swap_used_gb': usage.swap_used_gb,
            'swap_percent': usage.swap_percent,
            'process_mb': usage.process_memory_bytes / (1024 * 1024),
            'process_percent': usage.process_memory_percent,
        }
    
    def get_cpu_info(self) -> Dict[str, Any]:
        """Get CPU information in a structured format for logs or API"""
        usage = self.current_usage
        return {
            'total_cores': self.system_info.cpu_count_logical,
            'physical_cores': self.system_info.cpu_count_physical,
            'percent': usage.cpu_percent,
            'per_core_percent': usage.cpu_percent_per_core,
            'load_averages': usage.load_averages,
            'process_percent': usage.process_cpu_percent,
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of system info and current usage"""
        usage = self.current_usage
        return {
            'system': {
                'hostname': self.system_info.hostname,
                'platform': f"{self.system_info.platform} {self.system_info.platform_release}",
                'python_version': self.system_info.python_version,
                'uptime_hours': round(usage.system_uptime_seconds / 3600, 1),
                'process_uptime_hours': round(usage.process_uptime_seconds / 3600, 1),
            },
            'cpu': self.get_cpu_info(),
            'memory': self.get_memory_info(),
            'disk': {
                'total_gb': self.system_info.disk_total_gb,
                'available_gb': self.system_info.disk_available_gb,
                'read_mb_sec': usage.disk_read_bytes_sec / (1024 * 1024),
                'write_mb_sec': usage.disk_write_bytes_sec / (1024 * 1024),
            },
            'network': {
                'sent_mb_sec': usage.net_sent_bytes_sec / (1024 * 1024),
                'recv_mb_sec': usage.net_recv_bytes_sec / (1024 * 1024),
                'packets_sent_sec': usage.net_packets_sent_sec,
                'packets_recv_sec': usage.net_packets_recv_sec,
            },
            'process': {
                'pid': self.system_info.process_id,
                'threads': usage.process_threads,
                'open_files': usage.process_open_files,
            }
        } 