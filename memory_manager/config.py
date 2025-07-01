"""
Configuration Module
------------------
Defines configuration settings and thresholds for memory management.
Supports loading from environment variables, YAML files, or direct initialization.
"""

import os
import sys
import yaml
import json
import logging
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Union

logger = logging.getLogger("memory_manager")

@dataclass
class GarbageCollectionConfig:
    """Configuration for garbage collection optimization"""
    # Enable automatic garbage collection optimization
    enabled: bool = True
    
    # Threshold for triggering garbage collection (percentage of available memory)
    threshold_percent: float = 70.0
    
    # Interval between periodic garbage collections (seconds, 0 to disable)
    interval_seconds: float = 300.0
    
    # Tune garbage collection thresholds based on available memory
    tune_thresholds: bool = True
    
    # Tune factor (higher values = more aggressive collection)
    tune_factor: float = 0.8
    
    # Debug level for garbage collector
    debug_flags: int = 0
    
    # Maximum number of objects to collect per cycle (0 for unlimited)
    max_collect_objects: int = 0

@dataclass
class MemoryThresholds:
    """Memory usage thresholds for alerts and actions"""
    # Warning threshold (percentage of available memory)
    warning_percent: float = 70.0
    
    # Critical threshold (percentage of available memory)
    critical_percent: float = 85.0
    
    # Emergency threshold (percentage of available memory) - triggers emergency actions
    emergency_percent: float = 95.0
    
    # Process restart threshold (percentage of available memory)
    restart_percent: float = 97.0
    
    # Per-request memory growth warning threshold (MB)
    request_growth_mb: float = 50.0
    
    # Memory leak detection threshold (percentage growth over baseline)
    leak_percent: float = 10.0
    
    # Number of consecutive measurements above threshold to confirm a memory leak
    leak_consecutive_count: int = 3

@dataclass
class MonitoringConfig:
    """Configuration for monitoring and logging"""
    # Enable detailed monitoring
    enabled: bool = True
    
    # Monitoring interval in seconds
    interval_seconds: float = 5.0
    
    # Number of history points to keep
    history_size: int = 720  # 1 hour at 5-second intervals
    
    # Directory for log files
    log_directory: str = "logs/memory"
    
    # Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    log_level: str = "INFO"
    
    # Whether to log to file
    log_to_file: bool = True
    
    # Whether to log to console
    log_to_console: bool = True
    
    # Whether to expose Prometheus metrics
    expose_prometheus: bool = True
    
    # Interval for writing metrics to disk (seconds)
    metrics_write_interval: float = 60.0
    
    # Maximum size of log files (MB)
    max_log_size_mb: float = 100.0
    
    # Number of log files to keep
    max_log_files: int = 10

@dataclass
class StressHandlingConfig:
    """Configuration for handling stress and high load conditions"""
    # Enable stress handling
    enabled: bool = True
    
    # Check interval during normal operation (seconds)
    normal_check_interval: float = 5.0
    
    # Check interval during stress conditions (seconds)
    stress_check_interval: float = 1.0
    
    # Duration to consider a spike as stress (seconds)
    stress_duration_seconds: float = 30.0
    
    # CPU threshold to detect stress (percentage)
    cpu_threshold_percent: float = 95.0
    
    # Network I/O threshold to detect stress (MB/s)
    network_threshold_mbs: float = 250.0
    
    # List of critical endpoints that should always be prioritized
    critical_endpoints: List[str] = field(default_factory=list)
    
    # Actions to take during stress (pause_background, reduce_logging, etc.)
    stress_actions: List[str] = field(default_factory=lambda: ["pause_background", "reduce_logging"])
    
    # Maximum time for stress handling mode (seconds, 0 for unlimited)
    max_stress_time: float = 300.0  # 5 minutes

@dataclass
class SelfHealingConfig:
    """Configuration for self-healing capabilities"""
    # Enable self-healing
    enabled: bool = True
    
    # Enable automatic process restart on critical memory issues
    enable_restart: bool = True
    
    # Maximum number of restarts in a time period
    max_restarts: int = 3
    
    # Time period for restart limit (seconds)
    restart_period_seconds: float = 3600.0  # 1 hour
    
    # Time between restart attempts (seconds)
    restart_wait_seconds: float = 10.0
    
    # Enable cleanup of temporary files
    enable_temp_cleanup: bool = True
    
    # Enable notifications on critical events
    enable_notifications: bool = True
    
    # Notification methods (email, slack, etc.)
    notification_methods: List[str] = field(default_factory=lambda: ["log"])
    
    # Notification settings (depends on method)
    notification_settings: Dict[str, Any] = field(default_factory=dict)
    
    # Actions to take for different issues (dict mapping issue to action list)
    healing_actions: Dict[str, List[str]] = field(default_factory=lambda: {
        "memory_leak": ["collect_garbage", "restart_workers"],
        "high_cpu": ["throttle_requests"],
        "disk_full": ["clear_temp_files"]
    })

@dataclass
class APIConfig:
    """Configuration for the monitoring API"""
    # Enable the API
    enabled: bool = True
    
    # API endpoint prefix
    endpoint_prefix: str = "/memory"
    
    # Enable detailed endpoints (may impact performance)
    detailed_endpoints: bool = True
    
    # Enable management endpoints (allowing control via API)
    management_endpoints: bool = False
    
    # Authentication token for management endpoints
    auth_token: Optional[str] = None
    
    # Cross-Origin Resource Sharing (CORS) allowed origins
    cors_origins: List[str] = field(default_factory=lambda: ["*"])
    
    # Rate limiting for API requests (requests per minute)
    rate_limit: int = 60

class ComponentConfig:
    """Base configuration class for memory management components"""
    def __init__(self):
        self.enabled = True
        self.log_level = logging.INFO
        
class ObjectTrackerConfig(ComponentConfig):
    """Configuration for the object tracker component"""
    def __init__(self):
        super().__init__()
        self.tracking_interval = 60.0  # Seconds
        self.history_size = 20
        self.track_types = True
        self.detect_leaks = True
        self.detect_cycles = True

class HeapAnalyzerConfig(ComponentConfig):
    """Configuration for the heap analyzer component"""
    def __init__(self):
        super().__init__()
        self.analysis_interval = 300.0  # 5 minutes
        self.history_size = 24
        self.log_directory = "logs/memory"
        self.deep_analysis = False

class CriticalSectionConfig(ComponentConfig):
    """Configuration for the critical section analyzer component"""
    def __init__(self):
        super().__init__()
        self.tracking_enabled = True
        self.alert_threshold_mb = 50
        self.detailed_tracking = True
        self.history_points = 100

class MemoryMonitorConfig(ComponentConfig):
    """Configuration for the memory monitor component"""
    def __init__(self):
        super().__init__()
        self.monitoring_interval = 30.0  # Seconds
        self.warning_threshold = 0.8  # 80% of limit
        self.critical_threshold = 0.9  # 90% of limit
        self.history_size = 60  # Keep 60 data points
        
        # Try to get memory limit from environment
        try:
            env_limit = os.environ.get('MEMMAN_MEMORY_LIMIT_MB')
            self.memory_limit_mb = float(env_limit) if env_limit else 4096
        except (ValueError, TypeError):
            self.memory_limit_mb = 4096  # Default 4GB

class MemoryManagerConfig:
    """Master configuration class for the memory manager"""
    def __init__(self):
        # Initialize all component configs
        self.memory_monitor = MemoryMonitorConfig()
        self.object_tracker = ObjectTrackerConfig()
        self.heap_analyzer = HeapAnalyzerConfig()
        self.critical_section = CriticalSectionConfig()
        
        # Global settings
        self.enabled = True
        self.auto_start = True
        self.log_level = logging.INFO
        
        # Load from environment
        self._load_from_env()
        
        logger.debug("Memory manager configuration initialized")
        
    def _load_from_env(self):
        """Load configuration from environment variables"""
        # Basic example of environment loading
        if os.environ.get('MEMMAN_DISABLED') == '1':
            self.enabled = False
            
        # Memory monitor settings
        if os.environ.get('MEMMAN_MONITOR_DISABLED') == '1':
            self.memory_monitor.enabled = False
            
        # Object tracker settings
        if os.environ.get('MEMMAN_TRACKER_DISABLED') == '1':
            self.object_tracker.enabled = False
            
        # Heap analyzer settings
        if os.environ.get('MEMMAN_ANALYZER_DISABLED') == '1':
            self.heap_analyzer.enabled = False
            
        # Critical section settings
        if os.environ.get('MEMMAN_CRITICAL_DISABLED') == '1':
            self.critical_section.enabled = False

    def _load_from_file(self, file_path):
        """Load configuration from a YAML file"""
        try:
            with open(file_path, 'r') as f:
                config_data = yaml.safe_load(f)
            
            # Update from dictionary
            self._update_from_dict(config_data)
            
        except Exception as e:
            logger.error(f"Failed to load configuration from {file_path}: {e}")
    
    def _update_from_dict(self, config_dict):
        """Update configuration from a dictionary"""
        # Handle top-level attributes
        for key, value in config_dict.items():
            if key in ('gc_config', 'thresholds', 'monitoring', 
                       'stress_handling', 'self_healing', 'api'):
                if hasattr(self, key):
                    section = getattr(self, key)
                    # Update section attributes
                    for subkey, subvalue in value.items():
                        if hasattr(section, subkey):
                            setattr(section, subkey, subvalue)
            elif hasattr(self, key):
                # Update top-level attributes
                setattr(self, key, value)
    
    def to_dict(self):
        """Convert configuration to a dictionary"""
        result = asdict(self)
        
        # Convert sub-configurations
        result['object_tracker'] = asdict(self.object_tracker)
        result['heap_analyzer'] = asdict(self.heap_analyzer)
        result['critical_section'] = asdict(self.critical_section)
        result['memory_monitor'] = asdict(self.memory_monitor)
        
        return result
    
    def save(self, file_path=None):
        """Save configuration to a YAML file"""
        path = file_path or self.config_file_path
        if not path:
            logger.warning("No file path specified for saving configuration")
            return False
        
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(path), exist_ok=True)
            
            # Save as YAML
            with open(path, 'w') as f:
                yaml.dump(self.to_dict(), f, default_flow_style=False)
            
            return True
        except Exception as e:
            logger.error(f"Failed to save configuration to {path}: {e}")
            return False
    
    @classmethod
    def from_file(cls, file_path):
        """Create a configuration from a YAML file"""
        config = cls()
        config.config_file_path = file_path
        if os.path.exists(file_path):
            config._load_from_file(file_path)
        return config
    
    @classmethod
    def from_dict(cls, config_dict):
        """Create a configuration from a dictionary"""
        config = cls()
        config._update_from_dict(config_dict)
        return config 