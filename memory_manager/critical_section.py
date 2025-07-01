"""
Critical Section Analysis System
-----------------------------
Module for detecting critical memory sections and pressure points in the application.

This module provides tools to identify moments of high memory usage,
track memory allocation patterns during peak load, and analyze critical
sections of code that may cause memory issues.
"""

import os
import sys
import time
import logging
import threading
import traceback
from typing import Dict, List, Set, Any, Optional, Tuple, Union, Callable
from collections import defaultdict, deque
import gc

logger = logging.getLogger("memory_manager.critical_section")

class CriticalSectionAnalyzer:
    """
    Analyzes application execution to identify critical sections of memory usage
    and potential pressure points in the application lifecycle.
    """
    
    def __init__(self, app=None, config=None, system_detector=None):
        """Initialize the critical section analyzer"""
        self.app = app
        self.config = config
        self.system_detector = system_detector
        
        # Configuration defaults
        self.enabled = True
        self.monitor_interval = 1.0  # 1 second (faster for more precise detection)
        self.history_size = 300      # 5 minutes of history at 1s intervals
        self.pressure_threshold = 0.8  # 80% of max observed or system memory
        self.autosample_enabled = True  # Automatically take samples during high pressure
        self.adaptive_threshold = True  # Dynamically adjust threshold based on history
        
        # Override with config if available
        if config and hasattr(config, 'critical_section'):
            self.enabled = getattr(config.critical_section, 'enabled', self.enabled)
            self.monitor_interval = getattr(config.critical_section, 'monitor_interval', self.monitor_interval)
            self.history_size = getattr(config.critical_section, 'history_size', self.history_size)
            self.pressure_threshold = getattr(config.critical_section, 'pressure_threshold', self.pressure_threshold)
            self.autosample_enabled = getattr(config.critical_section, 'autosample_enabled', self.autosample_enabled)
            self.adaptive_threshold = getattr(config.critical_section, 'adaptive_threshold', self.adaptive_threshold)
        
        # Data structures for tracking
        self.memory_history = deque(maxlen=self.history_size)
        self.critical_sections = []
        self.current_critical_section = None
        self.max_memory_seen = 0
        self.baseline_memory = 0
        self.history_lock = threading.RLock()
        
        # Pressure point detection
        self.in_pressure_state = False
        self.pressure_start_time = 0
        self.last_pressure_time = 0
        self.pressure_frequency = 0  # Number of pressure points per hour
        self.pressure_count = 0
        
        # Thread to monitor memory pressure
        self.monitor_thread = None
        self.running = False
        
        # Callstack sampling during pressure
        self.pressure_samples = []
        self.max_pressure_samples = 50  # Maximum number of samples to keep
        
        # Initialize with reasonable baseline if system detector available
        if system_detector:
            try:
                usage = system_detector.get_resource_usage()
                self.baseline_memory = usage.process_memory_bytes
                self.max_memory_seen = self.baseline_memory * 1.2  # 20% higher than baseline
            except:
                pass
        
        logger.info("Critical section analyzer initialized")
    
    @property
    def is_monitoring(self):
        """Check if monitoring is currently active"""
        return self.running and self.monitor_thread is not None and self.monitor_thread.is_alive()
    
    def start_monitoring(self):
        """Start critical section monitoring thread"""
        if self.is_monitoring:
            logger.debug("Critical section monitoring already active")
            return True
        
        # Clean up dead thread if any
        if self.monitor_thread and not self.monitor_thread.is_alive():
            self.monitor_thread = None
        
        self.running = True
        self.monitor_thread = threading.Thread(
            target=self._monitoring_loop,
            daemon=True,
            name="critical-section-monitor"
        )
        self.monitor_thread.start()
        logger.info(f"Critical section monitoring started with interval: {self.monitor_interval}s")
        return True
    
    def stop_monitoring(self):
        """Stop critical section monitoring thread"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2.0)
        logger.info("Critical section monitoring stopped")
    
    def _monitoring_loop(self):
        """Background thread for monitoring memory pressure"""
        start_time = time.time()
        while self.running:
            try:
                # Get current memory usage
                memory_usage = self._get_current_memory()
                timestamp = time.time()
                
                # Update maximum memory seen
                if memory_usage > self.max_memory_seen:
                    self.max_memory_seen = memory_usage
                
                # Calculate adaptive threshold if enabled
                current_threshold = self._get_current_threshold(memory_usage)
                
                # Check if we're in a pressure state
                in_pressure = memory_usage > current_threshold
                
                # Record data point
                with self.history_lock:
                    self.memory_history.append({
                        'timestamp': timestamp,
                        'memory_bytes': memory_usage,
                        'memory_mb': memory_usage / (1024 * 1024),
                        'in_pressure': in_pressure,
                        'threshold_bytes': current_threshold,
                        'threshold_mb': current_threshold / (1024 * 1024)
                    })
                
                # Detect transitions into/out of pressure state
                self._detect_pressure_transitions(in_pressure, timestamp, memory_usage)
                
            except Exception as e:
                logger.error(f"Error in critical section monitoring loop: {e}")
                logger.error(traceback.format_exc())
            
            # Calculate time to next check
            elapsed = time.time() - timestamp
            sleep_time = max(0.1, self.monitor_interval - elapsed)
            time.sleep(sleep_time)
        
        # Update pressure frequency based on monitoring duration and pressure count
        total_hours = (time.time() - start_time) / 3600
        if total_hours > 0:
            self.pressure_frequency = self.pressure_count / total_hours
    
    def _get_current_memory(self):
        """Get current memory usage in bytes"""
        if self.system_detector:
            try:
                usage = self.system_detector.get_resource_usage()
                return usage.process_memory_bytes
            except:
                pass
        
        # Fallback method
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss
        except:
            # Last resort - use gc.get_stats() to estimate
            gc_stats = gc.get_stats()[0]
            return gc_stats['size'] * 1024  # Conservative estimate
    
    def _get_current_threshold(self, current_memory):
        """Calculate the current pressure threshold"""
        if not self.adaptive_threshold:
            # Static threshold based on max seen
            return self.max_memory_seen * self.pressure_threshold
        
        # Adaptive threshold based on recent history
        if len(self.memory_history) < 10:
            # Not enough history, use default threshold
            return max(current_memory * 1.2, self.max_memory_seen * self.pressure_threshold)
        
        # Calculate a baseline from recent non-pressure points
        with self.history_lock:
            recent_points = list(self.memory_history)[-30:]  # Last 30 points
            non_pressure_points = [p['memory_bytes'] for p in recent_points 
                                   if not p.get('in_pressure', False)]
            
            if non_pressure_points:
                baseline = sum(non_pressure_points) / len(non_pressure_points)
                # Set threshold higher than recent baseline
                adaptive_threshold = baseline * (1 + self.pressure_threshold)
                
                # But never less than global threshold
                return max(adaptive_threshold, self.max_memory_seen * self.pressure_threshold)
        
        # Fallback to default
        return self.max_memory_seen * self.pressure_threshold
    
    def _detect_pressure_transitions(self, in_pressure, timestamp, memory_bytes):
        """Detect transitions between normal and pressure states"""
        if in_pressure and not self.in_pressure_state:
            # Transition to pressure state
            self.in_pressure_state = True
            self.pressure_start_time = timestamp
            self.pressure_count += 1
            
            # Log the pressure start
            logger.warning(f"Memory pressure detected: {memory_bytes/(1024*1024):.1f}MB "
                           f"({memory_bytes/self.max_memory_seen:.1%} of max observed)")
            
            # Start a new critical section
            self._begin_critical_section(timestamp, memory_bytes)
            
            # Take stack sample if enabled
            if self.autosample_enabled:
                self._take_stack_sample(memory_bytes, "pressure_start")
        
        elif not in_pressure and self.in_pressure_state:
            # Transition out of pressure state
            self.in_pressure_state = False
            pressure_duration = timestamp - self.pressure_start_time
            
            # Log the pressure end
            logger.warning(f"Memory pressure relieved after {pressure_duration:.1f}s, "
                          f"current usage: {memory_bytes/(1024*1024):.1f}MB")
            
            # End the current critical section
            self._end_critical_section(timestamp, memory_bytes, pressure_duration)
            
            # Take stack sample if enabled
            if self.autosample_enabled:
                self._take_stack_sample(memory_bytes, "pressure_end")
        
        elif in_pressure and timestamp - self.last_pressure_time >= 60:
            # Still in pressure state after a minute
            self.last_pressure_time = timestamp
            
            # Log continued pressure
            pressure_duration = timestamp - self.pressure_start_time
            logger.warning(f"Memory pressure continuing for {pressure_duration:.1f}s, "
                          f"current usage: {memory_bytes/(1024*1024):.1f}MB")
            
            # Update the current critical section
            if self.current_critical_section:
                self.current_critical_section['current_memory_bytes'] = memory_bytes
                self.current_critical_section['max_memory_bytes'] = max(
                    self.current_critical_section['max_memory_bytes'],
                    memory_bytes
                )
                self.current_critical_section['duration'] = pressure_duration
            
            # Take stack sample if enabled
            if self.autosample_enabled:
                self._take_stack_sample(memory_bytes, "pressure_ongoing")
    
    def _begin_critical_section(self, timestamp, memory_bytes):
        """Begin a new critical section"""
        self.current_critical_section = {
            'start_time': timestamp,
            'start_memory_bytes': memory_bytes,
            'max_memory_bytes': memory_bytes,
            'current_memory_bytes': memory_bytes,
            'end_time': None,
            'end_memory_bytes': None,
            'duration': 0,
            'stack_samples': [],
            'events': [{
                'type': 'start',
                'timestamp': timestamp,
                'memory_bytes': memory_bytes
            }]
        }
    
    def _end_critical_section(self, timestamp, memory_bytes, duration):
        """End the current critical section"""
        if not self.current_critical_section:
            return
        
        # Update final state
        self.current_critical_section['end_time'] = timestamp
        self.current_critical_section['end_memory_bytes'] = memory_bytes
        self.current_critical_section['duration'] = duration
        
        # Add end event
        self.current_critical_section['events'].append({
            'type': 'end',
            'timestamp': timestamp,
            'memory_bytes': memory_bytes
        })
        
        # Add to history
        self.critical_sections.append(self.current_critical_section)
        self.current_critical_section = None
        
        # Keep history bounded
        if len(self.critical_sections) > 50:
            self.critical_sections = self.critical_sections[-50:]
    
    def _take_stack_sample(self, memory_bytes, reason):
        """Take a sample of the current stack trace"""
        try:
            # Get current stack trace
            stack = traceback.extract_stack()
            
            # Filter out memory management frames
            filtered_stack = [frame for frame in stack 
                             if 'memory_manager' not in frame.filename]
            
            # Create sample
            sample = {
                'timestamp': time.time(),
                'memory_bytes': memory_bytes,
                'memory_mb': memory_bytes / (1024 * 1024),
                'reason': reason,
                'stack': filtered_stack,
                'stack_summary': ''.join(traceback.format_list(filtered_stack[-10:]))  # Last 10 frames
            }
            
            # Add to samples list
            self.pressure_samples.append(sample)
            
            # Also add to current critical section if exists
            if self.current_critical_section:
                self.current_critical_section['stack_samples'].append(sample)
            
            # Keep samples bounded
            if len(self.pressure_samples) > self.max_pressure_samples:
                self.pressure_samples = self.pressure_samples[-self.max_pressure_samples:]
            
        except Exception as e:
            logger.error(f"Error taking stack sample: {e}")
    
    def mark_critical_point(self, label=None, details=None):
        """
        Manually mark a critical point in the application
        
        This can be called from application code to signal important events
        that might impact memory usage.
        
        Args:
            label: A label for this critical point
            details: Additional details or context
        """
        try:
            timestamp = time.time()
            memory_bytes = self._get_current_memory()
            
            event = {
                'type': 'manual_mark',
                'timestamp': timestamp,
                'memory_bytes': memory_bytes,
                'memory_mb': memory_bytes / (1024 * 1024),
                'label': label or 'Unmarked critical point',
                'details': details
            }
            
            # Take a stack trace
            stack = traceback.extract_stack()
            event['caller_stack'] = stack
            
            # Add to current critical section if we're in one
            if self.current_critical_section:
                self.current_critical_section['events'].append(event)
            
            logger.info(f"Critical point marked: {label}, "
                       f"memory usage: {memory_bytes/(1024*1024):.1f}MB")
            
            return event
            
        except Exception as e:
            logger.error(f"Error marking critical point: {e}")
            return None
    
    def get_current_pressure_status(self):
        """Get the current memory pressure status"""
        memory_bytes = self._get_current_memory()
        threshold = self._get_current_threshold(memory_bytes)
        
        return {
            'timestamp': time.time(),
            'memory_bytes': memory_bytes,
            'memory_mb': memory_bytes / (1024 * 1024),
            'threshold_bytes': threshold,
            'threshold_mb': threshold / (1024 * 1024),
            'in_pressure_state': self.in_pressure_state,
            'pressure_level': memory_bytes / threshold,
            'max_memory_seen_mb': self.max_memory_seen / (1024 * 1024),
            'pressure_count': self.pressure_count,
            'pressure_frequency': self.pressure_frequency
        }
    
    def get_recent_memory_history(self):
        """Get recent memory usage history"""
        with self.history_lock:
            return list(self.memory_history)
    
    def get_critical_sections(self):
        """Get all recorded critical sections"""
        # Return deep copy to avoid threading issues
        return [{
            'start_time': section['start_time'],
            'end_time': section['end_time'],
            'duration': section['duration'],
            'start_memory_mb': section['start_memory_bytes'] / (1024 * 1024),
            'max_memory_mb': section['max_memory_bytes'] / (1024 * 1024),
            'end_memory_mb': section['end_memory_bytes'] / (1024 * 1024) if section['end_memory_bytes'] else None,
            'event_count': len(section['events']),
            'has_samples': len(section['stack_samples']) > 0
        } for section in self.critical_sections]
    
    def get_section_details(self, index):
        """Get details of a specific critical section"""
        if 0 <= index < len(self.critical_sections):
            section = self.critical_sections[index]
            
            # Return a simplified view for API consumption
            return {
                'start_time': section['start_time'],
                'end_time': section['end_time'],
                'duration': section['duration'],
                'start_memory_mb': section['start_memory_bytes'] / (1024 * 1024),
                'max_memory_mb': section['max_memory_bytes'] / (1024 * 1024),
                'end_memory_mb': section['end_memory_bytes'] / (1024 * 1024) if section['end_memory_bytes'] else None,
                'events': [{
                    'type': event['type'],
                    'timestamp': event['timestamp'],
                    'memory_mb': event['memory_bytes'] / (1024 * 1024),
                    'label': event.get('label'),
                    'details': event.get('details')
                } for event in section['events']],
                'stack_samples': [{
                    'timestamp': sample['timestamp'],
                    'memory_mb': sample['memory_mb'],
                    'reason': sample['reason'],
                    'stack_summary': sample['stack_summary']
                } for sample in section['stack_samples']]
            }
        return None
    
    def get_metrics(self):
        """Get metrics about critical section analysis"""
        return {
            'is_in_pressure': self.in_pressure_state,
            'pressure_count': self.pressure_count,
            'pressure_frequency': self.pressure_frequency,
            'critical_sections_count': len(self.critical_sections),
            'current_memory_mb': self._get_current_memory() / (1024 * 1024),
            'max_memory_seen_mb': self.max_memory_seen / (1024 * 1024)
        }
    
    def register(self, app=None):
        """Register with Flask application if available"""
        if app:
            self.app = app
        
        # Start monitoring if enabled
        if self.enabled:
            self.start_monitoring()
        
        return self 