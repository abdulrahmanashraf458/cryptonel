"""
Async Utilities - Asynchronous endpoint support for Flask

This module provides utilities for creating async endpoints and background tasks
to improve performance under high load by avoiding blocking operations.
"""

import asyncio
import functools
import logging
import threading
import time
import queue
from typing import Any, Dict, List, Optional, Callable, Coroutine, TypeVar, Generic, Union, Tuple

# Configure logging
logger = logging.getLogger('cryptonel.async')

# Check if we're using a Flask version that supports async
try:
    from flask import current_app
    import flask
    
    FLASK_VERSION = tuple(int(x) for x in flask.__version__.split('.')[:2])
    HAS_ASYNC_FLASK = FLASK_VERSION >= (2, 0)
    
    if not HAS_ASYNC_FLASK:
        logger.warning("Flask version does not fully support async (< 2.0). Some features will be limited.")
    
except ImportError:
    HAS_ASYNC_FLASK = False
    logger.warning("Flask not installed. Async utilities will be limited.")

# Type variables for generics
T = TypeVar('T')
R = TypeVar('R')

# Task queue for background processing
_task_queue = queue.Queue()
_task_workers = []
_max_workers = 5
_is_initialized = False


def init_async_workers(max_workers: int = 5):
    """
    Initialize background task workers
    
    Args:
        max_workers: Maximum number of worker threads
    """
    global _max_workers, _is_initialized, _task_workers
    
    if _is_initialized:
        return
    
    _max_workers = max_workers
    
    # Start worker threads
    for i in range(_max_workers):
        worker = threading.Thread(target=_background_worker, daemon=True)
        worker.start()
        _task_workers.append(worker)
    
    logger.info(f"Started {_max_workers} async worker threads")
    _is_initialized = True


def _background_worker():
    """Worker thread function to process background tasks"""
    while True:
        try:
            # Get a task from the queue
            task_func, args, kwargs, result_callback = _task_queue.get()
            
            # Process the task
            try:
                start_time = time.time()
                result = task_func(*args, **kwargs)
                duration = time.time() - start_time
                
                # Log slow tasks (>1s)
                if duration > 1.0:
                    logger.warning(f"Slow background task: {task_func.__name__} ({duration:.2f}s)")
                
                # If task returns a coroutine, run it
                if asyncio.iscoroutine(result):
                    loop = asyncio.new_event_loop()
                    try:
                        asyncio.set_event_loop(loop)
                        result = loop.run_until_complete(result)
                    finally:
                        loop.close()
                
                # Call the callback with the result if provided
                if result_callback:
                    result_callback(result)
                
            except Exception as e:
                logger.error(f"Error in background task {task_func.__name__}: {e}")
            
            # Mark task as done
            _task_queue.task_done()
            
        except Exception as e:
            logger.error(f"Error in background worker: {e}")


def run_in_background(func=None, *, callback: Optional[Callable[[R], None]] = None):
    """
    Decorator to run a function in the background
    
    Args:
        func: Function to decorate
        callback: Optional callback to call with the result
        
    Returns:
        Wrapped function that runs in the background
    """
    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            # Initialize if not already done
            if not _is_initialized:
                init_async_workers()
            
            # Queue the task
            _task_queue.put((f, args, kwargs, callback))
            
            # Return immediately
            return None
        
        return wrapper
    
    if func is None:
        return decorator
    return decorator(func)


def async_endpoint(f):
    """
    Decorator to create an async Flask endpoint
    
    This will properly wrap an async function for use with Flask,
    handling differences between Flask versions.
    
    Args:
        f: Async function to wrap
        
    Returns:
        Wrapped function compatible with Flask
    """
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        if HAS_ASYNC_FLASK:
            # Flask 2.0+ has native async support
            return f(*args, **kwargs)
        else:
            # For older Flask versions, run in an event loop
            async def run():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    return await f(*args, **kwargs)
                finally:
                    loop.close()
            
            return asyncio.run(run())
    
    return wrapper


def run_async(coroutine: Coroutine) -> Any:
    """
    Run a coroutine function and return its result
    
    Args:
        coroutine: Coroutine to run
        
    Returns:
        Result of the coroutine
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coroutine)
    finally:
        loop.close()


async def gather_with_concurrency(n: int, *tasks):
    """
    Run coroutines with a concurrency limit
    
    Args:
        n: Maximum number of concurrent tasks
        *tasks: Tasks to run
        
    Returns:
        List of task results
    """
    semaphore = asyncio.Semaphore(n)
    
    async def sem_task(task):
        async with semaphore:
            return await task
    
    return await asyncio.gather(*(sem_task(task) for task in tasks))


class AsyncBatch:
    """Helper for batching async operations with concurrency control"""
    
    def __init__(self, max_concurrency: int = 10):
        """
        Initialize async batch processor
        
        Args:
            max_concurrency: Maximum concurrent operations
        """
        self.max_concurrency = max_concurrency
        self.tasks = []
    
    def add_task(self, coro: Coroutine):
        """
        Add a task to the batch
        
        Args:
            coro: Coroutine function to run
        """
        self.tasks.append(coro)
    
    async def execute(self) -> List[Any]:
        """
        Execute all tasks with concurrency control
        
        Returns:
            List of task results
        """
        if not self.tasks:
            return []
        
        return await gather_with_concurrency(self.max_concurrency, *self.tasks)


def timed_async(f):
    """
    Decorator to time async functions and log slow ones
    
    Args:
        f: Async function to decorate
        
    Returns:
        Wrapped async function with timing
    """
    @functools.wraps(f)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        result = await f(*args, **kwargs)
        duration = time.time() - start_time
        
        # Log slow async operations (>500ms)
        if duration > 0.5:
            logger.warning(f"Slow async operation: {f.__name__} ({duration:.2f}s)")
        
        return result
    
    return wrapper


class AsyncCache:
    """Simple cache for async function results"""
    
    def __init__(self, ttl: int = 300):
        """
        Initialize async cache
        
        Args:
            ttl: Default cache time-to-live in seconds
        """
        self.cache = {}
        self.timestamps = {}
        self.ttl = ttl
        self.lock = threading.RLock()
    
    async def get_or_set(self, key: str, coro_func: Callable[[], Coroutine[Any, Any, T]], ttl: Optional[int] = None) -> T:
        """
        Get from cache or set if missing
        
        Args:
            key: Cache key
            coro_func: Async function to call if cache miss
            ttl: Optional custom TTL
            
        Returns:
            Cached or fresh result
        """
        # Check if cache hit
        now = time.time()
        with self.lock:
            if key in self.cache and now - self.timestamps[key] < (ttl or self.ttl):
                return self.cache[key]
        
        # Cache miss, execute coroutine
        result = await coro_func()
        
        # Store in cache
        with self.lock:
            self.cache[key] = result
            self.timestamps[key] = now
            
            # Cleanup old entries
            for k in list(self.timestamps.keys()):
                if now - self.timestamps[k] >= (ttl or self.ttl):
                    del self.cache[k]
                    del self.timestamps[k]
        
        return result


# Initialize async workers on module import
init_async_workers() 