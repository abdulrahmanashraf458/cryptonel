"""
Memoization Utilities

This module provides memoization decorators to cache function results
and improve performance, especially for expensive operations like
JSON serialization and computation-heavy functions.

Features:
- Function result caching with TTL
- Argument-based cache key generation
- Memory and Redis-based caching options
- Specialized JSON memoization for serialization
"""

import time
import logging
import functools
import hashlib
import inspect
import json
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from datetime import datetime, timedelta

try:
    # Try to import Redis cache utilities
    from backend.utils.cache_utils import (
        get_redis_client,
        cache_set,
        cache_get,
        cache_delete
    )
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

# Configure logger
logger = logging.getLogger(__name__)

# Memory cache as fallback when Redis is not available
_memory_cache = {}
_memory_cache_expiry = {}


def _generate_cache_key(func: Callable, args: Tuple, kwargs: Dict, prefix: str = "") -> str:
    """
    Generate a unique cache key based on function name and arguments
    
    Args:
        func: The function being memoized
        args: Positional arguments to the function
        kwargs: Keyword arguments to the function
        prefix: Optional prefix for the key
        
    Returns:
        A unique cache key string
    """
    # Start with function name
    key_parts = [prefix or func.__module__, func.__name__]
    
    # Add stringified positional args
    for arg in args:
        try:
            # Handle non-serializable objects by using their repr
            arg_str = json.dumps(arg) if isinstance(arg, (dict, list, str, int, float, bool, type(None))) else repr(arg)
            key_parts.append(arg_str)
        except (TypeError, ValueError):
            key_parts.append(repr(arg))
    
    # Add stringified keyword args (sorted for determinism)
    for k in sorted(kwargs.keys()):
        v = kwargs[k]
        try:
            # Handle non-serializable objects by using their repr
            v_str = json.dumps(v) if isinstance(v, (dict, list, str, int, float, bool, type(None))) else repr(v)
            key_parts.append(f"{k}:{v_str}")
        except (TypeError, ValueError):
            key_parts.append(f"{k}:{repr(v)}")
    
    # Join all parts and create a hash
    key_string = "|".join(key_parts)
    return f"memo:{hashlib.md5(key_string.encode('utf-8')).hexdigest()}"


def _memory_cache_set(key: str, value: Any, ttl: Optional[int] = None) -> None:
    """
    Set value in memory cache with optional TTL
    
    Args:
        key: Cache key
        value: Value to cache
        ttl: Time to live in seconds
    """
    global _memory_cache, _memory_cache_expiry
    _memory_cache[key] = value
    
    if ttl:
        expiry = time.time() + ttl
        _memory_cache_expiry[key] = expiry
    else:
        # Remove any existing expiry
        _memory_cache_expiry.pop(key, None)


def _memory_cache_get(key: str) -> Tuple[bool, Any]:
    """
    Get value from memory cache
    
    Args:
        key: Cache key
        
    Returns:
        Tuple of (hit, value)
    """
    global _memory_cache, _memory_cache_expiry
    
    if key not in _memory_cache:
        return False, None
    
    # Check expiry if exists
    if key in _memory_cache_expiry:
        expiry = _memory_cache_expiry[key]
        if time.time() > expiry:
            # Expired, clean up
            del _memory_cache[key]
            del _memory_cache_expiry[key]
            return False, None
    
    return True, _memory_cache[key]


def _memory_cache_clear_expired() -> None:
    """Clean up expired items in memory cache"""
    global _memory_cache, _memory_cache_expiry
    now = time.time()
    
    # Find expired keys
    expired_keys = [k for k, v in _memory_cache_expiry.items() if now > v]
    
    # Remove expired items
    for key in expired_keys:
        _memory_cache.pop(key, None)
        _memory_cache_expiry.pop(key, None)


def memoize(ttl: Optional[int] = None, prefix: Optional[str] = None, use_redis: bool = True) -> Callable:
    """
    General purpose memoization decorator
    
    Args:
        ttl: Time to live in seconds (None for no expiry)
        prefix: Optional prefix for cache key
        use_redis: Whether to use Redis (if available) or memory cache
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = _generate_cache_key(func, args, kwargs, prefix)
            
            # Try to get from cache
            if REDIS_AVAILABLE and use_redis:
                # Try Redis cache
                cached_result = cache_get(cache_key)
                cache_hit = cached_result is not None
            else:
                # Fall back to memory cache
                cache_hit, cached_result = _memory_cache_get(cache_key)
                
                # Periodically clean up expired items
                if len(_memory_cache) > 100:  # Only clean up when cache grows
                    _memory_cache_clear_expired()
            
            if cache_hit:
                logger.debug(f"Cache hit for {func.__name__} with key {cache_key}")
                return cached_result
            
            # Cache miss, call the function
            result = func(*args, **kwargs)
            
            # Store in cache
            if REDIS_AVAILABLE and use_redis:
                cache_set(cache_key, result, ttl)
            else:
                _memory_cache_set(cache_key, result, ttl)
                
            logger.debug(f"Cache miss for {func.__name__}, stored with key {cache_key}")
            return result
            
        return wrapper
    
    return decorator


def clear_memoized(func: Callable, *args, **kwargs) -> None:
    """
    Clear memoized result for specific function and arguments
    
    Args:
        func: The memoized function
        args: Positional arguments to the function
        kwargs: Keyword arguments to the function
    """
    # Generate cache key
    cache_key = _generate_cache_key(func, args, kwargs)
    
    # Clear from Redis if available
    if REDIS_AVAILABLE:
        cache_delete(cache_key)
    
    # Also clear from memory cache
    if cache_key in _memory_cache:
        del _memory_cache[cache_key]
        _memory_cache_expiry.pop(cache_key, None)
        
    logger.debug(f"Cleared memoized result for {func.__name__} with key {cache_key}")


def clear_all_memoized(func: Optional[Callable] = None) -> None:
    """
    Clear all memoized results for a function (or all functions if None)
    
    Args:
        func: The memoized function, or None to clear all
    """
    global _memory_cache, _memory_cache_expiry
    
    if func is None:
        # Clear all cached results
        _memory_cache.clear()
        _memory_cache_expiry.clear()
        
        # Clear Redis cache if available
        if REDIS_AVAILABLE:
            redis = get_redis_client()
            if redis:
                redis.delete("memo:*")  # Delete all memo: keys
                
        logger.debug("Cleared all memoized results")
    else:
        # Clear only for specific function (approximate, as args are unknown)
        prefix = f"memo:{func.__module__}:{func.__name__}"
        
        # Filter memory cache
        keys_to_clear = [k for k in _memory_cache.keys() if k.startswith(prefix)]
        for key in keys_to_clear:
            del _memory_cache[key]
            _memory_cache_expiry.pop(key, None)
        
        # Clear Redis cache if available
        if REDIS_AVAILABLE:
            redis = get_redis_client()
            if redis:
                for key in redis.scan_iter(f"{prefix}*"):
                    redis.delete(key)
                    
        logger.debug(f"Cleared all memoized results for {func.__name__}")


def memoize_json(ttl: Optional[int] = 3600, compression: bool = False) -> Callable:
    """
    Specialized memoization decorator for JSON serialization operations
    
    This provides efficient caching for functions that produce JSON, with
    options for compression to reduce memory usage for large objects.
    
    Args:
        ttl: Time to live in seconds (None for no expiry)
        compression: Whether to compress cached data
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key with json specific prefix
            cache_key = _generate_cache_key(func, args, kwargs, "json")
            
            # Try to get from cache
            if REDIS_AVAILABLE:
                # Try Redis cache
                cached_result = cache_get(cache_key)
                cache_hit = cached_result is not None
            else:
                # Fall back to memory cache
                cache_hit, cached_result = _memory_cache_get(cache_key)
            
            if cache_hit:
                logger.debug(f"JSON cache hit for {func.__name__}")
                
                # If result is compressed, decompress it
                if compression and isinstance(cached_result, bytes):
                    try:
                        import zlib
                        cached_result = json.loads(zlib.decompress(cached_result).decode('utf-8'))
                    except ImportError:
                        # zlib not available, return as is
                        logger.warning("zlib not available for decompression")
                    except Exception as e:
                        logger.error(f"Error decompressing JSON result: {e}")
                        # Cache failed, call function
                        return func(*args, **kwargs)
                
                return cached_result
            
            # Cache miss, call the function
            result = func(*args, **kwargs)
            
            # Store in cache, with optional compression
            if compression:
                try:
                    import zlib
                    # Convert result to JSON and compress
                    json_result = json.dumps(result)
                    compressed = zlib.compress(json_result.encode('utf-8'))
                    
                    if REDIS_AVAILABLE:
                        cache_set(cache_key, compressed, ttl)
                    else:
                        _memory_cache_set(cache_key, compressed, ttl)
                        
                except ImportError:
                    # zlib not available, store uncompressed
                    logger.warning("zlib not available for compression, storing uncompressed")
                    if REDIS_AVAILABLE:
                        cache_set(cache_key, result, ttl)
                    else:
                        _memory_cache_set(cache_key, result, ttl)
                        
                except Exception as e:
                    logger.error(f"Error compressing JSON result: {e}")
                    # Store uncompressed as fallback
                    if REDIS_AVAILABLE:
                        cache_set(cache_key, result, ttl)
                    else:
                        _memory_cache_set(cache_key, result, ttl)
            else:
                # Store uncompressed
                if REDIS_AVAILABLE:
                    cache_set(cache_key, result, ttl)
                else:
                    _memory_cache_set(cache_key, result, ttl)
                    
            logger.debug(f"JSON cache miss for {func.__name__}, result stored")
            return result
            
        return wrapper
    
    return decorator


def timed_cache(seconds: int = 600) -> Callable:
    """
    Simple timed cache that expires after a set number of seconds
    
    Args:
        seconds: Number of seconds to cache the result
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        # Cache for this specific function
        cache = {}
        timestamps = {}
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Simple key based on the string representation of args and kwargs
            key = str((args, sorted(kwargs.items())))
            
            # Check if cached and not expired
            if key in cache and time.time() - timestamps[key] < seconds:
                return cache[key]
            
            # Not in cache or expired
            result = func(*args, **kwargs)
            cache[key] = result
            timestamps[key] = time.time()
            return result
            
        # Add method to clear this function's cache
        wrapper.clear_cache = lambda: cache.clear()
        
        return wrapper
    
    return decorator


def timed_memoize_json(seconds: int = 3600, max_size: int = 100) -> Callable:
    """
    Memory-only JSON memoization with time expiration and size limit
    
    Optimized for situations where Redis is not available or not needed.
    
    Args:
        seconds: Number of seconds to cache the result
        max_size: Maximum number of items in the cache
        
    Returns:
        Decorated function 
    """
    def decorator(func: Callable) -> Callable:
        # Cache for this specific function
        cache = {}
        timestamps = {}
        hits = {}
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Generate a key from the arguments
            try:
                # Try to create JSON string from arguments
                key_parts = [func.__name__]
                
                # Add args
                for arg in args:
                    if isinstance(arg, (dict, list, str, int, float, bool, type(None))):
                        key_parts.append(json.dumps(arg, sort_keys=True))
                    else:
                        key_parts.append(repr(arg))
                
                # Add kwargs (sorted)
                for k in sorted(kwargs.keys()):
                    v = kwargs[k]
                    if isinstance(v, (dict, list, str, int, float, bool, type(None))):
                        key_parts.append(f"{k}:{json.dumps(v, sort_keys=True)}")
                    else:
                        key_parts.append(f"{k}:{repr(v)}")
                
                key = "|".join(key_parts)
            except (TypeError, ValueError):
                # Fall back to string representation if JSON fails
                key = str((func.__name__, args, sorted(kwargs.items())))
            
            # Check if in cache and not expired
            current_time = time.time()
            if key in cache and current_time - timestamps[key] < seconds:
                # Update hit count
                hits[key] = hits.get(key, 0) + 1
                return cache[key]
            
            # Execute function
            result = func(*args, **kwargs)
            
            # Clean cache if it's getting too big
            if len(cache) >= max_size:
                # Strategy: remove oldest and least used entries
                if len(timestamps) > max_size // 2:
                    # Sort by (hits, timestamp) to prioritize keeping recently used items
                    items = [(k, hits.get(k, 0), ts) for k, ts in timestamps.items()]
                    items.sort(key=lambda x: (x[1], x[2]))  # Sort by hits, then by timestamp
                    
                    # Remove the oldest, least-used entries
                    to_remove = items[:len(items) // 2]  # Remove half the entries
                    for k, _, _ in to_remove:
                        cache.pop(k, None)
                        timestamps.pop(k, None)
                        hits.pop(k, None)
            
            # Cache the result
            cache[key] = result
            timestamps[key] = current_time
            hits[key] = 1
            
            return result
        
        # Attach a method to clear the cache for this function
        wrapper.clear_cache = lambda: (cache.clear(), timestamps.clear(), hits.clear())
        
        return wrapper
    
    return decorator 