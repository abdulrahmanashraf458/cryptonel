"""
Rate Limiting Utilities

This module provides rate limiting functionality to protect API endpoints
from abuse and ensure fair usage of resources. It supports different rate
limit strategies and can be easily integrated with Flask.

Features:
- Fixed window rate limiting (requests per minute/hour)
- Sliding window rate limiting for smoother traffic control
- Rate limit by IP, user ID, or custom keys
- Configurable rate limits per endpoint or globally
- Automatic limit headers in HTTP responses
"""

import time
import logging
import functools
import ipaddress
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from datetime import datetime, timedelta

try:
    # Import Redis cache utilities
    from backend.utils.cache_utils import (
        get_redis_client, 
        build_key, 
        cache_increment,
        cache_get
    )
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

# Configure logger
logger = logging.getLogger(__name__)

# Default rate limits
DEFAULT_LIMIT = 60  # requests
DEFAULT_PERIOD = 60  # seconds
DEFAULT_LIMIT_BY = "ip"  # ip, user, custom

class RateLimitExceeded(Exception):
    """Exception raised when rate limit is exceeded"""
    
    def __init__(self, limit: int, remaining: int, reset_time: int, key: str):
        self.limit = limit
        self.remaining = remaining
        self.reset_time = reset_time
        self.key = key
        message = f"Rate limit exceeded: {limit} requests per {reset_time} seconds"
        super().__init__(message)


def extract_ip(request) -> str:
    """
    Extract the real IP address from request headers
    
    Args:
        request: Flask request object
        
    Returns:
        IP address string
    """
    # Try to get IP from proxy headers
    headers_to_check = [
        'X-Forwarded-For',
        'X-Real-IP',
        'CF-Connecting-IP',  # Cloudflare
        'True-Client-IP'
    ]
    
    for header in headers_to_check:
        if header in request.headers:
            # X-Forwarded-For can contain multiple IPs - use the first one
            ip_str = request.headers[header].split(',')[0].strip()
            try:
                # Validate it's a proper IP address
                ipaddress.ip_address(ip_str)
                return ip_str
            except ValueError:
                continue
    
    # Fall back to remote address
    return request.remote_addr or '0.0.0.0'


def extract_user_id(request) -> Optional[str]:
    """
    Extract user ID from request, assuming Flask-Login is being used
    
    Args:
        request: Flask request object
        
    Returns:
        User ID or None if not authenticated
    """
    if hasattr(request, 'user') and hasattr(request.user, 'id'):
        return str(request.user.id)
    
    # Try to get from Flask-Login's current_user
    if hasattr(request, 'current_user') and hasattr(request.current_user, 'id'):
        return str(request.current_user.id)
    
    # Try session
    if hasattr(request, 'session') and 'user_id' in request.session:
        return str(request.session['user_id'])
    
    return None


def get_rate_limit_key(request, limit_by: str, namespace: Optional[str] = None) -> str:
    """
    Generate a rate limit key based on request attributes
    
    Args:
        request: Flask request object
        limit_by: Type of rate limiting (ip, user, path, custom)
        namespace: Optional namespace to add to key
        
    Returns:
        Rate limit key string
    """
    if limit_by == 'ip':
        identifier = extract_ip(request)
    elif limit_by == 'user':
        user_id = extract_user_id(request)
        identifier = user_id or extract_ip(request)
    elif limit_by == 'path':
        # Limit by URL path + IP
        path = request.path
        ip = extract_ip(request)
        identifier = f"{path}:{ip}"
    elif limit_by == 'global':
        # Global limit across all users/IPs
        identifier = 'global'
    else:
        # Custom key function should be passed in namespace
        identifier = namespace or 'custom'
    
    endpoint = request.endpoint or request.path
    return f"ratelimit:{endpoint}:{identifier}"


def check_rate_limit(
    key: str, 
    limit: int, 
    period: int
) -> Tuple[bool, int, int, int]:
    """
    Check if request should be rate limited
    
    Args:
        key: Rate limit key
        limit: Maximum number of requests allowed
        period: Time period in seconds
        
    Returns:
        Tuple of (is_allowed, remaining, limit, reset_time)
    """
    if not REDIS_AVAILABLE:
        # Without Redis, we can't effectively rate limit
        return True, limit, limit, int(time.time()) + period
    
    # Get current count
    current = cache_increment(key, 1, namespace=None, expiry=period)
    
    # If this is the first request, current will be 1
    if current is None:
        return True, limit - 1, limit, int(time.time()) + period
    
    # Calculate remaining and reset time
    remaining = max(0, limit - current)
    reset_time = int(time.time()) + period
    
    # Check if over limit
    is_allowed = current <= limit
    
    return is_allowed, remaining, limit, reset_time


def apply_rate_limit(request, limit: int, period: int, limit_by: str, 
                    namespace: Optional[str] = None) -> Tuple[bool, Dict[str, int]]:
    """
    Apply rate limiting to a request
    
    Args:
        request: Flask request object
        limit: Maximum number of requests allowed
        period: Time period in seconds
        limit_by: Type of rate limiting (ip, user, path, custom)
        namespace: Optional namespace for custom limiter
        
    Returns:
        Tuple of (is_allowed, rate_limit_headers)
    """
    # Generate rate limit key
    key = get_rate_limit_key(request, limit_by, namespace)
    
    # Check rate limit
    is_allowed, remaining, limit, reset_time = check_rate_limit(key, limit, period)
    
    # Prepare headers for HTTP response
    headers = {
        'X-RateLimit-Limit': limit,
        'X-RateLimit-Remaining': remaining,
        'X-RateLimit-Reset': reset_time
    }
    
    return is_allowed, headers


def rate_limit(
    limit: int = DEFAULT_LIMIT,
    period: int = DEFAULT_PERIOD,
    limit_by: str = DEFAULT_LIMIT_BY,
    namespace: Optional[str] = None
) -> Callable:
    """
    Decorator to apply rate limiting to a Flask route
    
    Args:
        limit: Maximum number of requests allowed 
        period: Time period in seconds
        limit_by: Type of rate limiting (ip, user, path, custom)
        namespace: Optional namespace for custom key
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Get Flask request object
            from flask import request, make_response, jsonify, current_app
            
            # Apply rate limiting
            is_allowed, headers = apply_rate_limit(request, limit, period, limit_by, namespace)
            
            if not is_allowed:
                # Return rate limit exceeded response
                response = make_response(jsonify({
                    'error': 'rate_limit_exceeded',
                    'message': f'You have exceeded the rate limit of {limit} requests per {period} seconds',
                    'status': 429,
                    'details': {
                        'limit': limit,
                        'period': period,
                        'limit_by': limit_by
                    }
                }), 429)
                
                # Add rate limit headers to response
                for key, value in headers.items():
                    response.headers[key] = str(value)
                
                # Add Retry-After header
                response.headers['Retry-After'] = str(period)
                
                # Log the rate limit event
                logger.warning(
                    f"Rate limit exceeded for {limit_by}={request.remote_addr or 'unknown'} "
                    f"on endpoint {request.endpoint or request.path}"
                )
                
                return response
            
            # Call the original function
            response = func(*args, **kwargs)
            
            # If response is a Flask response object, add rate limit headers
            if hasattr(response, 'headers'):
                for key, value in headers.items():
                    response.headers[key] = str(value)
            
            return response
        
        return wrapper
    
    return decorator


# Function to integrate with Flask application
def init_rate_limiting(app):
    """
    Initialize rate limiting for a Flask application
    
    Args:
        app: Flask application instance
        
    Returns:
        None
    """
    if not REDIS_AVAILABLE:
        logger.warning("Redis not available, rate limiting will be disabled")
        return
    
    # Apply the rate limiting extension
    app.extensions = getattr(app, 'extensions', {})
    app.extensions['rate_limiting'] = True
    
    # Configure from Flask application config
    global DEFAULT_LIMIT, DEFAULT_PERIOD, DEFAULT_LIMIT_BY
    DEFAULT_LIMIT = app.config.get('RATE_LIMIT', DEFAULT_LIMIT)
    DEFAULT_PERIOD = app.config.get('RATE_LIMIT_PERIOD', DEFAULT_PERIOD)
    DEFAULT_LIMIT_BY = app.config.get('RATE_LIMIT_BY', DEFAULT_LIMIT_BY)
    
    logger.info(f"Rate limiting initialized: {DEFAULT_LIMIT} requests per {DEFAULT_PERIOD}s by {DEFAULT_LIMIT_BY}")


# Tiered rate limiting for different types of users
def tiered_rate_limit(
    anonymous_limit: int = 30,
    authenticated_limit: int = 60,
    premium_limit: int = 120,
    period: int = 60
) -> Callable:
    """
    Apply different rate limits based on user tier/role
    
    Args:
        anonymous_limit: Rate limit for anonymous users
        authenticated_limit: Rate limit for authenticated users
        premium_limit: Rate limit for premium users
        period: Time period in seconds
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            from flask import request, make_response, jsonify, current_app
            
            # Determine user tier
            user_id = extract_user_id(request)
            
            if not user_id:
                # Anonymous user
                limit = anonymous_limit
                limit_by = 'ip'
            else:
                # Check if premium user (implementation depends on your app)
                user_is_premium = False
                
                # Try to get user from request
                if hasattr(request, 'user') and hasattr(request.user, 'is_premium'):
                    user_is_premium = request.user.is_premium
                
                # Or from Flask-Login's current_user
                elif hasattr(request, 'current_user') and hasattr(request.current_user, 'is_premium'):
                    user_is_premium = request.current_user.is_premium
                
                # Set appropriate limit
                limit = premium_limit if user_is_premium else authenticated_limit
                limit_by = 'user'
            
            # Apply rate limiting
            is_allowed, headers = apply_rate_limit(request, limit, period, limit_by)
            
            if not is_allowed:
                # Return rate limit exceeded response with tier-specific message
                tier_name = "premium" if limit == premium_limit else "authenticated" if limit == authenticated_limit else "anonymous"
                
                response = make_response(jsonify({
                    'error': 'rate_limit_exceeded',
                    'message': f'You have exceeded the {tier_name} rate limit of {limit} requests per {period} seconds',
                    'status': 429,
                    'details': {
                        'limit': limit,
                        'period': period,
                        'tier': tier_name
                    }
                }), 429)
                
                # Add rate limit headers to response
                for key, value in headers.items():
                    response.headers[key] = str(value)
                
                # Add Retry-After header
                response.headers['Retry-After'] = str(period)
                
                # Log the rate limit event
                logger.warning(
                    f"Rate limit exceeded for {tier_name} user (ID={user_id or 'anonymous'}) "
                    f"on endpoint {request.endpoint or request.path}"
                )
                
                return response
            
            # Call the original function
            response = func(*args, **kwargs)
            
            # If response is a Flask response object, add rate limit headers
            if hasattr(response, 'headers'):
                for key, value in headers.items():
                    response.headers[key] = str(value)
            
            return response
        
        return wrapper
    
    return decorator


# Sliding window rate limiter (more accurate than fixed window)
def sliding_window_rate_limit(
    limit: int = DEFAULT_LIMIT,
    period: int = DEFAULT_PERIOD,
    limit_by: str = DEFAULT_LIMIT_BY
) -> Callable:
    """
    Apply sliding window rate limiting to a Flask route
    
    Args:
        limit: Maximum number of requests allowed
        period: Time period in seconds
        limit_by: Type of rate limiting (ip, user, path, custom)
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            from flask import request, make_response, jsonify
            
            if not REDIS_AVAILABLE:
                # Without Redis, we can't do sliding window
                return func(*args, **kwargs)
            
            # Get Redis client
            redis = get_redis_client()
            if not redis:
                return func(*args, **kwargs)
            
            # Generate rate limit key
            key = get_rate_limit_key(request, limit_by)
            key_history = f"{key}:history"
            
            # Get current timestamp
            now = time.time()
            window_start = now - period
            
            try:
                # Add current request to history with timestamp as score
                pipe = redis.pipeline()
                pipe.zadd(key_history, {str(now): now})
                
                # Remove events outside the window
                pipe.zremrangebyscore(key_history, 0, window_start)
                
                # Count requests in current window
                pipe.zcard(key_history)
                
                # Set expiration on history
                pipe.expire(key_history, period * 2)  # 2x period for safety
                
                # Execute all commands as transaction
                _, _, current_count, _ = pipe.execute()
                
                # Determine if request is allowed
                is_allowed = current_count <= limit
                remaining = max(0, limit - current_count)
                
                # Get reset time (when oldest request expires)
                if current_count > 0 and not is_allowed:
                    # Get oldest request timestamp
                    oldest = float(redis.zrange(key_history, 0, 0, withscores=True)[0][1])
                    reset_time = int(oldest + period)
                else:
                    reset_time = int(now + period)
                
                # Prepare headers
                headers = {
                    'X-RateLimit-Limit': limit,
                    'X-RateLimit-Remaining': remaining,
                    'X-RateLimit-Reset': reset_time
                }
                
                if not is_allowed:
                    # Return rate limit exceeded response
                    response = make_response(jsonify({
                        'error': 'rate_limit_exceeded',
                        'message': f'You have exceeded the rate limit of {limit} requests per {period} seconds',
                        'status': 429,
                        'details': {
                            'limit': limit,
                            'period': period,
                            'limit_by': limit_by,
                            'sliding_window': True
                        }
                    }), 429)
                    
                    # Add rate limit headers to response
                    for key, value in headers.items():
                        response.headers[key] = str(value)
                    
                    # Add Retry-After header - time until oldest request expires
                    response.headers['Retry-After'] = str(max(1, reset_time - int(now)))
                    
                    # Log the rate limit event
                    logger.warning(
                        f"Sliding window rate limit exceeded for {limit_by}={request.remote_addr or 'unknown'} "
                        f"on endpoint {request.endpoint or request.path}"
                    )
                    
                    return response
                
                # Call the original function
                response = func(*args, **kwargs)
                
                # If response is a Flask response object, add rate limit headers
                if hasattr(response, 'headers'):
                    for key, value in headers.items():
                        response.headers[key] = str(value)
                
                return response
                
            except Exception as e:
                # Log error but don't block request
                logger.error(f"Error applying sliding window rate limit: {e}")
                # Fallback to original function
                return func(*args, **kwargs)
                
        return wrapper
    
    return decorator 