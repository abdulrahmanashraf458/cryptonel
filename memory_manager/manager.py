"""
Memory Manager
------------
Main module that coordinates memory monitoring, tracking, analysis, 
and optimization subsystems.

This module provides a unified API for managing all memory-related
functionality and coordinates between different subsystems.
"""

import logging
import threading
import time
from typing import Dict, Any, Optional

# Import existing components
from .monitor import MemoryMonitor

# Import new components
from .object_tracker import ObjectTracker
from .heap_analyzer import HeapAnalyzer  
from .critical_section import CriticalSectionAnalyzer

logger = logging.getLogger("memory_manager.manager")

class MemoryManager:
    """
    MemoryManager provides a unified interface for all memory management
    capabilities including monitoring, analysis, and optimization.
    """
    
    def __init__(self, app=None, config=None):
        """
        Initialize the memory manager with optional Flask app and configuration.
        
        Args:
            app: Optional Flask application to register with
            config: Optional configuration object or dictionary
        """
        self.app = app
        self.config = config
        self.initialized = False
        
        # Core components
        self.memory_monitor = None
        
        # Advanced analysis components
        self.object_tracker = None
        self.heap_analyzer = None
        self.critical_section_analyzer = None
        
        # Component status
        self.component_status = {}
        
        # Initialize immediately if app provided
        if app is not None:
            self.register(app)
    
    def register(self, app):
        """
        Register the memory manager with a Flask application.
        
        This initializes all components and integrates them with
        the Flask application lifecycle.
        
        Args:
            app: Flask application instance
        """
        self.app = app
        self.initialize()
        
        try:
            # Register with Flask
            if hasattr(app, 'before_first_request'):
                @app.before_first_request
                def initialize_memory_manager():
                    self.start()
            
            # For Flask 2.x which doesn't have before_first_request
            elif hasattr(app, 'before_request'):
                self._started = False
                
                @app.before_request
                def initialize_memory_manager():
                    if not self._started:
                        self._started = True
                        self.start()
        except Exception as e:
            logger.warning(f"Error registering with Flask app: {e}")
        
        return self
    
    def initialize(self):
        """
        Initialize all memory manager components.
        
        This sets up the object structures but doesn't start 
        any monitoring threads.
        """
        if self.initialized:
            return self
        
        # Initialize core monitor
        self.memory_monitor = MemoryMonitor(app=self.app, config=self.config)
        self.component_status['monitor'] = 'initialized'
        
        # Initialize advanced components
        try:
            # Object Tracker for memory leak detection
            self.object_tracker = ObjectTracker(
            app=self.app,
            config=self.config,
                system_detector=self.memory_monitor.system_detector if hasattr(self.memory_monitor, 'system_detector') else None
        )
            self.component_status['object_tracker'] = 'initialized'
        
            # Heap Analyzer for fragmentation analysis
            self.heap_analyzer = HeapAnalyzer(
            app=self.app,
            config=self.config,
                system_detector=self.memory_monitor.system_detector if hasattr(self.memory_monitor, 'system_detector') else None
        )
            self.component_status['heap_analyzer'] = 'initialized'
        
            # Critical Section Analyzer
            self.critical_section_analyzer = CriticalSectionAnalyzer(
            app=self.app,
            config=self.config,
                system_detector=self.memory_monitor.system_detector if hasattr(self.memory_monitor, 'system_detector') else None
            )
            self.component_status['critical_section_analyzer'] = 'initialized'
            
        except Exception as e:
            logger.error(f"Error initializing advanced memory components: {e}")
        
        self.initialized = True
        logger.info("Memory manager initialized with all components")
        return self
    
    def start(self):
        """
        Start all memory manager monitoring threads.
        
        This activates the monitoring, tracking, and analysis systems.
        """
        if not self.initialized:
            self.initialize()
        
        # Start core monitoring
        if self.memory_monitor:
            try:
                self.memory_monitor.start_monitoring()
                self.component_status['monitor'] = 'active'
            except Exception as e:
                logger.error(f"Error starting memory monitor: {e}")
                self.component_status['monitor'] = 'error'
        
        # Start advanced components
        try:
            # Object Tracker
            if self.object_tracker:
                self.object_tracker.start_tracking()
                self.component_status['object_tracker'] = 'active'
            
            # Heap Analyzer
            if self.heap_analyzer:
                self.heap_analyzer.start_analysis()
                self.component_status['heap_analyzer'] = 'active'
            
            # Critical Section Analyzer
            if self.critical_section_analyzer:
                self.critical_section_analyzer.start_monitoring()
                self.component_status['critical_section_analyzer'] = 'active'
                
        except Exception as e:
            logger.error(f"Error starting advanced memory components: {e}")
        
        logger.info("Memory manager started all components")
        return self
    
    def stop(self):
        """
        Stop all memory manager monitoring threads.
        """
        # Stop core monitoring
        if self.memory_monitor:
            try:
                self.memory_monitor.stop_monitoring()
                self.component_status['monitor'] = 'stopped'
            except Exception as e:
                logger.error(f"Error stopping memory monitor: {e}")
        
        # Stop advanced components
        try:
            # Object Tracker
            if self.object_tracker:
                self.object_tracker.stop_tracking()
                self.component_status['object_tracker'] = 'stopped'
            
            # Heap Analyzer
            if self.heap_analyzer:
                self.heap_analyzer.stop_analysis()
                self.component_status['heap_analyzer'] = 'stopped'
            
            # Critical Section Analyzer
            if self.critical_section_analyzer:
                self.critical_section_analyzer.stop_monitoring()
                self.component_status['critical_section_analyzer'] = 'stopped'
                
        except Exception as e:
            logger.error(f"Error stopping advanced memory components: {e}")
        
        logger.info("Memory manager stopped all components")
        return self
    
    def get_status(self):
        """
        Get the current status of all memory manager components.
        
        Returns:
            Dict containing status information for all components
        """
        status = {
            'initialized': self.initialized,
            'components': self.component_status
        }
        
        # Add monitoring status
        if self.memory_monitor:
            status['monitoring'] = {
                'active': self.memory_monitor.is_monitoring,
                'uptime': self.memory_monitor.get_uptime() if hasattr(self.memory_monitor, 'get_uptime') else 0,
                'last_reading': self.memory_monitor.get_latest_memory_reading() 
                    if hasattr(self.memory_monitor, 'get_latest_memory_reading') else None
            }
        
        # Add advanced component statuses
        advanced_status = {}
        
        # Object Tracker status
        if self.object_tracker:
            obj_metrics = self.object_tracker.get_metrics()
            advanced_status['object_tracker'] = {
                'active': self.object_tracker.is_tracking,
                'tracked_objects': obj_metrics.get('tracked_objects', 0),
                'retain_cycles': obj_metrics.get('retain_cycles', 0),
                'dangling_pointers': obj_metrics.get('dangling_pointers', 0)
            }
        
        # Heap Analyzer status
        if self.heap_analyzer:
            heap_metrics = self.heap_analyzer.get_metrics()
            advanced_status['heap_analyzer'] = {
                'active': self.heap_analyzer.is_analyzing,
                'fragmentation_index': heap_metrics.get('fragmentation_index', 0),
                'snapshots': heap_metrics.get('snapshots_count', 0)
            }
        
        # Critical Section status
        if self.critical_section_analyzer:
            cs_metrics = self.critical_section_analyzer.get_metrics()
            advanced_status['critical_section'] = {
                'active': self.critical_section_analyzer.is_monitoring,
                'pressure_state': cs_metrics.get('is_in_pressure', False),
                'pressure_count': cs_metrics.get('pressure_count', 0),
                'max_memory_mb': cs_metrics.get('max_memory_seen_mb', 0)
            }
            
        status['advanced'] = advanced_status
        return status
    
    def get_memory_summary(self):
        """
        Get a comprehensive summary of memory usage and analysis.
        
        Returns:
            Dict containing memory usage summary from all components
        """
        summary = {
            'timestamp': time.time(),
            'basic': {}
        }
        
        # Get basic memory info from monitor
        if self.memory_monitor:
            try:
                memory_info = self.memory_monitor.get_latest_memory_reading()
                if memory_info:
                    summary['basic'] = {
                        'process_memory_mb': memory_info.get('process_memory_mb', 0),
                        'system_memory_mb': memory_info.get('system_memory_mb', 0),
                        'memory_percent': memory_info.get('memory_percent', 0)
                    }
            except Exception as e:
                logger.error(f"Error getting memory summary from monitor: {e}")
        
        # Get object tracking summary
        if self.object_tracker:
            try:
                summary['object_tracking'] = self.object_tracker.get_object_summary()
            except Exception as e:
                logger.error(f"Error getting object tracking summary: {e}")
        
        # Get heap analysis summary
        if self.heap_analyzer:
            try:
                summary['heap'] = self.heap_analyzer.get_heap_summary()
            except Exception as e:
                logger.error(f"Error getting heap summary: {e}")
        
        # Get critical section summary
        if self.critical_section_analyzer:
            try:
                summary['pressure'] = self.critical_section_analyzer.get_current_pressure_status()
            except Exception as e:
                logger.error(f"Error getting pressure status: {e}")
        
        return summary
    
    def get_memory_issues(self):
        """
        Get a list of detected memory issues from all analyzers.
        
        Returns:
            Dict containing memory issues from all components
        """
        issues = {
            'timestamp': time.time(),
            'has_issues': False,
            'issues': []
        }
        
        # Check for memory leaks (retain cycles)
        if self.object_tracker:
            try:
                # Get retain cycles
                retain_cycles = self.object_tracker.get_retain_cycles()
                if retain_cycles:
                    for cycle in retain_cycles:
                        issues['issues'].append({
                            'type': 'retain_cycle',
                            'severity': 'high',
                            'description': f"Detected retain cycle with {cycle.get('cycle_length', 0)} objects",
                            'details': cycle
                        })
                
                # Get dangling pointers
                dangling_pointers = self.object_tracker.get_dangling_pointers()
                if dangling_pointers:
                    for pointer in dangling_pointers:
                        issues['issues'].append({
                            'type': 'dangling_pointer',
                            'severity': 'medium',
                            'description': f"Detected dangling pointer to {pointer.get('object_type', 'unknown')} object",
                            'details': pointer
                        })
            except Exception as e:
                logger.error(f"Error getting memory issues from object tracker: {e}")
        
        # Check for heap fragmentation
        if self.heap_analyzer:
            try:
                # Get fragmentation data
                heap_summary = self.heap_analyzer.get_heap_summary()
                frag_index = heap_summary.get('fragmentation_index', 0)
                
                if frag_index > 0.7:
                    issues['issues'].append({
                        'type': 'high_fragmentation',
                        'severity': 'high',
                        'description': f"High heap fragmentation detected: {frag_index:.2f}",
                        'details': {'fragmentation_index': frag_index}
                    })
                elif frag_index > 0.4:
                    issues['issues'].append({
                        'type': 'moderate_fragmentation',
                        'severity': 'medium',
                        'description': f"Moderate heap fragmentation detected: {frag_index:.2f}",
                        'details': {'fragmentation_index': frag_index}
                    })
                
                # Get optimization suggestions
                suggestions = self.heap_analyzer.suggest_optimizations()
                if suggestions:
                    for suggestion in suggestions:
                        if suggestion['priority'] == 'High':
                            issues['issues'].append({
                                'type': 'optimization_needed',
                                'severity': 'medium',
                                'description': suggestion['issue'],
                                'suggestion': suggestion['suggestion'],
                                'details': suggestion
                            })
            except Exception as e:
                logger.error(f"Error getting memory issues from heap analyzer: {e}")
        
        # Check for critical sections under pressure
        if self.critical_section_analyzer:
            try:
                pressure_status = self.critical_section_analyzer.get_current_pressure_status()
                
                # Currently under pressure
                if pressure_status.get('in_pressure_state', False):
                    issues['issues'].append({
                        'type': 'memory_pressure',
                        'severity': 'high',
                        'description': f"System is currently under memory pressure: {pressure_status.get('memory_mb', 0):.1f}MB",
                        'details': pressure_status
                    })
                
                # Frequent pressure points
                if pressure_status.get('pressure_frequency', 0) > 10:  # More than 10 per hour
                    issues['issues'].append({
                        'type': 'frequent_pressure',
                        'severity': 'high',
                        'description': f"Frequent memory pressure events: {pressure_status.get('pressure_frequency', 0):.1f} per hour",
                        'details': {
                            'frequency': pressure_status.get('pressure_frequency', 0),
                            'count': pressure_status.get('pressure_count', 0)
                        }
                    })
            except Exception as e:
                logger.error(f"Error getting memory issues from critical section analyzer: {e}")
        
        # Check if we have any issues
        if issues['issues']:
            issues['has_issues'] = True
            issues['count'] = len(issues['issues'])
        
        return issues
    
    def mark_critical_point(self, label, details=None):
        """
        Mark a critical point in the application for memory analysis.
        
        This can be called from application code to signal important events
        that might impact memory usage.
        
        Args:
            label: A label for this critical point
            details: Additional details or context
            
        Returns:
            Dict containing the event information or None if marking failed
        """
        if self.critical_section_analyzer:
            try:
                return self.critical_section_analyzer.mark_critical_point(label, details)
            except Exception as e:
                logger.error(f"Error marking critical point: {e}")
        return None
    
    def run_immediate_analysis(self):
        """
        Run an immediate analysis of memory state across all analyzers.
        
        Returns:
            Dict containing comprehensive analysis results
        """
        results = {
            'timestamp': time.time(),
        }
        
        # Run object tracking analysis
        if self.object_tracker:
            try:
                results['objects'] = self.object_tracker.get_object_summary()
            except Exception as e:
                logger.error(f"Error running immediate object analysis: {e}")
        
        # Run heap analysis
        if self.heap_analyzer:
            try:
                results['heap'] = self.heap_analyzer.run_immediate_analysis()
                results['hotspots'] = self.heap_analyzer.get_allocation_hotspots()
                results['suggestions'] = self.heap_analyzer.suggest_optimizations()
            except Exception as e:
                logger.error(f"Error running immediate heap analysis: {e}")
        
        # Get critical section status
        if self.critical_section_analyzer:
            try:
                results['pressure'] = self.critical_section_analyzer.get_current_pressure_status()
                results['critical_sections'] = self.critical_section_analyzer.get_critical_sections()
            except Exception as e:
                logger.error(f"Error getting critical section status: {e}")
        
        return results 