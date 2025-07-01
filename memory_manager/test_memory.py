"""
Memory Manager Test Module
-----------------------
Simple test and demonstration of the memory management system.

This module creates a simple Flask application, initializes the memory manager,
and demonstrates various memory usage patterns to trigger tracking and analysis.
"""

import os
import sys
import time
import logging
import threading
import random
from typing import List, Dict, Any

# Try to import Flask
try:
    from flask import Flask
except ImportError:
    print("Flask is not installed. Installing test dependencies...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "flask"])
    from flask import Flask

# Configure logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Import memory manager components
from memory_manager import init_manager
from memory_manager.config import MemoryManagerConfig

# Global variables to simulate memory leaks and high usage
leaked_objects = []
large_objects = []
reference_cycle = []

class LeakyObject:
    """Object designed to leak memory by storing references to other objects"""
    def __init__(self, name, data_size=1000):
        self.name = name
        # Create some data to consume memory
        self.data = [random.random() for _ in range(data_size)]
        # Keep references to previously created objects (leak)
        self.references = []
        
    def add_reference(self, obj):
        """Add reference to another object"""
        self.references.append(obj)
    
    def __repr__(self):
        return f"LeakyObject({self.name}, {len(self.data)} items, {len(self.references)} refs)"

def create_reference_cycle():
    """Create a cycle of objects that reference each other"""
    obj1 = LeakyObject("cycle-1")
    obj2 = LeakyObject("cycle-2")
    obj3 = LeakyObject("cycle-3")
    
    # Create a cycle: obj1 -> obj2 -> obj3 -> obj1
    obj1.add_reference(obj2)
    obj2.add_reference(obj3)
    obj3.add_reference(obj1)
    
    # Keep a reference to the cycle to make sure it's not garbage collected
    reference_cycle.append([obj1, obj2, obj3])
    return [obj1, obj2, obj3]

def leak_memory(count=100):
    """Simulates a memory leak by creating objects and keeping references"""
    for i in range(count):
        obj = LeakyObject(f"leak-{i}")
        # Connect to previous objects to create complex structures
        if leaked_objects:
            obj.add_reference(leaked_objects[-1])
        leaked_objects.append(obj)
    
    # Create some reference cycles
    create_reference_cycle()
    
    return len(leaked_objects)

def high_memory_usage(size=10):
    """Create temporary high memory usage"""
    large_obj = [random.random() for _ in range(size * 1000000)]
    large_objects.append(large_obj)
    return len(large_obj)

def create_flask_app():
    """Create a simple Flask application for testing"""
    app = Flask("MemoryManagerTest")
    
    @app.route('/')
    def index():
        return "Memory Manager Test App"
    
    @app.route('/leak/<int:count>')
    def leak(count):
        count = min(count, 1000)  # Limit to 1000 for safety
        leak_memory(count)
        return f"Leaked {count} objects. Total leaked: {len(leaked_objects)}"
    
    @app.route('/high_usage/<int:size>')
    def high_usage(size):
        size = min(size, 100)  # Limit to 100MB for safety
        items = high_memory_usage(size)
        return f"Created high memory usage with {items} items"
    
    @app.route('/status')
    def status():
        if not hasattr(app, 'memory_manager'):
            return "Memory manager not initialized"
            
        status = app.memory_manager.get_status()
        return str(status)
    
    @app.route('/analyze')
    def analyze():
        if not hasattr(app, 'memory_manager'):
            return "Memory manager not initialized"
            
        issues = app.memory_manager.get_memory_issues()
        return str(issues)
    
    return app

def run_memory_tests():
    """Run a series of memory tests"""
    print("=" * 50)
    print("Memory Manager Test Suite")
    print("=" * 50)
    
    # Create Flask app
    app = create_flask_app()
    
    # Configure memory manager with all analyzers enabled
    config = MemoryManagerConfig()
    config.object_tracker.enabled = True
    config.heap_analyzer.enabled = True
    config.critical_section.enabled = True
    
    # Configure for faster analysis in test mode
    config.object_tracker.track_interval = 2.0  # Check every 2 seconds
    config.heap_analyzer.analysis_interval = 5.0  # Check every 5 seconds
    
    # Initialize and start memory manager
    memory_manager = init_manager(app=app, config=config)
    if not memory_manager:
        print("Failed to initialize memory manager")
        return
    
    app.memory_manager = memory_manager
    memory_manager.start()
    print("Memory manager initialized and started")
    time.sleep(1)  # Give time to initialize
    
    # Run tests
    print("\nRunning memory tests...")
    
    # Test 1: Leak some memory
    print("\n[Test 1] Leaking memory by creating objects with lingering references")
    leak_memory(200)
    time.sleep(2)
    
    # Test 2: Create reference cycles
    print("\n[Test 2] Creating reference cycles")
    for _ in range(5):
        create_reference_cycle()
    time.sleep(2)
    
    # Test 3: Create high memory usage
    print("\n[Test 3] Creating high memory usage")
    high_memory_usage(20)  # 20MB
    time.sleep(2)
    
    # Test 4: Rapid memory allocation/deallocation to cause fragmentation
    print("\n[Test 4] Causing memory fragmentation with rapid allocation/deallocation")
    for _ in range(10):
        temp = []
        for _ in range(10):
            temp.append([random.random() for _ in range(100000)])
            time.sleep(0.1)
        # Keep some objects, discard others
        large_objects.append(temp[0])
        large_objects.append(temp[-1])
    time.sleep(3)
    
    # Test 5: Mark critical points
    print("\n[Test 5] Marking critical points in application")
    for i in range(3):
        name = f"Test critical point {i}"
        memory_manager.mark_critical_point(name, {"test_id": i})
        # Create some memory pressure
        high_memory_usage(10)  # 10MB
        time.sleep(0.5)
    time.sleep(2)
    
    # Get status after tests
    print("\nGetting memory manager status after tests...")
    status = memory_manager.get_status()
    print(f"Memory manager status: {status}")
    
    # Check if there are any detected issues
    print("\nChecking for memory issues...")
    issues = memory_manager.get_memory_issues()
    if issues and issues.get('has_issues', False):
        print(f"Detected {len(issues.get('issues', []))} memory issues:")
        for i, issue in enumerate(issues.get('issues', [])):
            print(f"  {i+1}. [{issue.get('severity', 'unknown')}] {issue.get('description', 'No description')}")
    else:
        print("No memory issues detected")
    
    # Run a full analysis
    print("\nRunning full memory analysis...")
    analysis = memory_manager.run_immediate_analysis()
    print("Analysis completed")
    
    # Summary
    print("\n" + "=" * 50)
    
    # Memory summary
    memory_summary = memory_manager.get_memory_summary()
    if 'basic' in memory_summary and memory_summary['basic']:
        process_mb = memory_summary['basic'].get('process_memory_mb', 0)
        print(f"Current process memory: {process_mb:.1f}MB")
    
    # Object tracking summary
    if 'object_tracking' in memory_summary:
        obj_count = memory_summary['object_tracking'].get('total_tracked_objects', 0)
        print(f"Total tracked objects: {obj_count}")
        
        top_types = memory_summary['object_tracking'].get('top_types', [])
        if top_types:
            print("\nTop object types by count:")
            for type_name, count in top_types[:5]:
                print(f"  {type_name}: {count}")
    
    # Heap analysis summary
    if 'heap' in memory_summary:
        frag_index = memory_summary['heap'].get('fragmentation_index', 0)
        print(f"\nHeap fragmentation index: {frag_index:.2f}")
    
    print("\nTest completed")
    print("=" * 50)
    
    # Clean up
    memory_manager.stop()

if __name__ == "__main__":
    run_memory_tests() 