"""
Memory Monitoring Module
----------------------
Provides detailed memory usage monitoring, logging, and metrics exposure.
Includes a dashboard interface and Prometheus metric integration.
"""

import os
import sys
import time
import json
import logging
import threading
import traceback
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime, timedelta
from collections import deque
import statistics
import inspect

# Try to import optional modules
try:
    from prometheus_client import Gauge, Counter, Histogram, start_http_server
    HAS_PROMETHEUS = True
except ImportError:
    HAS_PROMETHEUS = False

logger = logging.getLogger("memory_manager.monitor")

class MemoryMonitor:
    """Monitors memory usage and provides logging, metrics, and visualization"""
    
    def __init__(self, app=None, config=None, system_detector=None, memory_optimizer=None, stress_handler=None):
        """Initialize the memory monitor"""
        self.app = app
        self.config = config
        self.system_detector = system_detector
        self.memory_optimizer = memory_optimizer
        self.stress_handler = stress_handler
        
        # Get monitoring configuration
        if config and hasattr(config, 'monitoring'):
            self.enabled = config.monitoring.enabled
            self.interval = config.monitoring.interval_seconds
            self.history_size = config.monitoring.history_size
            self.log_directory = config.monitoring.log_directory
            self.log_level = config.monitoring.log_level
            self.log_to_file = config.monitoring.log_to_file
            self.log_to_console = config.monitoring.log_to_console
            self.expose_prometheus = config.monitoring.expose_prometheus
            self.metrics_write_interval = config.monitoring.metrics_write_interval
            self.max_log_size = config.monitoring.max_log_size_mb * 1024 * 1024
            self.max_log_files = config.monitoring.max_log_files
        else:
            # Default values
            self.enabled = True
            self.interval = 5.0
            self.history_size = 720  # 1 hour at 5-second intervals
            self.log_directory = "logs/memory"
            self.log_level = "INFO"
            self.log_to_file = True
            self.log_to_console = True
            self.expose_prometheus = True
            self.metrics_write_interval = 60.0
            self.max_log_size = 100 * 1024 * 1024  # 100 MB
            self.max_log_files = 10
        
        # Get API configuration
        if config and hasattr(config, 'api'):
            self.api_enabled = config.api.enabled
            self.api_prefix = config.api.endpoint_prefix
            self.detailed_endpoints = config.api.detailed_endpoints
            self.management_endpoints = config.api.management_endpoints
            self.auth_token = config.api.auth_token
        else:
            # Default values
            self.api_enabled = True
            self.api_prefix = "/memory"
            self.detailed_endpoints = True
            self.management_endpoints = False
            self.auth_token = None
        
        # Memory history tracking
        self.history_lock = threading.RLock()
        self.memory_history = deque(maxlen=self.history_size)
        
        # Memory spike detection
        self.spike_threshold_mb = 50  # MB
        self.memory_spikes = []
        self.last_memory_value = 0
        
        # Per-request memory tracking
        self.request_memory_tracking = {}
        
        # Log file handling
        self._setup_logging()
        
        # Prometheus metrics
        self.prometheus_started = False
        if self.expose_prometheus and HAS_PROMETHEUS:
            self._setup_prometheus_metrics()
        
        # Monitoring thread
        self.monitor_thread = None
        self.running = False
        
        # Metrics file writing
        self.last_metrics_write = 0
        
        logger.info(f"Memory monitor initialized with interval: {self.interval}s")
    
    @property
    def is_monitoring(self):
        """Check if monitoring is currently active"""
        return self.running and self.monitor_thread is not None and self.monitor_thread.is_alive()
    
    def _setup_logging(self):
        """Set up logging for memory monitoring"""
        try:
            # Create log directory if it doesn't exist
            if self.log_to_file and self.log_directory:
                os.makedirs(self.log_directory, exist_ok=True)
            
            # Create a dedicated memory logger
            self.memory_logger = logging.getLogger("memory_metrics")
            self.memory_logger.setLevel(getattr(logging, self.log_level))
            self.memory_logger.propagate = False  # Don't propagate to parent
            
            # Clear any existing handlers
            if self.memory_logger.handlers:
                self.memory_logger.handlers.clear()
            
            # Create formatter
            formatter = logging.Formatter(
                '%(asctime)s [%(levelname)s] %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            
            # Add file handler if enabled
            if self.log_to_file:
                log_file = os.path.join(self.log_directory, "memory_usage.log")
                file_handler = logging.handlers.RotatingFileHandler(
                    log_file,
                    maxBytes=self.max_log_size,
                    backupCount=self.max_log_files
                )
                file_handler.setFormatter(formatter)
                self.memory_logger.addHandler(file_handler)
            
            # Add console handler if enabled
            if self.log_to_console:
                console_handler = logging.StreamHandler()
                console_handler.setFormatter(formatter)
                self.memory_logger.addHandler(console_handler)
            
            return True
        except Exception as e:
            logger.error(f"Error setting up memory logging: {e}")
            return False
    
    def _setup_prometheus_metrics(self):
        """Set up Prometheus metrics if available"""
        if not HAS_PROMETHEUS:
            logger.warning("Prometheus client not available")
            return False
        
        try:
            # Create metrics
            self.prom_memory_usage = Gauge(
                'python_memory_usage_bytes',
                'Current memory usage in bytes'
            )
            
            self.prom_memory_percent = Gauge(
                'python_memory_usage_percent',
                'Current memory usage as percentage of total'
            )
            
            self.prom_peak_memory = Gauge(
                'python_peak_memory_bytes',
                'Peak memory usage in bytes'
            )
            
            self.prom_available_memory = Gauge(
                'system_memory_available_bytes',
                'Available system memory in bytes'
            )
            
            self.prom_memory_limit = Gauge(
                'memory_limit_bytes',
                'Configured memory limit in bytes'
            )
            
            self.prom_gc_collections = Counter(
                'gc_collections_total',
                'Total number of garbage collections'
            )
            
            self.prom_memory_spikes = Counter(
                'memory_spikes_total',
                'Total number of memory spikes detected'
            )
            
            self.prom_memory_optimization = Counter(
                'memory_optimizations_total',
                'Total number of memory optimizations performed'
            )
            
            self.prom_memory_freed = Counter(
                'memory_freed_bytes_total',
                'Total memory freed by optimizations in bytes'
            )
            
            # Start HTTP server for metrics if not already running
            if not self.prometheus_started:
                try:
                    # Try to start the server on port 8000, but increment if port is in use
                    port = 8000
                    max_attempts = 10
                    for attempt in range(max_attempts):
                        try:
                            start_http_server(port)
                            self.prometheus_started = True
                            logger.info(f"Prometheus metrics available on port {port}")
                            break
                        except OSError:
                            # Port in use, try next one
                            port += 1
                    
                    if not self.prometheus_started:
                        logger.warning(f"Failed to start Prometheus server after {max_attempts} attempts")
                except Exception as e:
                    logger.error(f"Error starting Prometheus server: {e}")
            
            return self.prometheus_started
            
        except Exception as e:
            logger.error(f"Error setting up Prometheus metrics: {e}")
            return False
    
    def register(self, app=None):
        """Register with the Flask application"""
        if app:
            self.app = app
        
        # Start monitoring thread if enabled
        if self.enabled:
            self.start_monitoring()
        
        # Register API endpoints if enabled and using Flask
        if self.api_enabled and self.app and hasattr(self.app, 'route'):
            try:
                self._register_api_endpoints()
                logger.info("Memory monitoring API endpoints registered")
            except Exception as e:
                logger.warning(f"Failed to register API endpoints: {e}")
        
        # Register request tracking if using Flask
        if self.app and hasattr(self.app, 'before_request') and hasattr(self.app, 'after_request'):
            try:
                @self.app.before_request
                def track_request_memory_start():
                    # Record memory usage at start of request
                    if self.system_detector:
                        try:
                            usage = self.system_detector.get_resource_usage()
                            request_id = id(threading.current_thread())
                            self.request_memory_tracking[request_id] = {
                                'start_memory': usage.process_memory_bytes,
                                'start_time': time.time()
                            }
                        except:
                            pass
                
                @self.app.after_request
                def track_request_memory_end(response):
                    # Record memory usage at end of request and log if significant
                    if self.system_detector:
                        try:
                            usage = self.system_detector.get_resource_usage()
                            request_id = id(threading.current_thread())
                            
                            if request_id in self.request_memory_tracking:
                                start_data = self.request_memory_tracking[request_id]
                                memory_diff = usage.process_memory_bytes - start_data['start_memory']
                                time_diff = time.time() - start_data['start_time']
                                
                                # Clean up tracking data
                                del self.request_memory_tracking[request_id]
                                
                                # Log significant memory changes
                                if memory_diff > (self.spike_threshold_mb * 1024 * 1024):
                                    from flask import request
                                    logger.warning(
                                        f"Large memory increase: {memory_diff/(1024*1024):.1f}MB for "
                                        f"request {request.method} {request.path} ({time_diff:.3f}s)"
                                    )
                        except:
                            pass
                    
                    return response
                
                logger.info("Request memory tracking registered")
            except Exception as e:
                logger.warning(f"Failed to register request memory tracking: {e}")
        
        # Return self for method chaining
        return self
    
    def _register_api_endpoints(self):
        """Register API endpoints with Flask app"""
        if not self.app or not hasattr(self.app, 'route'):
            return False
        
        # Endpoint for basic memory status
        @self.app.route(f"{self.api_prefix}/status")
        def memory_status():
            from flask import jsonify
            
            # Check authentication if required
            if self.management_endpoints and self.auth_token:
                from flask import request
                token = request.headers.get('X-Auth-Token')
                if token != self.auth_token:
                    return jsonify({'error': 'Unauthorized'}), 401
            
            # Get memory status
            status = self.get_memory_status()
            return jsonify(status)
        
        # Endpoint for memory history
        if self.detailed_endpoints:
            @self.app.route(f"{self.api_prefix}/history")
            def memory_history():
                from flask import jsonify, request
                
                # Get minutes parameter
                minutes = int(request.args.get('minutes', 5))
                minutes = min(max(1, minutes), 60)  # Limit to 1-60 minutes
                
                # Get memory history
                history = self.get_memory_history(minutes)
                return jsonify(history)
        
        # Endpoint for memory optimization (management)
        if self.management_endpoints:
            @self.app.route(f"{self.api_prefix}/optimize", methods=['POST'])
            def memory_optimize():
                from flask import jsonify, request
                
                # Check authentication
                if self.auth_token:
                    token = request.headers.get('X-Auth-Token')
                    if token != self.auth_token:
                        return jsonify({'error': 'Unauthorized'}), 401
                
                # Get optimization level
                data = request.get_json() or {}
                level = data.get('level', 'normal')
                
                # Run optimization
                if self.memory_optimizer:
                    result = self.memory_optimizer.optimize_memory(level=level)
                    return jsonify(result)
                else:
                    return jsonify({'error': 'Memory optimizer not available'}), 400
        
        return True
    
    def start_monitoring(self):
        """Start memory monitoring thread"""
        # Check if monitoring is already active
        if self.is_monitoring:
            logger.debug("Memory monitoring already active, no need to start again")
            return True
            
        # If we had a previous thread that's dead, clean it up
        if self.monitor_thread and not self.monitor_thread.is_alive():
            self.monitor_thread = None
        
        self.running = True
        self.monitor_thread = threading.Thread(
            target=self._monitoring_loop,
            daemon=True
        )
        self.monitor_thread.start()
        logger.info(f"Memory monitoring started with interval: {self.interval}s")
        return True
    
    def stop_monitoring(self):
        """Stop memory monitoring thread"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2.0)
        logger.info("Memory monitoring stopped")
    
    def _monitoring_loop(self):
        """Background thread for memory monitoring"""
        while self.running:
            try:
                # Get current memory usage
                self._record_memory_usage()
                
                # Write metrics to file if it's time
                current_time = time.time()
                if current_time - self.last_metrics_write >= self.metrics_write_interval:
                    self._write_metrics_to_file()
                    self.last_metrics_write = current_time
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
            
            # Sleep for the interval
            time.sleep(self.interval)
    
    def _record_memory_usage(self):
        """Record current memory usage and log"""
        try:
            # Need system detector for this
            if not self.system_detector:
                return False
            
            # Get resource usage
            usage = self.system_detector.get_resource_usage()
            
            # Create metrics object
            metrics = {
                'timestamp': time.time(),
                'datetime': datetime.now().isoformat(),
                'process_memory_bytes': usage.process_memory_bytes,
                'process_memory_mb': usage.process_memory_bytes / (1024 * 1024),
                'process_memory_percent': usage.process_memory_percent,
                'system_memory_percent': usage.memory_percent,
                'system_memory_available_mb': usage.memory_available_bytes / (1024 * 1024),
                'system_memory_used_mb': usage.memory_used_bytes / (1024 * 1024),
                'cpu_percent': usage.cpu_percent,
                'cpu_process_percent': usage.process_cpu_percent,
            }
            
            # Add GC metrics if optimizer available
            if self.memory_optimizer:
                gc_metrics = self.memory_optimizer.get_metrics()
                metrics.update({
                    'gc_collections': gc_metrics.get('gc_collections', 0),
                    'gc_objects_collected': gc_metrics.get('objects_collected', 0),
                    'peak_memory_mb': gc_metrics.get('peak_memory_bytes', 0) / (1024 * 1024),
                })
            
            # Add stress metrics if handler available
            if self.stress_handler:
                stress_metrics = self.stress_handler.get_stress_metrics()
                metrics.update({
                    'stress_level': stress_metrics.get('current_stress_level', 0),
                    'stress_state': stress_metrics.get('current_state', 'NORMAL'),
                })
            
            # Save to history
            with self.history_lock:
                self.memory_history.append(metrics)
            
            # Detect memory spikes
            self._detect_memory_spike(metrics)
            
            # Update Prometheus metrics if enabled
            if self.expose_prometheus and HAS_PROMETHEUS and self.prometheus_started:
                self._update_prometheus_metrics(metrics, usage)
            
            # Log memory usage periodically
            self._log_memory_usage(metrics)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error recording memory usage: {e}")
            return None
    
    def _detect_memory_spike(self, metrics):
        """Detect memory spikes based on rapid increases"""
        try:
            current_memory = metrics['process_memory_mb']
            
            # Check for spike if we have a previous value
            if self.last_memory_value > 0:
                memory_diff = current_memory - self.last_memory_value
                
                # Consider it a spike if it exceeds threshold
                if memory_diff > self.spike_threshold_mb:
                    spike_info = {
                        'timestamp': metrics['timestamp'],
                        'datetime': metrics['datetime'],
                        'previous_mb': self.last_memory_value,
                        'current_mb': current_memory,
                        'diff_mb': memory_diff,
                        'system_memory_percent': metrics.get('system_memory_percent', 0),
                    }
                    
                    # Add call stack if possible
                    try:
                        stack = [frame[2] for frame in inspect.stack()[1:10]]  # Skip this frame
                        spike_info['stack'] = stack
                    except:
                        pass
                    
                    # Record the spike
                    self.memory_spikes.append(spike_info)
                    if len(self.memory_spikes) > 50:  # Keep only recent spikes
                        self.memory_spikes = self.memory_spikes[-50:]
                    
                    # Log the spike
                    logger.warning(f"Memory spike detected: +{memory_diff:.1f}MB, now at {current_memory:.1f}MB")
                    
                    # Update Prometheus counter if enabled
                    if self.expose_prometheus and HAS_PROMETHEUS and self.prometheus_started:
                        self.prom_memory_spikes.inc()
            
            # Update last memory value
            self.last_memory_value = current_memory
            
        except Exception as e:
            logger.error(f"Error detecting memory spike: {e}")
    
    def _update_prometheus_metrics(self, metrics, usage):
        """Update Prometheus metrics with current values"""
        try:
            # Update gauge values
            self.prom_memory_usage.set(metrics['process_memory_bytes'])
            self.prom_memory_percent.set(metrics['process_memory_percent'])
            self.prom_available_memory.set(usage.memory_available_bytes)
            
            # Update peak memory if available
            if 'peak_memory_mb' in metrics:
                peak_bytes = metrics['peak_memory_mb'] * 1024 * 1024
                self.prom_peak_memory.set(peak_bytes)
            
            # Update GC collections if available
            if 'gc_collections' in metrics and self.memory_optimizer:
                current_collections = metrics['gc_collections']
                previous_collections = getattr(self, '_previous_gc_collections', 0)
                
                if current_collections > previous_collections:
                    self.prom_gc_collections.inc(current_collections - previous_collections)
                
                # Remember current value for next time
                self._previous_gc_collections = current_collections
            
            # Set memory limit if configured
            if self.config and hasattr(self.config, 'memory_limit_mb') and self.config.memory_limit_mb > 0:
                limit_bytes = self.config.memory_limit_mb * 1024 * 1024
                self.prom_memory_limit.set(limit_bytes)
            
        except Exception as e:
            logger.error(f"Error updating Prometheus metrics: {e}")
    
    def _log_memory_usage(self, metrics):
        """Log memory usage metrics to dedicated log file"""
        try:
            # Format message for logging
            log_message = (
                f"Memory: {metrics['process_memory_mb']:.1f}MB "
                f"({metrics['process_memory_percent']:.1f}%), "
                f"System: {metrics['system_memory_percent']:.1f}%, "
                f"CPU: {metrics['cpu_percent']:.1f}%"
            )
            
            # Add GC info if available
            if 'gc_collections' in metrics:
                log_message += f", GC: {metrics['gc_collections']}"
            
            # Add stress info if available
            if 'stress_state' in metrics and metrics['stress_state'] != 'NORMAL':
                log_message += f", Stress: {metrics['stress_state']}"
            
            # Log at appropriate level based on memory usage
            if 'system_memory_percent' in metrics:
                mem_percent = metrics['system_memory_percent']
                if mem_percent > 95:
                    self.memory_logger.critical(log_message)
                elif mem_percent > 85:
                    self.memory_logger.error(log_message)
                elif mem_percent > 75:
                    self.memory_logger.warning(log_message)
                elif mem_percent > 50:
                    self.memory_logger.info(log_message)
                else:
                    self.memory_logger.debug(log_message)
            else:
                self.memory_logger.info(log_message)
                
        except Exception as e:
            logger.error(f"Error logging memory usage: {e}")
    
    def _write_metrics_to_file(self):
        """Write metrics history to a JSON file"""
        try:
            # Create log directory if it doesn't exist
            if self.log_directory:
                os.makedirs(self.log_directory, exist_ok=True)
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(self.log_directory, f"memory_metrics_{timestamp}.json")
            
            # Copy history with lock to prevent changes during writing
            with self.history_lock:
                history_copy = list(self.memory_history)
            
            # Write to file
            with open(filename, 'w') as f:
                json.dump(history_copy, f, indent=2)
            
            logger.info(f"Memory metrics written to {filename}")
            
            # Clean up old metric files
            self._cleanup_old_metric_files()
            
            return True
            
        except Exception as e:
            logger.error(f"Error writing metrics to file: {e}")
            return False
    
    def _cleanup_old_metric_files(self):
        """Clean up old metric files to prevent disk space issues"""
        try:
            # List all metric files in the directory
            metric_files = []
            for filename in os.listdir(self.log_directory):
                if filename.startswith("memory_metrics_") and filename.endswith(".json"):
                    filepath = os.path.join(self.log_directory, filename)
                    # Get file stats
                    stats = os.stat(filepath)
                    metric_files.append((filepath, stats.st_mtime))
            
            # Sort by modification time (oldest first)
            metric_files.sort(key=lambda x: x[1])
            
            # Delete oldest files if we have too many
            if len(metric_files) > self.max_log_files:
                files_to_delete = metric_files[:-self.max_log_files]
                for filepath, _ in files_to_delete:
                    os.remove(filepath)
                    logger.debug(f"Deleted old metric file: {filepath}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error cleaning up old metric files: {e}")
            return False
    
    def get_memory_status(self):
        """Get current memory status"""
        # Get current metrics if available
        if self.memory_history:
            current_metrics = self.memory_history[-1]
        else:
            # If no history yet, get current usage
            if self.system_detector:
                metrics = self._record_memory_usage()
                current_metrics = metrics if metrics else {}
            else:
                current_metrics = {}
        
        # Add system information
        status = {
            'current': current_metrics,
            'peak_detected': self.memory_optimizer.peak_memory / (1024 * 1024) if self.memory_optimizer else 0,
            'memory_spikes': len(self.memory_spikes),
            'last_spike': self.memory_spikes[-1] if self.memory_spikes else None,
        }
        
        # Add system info if available
        if self.system_detector:
            status['system'] = self.system_detector.get_summary()
        
        # Add memory growth info if available
        if self.memory_optimizer:
            status['growth'] = self.memory_optimizer.check_memory_growth()
        
        # Add stress info if available
        if self.stress_handler:
            status['stress'] = self.stress_handler.get_stress_metrics()
        
        return status
    
    def get_memory_history(self, minutes=5):
        """Get memory usage history for the specified number of minutes"""
        try:
            with self.history_lock:
                # Calculate how many data points we need
                points_needed = int(minutes * 60 / self.interval)
                history = list(self.memory_history)[-points_needed:] if points_needed < len(self.memory_history) else list(self.memory_history)
            
            # Calculate summary statistics
            if history:
                memory_values = [point['process_memory_mb'] for point in history]
                system_mem_values = [point.get('system_memory_percent', 0) for point in history]
                cpu_values = [point.get('cpu_percent', 0) for point in history]
                
                summary = {
                    'start_time': history[0]['timestamp'] if history else time.time(),
                    'end_time': history[-1]['timestamp'] if history else time.time(),
                    'duration_seconds': (history[-1]['timestamp'] - history[0]['timestamp']) if len(history) > 1 else 0,
                    'points': len(history),
                    'interval_seconds': self.interval,
                    'memory_mb_min': min(memory_values) if memory_values else 0,
                    'memory_mb_max': max(memory_values) if memory_values else 0,
                    'memory_mb_avg': statistics.mean(memory_values) if memory_values else 0,
                    'memory_mb_median': statistics.median(memory_values) if memory_values else 0,
                    'system_memory_percent_avg': statistics.mean(system_mem_values) if system_mem_values else 0,
                    'system_memory_percent_max': max(system_mem_values) if system_mem_values else 0,
                    'cpu_percent_avg': statistics.mean(cpu_values) if cpu_values else 0,
                    'cpu_percent_max': max(cpu_values) if cpu_values else 0,
                }
                
                # Calculate memory growth
                if len(memory_values) > 1:
                    growth_mb = memory_values[-1] - memory_values[0]
                    growth_percent = (growth_mb / memory_values[0]) * 100 if memory_values[0] > 0 else 0
                    summary['memory_growth_mb'] = growth_mb
                    summary['memory_growth_percent'] = growth_percent
                
                return {
                    'summary': summary,
                    'history': history
                }
            else:
                return {
                    'summary': {
                        'start_time': time.time(),
                        'end_time': time.time(),
                        'duration_seconds': 0,
                        'points': 0
                    },
                    'history': []
                }
                
        except Exception as e:
            logger.error(f"Error getting memory history: {e}")
            return {
                'error': str(e),
                'history': []
            }
    
    def get_memory_spikes(self):
        """Get detected memory spikes"""
        return self.memory_spikes
    
    def get_metrics(self):
        """Get monitor metrics"""
        return {
            'memory_spikes': len(self.memory_spikes),
            'history_points': len(self.memory_history),
            'monitoring_active': self.running,
            'prometheus_active': self.prometheus_started if HAS_PROMETHEUS else False,
            'last_metrics_write': self.last_metrics_write,
        } 