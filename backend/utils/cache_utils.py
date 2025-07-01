"""
Redis Cache Utilities

This module provides utilities for Redis-based caching operations,
including connection management, key-value operations, and specialized
caching functions for common data types like JSON.

Features:
- Redis connection management
- Key-value operations with TTL support
- JSON serialization/deserialization for cached objects
- Cache invalidation and management utilities
"""

import json
import time
import logging
import pickle
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from datetime import datetime, timedelta
import redis
import os
from functools import wraps
from bson.objectid import ObjectId

# Configure logger
logger = logging.getLogger(__name__)

# Global Redis client
_redis_client = None
_redis_available = False

try:
    # Redis is importable
    _redis_available = True
except ImportError:
    logger.info("Redis library not available. Cache operations will use in-memory fallback.")

# Add a custom JSON encoder that can handle MongoDB ObjectId
class MongoJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        elif isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

def get_redis_client(force_reconnect: bool = False) -> Optional["redis.Redis"]:
    """
    Get a Redis client connection, creating it if needed
    
    Args:
        force_reconnect: Force a new connection even if one exists
        
    Returns:
        Redis client instance or None if Redis is not available
    """
    global _redis_client, _redis_available
    
    if not _redis_available:
        return None
    
    if _redis_client is None or force_reconnect:
        try:
            # Try to get Redis config from application config
            try:
                from backend.config import Config
                redis_host = getattr(Config, 'REDIS_HOST', 'localhost')
                redis_port = getattr(Config, 'REDIS_PORT', 6379)
                redis_db = getattr(Config, 'REDIS_DB', 0)
                redis_password = getattr(Config, 'REDIS_PASSWORD', None)
            except ImportError:
                # Default values if config not available
                redis_host = os.environ.get('REDIS_HOST', 'localhost')
                redis_port = int(os.environ.get('REDIS_PORT', 6379))
                redis_db = int(os.environ.get('REDIS_DB', 0))
                redis_password = os.environ.get('REDIS_PASSWORD')
            
            # Connect to Redis
            _redis_client = redis.Redis(
                host=redis_host,
                port=redis_port,
                db=redis_db,
                password=redis_password,
                socket_timeout=5,  # Increased from 2 to 5
                socket_connect_timeout=5,  # Increased from 2 to 5
                health_check_interval=30,
                decode_responses=False,  # Keep as bytes for flexibility
                retry_on_timeout=True,   # Enable retries
                max_connections=10       # Set maximum connections
            )
            
            # Test connection
            _redis_client.ping()
            
            # Hide password in logs if present
            log_host = f"{redis_host}:{redis_port}/{redis_db}"
            logger.info(f"Connected to Redis at {log_host}")
            
        except Exception as e:
            _redis_client = None
            _redis_available = False
            logger.warning(f"Could not connect to Redis: {str(e)}")
    
    return _redis_client


# For backward compatibility with rate_limiting_system.py
def get_redis() -> Optional["redis.Redis"]:
    """
    Alias for get_redis_client for backward compatibility
    
    Returns:
        Redis client instance or None if Redis is not available
    """
    return get_redis_client()


def cache_set(key: str, value: Any, ttl: Optional[int] = None) -> bool:
    """
    Set a value in the Redis cache
    
    Args:
        key: Cache key
        value: Python object to cache
        ttl: Time to live in seconds, None for no expiry
        
    Returns:
        True if successful, False otherwise
    """
    client = get_redis_client()
    if client is None:
        logger.debug("Redis not available for cache_set")
        return False
    
    try:
        # Use the custom encoder to handle ObjectId objects
        serialized = json.dumps(value, cls=MongoJSONEncoder).encode('utf-8')
        prefix = b'json:'
        
        # Store with type prefix for proper deserialization
        if ttl:
            success = client.setex(key, ttl, prefix + serialized)
        else:
            success = client.set(key, prefix + serialized)
        
        logger.debug(f"Cache set: {key}, TTL: {ttl or 'None'}")
        return bool(success)
    
    except Exception as e:
        logger.error(f"Error setting cache key {key}: {str(e)}")
        return False


def cache_get(key: str) -> Any:
    """
    Get a value from the Redis cache
    
    Args:
        key: Cache key
        
    Returns:
        Cached value or None if not found/expired
    """
    client = get_redis_client()
    if client is None:
        logger.debug("Redis not available for cache_get")
        return None
    
    try:
        value = client.get(key)
        if not value:
            return None
        
        # Determine serialization format from prefix
        if value.startswith(b'json:'):
            # JSON serialized data
            serialized = value[5:]  # Skip 'json:' prefix
            result = json.loads(serialized.decode('utf-8'))
        elif value.startswith(b'pickle:'):
            # Pickle serialized data
            serialized = value[7:]  # Skip 'pickle:' prefix
            result = pickle.loads(serialized)
        else:
            # Legacy data without prefix - try JSON first
            try:
                result = json.loads(value.decode('utf-8'))
            except (json.JSONDecodeError, UnicodeDecodeError):
                # Fall back to pickle
                try:
                    result = pickle.loads(value)
                except Exception:
                    # Return raw value as last resort
                    result = value
        
        logger.debug(f"Cache hit: {key}")
        return result
    
    except Exception as e:
        logger.error(f"Error getting cache key {key}: {str(e)}")
        return None


def cache_delete(key: str) -> bool:
    """
    Delete a key from the Redis cache
    
    Args:
        key: Cache key to delete
        
    Returns:
        True if key was deleted, False otherwise
    """
    client = get_redis_client()
    if client is None:
        logger.debug("Redis not available for cache_delete")
        return False
    
    try:
        result = client.delete(key)
        logger.debug(f"Cache delete: {key}")
        return bool(result)
    
    except Exception as e:
        logger.error(f"Error deleting cache key {key}: {str(e)}")
        return False


def cache_exists(key: str) -> bool:
    """
    Check if a key exists in the Redis cache
    
    Args:
        key: Cache key to check
        
    Returns:
        True if key exists, False otherwise
    """
    client = get_redis_client()
    if client is None:
        logger.debug("Redis not available for cache_exists")
        return False
    
    try:
        return bool(client.exists(key))
    
    except Exception as e:
        logger.error(f"Error checking cache key {key}: {str(e)}")
        return False


def cache_ttl(key: str) -> Optional[int]:
    """
    Get the TTL of a key in the Redis cache
    
    Args:
        key: Cache key to check
        
    Returns:
        TTL in seconds, -1 if the key exists but has no TTL,
        or None if the key doesn't exist or an error occurs
    """
    client = get_redis_client()
    if client is None:
        logger.debug("Redis not available for cache_ttl")
        return None
    
    try:
        ttl = client.ttl(key)
        # Redis returns -2 if the key doesn't exist
        return ttl if ttl != -2 else None
    
    except Exception as e:
        logger.error(f"Error getting TTL for cache key {key}: {str(e)}")
        return None


def cache_clear_pattern(pattern: str) -> int:
    """
    Clear all keys matching a pattern
    
    Args:
        pattern: Redis key pattern to match
        
    Returns:
        Number of keys deleted
    """
    client = get_redis_client()
    if client is None:
        logger.debug("Redis not available for cache_clear_pattern")
        return 0
    
    try:
        # Find keys matching pattern
        keys = client.keys(pattern)
        if not keys:
            return 0
        
        # Delete all matching keys
        deleted = client.delete(*keys)
        logger.info(f"Cleared {deleted} keys matching pattern '{pattern}'")
        return deleted
    
    except Exception as e:
        logger.error(f"Error clearing cache keys with pattern '{pattern}': {str(e)}")
        return 0


def cache_set_json(key: str, value: Any, ttl: Optional[int] = None) -> bool:
    """
    Set a JSON-serializable value in the Redis cache
    
    Args:
        key: Cache key
        value: JSON-serializable Python object to cache
        ttl: Time to live in seconds, None for no expiry
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Pre-serialize to ensure valid JSON
        json_str = json.dumps(value)
        return cache_set(key, value, ttl)
    except (TypeError, ValueError):
        logger.error(f"Value for {key} is not JSON serializable")
        return False


def cache_get_json(key: str) -> Any:
    """
    Get a JSON-serialized value from the Redis cache
    
    Args:
        key: Cache key
        
    Returns:
        Deserialized JSON value or None if not found/expired
    """
    return cache_get(key)


def cache_increment(key: str, amount: int = 1, ttl: Optional[int] = None) -> Optional[int]:
    """
    Increment a numeric value in the Redis cache
    
    Args:
        key: Cache key
        amount: Amount to increment by
        ttl: Time to live after incrementing, None for no change
        
    Returns:
        New value after incrementing, or None if operation failed
    """
    client = get_redis_client()
    if client is None:
        logger.debug("Redis not available for cache_increment")
        return None
    
    try:
        if amount == 1:
            # Use INCR for single increment
            new_value = client.incr(key)
        else:
            # Use INCRBY for custom increment
            new_value = client.incrby(key, amount)
        
        # Set TTL if specified
        if ttl is not None:
            client.expire(key, ttl)
        
        logger.debug(f"Cache increment: {key} by {amount}, new value: {new_value}")
        return new_value
    
    except Exception as e:
        logger.error(f"Error incrementing cache key {key}: {str(e)}")
        return None


def cache_healthcheck() -> bool:
    """
    Check if Redis cache is available and responding
    
    Returns:
        True if Redis is available and responding, False otherwise
    """
    try:
        client = get_redis_client(force_reconnect=True)
        if client is None:
            return False
        
        # Test connection with PING
        return client.ping()
    
    except Exception as e:
        logger.error(f"Redis healthcheck failed: {str(e)}")
        return False


class RateLimiter:
    """Rate limiter using Redis"""
    
    def __init__(self, key_prefix: str = "ratelimit:", window_seconds: int = 60):
        """
        Initialize a rate limiter
        
        Args:
            key_prefix: Prefix for rate limit keys
            window_seconds: Time window in seconds
        """
        self.key_prefix = key_prefix
        self.window_seconds = window_seconds
    
    def _get_key(self, resource_id: str) -> str:
        """
        Get Redis key for a resource
        
        Args:
            resource_id: Identifier for the resource (e.g. IP, user_id)
            
        Returns:
            Redis key string
        """
        return f"{self.key_prefix}{resource_id}"
    
    def check_rate_limit(self, resource_id: str, limit: int) -> Tuple[bool, int]:
        """
        Check if a request should be rate limited
        
        Args:
            resource_id: Identifier for the resource (e.g. IP, user_id)
            limit: Maximum number of requests in the time window
            
        Returns:
            Tuple of (allowed, current_count)
        """
        key = self._get_key(resource_id)
        count = cache_increment(key, 1, self.window_seconds)
        
        if count is None:
            # Redis not available, allow request
            logger.warning("Rate limiting disabled: Redis not available")
            return True, 0
        
        return count <= limit, count
    
    def reset_counter(self, resource_id: str) -> bool:
        """
        Reset rate limit counter for a resource
        
        Args:
            resource_id: Identifier for the resource
            
        Returns:
            True if counter was reset, False otherwise
        """
        key = self._get_key(resource_id)
        return cache_delete(key)
    
    def get_counter(self, resource_id: str) -> int:
        """
        Get current rate limit counter for a resource
        
        Args:
            resource_id: Identifier for the resource
            
        Returns:
            Current counter value, 0 if not set
        """
        key = self._get_key(resource_id)
        value = cache_get(key)
        return int(value) if value is not None else 0
    
    def get_ttl(self, resource_id: str) -> Optional[int]:
        """
        Get remaining window time for a resource
        
        Args:
            resource_id: Identifier for the resource
            
        Returns:
            Remaining time in seconds, None if not set
        """
        key = self._get_key(resource_id)
        return cache_ttl(key)


def init_redis_cache():
    """
    Initialize Redis cache connection
    
    Returns:
        True if Redis is available, False otherwise
    """
    # Try to connect multiple times before giving up
    for attempt in range(3):
        try:
            client = get_redis_client(force_reconnect=True)
            if client is not None:
                logger.info(f"Redis connected successfully on attempt {attempt+1}")
                return True
            time.sleep(1)  # Wait a bit between attempts
        except Exception as e:
            logger.warning(f"Redis connection attempt {attempt+1} failed: {e}")
            time.sleep(1)  # Wait before retry
    
    logger.warning("All Redis connection attempts failed")
    return False 

# In-memory fallback cache
memory_cache = {}

def cache_set(key, value, ttl=300):
    """Set a value in cache (Redis or in-memory fallback)"""
    try:
        if _redis_client:
            # Use the custom encoder to handle ObjectId objects
            serialized_value = json.dumps(value, cls=MongoJSONEncoder)
            return _redis_client.setex(key, ttl, serialized_value)
        else:
            # In-memory fallback
            expiry = time.time() + ttl
            memory_cache[key] = {'value': value, 'expiry': expiry}
            return True
    except Exception as e:
        logger.error(f"Error setting cache key {key}: {e}")
        return False

def cache_get(key):
    """Get a value from cache (Redis or in-memory fallback)"""
    try:
        if _redis_client:
            # Get from Redis
            data = _redis_client.get(key)
            if data:
                return json.loads(data)
            return None
        else:
            # Get from in-memory fallback
            cached = memory_cache.get(key)
            if cached and cached['expiry'] > time.time():
                return cached['value']
            elif cached:
                # Remove expired key
                del memory_cache[key]
            return None
    except Exception as e:
        logger.error(f"Error getting cache key {key}: {e}")
        return None

def cache_delete(key):
    """Delete a key from cache (Redis or in-memory fallback)"""
    try:
        if _redis_client:
            return _redis_client.delete(key)
        else:
            # Delete from in-memory fallback
            if key in memory_cache:
                del memory_cache[key]
            return True
    except Exception as e:
        logger.error(f"Error deleting cache key {key}: {e}")
        return False

def cache_clear():
    """Clear all cache (Redis or in-memory fallback)"""
    try:
        if _redis_client:
            return _redis_client.flushdb()
        else:
            memory_cache.clear()
            return True
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        return False

# Decorator for caching function results
def cached(ttl=300, key_prefix='cache'):
    """Decorator for caching function results"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            # Simple key generation - can be improved
            key = f"{key_prefix}:{func.__name__}:{str(args)}:{str(kwargs)}"
            
            # Try to get from cache
            cached_value = cache_get(key)
            if cached_value is not None:
                return cached_value
                
            # Call the function
            result = func(*args, **kwargs)
            
            # Cache the result
            cache_set(key, result, ttl)
            
            return result
        return wrapper
    return decorator 

def cache_serialize(value: Any) -> Tuple[bytes, bytes]:
    """Serialize a value for storage in Redis, handling ObjectId and other special types"""
    try:
        # Serialize value based on type
        if isinstance(value, (dict, list, str, int, float, bool, type(None))):
            # For JSON-serializable types
            # Add special handling for ObjectId and datetime objects
            serialized = json.dumps(value, cls=MongoJSONEncoder).encode('utf-8')
            prefix = b'json:'
        else:
            # For other Python objects
            serialized = pickle.dumps(value)
            prefix = b'pickle:'
        
        return serialized, prefix
    except Exception as e:
        logger.error(f"Error serializing cache value: {e}")
        # Return empty values in case of error
        return b'', b''