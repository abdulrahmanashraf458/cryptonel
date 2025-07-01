"""
Heap Analysis System
------------------
Advanced module for tracking heap usage, analyzing memory fragmentation,
and optimizing memory allocation patterns.

This module provides tools to understand memory layout, detect fragmentation
issues, and track allocation patterns over time.
"""

import os
import sys
import time
import logging
import threading
import traceback
from typing import Dict, List, Any, Optional, Tuple, Union
from collections import defaultdict, deque
import gc

# Try to import optional modules for deeper heap analysis
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

# Make guppy/guppy3 import optional
HAS_GUPPY = False
try:
    # Try guppy3 first (Python 3)
    from guppy3 import hpy  # type: ignore
    HAS_GUPPY = True
except ImportError:
    try:
        # Fall back to legacy guppy
        from guppy import hpy  # type: ignore
        HAS_GUPPY = True
    except ImportError:
        # Neither available - disable functionality
        pass

try:
    import pympler.muppy as muppy
    import pympler.summary as summary
    import pympler.tracker as tracker
    HAS_PYMPLER = True
except ImportError:
    HAS_PYMPLER = False

logger = logging.getLogger("memory_manager.heap_analyzer")

class HeapAnalyzer:
    """
    Analyzes heap memory layout, detects fragmentation, and provides
    insights into memory allocation patterns.
    """
    
    def __init__(self, app=None, config=None, system_detector=None):
        """Initialize the heap analyzer"""
        self.app = app
        self.config = config
        self.system_detector = system_detector
        
        # Configuration defaults
        self.enabled = True
        self.analysis_interval = 300.0  # 5 minutes
        self.history_size = 24  # Keep 24 snapshots
        self.log_directory = "logs/memory"
        self.deep_analysis = HAS_PYMPLER or HAS_GUPPY  # Use deep analysis if available
        
        # Override with config if available
        if config and hasattr(config, 'heap_analyzer'):
            self.enabled = getattr(config.heap_analyzer, 'enabled', self.enabled)
            self.analysis_interval = getattr(config.heap_analyzer, 'analysis_interval', self.analysis_interval)
            self.history_size = getattr(config.heap_analyzer, 'history_size', self.history_size)
            self.log_directory = getattr(config.heap_analyzer, 'log_directory', self.log_directory)
            self.deep_analysis = getattr(config.heap_analyzer, 'deep_analysis', self.deep_analysis)
        
        # Set up data structures for tracking heap metrics
        self.heap_history = deque(maxlen=self.history_size)
        self.last_gc_count = 0
        self.fragmentation_index = 0.0  # 0-1 scale, higher means more fragmented
        self.history_lock = threading.RLock()
        
        # Advanced analysis tools
        self.pympler_tracker = None
        if HAS_PYMPLER and self.deep_analysis:
            try:
                self.pympler_tracker = tracker.SummaryTracker()
                logger.info("Initialized Pympler memory tracker")
            except Exception as e:
                logger.warning(f"Failed to initialize Pympler tracker: {e}")
        
        # Analysis thread
        self.analyzer_thread = None
        self.running = False
        
        # Initialize heap monitoring
        if self.enabled:
            # Make sure directory exists
            if self.log_directory:
                os.makedirs(self.log_directory, exist_ok=True)
        
        logger.info("Heap analyzer initialized")
        
        # Log available analysis tools
        available_tools = []
        if HAS_PSUTIL:
            available_tools.append("psutil")
        if HAS_GUPPY:
            available_tools.append("guppy")
        if HAS_PYMPLER:
            available_tools.append("pympler")
        
        if available_tools:
            logger.info(f"Heap analysis will use: {', '.join(available_tools)}")
        else:
            logger.warning("No advanced heap analysis tools available, using basic analysis only")
    
    @property
    def is_analyzing(self):
        """Check if analysis is currently active"""
        return self.running and self.analyzer_thread is not None and self.analyzer_thread.is_alive()
    
    def start_analysis(self):
        """Start heap analysis thread"""
        if self.is_analyzing:
            logger.debug("Heap analysis already active")
            return True
        
        # Clean up dead thread if any
        if self.analyzer_thread and not self.analyzer_thread.is_alive():
            self.analyzer_thread = None
        
        self.running = True
        self.analyzer_thread = threading.Thread(
            target=self._analysis_loop,
            daemon=True,
            name="heap-analyzer"
        )
        self.analyzer_thread.start()
        logger.info(f"Heap analysis started with interval: {self.analysis_interval}s")
        return True
    
    def stop_analysis(self):
        """Stop heap analysis thread"""
        self.running = False
        if self.analyzer_thread:
            self.analyzer_thread.join(timeout=2.0)
        logger.info("Heap analysis stopped")
    
    def _analysis_loop(self):
        """Background thread for heap analysis"""
        while self.running:
            try:
                # Analyze heap
                self._analyze_heap()
                
                # Detect fragmentation
                self._analyze_fragmentation()
                
            except Exception as e:
                logger.error(f"Error in heap analysis loop: {e}")
                logger.error(traceback.format_exc())
            
            # Sleep for the analysis interval
            time.sleep(self.analysis_interval)
    
    def _analyze_heap(self):
        """Analyze heap memory usage and collect metrics"""
        try:
            # Basic metrics
            gc.collect()  # Force garbage collection for more accurate stats
            
            # Get current memory usage
            if self.system_detector:
                usage = self.system_detector.get_resource_usage()
                process_memory = usage.process_memory_bytes
            else:
                # Fallback
                process_memory = 0
                if HAS_PSUTIL:
                    process = psutil.Process()
                    process_memory = process.memory_info().rss
            
            # Collect GC stats
            gc_stats = {
                'collections': gc.get_count(),
                'objects': len(gc.get_objects()),
                'garbage': len(gc.garbage)
            }
            
            # Compute GC efficiency
            current_gc_total = sum(gc_stats['collections'])
            gc_count_delta = current_gc_total - self.last_gc_count
            self.last_gc_count = current_gc_total
            
            # Create base metrics
            metrics = {
                'timestamp': time.time(),
                'process_memory_bytes': process_memory,
                'process_memory_mb': process_memory / (1024 * 1024),
                'gc_stats': gc_stats,
                'gc_count_delta': gc_count_delta,
                'fragmentation_index': self.fragmentation_index
            }
            
            # Add Pympler metrics if available
            if self.pympler_tracker:
                try:
                    # Get detailed size by type
                    all_objects = muppy.get_objects()
                    sum_data = summary.summarize(all_objects)
                    
                    # Extract top types by size
                    type_stats = []
                    for row in sum_data:
                        type_stats.append({
                            'type': str(row[0]),
                            'count': row[1],
                            'size_bytes': row[2]
                        })
                    
                    # Sort by size (descending)
                    metrics['top_types_by_size'] = sorted(
                        type_stats, 
                        key=lambda x: x['size_bytes'], 
                        reverse=True
                    )[:10]  # Top 10
                    
                    # Get memory diff since last snapshot
                    try:
                        diff = self.pympler_tracker.diff()
                        # Convert to simpler dict format
                        diff_data = []
                        for row in diff:
                            diff_data.append({
                                'type': str(row[0]),
                                'count_delta': row[1],
                                'size_delta': row[2]
                            })
                        
                        metrics['memory_diff'] = sorted(
                            diff_data, 
                            key=lambda x: abs(x['size_delta']), 
                            reverse=True
                        )[:10]  # Top 10 changes
                    except Exception as e:
                        logger.debug(f"Error getting memory diff: {e}")
                        
                except Exception as e:
                    logger.warning(f"Error collecting Pympler metrics: {e}")
            
            # Add Guppy metrics if available
            if HAS_GUPPY and self.deep_analysis:
                try:
                    h = hpy()
                    heap = h.heap()
                    metrics['heap_size'] = heap.size
                    metrics['heap_count'] = heap.count
                    
                    # Get top 10 types by size
                    guppy_stats = []
                    for row in heap.byrcs:
                        guppy_stats.append({
                            'type': str(row.rcs.rs_name),
                            'count': row.rcs.rs_ninstance,
                            'size_bytes': row.size
                        })
                    
                    if not metrics.get('top_types_by_size'):
                        metrics['top_types_by_size'] = sorted(
                            guppy_stats, 
                            key=lambda x: x['size_bytes'], 
                            reverse=True
                        )[:10]  # Top 10
                        
                except Exception as e:
                    logger.debug(f"Error collecting Guppy metrics: {e}")
            
            # Save metrics to history
            with self.history_lock:
                self.heap_history.append(metrics)
            
            logger.info(f"Heap analysis completed: {metrics['process_memory_mb']:.1f}MB, "
                       f"fragmentation index: {self.fragmentation_index:.2f}")
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error analyzing heap: {e}")
            logger.error(traceback.format_exc())
            return None
    
    def _analyze_fragmentation(self):
        """Analyze heap fragmentation"""
        try:
            # Check if we have enough history to calculate fragmentation
            if len(self.heap_history) < 2:
                return
            
            with self.history_lock:
                # Get last two snapshots
                current = self.heap_history[-1]
                previous = self.heap_history[-2]
                
                # Calculate metrics that indicate fragmentation
                
                # 1. Memory growth without object count growth can indicate fragmentation
                memory_growth = current['process_memory_bytes'] - previous['process_memory_bytes']
                object_count_diff = current['gc_stats']['objects'] - previous['gc_stats']['objects']
                
                # If memory grew but object count didn't grow proportionally
                if memory_growth > 0 and object_count_diff <= 0:
                    # This could indicate fragmentation - memory growing without new objects
                    fragmentation_factor = min(1.0, memory_growth / (1024 * 1024 * 10))  # Cap at 1.0, 10MB is max
                else:
                    fragmentation_factor = 0.0
                
                # 2. GC efficiency - if GC is running but not reclaiming much memory
                gc_factor = 0.0
                if current['gc_count_delta'] > 0 and memory_growth > 0:
                    # GC ran but memory still grew - possible fragmentation
                    gc_factor = min(1.0, 0.2 * (current['gc_count_delta']))
                
                # 3. Process memory vs. actual object size ratio (if available from Pympler)
                object_size_factor = 0.0
                if 'top_types_by_size' in current:
                    # Sum the sizes of all top objects
                    total_object_size = sum(item['size_bytes'] for item in current['top_types_by_size'])
                    # If objects take less space than process memory, the rest might be fragmentation
                    if total_object_size > 0 and current['process_memory_bytes'] > total_object_size:
                        ratio = (current['process_memory_bytes'] - total_object_size) / current['process_memory_bytes']
                        object_size_factor = min(1.0, ratio)
                
                # Calculate combined fragmentation index (weighted average)
                self.fragmentation_index = 0.5 * fragmentation_factor + 0.3 * gc_factor + 0.2 * object_size_factor
                
                # Update the current metrics with the new fragmentation index
                current['fragmentation_index'] = self.fragmentation_index
                
                # Log if significant fragmentation detected
                if self.fragmentation_index > 0.5:
                    logger.warning(f"High heap fragmentation detected: {self.fragmentation_index:.2f}")
                
        except Exception as e:
            logger.error(f"Error analyzing fragmentation: {e}")
            logger.error(traceback.format_exc())
    
    def get_heap_summary(self):
        """Get current heap summary"""
        with self.history_lock:
            if not self.heap_history:
                return {
                    'error': 'No heap analysis data available',
                    'fragmentation_index': 0.0
                }
            
            # Get latest heap snapshot
            latest = self.heap_history[-1]
            
            # Create summary
            summary = {
                'timestamp': latest['timestamp'],
                'process_memory_mb': latest['process_memory_mb'],
                'fragmentation_index': self.fragmentation_index,
                'gc_stats': latest['gc_stats'],
            }
            
            # Add top types if available
            if 'top_types_by_size' in latest:
                summary['top_types_by_size'] = latest['top_types_by_size']
            
            # Add diff if available
            if 'memory_diff' in latest:
                summary['memory_diff'] = latest['memory_diff']
            
            return summary
    
    def get_fragmentation_history(self):
        """Get fragmentation history"""
        with self.history_lock:
            history = []
            for snapshot in self.heap_history:
                history.append({
                    'timestamp': snapshot['timestamp'],
                    'fragmentation_index': snapshot.get('fragmentation_index', 0.0),
                    'process_memory_mb': snapshot['process_memory_mb']
                })
            return history
    
    def run_immediate_analysis(self):
        """Run an immediate heap analysis"""
        try:
            # Force garbage collection
            gc.collect()
            
            # Run analysis
            metrics = self._analyze_heap()
            self._analyze_fragmentation()
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error in immediate heap analysis: {e}")
            logger.error(traceback.format_exc())
            return {'error': str(e)}
    
    def get_allocation_hotspots(self):
        """
        Try to identify hotspots of memory allocation
        
        Returns:
            List of allocation hotspots if available
        """
        # This is expensive, so we only do it on request
        hotspots = []
        
        # Use Pympler if available for allocation tracking
        if HAS_PYMPLER:
            try:
                # Get list of objects by size
                all_objects = muppy.get_objects()
                sum_data = summary.summarize(all_objects)
                
                # Check for unusually large objects
                for row in sum_data:
                    type_name = str(row[0])
                    count = row[1]
                    size = row[2]
                    
                    # Skip small allocations
                    if size < 1024 * 1024:  # 1MB
                        continue
                    
                    # Get average size per object of this type
                    avg_size = size / count if count > 0 else size
                    
                    # If average object size is large, it's a potential hotspot
                    if avg_size > 100 * 1024:  # 100KB per object
                        hotspots.append({
                            'type': type_name,
                            'count': count,
                            'total_size_mb': size / (1024 * 1024),
                            'avg_size_kb': avg_size / 1024,
                            'issue': 'Large individual objects'
                        })
                    
                    # If total size is large but many small objects, possible wasteful allocation
                    elif size > 10 * 1024 * 1024 and count > 1000:  # >10MB and >1000 objects
                        hotspots.append({
                            'type': type_name,
                            'count': count,
                            'total_size_mb': size / (1024 * 1024),
                            'avg_size_kb': avg_size / 1024,
                            'issue': 'Many small objects (possible inefficient allocation)'
                        })
            
            except Exception as e:
                logger.error(f"Error getting allocation hotspots: {e}")
        
        return hotspots
    
    def suggest_optimizations(self):
        """
        Suggest memory optimizations based on analysis
        
        Returns:
            List of suggested optimizations
        """
        suggestions = []
        
        # Check fragmentation
        if self.fragmentation_index > 0.7:
            suggestions.append({
                'issue': 'High memory fragmentation',
                'suggestion': 'Consider implementing object pooling for frequently allocated/deallocated objects',
                'priority': 'High'
            })
        elif self.fragmentation_index > 0.4:
            suggestions.append({
                'issue': 'Moderate memory fragmentation',
                'suggestion': 'Review allocation patterns, especially in high-traffic code paths',
                'priority': 'Medium'
            })
        
        # Get latest heap data if available
        latest = None
        if self.heap_history:
            latest = self.heap_history[-1]
            
            # Check for many garbage objects
            if latest['gc_stats']['garbage'] > 100:
                suggestions.append({
                    'issue': f"Large number of uncollectable objects ({latest['gc_stats']['garbage']})",
                    'suggestion': 'Check for circular references that GC cannot break',
                    'priority': 'High'
                })
            
            # Check memory diff for growing types
            if 'memory_diff' in latest:
                for diff in latest['memory_diff']:
                    if diff['size_delta'] > 1024 * 1024:  # >1MB
                        suggestions.append({
                            'issue': f"Rapidly growing object type: {diff['type']} (+{diff['size_delta']/(1024*1024):.1f}MB)",
                            'suggestion': 'Review lifecycle management and potential memory leaks',
                            'priority': 'High'
                        })
        
        # Add general suggestions based on available tools
        if not HAS_PYMPLER and not HAS_GUPPY:
            suggestions.append({
                'issue': 'Limited heap analysis capabilities',
                'suggestion': 'Install Pympler or Guppy for more detailed memory diagnostics',
                'priority': 'Medium'
            })
        
        return suggestions
    
    def get_metrics(self):
        """Get metrics about heap analysis"""
        return {
            'fragmentation_index': self.fragmentation_index,
            'snapshots_count': len(self.heap_history),
            'deep_analysis_available': self.deep_analysis,
            'pympler_available': HAS_PYMPLER,
            'guppy_available': HAS_GUPPY
        }
    
    def register(self, app=None):
        """Register with Flask application if available"""
        if app:
            self.app = app
        
        # Start analysis if enabled
        if self.enabled:
            self.start_analysis()
        
        return self 