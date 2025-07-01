"""
DDoS Protection System - Monitoring Module
-----------------------------------------
Handles monitoring, alerting, and metrics collection for the DDoS protection system.

This package includes:
- Monitor: Main monitoring system that collects metrics and generates alerts
- Prometheus: Prometheus metrics exporter
- Alerts: Alert generation and delivery (email, Slack, webhook)
"""

import logging
import os

# Configure logger
logger = logging.getLogger("ddos_protection.monitoring")

# Import monitor components
try:
    from .monitor import Monitor, create_monitor
    from .monitoring import MonitorSystem
    
    # Initialize monitor system
    monitor_system = MonitorSystem()
    
    MONITOR_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Monitor module not available: {e}")
    MONITOR_AVAILABLE = False
    monitor_system = None

# Apply OPTIONS patch to prevent blocking legitimate requests
try:
    from .options_patch import patch_ddos_system
    # Call the patch function but don't halt on errors
    try:
        patch_ddos_system()
        logger.info("Applied OPTIONS patch to DDoS protection system")
    except Exception as e:
        logger.error(f"Failed to apply OPTIONS patch: {e}")
except ImportError as e:
    logger.warning(f"OPTIONS patch not available: {e}")

__all__ = ["Monitor", "create_monitor", "MonitorSystem", "monitor_system"] 