"""
Stress Handler Module
------------------
Detects and handles high stress conditions in the application,
dynamically adjusting resource usage to maintain stability during load spikes.
"""

import os
import sys
import time
import logging
import threading
import traceback
from typing import Dict, List, Set, Tuple, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum, auto
from collections import deque

logger = logging.getLogger("memory_manager.stress_handler")

class StressState(Enum):
    """Current stress state of the system"""
    NORMAL = auto()
    ELEVATED = auto()
    HIGH = auto()
    CRITICAL = auto()


class StressHandler:
    """Handles high load conditions and stress scenarios"""
    
    def __init__(self, app=None, config=None, system_detector=None, memory_optimizer=None):
        """Initialize the stress handler"""
        self.app = app
        self.config = config
        self.system_detector = system_detector
        self.memory_optimizer = memory_optimizer
        
        # Get stress handling configuration
        if config and hasattr(config, 'stress_handling'):
            self.enabled = config.stress_handling.enabled
            self.normal_check_interval = config.stress_handling.normal_check_interval
            self.stress_check_interval = config.stress_handling.stress_check_interval
            self.stress_duration = config.stress_handling.stress_duration_seconds
            self.cpu_threshold = config.stress_handling.cpu_threshold_percent
            self.network_threshold = config.stress_handling.network_threshold_mbs
            self.critical_endpoints = config.stress_handling.critical_endpoints
            self.stress_actions = config.stress_handling.stress_actions
            self.max_stress_time = config.stress_handling.max_stress_time
        else:
            # Default values
            self.enabled = True
            self.normal_check_interval = 5.0
            self.stress_check_interval = 1.0
            self.stress_duration = 30.0
            self.cpu_threshold = 80.0
            self.network_threshold = 100.0  # MB/s
            self.critical_endpoints = []
            self.stress_actions = ["pause_background", "reduce_logging"]
            self.max_stress_time = 300.0  # 5 minutes
        
        # Get memory thresholds from config
        if config and hasattr(config, 'thresholds'):
            self.memory_warning_threshold = config.thresholds.warning_percent
            self.memory_critical_threshold = config.thresholds.critical_percent
            self.memory_emergency_threshold = config.thresholds.emergency_percent
        else:
            # Default values
            self.memory_warning_threshold = 70.0
            self.memory_critical_threshold = 85.0
            self.memory_emergency_threshold = 95.0
        
        # Initialize stress state tracking
        self.current_state = StressState.NORMAL
        self.stress_history = []
        self.stress_start_time = 0
        self.stress_duration_time = 0
        self.consecutive_stress_detections = 0
        
        # Stress monitoring thread
        self.monitor_thread = None
        self.running = False
        
        # Circuit breaker for critical operations
        self.circuit_breaker_active = False
        self.circuit_breaker_start_time = 0
        self.circuit_breaker_trips = 0
        
        # Resource tracking
        self.resource_history = deque(maxlen=60)  # 5 minutes at 5-second intervals
        self.cpu_history = deque(maxlen=60)
        self.memory_history = deque(maxlen=60)
        self.network_history = deque(maxlen=60)
        
        # Action handlers
        self.action_handlers = {
            "pause_background": self._pause_background_tasks,
            "reduce_logging": self._reduce_logging_verbosity, 
            "circuit_break": self._activate_circuit_breaker,
            "optimize_memory": self._optimize_memory,
            "throttle_requests": self._throttle_requests
        }
        
        # Background tasks registry - to be populated by app
        self.background_tasks = {}
        self.background_tasks_paused = False
        
        # Metrics
        self.metrics = {
            'stress_events': 0,
            'max_stress_level': 0.0,
            'current_state': self.current_state.name,
            'total_stress_time': 0.0,
            'circuit_breaker_trips': 0,
            'actions_taken': {},
            'last_stress_time': 0.0,
        }
        
        logger.info(f"Stress handler initialized with CPU threshold: {self.cpu_threshold}%")
    
    def register(self, app=None):
        """Register with the application"""
        if app:
            self.app = app
        
        # Start stress monitoring thread if enabled
        if self.enabled:
            self.start_monitoring()
        
        # Register middleware for request prioritization if using Flask
        if self.app and hasattr(self.app, 'before_request'):
            try:
                # Register before_request handler for prioritization
                @self.app.before_request
                def prioritize_requests():
                    # Skip if not in stress mode
                    if self.current_state == StressState.NORMAL:
                        return None
                    
                    # Get the current endpoint (route)
                    endpoint = None
                    if hasattr(self.app, 'current_url_rule') and self.app.current_url_rule:
                        endpoint = self.app.current_url_rule.endpoint
                    
                    # Apply circuit breaking if active and not a critical endpoint
                    if (self.circuit_breaker_active and 
                        endpoint and 
                        endpoint not in self.critical_endpoints):
                        from flask import request, jsonify
                        # Return a service unavailable response
                        response = jsonify({
                            'status': 'error',
                            'message': 'Service temporarily unavailable due to high load'
                        })
                        response.status_code = 503
                        return response
                
                logger.info("Request prioritization middleware registered")
            except Exception as e:
                logger.warning(f"Failed to register request prioritization middleware: {e}")
        
        # Return self for method chaining
        return self
    
    def start_monitoring(self):
        """Start stress monitoring thread"""
        if self.monitor_thread and self.monitor_thread.is_alive():
            logger.warning("Stress monitoring thread already running")
            return False
        
        self.running = True
        self.monitor_thread = threading.Thread(
            target=self._monitoring_loop,
            daemon=True
        )
        self.monitor_thread.start()
        logger.info("Stress monitoring started")
        return True
    
    def stop_monitoring(self):
        """Stop stress monitoring thread"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2.0)
        logger.info("Stress monitoring stopped")
    
    def _monitoring_loop(self):
        """Background thread for stress monitoring"""
        while self.running:
            try:
                # Check for stress conditions
                stress_level = self._check_stress_level()
                
                # Take action based on stress level
                self._handle_stress(stress_level)
                
                # Determine next check interval based on current state
                if self.current_state != StressState.NORMAL:
                    check_interval = self.stress_check_interval
                else:
                    check_interval = self.normal_check_interval
                
            except Exception as e:
                logger.error(f"Error in stress monitoring loop: {e}")
                check_interval = self.normal_check_interval
            
            # Sleep for the appropriate interval
            time.sleep(check_interval)
    
    def _check_stress_level(self) -> float:
        """Check the current stress level of the system"""
        # Need system detector to check stress
        if not self.system_detector:
            return 0.0
        
        # Get current resource usage
        usage = self.system_detector.get_resource_usage()
        
        # Calculate stress level based on CPU and memory usage
        cpu_stress = usage.cpu_percent / self.cpu_threshold if self.cpu_threshold > 0 else 0
        memory_stress = usage.memory_percent / self.memory_warning_threshold if self.memory_warning_threshold > 0 else 0
        
        # Network stress
        network_mbps = (usage.net_recv_bytes_sec + usage.net_sent_bytes_sec) / (1024 * 1024)
        network_stress = network_mbps / self.network_threshold if self.network_threshold > 0 else 0
        
        # Combine stress factors (max value)
        stress_level = max(cpu_stress, memory_stress, network_stress)
        
        # Add to history
        self.resource_history.append((time.time(), stress_level))
        self.cpu_history.append((time.time(), cpu_stress))
        self.memory_history.append((time.time(), memory_stress))
        self.network_history.append((time.time(), network_stress))
        
        return stress_level
    
    def _handle_stress(self, stress_level: float):
        """Handle stress based on the current level"""
        previous_state = self.current_state
        
        # Determine new state based on stress level
        if stress_level >= 1.5:
            new_state = StressState.CRITICAL
        elif stress_level >= 1.2:
            new_state = StressState.HIGH
        elif stress_level >= 1.0:
            new_state = StressState.ELEVATED
        else:
            new_state = StressState.NORMAL
        
        # Update state
        self.current_state = new_state
        
        # Record metrics
        self.metrics['current_state'] = new_state.name
        self.metrics['max_stress_level'] = max(self.metrics['max_stress_level'], stress_level)
        
        # Handle state change
        if new_state != previous_state:
            if new_state != StressState.NORMAL:
                # Entering stress state
                if previous_state == StressState.NORMAL:
                    self.stress_start_time = time.time()
                    self.consecutive_stress_detections = 1
                    self.metrics['stress_events'] += 1
                    self.metrics['last_stress_time'] = time.time()
                    logger.warning(f"Entering stress state: {new_state.name} (level: {stress_level:.2f})")
                    
                    # Take actions based on stress level
                    self._take_stress_actions(new_state)
                else:
                    # State escalation
                    logger.warning(f"Stress escalating: {previous_state.name} -> {new_state.name} (level: {stress_level:.2f})")
                    self._take_stress_actions(new_state)
            else:
                # Returning to normal state
                stress_duration = time.time() - self.stress_start_time
                self.metrics['total_stress_time'] += stress_duration
                logger.info(f"Returning to normal state after {stress_duration:.1f}s in stress")
                
                # Reset stress tracking
                self.consecutive_stress_detections = 0
                
                # Restore normal operation
                self._restore_normal_operation()
        else:
            # Same state as before
            if new_state != StressState.NORMAL:
                # Still in stress state
                self.consecutive_stress_detections += 1
                self.stress_duration_time = time.time() - self.stress_start_time
                
                # Check for max stress time
                if self.max_stress_time > 0 and self.stress_duration_time > self.max_stress_time:
                    logger.warning(f"Maximum stress time exceeded: {self.stress_duration_time:.1f}s")
                    
                    # Take more aggressive actions
                    self._take_emergency_actions()
    
    def _take_stress_actions(self, state: StressState):
        """Take actions based on the current stress state"""
        actions = []
        
        # Different actions based on stress level
        if state == StressState.ELEVATED:
            # Mild actions for elevated stress
            if "reduce_logging" in self.stress_actions:
                actions.append("reduce_logging")
            
            # Run GC if memory optimizer available
            if self.memory_optimizer:
                self.memory_optimizer._run_garbage_collection()
        
        elif state == StressState.HIGH:
            # More aggressive actions for high stress
            if "pause_background" in self.stress_actions:
                actions.append("pause_background")
            
            if "optimize_memory" in self.stress_actions:
                actions.append("optimize_memory")
        
        elif state == StressState.CRITICAL:
            # Critical actions for extreme stress
            if "circuit_break" in self.stress_actions:
                actions.append("circuit_break")
            
            if "throttle_requests" in self.stress_actions:
                actions.append("throttle_requests")
            
            # Additional actions based on available handlers
            for action in self.stress_actions:
                if action in self.action_handlers and action not in actions:
                    actions.append(action)
        
        # Execute the selected actions
        for action in actions:
            if action in self.action_handlers:
                handler = self.action_handlers[action]
                try:
                    result = handler()
                    
                    # Update metrics
                    if action not in self.metrics['actions_taken']:
                        self.metrics['actions_taken'][action] = 0
                    self.metrics['actions_taken'][action] += 1
                    
                    logger.info(f"Stress action taken: {action} - result: {result}")
                except Exception as e:
                    logger.error(f"Error executing stress action {action}: {e}")
    
    def _take_emergency_actions(self):
        """Take emergency actions when max stress time is exceeded"""
        logger.warning("Taking emergency actions due to prolonged stress")
        
        # Run aggressive memory optimization
        if self.memory_optimizer:
            self.memory_optimizer.optimize_memory(level='aggressive')
        
        # Activate circuit breaker
        self._activate_circuit_breaker()
        
        # Additional emergency measures could be implemented here
        
        # Reset stress start time to prevent repeated emergency actions
        self.stress_start_time = time.time()
    
    def _restore_normal_operation(self):
        """Restore normal operation after stress subsides"""
        # Deactivate circuit breaker
        if self.circuit_breaker_active:
            self._deactivate_circuit_breaker()
        
        # Resume background tasks
        if self.background_tasks_paused:
            self._resume_background_tasks()
        
        # Restore logging verbosity
        self._restore_logging_verbosity()
        
        # Additional restoration actions could be implemented here
        
        logger.info("Normal operation restored after stress period")
    
    def _pause_background_tasks(self):
        """Pause non-critical background tasks"""
        if self.background_tasks_paused:
            return False
        
        paused_count = 0
        if self.background_tasks:
            for task_name, task_info in self.background_tasks.items():
                if task_info.get('pausable', False) and not task_info.get('paused', False):
                    # Try to pause the task
                    pauser = task_info.get('pause_function')
                    if pauser and callable(pauser):
                        try:
                            pauser()
                            self.background_tasks[task_name]['paused'] = True
                            paused_count += 1
                        except Exception as e:
                            logger.error(f"Failed to pause background task {task_name}: {e}")
        
        self.background_tasks_paused = paused_count > 0
        return paused_count > 0
    
    def _resume_background_tasks(self):
        """Resume previously paused background tasks"""
        if not self.background_tasks_paused:
            return False
        
        resumed_count = 0
        if self.background_tasks:
            for task_name, task_info in self.background_tasks.items():
                if task_info.get('paused', False):
                    # Try to resume the task
                    resumer = task_info.get('resume_function')
                    if resumer and callable(resumer):
                        try:
                            resumer()
                            self.background_tasks[task_name]['paused'] = False
                            resumed_count += 1
                        except Exception as e:
                            logger.error(f"Failed to resume background task {task_name}: {e}")
        
        self.background_tasks_paused = resumed_count == 0
        return resumed_count > 0
    
    def _reduce_logging_verbosity(self):
        """Reduce logging verbosity during stress"""
        try:
            # Store original logging levels if not already stored
            if not hasattr(self, 'original_log_levels'):
                self.original_log_levels = {}
                
                for logger_name, logger_obj in logging.Logger.manager.loggerDict.items():
                    if isinstance(logger_obj, logging.Logger):
                        self.original_log_levels[logger_name] = logger_obj.level
                
                # Store root logger level
                root_logger = logging.getLogger()
                self.original_log_levels['root'] = root_logger.level
            
            # Set new reduced logging levels
            for logger_name, logger_obj in logging.Logger.manager.loggerDict.items():
                if isinstance(logger_obj, logging.Logger) and logger_obj.level < logging.WARNING:
                    logger_obj.setLevel(logging.WARNING)
            
            # Set root logger to WARNING if below
            root_logger = logging.getLogger()
            if root_logger.level < logging.WARNING:
                root_logger.setLevel(logging.WARNING)
            
            return True
        except Exception as e:
            logger.error(f"Error reducing logging verbosity: {e}")
            return False
    
    def _restore_logging_verbosity(self):
        """Restore original logging verbosity"""
        try:
            # Check if we have stored original levels
            if hasattr(self, 'original_log_levels'):
                # Restore original logging levels
                for logger_name, level in self.original_log_levels.items():
                    if logger_name == 'root':
                        # Special case for root logger
                        root_logger = logging.getLogger()
                        root_logger.setLevel(level)
                    else:
                        # Normal logger
                        logger_obj = logging.getLogger(logger_name)
                        logger_obj.setLevel(level)
                
                return True
            return False
        except Exception as e:
            logger.error(f"Error restoring logging verbosity: {e}")
            return False
    
    def _activate_circuit_breaker(self):
        """Activate circuit breaker to reject non-critical requests"""
        if self.circuit_breaker_active:
            return False
        
        self.circuit_breaker_active = True
        self.circuit_breaker_start_time = time.time()
        self.circuit_breaker_trips += 1
        self.metrics['circuit_breaker_trips'] += 1
        
        logger.warning("Circuit breaker activated - non-critical requests will be rejected")
        return True
    
    def _deactivate_circuit_breaker(self):
        """Deactivate circuit breaker"""
        if not self.circuit_breaker_active:
            return False
        
        self.circuit_breaker_active = False
        cb_duration = time.time() - self.circuit_breaker_start_time
        
        logger.info(f"Circuit breaker deactivated after {cb_duration:.1f}s")
        return True
    
    def _optimize_memory(self):
        """Optimize memory during stress"""
        if not self.memory_optimizer:
            return False
        
        # Run memory optimization
        result = self.memory_optimizer.optimize_memory(level='normal')
        return result and result.get('saved_mb', 0) > 0
    
    def _throttle_requests(self):
        """Throttle incoming requests during stress"""
        # Implementation depends on the web framework
        # For Flask, we could use a rate limiter
        # This is a placeholder
        return False
    
    def register_background_task(self, name, pause_function=None, resume_function=None, is_critical=False):
        """Register a background task that can be paused during stress"""
        self.background_tasks[name] = {
            'pause_function': pause_function,
            'resume_function': resume_function,
            'is_critical': is_critical,
            'pausable': pause_function is not None and resume_function is not None,
            'paused': False
        }
        logger.info(f"Background task registered: {name} (critical: {is_critical})")
        return True
    
    def get_stress_metrics(self):
        """Get current stress metrics"""
        # Update current state in metrics
        self.metrics['current_state'] = self.current_state.name
        
        # Calculate current stress level
        current_stress = 0.0
        if self.resource_history:
            current_stress = self.resource_history[-1][1]
        
        # Add real-time metrics
        metrics = {
            **self.metrics,
            'current_stress_level': current_stress,
            'current_state': self.current_state.name,
            'stress_duration': self.stress_duration_time if self.current_state != StressState.NORMAL else 0,
            'circuit_breaker_active': self.circuit_breaker_active,
            'background_tasks_paused': self.background_tasks_paused
        }
        
        # Add resource history summaries if available
        if self.cpu_history and self.memory_history:
            # Calculate averages
            cpu_values = [v for _, v in self.cpu_history]
            memory_values = [v for _, v in self.memory_history]
            network_values = [v for _, v in self.network_history] if self.network_history else []
            
            metrics.update({
                'cpu_stress_avg': sum(cpu_values) / len(cpu_values) if cpu_values else 0,
                'memory_stress_avg': sum(memory_values) / len(memory_values) if memory_values else 0,
                'network_stress_avg': sum(network_values) / len(network_values) if network_values else 0,
                'cpu_stress_current': cpu_values[-1] if cpu_values else 0,
                'memory_stress_current': memory_values[-1] if memory_values else 0,
                'network_stress_current': network_values[-1] if network_values else 0,
            })
        
        return metrics 