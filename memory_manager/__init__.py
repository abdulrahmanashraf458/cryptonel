"""
Memory Manager
-------------
Advanced system for memory monitoring, analysis, and management.

This package provides comprehensive tools for tracking memory usage,
detecting memory leaks, analyzing heap fragmentation, and identifying
critical sections in memory usage.
"""

import logging
from .manager import MemoryManager
from .monitor import MemoryMonitor

# Add imports for new analysis systems
from .object_tracker import ObjectTracker
from .heap_analyzer import HeapAnalyzer
from .critical_section import CriticalSectionAnalyzer

# Setup logging
logger = logging.getLogger("memory_manager")

__version__ = "2.0.0"

# Create a singleton instance
memory_manager = None

def init_manager(app=None, config=None):
    """Initialize memory manager with application instance and config"""
    global memory_manager
    
    if memory_manager is None:
        memory_manager = MemoryManager(app=app, config=config)
    elif app is not None:
        # If the manager exists but app is provided, register the app
        memory_manager.register(app)
    
    return memory_manager

# Make components available at package level
__all__ = [
    'MemoryManager',
    'MemoryMonitor',
    'ObjectTracker',
    'HeapAnalyzer', 
    'CriticalSectionAnalyzer',
    'init_manager',
    'memory_manager'
] 