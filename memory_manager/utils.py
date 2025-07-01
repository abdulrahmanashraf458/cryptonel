"""
Memory Manager Utilities
----------------------
Utility functions for memory management and analysis.
"""

import os
import sys
import gc
import time
import logging
import threading
import traceback
import inspect
from typing import Dict, List, Set, Tuple, Any, Optional, Callable
from collections import defaultdict

logger = logging.getLogger("memory_manager.utils")

# Object size estimation utilities
def get_size(obj, seen=None):
    """Recursively find size of objects in bytes"""
    if seen is None:
        seen = set()
    
    # Skip if we've seen this object already
    obj_id = id(obj)
    if obj_id in seen:
        return 0
    
    # Mark as seen
    seen.add(obj_id)
    
    # Get size of object
    size = sys.getsizeof(obj)
    
    # Handle containers
    if isinstance(obj, (dict, defaultdict)):
        size += sum(get_size(k, seen) + get_size(v, seen) for k, v in obj.items())
    elif isinstance(obj, (list, tuple, set, frozenset)):
        size += sum(get_size(x, seen) for x in obj)
    
    return size

def get_type_distribution(limit=20):
    """Get distribution of objects by type"""
    # Collect all objects
    objs = gc.get_objects()
    
    # Count by type
    type_counts = defaultdict(int)
    type_sizes = defaultdict(int)
    
    # Process objects
    for obj in objs:
        try:
            obj_type = type(obj).__name__
            type_counts[obj_type] += 1
            type_sizes[obj_type] += sys.getsizeof(obj)
        except:
            # Skip problematic objects
            pass
    
    # Sort by count (most frequent first)
    sorted_types = sorted(type_counts.items(), key=lambda x: x[1], reverse=True)
    
    # Prepare results (top N types)
    result = []
    for type_name, count in sorted_types[:limit]:
        size = type_sizes.get(type_name, 0)
        result.append({
            'type': type_name,
            'count': count,
            'size_bytes': size,
            'avg_size': size / count if count > 0 else 0
        })
    
    return result

def find_leaking_objects(top_n=10):
    """Find potentially leaking objects by looking at objects that are growing"""
    # This function requires multiple calls to build up history
    if not hasattr(find_leaking_objects, 'type_history'):
        find_leaking_objects.type_history = []
    
    # Get current type distribution
    current_types = {t['type']: t['count'] for t in get_type_distribution(limit=100)}
    timestamp = time.time()
    
    # Add to history
    find_leaking_objects.type_history.append((timestamp, current_types))
    
    # Limit history to last 10 snapshots
    if len(find_leaking_objects.type_history) > 10:
        find_leaking_objects.type_history = find_leaking_objects.type_history[-10:]
    
    # Need at least 2 snapshots to detect growth
    if len(find_leaking_objects.type_history) < 2:
        return []
    
    # Get first and last snapshots
    first_time, first_types = find_leaking_objects.type_history[0]
    last_time, last_types = find_leaking_objects.type_history[-1]
    time_diff = last_time - first_time
    
    # Calculate growth rate for each type
    growth_rates = []
    for type_name, count in last_types.items():
        if type_name in first_types:
            first_count = first_types[type_name]
            if first_count > 0 and count > first_count:
                growth = count - first_count
                growth_pct = (growth / first_count) * 100
                growth_per_hour = growth_pct * (3600 / time_diff) if time_diff > 0 else 0
                
                # Only include types with significant growth
                if growth > 10 and growth_pct > 10:
                    growth_rates.append({
                        'type': type_name,
                        'first_count': first_count,
                        'last_count': count,
                        'growth': growth,
                        'growth_percent': growth_pct,
                        'growth_per_hour': growth_per_hour,
                        'time_period_seconds': time_diff
                    })
    
    # Sort by growth percentage (highest first)
    growth_rates.sort(key=lambda x: x['growth_percent'], reverse=True)
    
    # Return top N results
    return growth_rates[:top_n]

def analyze_memory_usage():
    """Analyze current memory usage and return detailed information"""
    # Get basic memory usage
    process_memory = 0
    try:
        import psutil
        process = psutil.Process(os.getpid())
        process_memory = process.memory_info().rss
    except:
        # Fall back to less accurate method
        import resource
        process_memory = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024
    
    # Get GC statistics
    gc_stats = {
        'gc_enabled': gc.isenabled(),
        'gc_counts': gc.get_count(),
        'gc_threshold': gc.get_threshold(),
        'gc_objects': len(gc.get_objects())
    }
    
    # Get top types by count
    top_types = get_type_distribution(limit=20)
    
    # Get potentially leaking objects
    leaking_objects = find_leaking_objects(top_n=10)
    
    # Analyze reference cycles
    unreachable = gc.collect()
    
    # Gather all results
    return {
        'timestamp': time.time(),
        'process_memory_bytes': process_memory,
        'process_memory_mb': process_memory / (1024 * 1024),
        'gc_stats': gc_stats,
        'top_types': top_types,
        'leaking_objects': leaking_objects,
        'unreachable_objects': unreachable
    }

def get_referrers(obj, max_depth=2, current_depth=0):
    """Get objects that refer to the given object"""
    if current_depth >= max_depth:
        return []
    
    import gc
    refs = gc.get_referrers(obj)
    result = []
    
    for ref in refs:
        ref_type = type(ref).__name__
        ref_info = {
            'type': ref_type,
            'id': id(ref),
            'size': sys.getsizeof(ref),
            'summary': str(ref)[:100] if len(str(ref)) > 100 else str(ref)
        }
        
        # Recursively get referrers of this referrer
        if current_depth < max_depth - 1:
            ref_info['referrers'] = get_referrers(ref, max_depth, current_depth + 1)
        
        result.append(ref_info)
    
    return result

def clear_memory_caches():
    """Clear various memory caches to free up memory"""
    freed_count = 0
    
    # Clear regex cache
    import re
    re.purge()
    freed_count += 1
    
    # Clear functools LRU caches
    try:
        import functools
        cached_functions = []
        
        # Find all objects with a cache_clear method (LRU cached functions)
        for obj in gc.get_objects():
            if hasattr(obj, 'cache_clear') and callable(obj.cache_clear):
                cached_functions.append(obj)
        
        # Clear each cache
        for func in cached_functions:
            try:
                func.cache_clear()
                freed_count += 1
            except:
                pass
    except:
        pass
    
    # Run garbage collection
    gc.collect()
    
    return {
        'caches_cleared': freed_count,
        'gc_run': True
    }

def install_memory_profiler(app=None):
    """Install memory profiling hooks for Flask or other web apps"""
    if not app:
        return False
    
    # Check if Flask
    if hasattr(app, 'before_request') and hasattr(app, 'after_request'):
        try:
            @app.before_request
            def profile_memory_start():
                import flask
                import resource
                flask.g.memory_start = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
                flask.g.memory_start_time = time.time()
            
            @app.after_request
            def profile_memory_end(response):
                import flask
                import resource
                if hasattr(flask.g, 'memory_start'):
                    memory_end = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
                    memory_diff = memory_end - flask.g.memory_start
                    time_diff = time.time() - flask.g.memory_start_time
                    
                    # Add memory usage headers to response
                    response.headers['X-Memory-Usage-KB'] = str(memory_end)
                    response.headers['X-Memory-Change-KB'] = str(memory_diff)
                    response.headers['X-Response-Time-MS'] = str(int(time_diff * 1000))
                
                return response
            
            logger.info("Memory profiling hooks installed for Flask app")
            return True
        except Exception as e:
            logger.error(f"Error installing memory profiling hooks: {e}")
            return False
    
    return False

def get_stack_trace():
    """Get the current stack trace"""
    stack = traceback.extract_stack()
    formatted_stack = []
    
    for frame in stack[:-1]:  # Skip the last frame (this function)
        filename, line, func, code = frame
        formatted_stack.append({
            'file': filename,
            'line': line,
            'function': func,
            'code': code
        })
    
    return formatted_stack

def format_bytes(bytes_value, precision=2):
    """Format bytes value to appropriate unit (KB, MB, GB, etc.)"""
    if bytes_value < 1024:
        return f"{bytes_value} bytes"
    elif bytes_value < 1024 ** 2:
        return f"{bytes_value / 1024:.{precision}f} KB"
    elif bytes_value < 1024 ** 3:
        return f"{bytes_value / (1024 ** 2):.{precision}f} MB"
    else:
        return f"{bytes_value / (1024 ** 3):.{precision}f} GB" 