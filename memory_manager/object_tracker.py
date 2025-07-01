"""
Object Tracking System
---------------------
Advanced module for tracking object allocations, detecting memory leaks,
and identifying retain cycles in the application.

This module provides tools to analyze objects lifecycle, track references,
and detect memory-related issues like retain cycles and orphaned objects.
"""

import sys
import gc
import time
import logging
import threading
import weakref
import inspect
from typing import Dict, List, Set, Any, Optional, Tuple, Union, Callable
from collections import defaultdict, deque
import traceback

logger = logging.getLogger("memory_manager.object_tracker")

class ObjectTracker:
    """
    Tracks object allocations and references to detect memory leaks,
    retain cycles, and other memory management issues.
    """
    
    def __init__(self, app=None, config=None, system_detector=None):
        """Initialize the object tracker"""
        self.app = app
        self.config = config
        self.system_detector = system_detector
        
        # Configuration defaults
        self.enabled = True
        self.track_interval = 60.0  # seconds
        self.max_objects_tracked = 5000
        self.track_types = []  # Empty list means track all types
        self.ignore_types = ['function', 'module', 'type', 'NoneType', 'frame']
        
        # Override with config if available
        if config and hasattr(config, 'object_tracker'):
            self.enabled = getattr(config.object_tracker, 'enabled', self.enabled)
            self.track_interval = getattr(config.object_tracker, 'track_interval', self.track_interval)
            self.max_objects_tracked = getattr(config.object_tracker, 'max_objects_tracked', self.max_objects_tracked)
            self.track_types = getattr(config.object_tracker, 'track_types', self.track_types)
            self.ignore_types = getattr(config.object_tracker, 'ignore_types', self.ignore_types)
        
        # Object tracking data structures
        self.object_counts = defaultdict(int)
        self.previous_counts = defaultdict(int)
        self.tracked_objects = {}  # id -> (type, creation_time, creation_stack)
        self.reference_map = {}    # id -> set(referenced_ids)
        self.tracking_lock = threading.RLock()
        
        # Tracking thread
        self.tracking_thread = None
        self.running = False
        
        # Retain cycle detection
        self.cycle_candidates = set()
        self.detected_cycles = []
        
        # Dangling pointer detection
        self.weak_references = {}  # id -> weakref
        self.dangling_pointers = []
        
        logger.info("Object tracker initialized")
    
    @property
    def is_tracking(self):
        """Check if tracking is currently active"""
        return self.running and self.tracking_thread is not None and self.tracking_thread.is_alive()
    
    def start_tracking(self):
        """Start object tracking thread"""
        if self.is_tracking:
            logger.debug("Object tracking already active")
            return True
        
        # Clean up dead thread if any
        if self.tracking_thread and not self.tracking_thread.is_alive():
            self.tracking_thread = None
        
        self.running = True
        self.tracking_thread = threading.Thread(
            target=self._tracking_loop,
            daemon=True,
            name="object-tracker"
        )
        self.tracking_thread.start()
        logger.info(f"Object tracking started with interval: {self.track_interval}s")
        return True
    
    def stop_tracking(self):
        """Stop object tracking thread"""
        self.running = False
        if self.tracking_thread:
            self.tracking_thread.join(timeout=2.0)
        logger.info("Object tracking stopped")
    
    def _tracking_loop(self):
        """Background thread for object tracking"""
        while self.running:
            try:
                self._scan_objects()
                self._detect_memory_issues()
            except Exception as e:
                logger.error(f"Error in object tracking loop: {e}")
                logger.error(traceback.format_exc())
            
            # Sleep for the tracking interval
            time.sleep(self.track_interval)
    
    def _scan_objects(self):
        """Scan all objects in memory and update tracking data"""
        with self.tracking_lock:
            # Store previous counts for comparison
            self.previous_counts = self.object_counts.copy()
            self.object_counts.clear()
            
            # Get all objects from garbage collector
            all_objects = gc.get_objects()
            
            # Count objects by type
            for obj in all_objects:
                if len(self.tracked_objects) >= self.max_objects_tracked:
                    break
                
                try:
                    obj_type = type(obj).__name__
                    
                    # Skip ignored types
                    if obj_type in self.ignore_types:
                        continue
                    
                    # Only track specified types if list is not empty
                    if self.track_types and obj_type not in self.track_types:
                        continue
                    
                    # Count by type
                    self.object_counts[obj_type] += 1
                    
                    # Check if this is a new object to track
                    obj_id = id(obj)
                    if obj_id not in self.tracked_objects:
                        # Get creation stack if possible
                        creation_stack = None
                        try:
                            if hasattr(obj, "__traceback__"):
                                creation_stack = traceback.extract_stack()
                        except:
                            pass
                        
                        # Store object info
                        self.tracked_objects[obj_id] = (
                            obj_type,
                            time.time(),
                            creation_stack
                        )
                        
                        # Try to create a weak reference for dangling pointer detection
                        try:
                            self.weak_references[obj_id] = weakref.ref(obj)
                        except TypeError:
                            # Some objects don't support weak references
                            pass
                    
                    # Update reference map
                    self._update_references(obj, obj_id)
                    
                except Exception as e:
                    # Some objects may not be properly inspectable
                    continue
            
            # Log notable changes
            self._log_object_count_changes()
    
    def _update_references(self, obj, obj_id):
        """Update the reference map for an object"""
        try:
            # Get all references this object holds
            refs = set()
            
            # Check different types of references based on object type
            if isinstance(obj, (list, tuple, set)):
                for item in obj:
                    if isinstance(item, object) and id(item) != obj_id:
                        refs.add(id(item))
            elif isinstance(obj, dict):
                for k, v in obj.items():
                    if isinstance(k, object) and id(k) != obj_id:
                        refs.add(id(k))
                    if isinstance(v, object) and id(v) != obj_id:
                        refs.add(id(v))
            elif hasattr(obj, "__dict__"):
                for attr_name, attr_value in obj.__dict__.items():
                    if isinstance(attr_value, object) and id(attr_value) != obj_id:
                        refs.add(id(attr_value))
            
            # Update reference map
            self.reference_map[obj_id] = refs
            
            # If this object has references to other objects and is referenced by those objects,
            # it's a candidate for a retain cycle
            for ref_id in refs:
                if ref_id in self.reference_map and obj_id in self.reference_map[ref_id]:
                    self.cycle_candidates.add((obj_id, ref_id))
        
        except Exception as e:
            # Some objects may raise exceptions during inspection
            pass
    
    def _log_object_count_changes(self):
        """Log significant changes in object counts"""
        for obj_type, count in self.object_counts.items():
            prev_count = self.previous_counts.get(obj_type, 0)
            delta = count - prev_count
            
            # Log if significant change (more than 10% and at least 10 objects)
            if abs(delta) > max(10, prev_count * 0.1):
                if delta > 0:
                    logger.info(f"Increased {obj_type} objects: {prev_count} → {count} (+{delta})")
                else:
                    logger.info(f"Decreased {obj_type} objects: {prev_count} → {count} ({delta})")
    
    def _detect_memory_issues(self):
        """Detect memory issues like retain cycles and dangling pointers"""
        try:
            # Process detected cycle candidates
            self._detect_retain_cycles()
            
            # Check for dangling pointers
            self._detect_dangling_pointers()
            
        except Exception as e:
            logger.error(f"Error detecting memory issues: {e}")
            logger.error(traceback.format_exc())
    
    def _detect_retain_cycles(self):
        """Detect retain cycles in the reference map"""
        with self.tracking_lock:
            # Process candidates to confirm cycles
            cycles_found = []
            
            for obj_id1, obj_id2 in list(self.cycle_candidates):
                # Skip if either object no longer tracked
                if obj_id1 not in self.tracked_objects or obj_id2 not in self.tracked_objects:
                    self.cycle_candidates.remove((obj_id1, obj_id2))
                    continue
                
                # Check if this forms a full cycle with more objects
                cycle = self._find_cycle(obj_id1)
                if cycle and len(cycle) > 1:
                    # Get cycle details
                    cycle_info = {
                        'detected_time': time.time(),
                        'cycle_objects': [(id_val, self.tracked_objects.get(id_val, ('unknown', 0, None))[0]) 
                                          for id_val in cycle],
                        'cycle_length': len(cycle)
                    }
                    
                    # Add to detected cycles
                    cycles_found.append(cycle_info)
                    
                    # Remove this candidate
                    self.cycle_candidates.remove((obj_id1, obj_id2))
            
            # Store newly found cycles
            if cycles_found:
                self.detected_cycles.extend(cycles_found)
                logger.warning(f"Detected {len(cycles_found)} potential retain cycles")
                
                # Keep only recent cycles (maximum 50)
                if len(self.detected_cycles) > 50:
                    self.detected_cycles = self.detected_cycles[-50:]
    
    def _find_cycle(self, start_id, visited=None, path=None):
        """Find a reference cycle starting from the given object ID"""
        if visited is None:
            visited = set()
        if path is None:
            path = []
        
        # Skip if already visited
        if start_id in visited:
            # If we've seen this ID in the current path, we found a cycle
            if start_id in path:
                cycle_start = path.index(start_id)
                return path[cycle_start:]
            return None
        
        # Add to visited set and path
        visited.add(start_id)
        path.append(start_id)
        
        # Check all references
        refs = self.reference_map.get(start_id, set())
        for ref_id in refs:
            if ref_id in self.reference_map:
                cycle = self._find_cycle(ref_id, visited, path[:])
                if cycle:
                    return cycle
        
        return None
    
    def _detect_dangling_pointers(self):
        """Detect dangling pointers using weak references"""
        with self.tracking_lock:
            # Check each weak reference
            dangling_found = []
            
            for obj_id, weak_ref in list(self.weak_references.items()):
                # Check if the object is gone (weak reference returns None)
                if weak_ref() is None:
                    # Object is gone, but check if it's still referenced
                    is_referenced = False
                    for refs in self.reference_map.values():
                        if obj_id in refs:
                            is_referenced = True
                            break
                    
                    if is_referenced:
                        # This is a dangling pointer!
                        obj_type = self.tracked_objects.get(obj_id, ('unknown', 0, None))[0]
                        dangling_info = {
                            'detected_time': time.time(),
                            'object_id': obj_id,
                            'object_type': obj_type,
                            'referenced_by': [ref_id for ref_id, refs in self.reference_map.items() 
                                              if obj_id in refs]
                        }
                        dangling_found.append(dangling_info)
                    
                    # Clean up tracking for this object
                    del self.weak_references[obj_id]
                    if obj_id in self.tracked_objects:
                        del self.tracked_objects[obj_id]
                    if obj_id in self.reference_map:
                        del self.reference_map[obj_id]
            
            # Store newly found dangling pointers
            if dangling_found:
                self.dangling_pointers.extend(dangling_found)
                logger.warning(f"Detected {len(dangling_found)} potential dangling pointers")
                
                # Keep only recent reports (maximum 50)
                if len(self.dangling_pointers) > 50:
                    self.dangling_pointers = self.dangling_pointers[-50:]
    
    def get_object_summary(self):
        """Get summary of tracked objects"""
        with self.tracking_lock:
            return {
                'total_tracked_objects': len(self.tracked_objects),
                'object_counts': dict(self.object_counts),
                'top_types': sorted(self.object_counts.items(), key=lambda x: x[1], reverse=True)[:10],
                'potential_cycles': len(self.detected_cycles),
                'potential_dangling_pointers': len(self.dangling_pointers)
            }
    
    def get_retain_cycles(self):
        """Get detected retain cycles"""
        with self.tracking_lock:
            return self.detected_cycles
    
    def get_dangling_pointers(self):
        """Get detected dangling pointers"""
        with self.tracking_lock:
            return self.dangling_pointers
    
    def track_specific_type(self, class_name):
        """Add a specific class type to track"""
        if class_name not in self.track_types:
            self.track_types.append(class_name)
    
    def ignore_specific_type(self, class_name):
        """Add a specific class type to ignore"""
        if class_name not in self.ignore_types:
            self.ignore_types.append(class_name)
    
    def get_metrics(self):
        """Get metrics about object tracking"""
        return {
            'tracked_objects': len(self.tracked_objects),
            'object_types': len(self.object_counts),
            'retain_cycles': len(self.detected_cycles),
            'dangling_pointers': len(self.dangling_pointers)
        }
    
    def register(self, app=None):
        """Register with Flask application if available"""
        if app:
            self.app = app
        
        # Start tracking if enabled
        if self.enabled:
            self.start_tracking()
        
        return self 