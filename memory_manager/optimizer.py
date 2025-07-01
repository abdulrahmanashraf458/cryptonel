"""
Memory Optimizer Module
---------------------
Optimizes memory usage by managing garbage collection, monitoring memory usage,
and applying optimization strategies to prevent memory-related issues.
"""

import gc
import os
import sys
import time
import logging
import threading
import traceback
import weakref
from typing import Dict, List, Set, Tuple, Any, Optional, Callable
from collections import defaultdict, deque

# Try to import optional modules for enhanced functionality
try:
    import tracemalloc
    HAS_TRACEMALLOC = True
except ImportError:
    HAS_TRACEMALLOC = False

try:
    import objgraph
    HAS_OBJGRAPH = True
except ImportError:
    HAS_OBJGRAPH = False

try:
    import pympler.muppy as muppy
    import pympler.summary as summary
    HAS_PYMPLER = True
except ImportError:
    HAS_PYMPLER = False

# Try to import platform-specific modules
try:
    import resource
    HAS_RESOURCE = True
except ImportError:
    HAS_RESOURCE = False

logger = logging.getLogger("memory_manager.optimizer")

# A dictionary to store weak references to objects we want to track
tracked_objects = {}
tracked_object_count = 0

class MemoryOptimizer:
    """Memory optimization and garbage collection management"""
    
    def __init__(self, app=None, config=None, system_detector=None):
        """Initialize the memory optimizer"""
        self.app = app
        self.config = config
        self.system_detector = system_detector
        
        # Enable monitoring for object growth if supported
        self.objgraph_enabled = HAS_OBJGRAPH
        self.pympler_enabled = HAS_PYMPLER
        self.tracemalloc_enabled = HAS_TRACEMALLOC
        
        # Initialize tracemalloc if available and enabled
        if self.tracemalloc_enabled and config and config.gc_config.enabled:
            if not tracemalloc.is_tracing():
                tracemalloc.start(25)  # Track 25 frames
        
        # Get thresholds from config
        if config:
            self.gc_threshold_percent = config.gc_config.threshold_percent
            self.gc_interval_seconds = config.gc_config.interval_seconds
            self.gc_tune_factor = config.gc_config.tune_factor
            self.tune_thresholds = config.gc_config.tune_thresholds
        else:
            # Default values
            self.gc_threshold_percent = 70.0
            self.gc_interval_seconds = 300.0
            self.gc_tune_factor = 0.8
            self.tune_thresholds = True
        
        # Set debug flags for GC if configured
        if config and hasattr(config.gc_config, 'debug_flags'):
            gc.set_debug(config.gc_config.debug_flags)
        
        # Initialize GC tracking
        self.last_gc_time = time.time()
        self.gc_count = 0
        self.emergency_gc_count = 0
        self.objects_collected = 0
        self.collection_times = []
        
        # Memory tracking
        self.memory_growth_history = []
        self.baseline_memory = 0
        self.baseline_time = time.time()
        self.peak_memory = 0
        self.last_memory_check = 0
        self.memory_growth_data = {
            'growth_rate': 0.0,
            'growth_per_hour': 0.0,
            'consistent_growth': False,
            'last_growth_check': 0.0
        }
        
        # Track objects by type
        self.type_counts = defaultdict(int)
        self.type_growth = defaultdict(int)
        
        # Get initial memory usage if system detector is provided
        if self.system_detector:
            usage = self.system_detector.get_resource_usage()
            self.baseline_memory = usage.process_memory_bytes
            self.peak_memory = self.baseline_memory
        
        # GC optimization thread
        self.gc_thread = None
        self.running = False
        
        # Tune GC thresholds if enabled
        if self.tune_thresholds:
            self._tune_gc_thresholds()
        
        logger.info(f"Memory optimizer initialized with GC threshold: {self.gc_threshold_percent}%")
        
        # List of available optimizations
        self.available_optimizations = [
            self._run_garbage_collection,
            self._clear_caches,
            self._reduce_object_references,
        ]
        
        # Initialize metrics
        self.metrics = {
            'gc_collections': 0,
            'objects_collected': 0,
            'emergency_collections': 0,
            'optimizations_applied': 0,
            'memory_saved_bytes': 0,
            'peak_memory_bytes': 0,
            'last_collection_time': 0,
            'average_collection_time_ms': 0,
        }
    
    def register(self, app=None):
        """Register with the Flask application"""
        if app:
            self.app = app
        
        # Start the GC optimization thread if configured
        if self.gc_interval_seconds > 0:
            self.start_gc_optimization_thread()
        
        # Remember baseline memory
        if self.system_detector:
            usage = self.system_detector.get_resource_usage()
            self.baseline_memory = usage.process_memory_bytes
            self.peak_memory = self.baseline_memory
            logger.info(f"Baseline memory usage: {self.baseline_memory / (1024*1024):.1f} MB")
        
        # Return self for method chaining
        return self
    
    def start_gc_optimization_thread(self):
        """Start background thread for periodic garbage collection"""
        if self.gc_thread and self.gc_thread.is_alive():
            logger.warning("GC optimization thread already running")
            return False
        
        self.running = True
        self.gc_thread = threading.Thread(
            target=self._gc_optimization_loop,
            daemon=True
        )
        self.gc_thread.start()
        logger.info(f"Garbage collection optimization thread started with interval: {self.gc_interval_seconds}s")
        return True
    
    def stop_gc_optimization_thread(self):
        """Stop the GC optimization thread"""
        self.running = False
        if self.gc_thread:
            self.gc_thread.join(timeout=2.0)
        logger.info("Garbage collection optimization thread stopped")
    
    def _gc_optimization_loop(self):
        """Background thread for periodic garbage collection"""
        while self.running:
            try:
                # Check if it's time to run GC
                current_time = time.time()
                if current_time - self.last_gc_time >= self.gc_interval_seconds:
                    # Run garbage collection
                    self._run_garbage_collection()
                    
                    # Update last GC time
                    self.last_gc_time = current_time
            
            except Exception as e:
                logger.error(f"Error in GC optimization loop: {e}")
            
            # Sleep for a shorter interval to allow more responsive termination
            sleep_interval = min(30.0, self.gc_interval_seconds / 10)
            time.sleep(sleep_interval)
    
    def _tune_gc_thresholds(self):
        """Tune garbage collection thresholds based on system memory"""
        try:
            # Get current thresholds
            thresholds = gc.get_threshold()
            
            # Get system memory information
            if self.system_detector:
                system_info = self.system_detector.system_info
                # Calculate appropriate thresholds based on available memory
                # More memory = higher thresholds (less frequent collection)
                memory_gb = system_info.total_memory_gb
                
                # Scale factor based on available memory
                # More memory = higher thresholds (less frequent collection)
                memory_factor = min(2.0, max(0.5, memory_gb / 4.0))
                
                # Apply memory factor and tune factor from config
                threshold_0 = int(thresholds[0] * memory_factor * self.gc_tune_factor)
                threshold_1 = int(thresholds[1] * memory_factor * self.gc_tune_factor)
                threshold_2 = int(thresholds[2] * memory_factor * self.gc_tune_factor)
                
                # Ensure minimum reasonable values
                threshold_0 = max(threshold_0, 100)
                threshold_1 = max(threshold_1, 5)
                threshold_2 = max(threshold_2, 5)
                
                # Set new thresholds
                new_thresholds = (threshold_0, threshold_1, threshold_2)
                gc.set_threshold(*new_thresholds)
                
                logger.info(f"GC thresholds optimized: {thresholds} -> {new_thresholds}")
                return new_thresholds
            
            return thresholds
            
        except Exception as e:
            logger.error(f"Error tuning GC thresholds: {e}")
            return gc.get_threshold()
    
    def _run_garbage_collection(self, force=False):
        """Run garbage collection and return statistics"""
        try:
            # Check if we need to run GC based on memory usage
            should_run = force
            
            if self.system_detector and not force:
                # Get current memory usage
                usage = self.system_detector.get_resource_usage()
                memory_percent = usage.memory_percent
                process_memory = usage.process_memory_bytes
                
                # Update peak memory
                self.peak_memory = max(self.peak_memory, process_memory)
                self.metrics['peak_memory_bytes'] = self.peak_memory
                
                # Run if memory usage exceeds threshold
                should_run = memory_percent > self.gc_threshold_percent
            
            if should_run or force:
                # Record pre-GC statistics if we have objgraph
                pre_objects = None
                if self.objgraph_enabled:
                    try:
                        pre_objects = objgraph.typestats()
                    except:
                        pass
                
                # Measure time and run GC
                start_time = time.time()
                gc.collect()
                end_time = time.time()
                collection_time = (end_time - start_time) * 1000  # to milliseconds
                
                # Update metrics
                self.gc_count += 1
                self.metrics['gc_collections'] += 1
                self.metrics['last_collection_time'] = time.time()
                self.collection_times.append(collection_time)
                if len(self.collection_times) > 10:
                    self.collection_times = self.collection_times[-10:]
                self.metrics['average_collection_time_ms'] = sum(self.collection_times) / len(self.collection_times)
                
                # Record post-GC statistics if we have objgraph
                if self.objgraph_enabled and pre_objects:
                    try:
                        post_objects = objgraph.typestats()
                        objects_freed = sum((pre_objects.get(name, 0) - count) 
                                          for name, count in post_objects.items() 
                                          if name in pre_objects and pre_objects[name] > count)
                        self.objects_collected += objects_freed
                        self.metrics['objects_collected'] += objects_freed
                        
                        # Calculate memory saved (rough estimate)
                        # Assume average object size of 100 bytes
                        memory_saved = objects_freed * 100
                        self.metrics['memory_saved_bytes'] += memory_saved
                        
                        # Log significant collections
                        if objects_freed > 1000 or force:
                            logger.info(f"Garbage collection freed {objects_freed} objects in {collection_time:.1f}ms")
                    except:
                        pass
                
                # If forced, consider it an emergency collection
                if force:
                    self.emergency_gc_count += 1
                    self.metrics['emergency_collections'] += 1
                
                # Return collection stats
                return {
                    'successful': True,
                    'collection_time_ms': collection_time,
                    'objects_collected': objects_freed if 'objects_freed' in locals() else 0,
                    'memory_saved_bytes': memory_saved if 'memory_saved' in locals() else 0,
                    'emergency': force
                }
            
            return {
                'successful': False,
                'reason': 'Not needed',
                'memory_percent': memory_percent if 'memory_percent' in locals() else 0
            }
            
        except Exception as e:
            logger.error(f"Error running garbage collection: {e}")
            return {
                'successful': False,
                'error': str(e)
            }
    
    def _clear_caches(self):
        """Clear various caches to free memory"""
        try:
            caches_cleared = 0
            bytes_cleared = 0
            
            # Check if we have app
            if self.app:
                # Find and clear Flask caches
                for attr_name in dir(self.app):
                    if "_cache" in attr_name.lower() and hasattr(self.app, attr_name):
                        cache_obj = getattr(self.app, attr_name)
                        
                        # Clear different types of caches
                        if hasattr(cache_obj, "clear"):
                            # Call clear() method
                            cache_obj.clear()
                            caches_cleared += 1
                        elif isinstance(cache_obj, dict):
                            # Clear dictionary
                            size_before = sys.getsizeof(cache_obj)
                            cache_obj.clear()
                            size_after = sys.getsizeof(cache_obj)
                            bytes_cleared += (size_before - size_after)
                            caches_cleared += 1
                        elif isinstance(cache_obj, list):
                            # Clear list
                            size_before = sys.getsizeof(cache_obj)
                            cache_obj.clear()
                            size_after = sys.getsizeof(cache_obj)
                            bytes_cleared += (size_before - size_after)
                            caches_cleared += 1
            
            # Clear Python internal caches
            # Regex cache
            if hasattr(sys, "_getframe"):
                # Get the current frame
                frame = sys._getframe()
                # Look for regex module in locals/globals
                for frame_obj in (frame.f_locals, frame.f_globals):
                    if "re" in frame_obj and hasattr(frame_obj["re"], "purge"):
                        frame_obj["re"].purge()
                        caches_cleared += 1
            
            # Update metrics
            self.metrics['optimizations_applied'] += 1
            self.metrics['memory_saved_bytes'] += bytes_cleared
            
            if caches_cleared > 0:
                logger.info(f"Cleared {caches_cleared} caches, freed approximately {bytes_cleared/1024:.1f} KB")
            
            return {
                'successful': True,
                'caches_cleared': caches_cleared,
                'bytes_cleared': bytes_cleared
            }
            
        except Exception as e:
            logger.error(f"Error clearing caches: {e}")
            return {
                'successful': False,
                'error': str(e)
            }
    
    def _reduce_object_references(self):
        """Identify and reduce unnecessary object references"""
        try:
            # Run only if objgraph is available
            if not self.objgraph_enabled:
                return {
                    'successful': False,
                    'reason': 'objgraph not available'
                }
            
            # Collect reference reduction statistics
            refs_reduced = 0
            
            # This is a more complex optimization that would require deeper analysis
            # A full implementation would profile objects, identify reference cycles,
            # and suggest code changes. For now, we'll just provide a placeholder.
            
            # Update metrics
            self.metrics['optimizations_applied'] += 1
            
            return {
                'successful': True,
                'references_reduced': refs_reduced
            }
            
        except Exception as e:
            logger.error(f"Error reducing object references: {e}")
            return {
                'successful': False,
                'error': str(e)
            }
    
    def check_memory_growth(self):
        """Check for abnormal memory growth patterns"""
        try:
            # Need system detector for this
            if not self.system_detector:
                return {
                    'growth_detected': False,
                    'reason': 'System detector not available'
                }
            
            # Get current memory usage
            usage = self.system_detector.get_resource_usage()
            current_memory = usage.process_memory_bytes
            current_time = time.time()
            
            # Calculate time since baseline
            time_diff = current_time - self.baseline_time
            if time_diff <= 0:
                return {
                    'growth_detected': False,
                    'reason': 'Insufficient time data'
                }
            
            # Calculate growth rate
            memory_diff = current_memory - self.baseline_memory
            growth_percent = (memory_diff / self.baseline_memory) * 100 if self.baseline_memory > 0 else 0
            growth_per_hour = (growth_percent / time_diff) * 3600  # Scale to per hour
            
            # Update memory growth data
            self.memory_growth_data['growth_rate'] = growth_percent
            self.memory_growth_data['growth_per_hour'] = growth_per_hour
            self.memory_growth_data['last_growth_check'] = current_time
            
            # Add to history
            self.memory_growth_history.append((current_time, current_memory, growth_percent))
            if len(self.memory_growth_history) > 60:  # Keep last 60 data points
                self.memory_growth_history = self.memory_growth_history[-60:]
            
            # Check for consistent growth
            consistent_growth = False
            if len(self.memory_growth_history) >= 3:
                # Check if the last 3 points show consistent growth
                consistent_growth = True
                for i in range(len(self.memory_growth_history) - 1, max(0, len(self.memory_growth_history) - 3), -1):
                    if self.memory_growth_history[i][2] <= 0:
                        consistent_growth = False
                        break
            
            self.memory_growth_data['consistent_growth'] = consistent_growth
            
            # Get memory leak threshold from config if available
            leak_threshold = 10.0  # Default
            if self.config and hasattr(self.config, 'thresholds'):
                leak_threshold = self.config.thresholds.leak_percent
            
            # Check if growth is abnormal
            is_abnormal = growth_per_hour > leak_threshold and consistent_growth
            
            # Generate report
            report = {
                'growth_detected': is_abnormal,
                'current_memory_mb': current_memory / (1024 * 1024),
                'baseline_memory_mb': self.baseline_memory / (1024 * 1024),
                'growth_percent': growth_percent,
                'growth_per_hour': growth_per_hour,
                'consistent_growth': consistent_growth,
                'measured_over_seconds': time_diff,
                'threshold_percent': leak_threshold
            }
            
            # Log if abnormal growth detected
            if is_abnormal:
                logger.warning(f"Abnormal memory growth detected: {growth_per_hour:.1f}% per hour")
            
            return report
            
        except Exception as e:
            logger.error(f"Error checking memory growth: {e}")
            return {
                'growth_detected': False,
                'error': str(e)
            }
    
    def get_memory_profile(self):
        """Get detailed memory profile if Pympler is available"""
        try:
            if not self.pympler_enabled:
                return {
                    'available': False,
                    'reason': 'Pympler not available'
                }
            
            # Get objects summary using Pympler
            all_objects = muppy.get_objects()
            objects_summary = summary.summarize(all_objects)
            
            # Convert to a serializable format
            result = []
            for row in objects_summary:
                if len(row) >= 3:
                    result.append({
                        'type': str(row[0]),
                        'count': row[1],
                        'size_bytes': row[2]
                    })
            
            return {
                'available': True,
                'timestamp': time.time(),
                'objects': result,
                'total_types': len(result),
                'total_objects': sum(item['count'] for item in result),
                'total_size_mb': sum(item['size_bytes'] for item in result) / (1024 * 1024)
            }
            
        except Exception as e:
            logger.error(f"Error getting memory profile: {e}")
            return {
                'available': False,
                'error': str(e)
            }
    
    def get_tracemalloc_snapshot(self, top_n=10):
        """Get tracemalloc snapshot for memory allocation tracking"""
        try:
            if not self.tracemalloc_enabled or not tracemalloc.is_tracing():
                return {
                    'available': False,
                    'reason': 'tracemalloc not enabled'
                }
            
            # Take a snapshot
            snapshot = tracemalloc.take_snapshot()
            
            # Group by filename and line number
            top_stats = snapshot.statistics('lineno')
            
            # Convert to serializable format
            result = []
            for stat in top_stats[:top_n]:
                frame = stat.traceback[0]
                result.append({
                    'file': frame.filename,
                    'line': frame.lineno,
                    'size_bytes': stat.size,
                    'count': stat.count
                })
            
            return {
                'available': True,
                'timestamp': time.time(),
                'top_allocations': result,
                'total_traced_memory_mb': sum(stat.size for stat in top_stats) / (1024 * 1024)
            }
            
        except Exception as e:
            logger.error(f"Error getting tracemalloc snapshot: {e}")
            return {
                'available': False,
                'error': str(e)
            }
    
    def optimize_memory(self, level='normal'):
        """Optimize memory usage by applying various strategies"""
        start_memory = 0
        if self.system_detector:
            usage = self.system_detector.get_resource_usage()
            start_memory = usage.process_memory_bytes
        
        results = {}
        
        # Apply optimizations based on level
        if level == 'normal' or level == 'aggressive':
            # Run garbage collection
            results['gc'] = self._run_garbage_collection(force=True)
            
            # Clear caches
            results['caches'] = self._clear_caches()
        
        if level == 'aggressive':
            # Additional optimizations for aggressive mode
            results['references'] = self._reduce_object_references()
            
            # Compact memory on supported platforms
            if HAS_RESOURCE and hasattr(resource, 'malloc_trim'):
                try:
                    resource.malloc_trim(0)
                    results['malloc_trim'] = {'successful': True}
                except:
                    results['malloc_trim'] = {'successful': False}
        
        # Calculate memory saved
        total_saved_bytes = 0
        if self.system_detector:
            usage = self.system_detector.get_resource_usage()
            end_memory = usage.process_memory_bytes
            total_saved_bytes = max(0, start_memory - end_memory)
        
        # Update metrics
        self.metrics['optimizations_applied'] += 1
        self.metrics['memory_saved_bytes'] += total_saved_bytes
        
        # Log results
        logger.info(f"Memory optimization ({level}) freed {total_saved_bytes/(1024*1024):.1f} MB")
        
        return {
            'level': level,
            'saved_bytes': total_saved_bytes,
            'saved_mb': total_saved_bytes / (1024 * 1024),
            'details': results
        }
    
    def set_memory_limit(self, limit_mb):
        """Set memory limit for the process (Unix only)"""
        if not HAS_RESOURCE:
            return {
                'success': False,
                'reason': 'resource module not available on this platform'
            }
        
        try:
            # Convert MB to bytes
            limit_bytes = limit_mb * 1024 * 1024
            
            # Set the memory limit (soft and hard)
            resource.setrlimit(resource.RLIMIT_AS, (limit_bytes, limit_bytes))
            
            logger.info(f"Memory limit set to {limit_mb} MB")
            return {
                'success': True,
                'limit_mb': limit_mb
            }
        except Exception as e:
            logger.error(f"Failed to set memory limit: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_metrics(self):
        """Get memory optimizer metrics"""
        # Update memory metrics if system detector is available
        if self.system_detector:
            usage = self.system_detector.get_resource_usage()
            self.peak_memory = max(self.peak_memory, usage.process_memory_bytes)
            self.metrics['peak_memory_bytes'] = self.peak_memory
        
        # Add GC metrics
        self.metrics['gc_current_threshold'] = gc.get_threshold()
        self.metrics['gc_current_count'] = gc.get_count()
        self.metrics['gc_enabled'] = gc.isenabled()
        
        # Add general metrics
        self.metrics['current_time'] = time.time()
        
        return self.metrics 