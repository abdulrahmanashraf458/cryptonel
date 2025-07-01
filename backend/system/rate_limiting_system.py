"""
Rate Limiting System - Advanced rate limiting with Redis and per-endpoint controls

This module manages API rate limiting with adaptive limits, user notifications,
and distributed rate limiting using Redis.
"""

import os
import time
import logging
from typing import Dict, List, Optional, Union, Callable
from functools import wraps

from flask import Flask, request, jsonify, g, Blueprint
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Import our cache utilities for Redis support
from backend.utils.cache_utils import get_redis
from backend.api.response_handler import ApiResponse

# Configure logger
logger = logging.getLogger('cryptonel.ratelimit')

# Default rate limit storage URI
DEFAULT_REDIS_URI = os.environ.get('REDIS_URI', 'memory://')

# Global limiter
_limiter = None

# Rate limit definitions by endpoint and user type
RATE_LIMITS = {
    # Default limits
    'default': {
        'anonymous': '100/hour;30/minute;5/second',
        'user': '500/hour;60/minute;10/second',
        'admin': '1000/hour;100/minute;15/second'
    },
    
    # Login endpoint (more restrictive to prevent brute force)
    'login': {
        'anonymous': '10/hour;3/minute;1/5seconds',
        'user': '10/hour;3/minute;1/5seconds',  # Same as anonymous for login
        'admin': '10/hour;3/minute;1/5seconds'  # Same as anonymous for login
    },
    
    # Signup endpoint (more restrictive to prevent abuse)
    'signup': {
        'anonymous': '5/hour;2/minute;1/10seconds',
        'user': '5/hour;2/minute;1/10seconds',  # Same as anonymous for signup
        'admin': '5/hour;2/minute;1/10seconds'  # Same as anonymous for signup
    },
    
    # Transfer endpoint (more restrictive for sensitive operations)
    'transfers': {
        'anonymous': '0/hour',  # Anonymous users cannot transfer
        'user': '50/hour;10/minute;2/second',
        'admin': '100/hour;20/minute;3/second'
    },
    
    # Mining endpoint
    'mining': {
        'anonymous': '0/hour',  # Anonymous users cannot mine
        'user': '200/hour;30/minute;5/second',
        'admin': '300/hour;40/minute;10/second'
    },
    
    # Dashboard endpoints (frequent access allowed)
    'dashboard': {
        'anonymous': '50/hour;20/minute;5/second',
        'user': '300/hour;50/minute;10/second',
        'admin': '500/hour;80/minute;15/second'
    },
    
    # Static resources - very permissive 
    'static': {
        'anonymous': '1000/hour;200/minute;20/second',
        'user': '1000/hour;200/minute;20/second',
        'admin': '1000/hour;200/minute;20/second'
    },
    
    # Health check endpoints exempted
    'health': {
        'anonymous': None,  # No limit
        'user': None,       # No limit
        'admin': None       # No limit
    }
}

# Endpoint to rate limit mapping - used to determine which limit set to use
ENDPOINT_MAPPING = {
    # Auth & account endpoints
    'login': 'login',
    'auth.login': 'login',
    'auth.logout': 'default',
    'signup': 'signup',
    'auth.signup': 'signup',
    'auth.reset_password': 'login',
    'auth.verify_email': 'default',
    'profile': 'default',
    
    # Transaction-related endpoints
    'transfers.create': 'transfers',
    'transfers.list': 'default',
    'transfers.details': 'default',
    'transaction_history': 'default',
    
    # Mining endpoints
    'mining.start': 'mining',
    'mining.status': 'mining',
    'mining.reward': 'mining',
    
    # Dashboard and overview endpoints
    'overview.dashboard': 'dashboard',
    'overview.summary': 'dashboard',
    'overview.charts': 'dashboard',
    
    # Asset endpoints
    'static.serve': 'static',
    'health_check': 'health',
}

def configure_rate_limiting(app: Flask) -> Limiter:
    """
    Configure rate limiting for the application
    
    Args:
        app: Flask application
        
    Returns:
        Limiter: Configured Flask-Limiter instance
    """
    global _limiter
    
    # Get Redis URI or use in-memory fallback
    redis_uri = os.environ.get('REDIS_URI')
    
    # If REDIS_URI is not set, try to build it from config
    if not redis_uri:
        try:
            from backend.config import Config
            redis_host = getattr(Config, 'REDIS_HOST', 'localhost')
            redis_port = getattr(Config, 'REDIS_PORT', 6379)
            redis_db = getattr(Config, 'REDIS_DB', 0)
            redis_password = getattr(Config, 'REDIS_PASSWORD', None)
            
            # Build Redis URI
            if redis_password:
                # Properly encode the password to handle special characters
                from urllib.parse import quote_plus
                encoded_password = quote_plus(redis_password)
                redis_uri = f"redis://:{encoded_password}@{redis_host}:{redis_port}/{redis_db}"
            else:
                redis_uri = f"redis://{redis_host}:{redis_port}/{redis_db}"
                
            logger.info(f"Configuring rate limiting with Redis from config settings")
        except ImportError:
            redis_uri = None
            logger.warning("Could not import Config, falling back to in-memory rate limiting")
    
    # Set up storage
    if redis_uri:
        # Hide password in logs
        log_uri = redis_uri.split('@')[-1] if '@' in redis_uri else redis_uri
        logger.info(f"Configuring rate limiting with Redis: {log_uri}")
        storage_uri = redis_uri
        
        # Test connection to Redis
        try:
            import redis
            parts = redis_uri.replace('redis://', '').split('@')
            if len(parts) > 1:
                auth, location = parts
                password = auth.split(':')[-1]
            else:
                location = parts[0]
                password = None
                
            host_port_db = location.split('/')
            host_port = host_port_db[0].split(':')
            host = host_port[0]
            port = int(host_port[1]) if len(host_port) > 1 else 6379
            db = int(host_port_db[1]) if len(host_port_db) > 1 else 0
            
            # Try to connect to Redis
            r = redis.Redis(
                host=host, 
                port=port, 
                db=db, 
                password=password,
                socket_timeout=3,
                socket_connect_timeout=3
            )
            r.ping()
            logger.info("Redis connection successful")
        except Exception as e:
            logger.error(f"Redis connection failed, falling back to memory storage: {str(e)}")
            storage_uri = "memory://"
    else:
        logger.warning("Redis not configured. Using in-memory rate limiting (not suitable for distributed setup)")
        storage_uri = "memory://"
    
    # Create limiter with our custom keyfunc
    _limiter = Limiter(
        app=app,
        key_func=get_rate_limit_identifier,
        default_limits=[], # We'll apply limits per endpoint explicitly
        storage_uri=storage_uri,
        strategy="fixed-window",
        headers_enabled=True, # Return rate limit info in headers
        swallow_errors=True, # Don't break on errors
        header_name_mapping={
            'X-RateLimit-Limit': 'RateLimit-Limit',
            'X-RateLimit-Remaining': 'RateLimit-Remaining',
            'X-RateLimit-Reset': 'RateLimit-Reset',
        }
    )
    
    # Register limit exceeded handler
    @app.errorhandler(429)
    def ratelimit_handler(e):
        return handle_rate_limit_exceeded(e)
    
    # Set up decorators for endpoints that need specific rate limiting
    setup_endpoint_decorators(app)
    
    return _limiter


def setup_endpoint_decorators(app: Flask) -> None:
    """
    Set up rate limiting decorators for specific endpoints
    
    Args:
        app: Flask application
    """
    # Make sure static resources are rate limited
    if app.static_folder:
        # Static route is already registered by Flask but we want to decorate it
        for rule in app.url_map.iter_rules():
            if rule.endpoint == 'static':
                # Find the static view function
                static_view = app.view_functions['static']
                # Apply rate limiting
                app.view_functions['static'] = apply_endpoint_rate_limit('static')(static_view)
                break


def get_rate_limit_identifier() -> str:
    """
    Get identifier for rate limiting
    
    Returns more precise identifier than just IP address when possible,
    taking into account user ID, API key, or other identifiers.
    
    Returns:
        str: Rate limit identifier
    """
    # Try to get authenticated user ID first
    user_id = None
    if hasattr(g, 'user') and g.user and hasattr(g.user, 'id'):
        user_id = str(g.user.id)
    
    # Then check for API keys
    api_key = request.headers.get('X-API-Key')
    
    # Use the most specific identifier available
    if user_id:
        return f"user:{user_id}"
    elif api_key:
        return f"api:{api_key}"
    
    # Fall back to IP address if no other identifier
    return get_remote_address()


def get_user_role() -> str:
    """
    Get the current user role for rate limiting
    
    Returns:
        str: Role ('anonymous', 'user', or 'admin')
    """
    # Check if user is authenticated
    if hasattr(g, 'user') and g.user:
        # Check if admin
        if hasattr(g.user, 'is_admin') and g.user.is_admin:
            return 'admin'
        return 'user'
    
    return 'anonymous'


def get_endpoint_limits(endpoint: str, role: str) -> Optional[str]:
    """
    Get the rate limits for an endpoint and role
    
    Args:
        endpoint: Flask endpoint name
        role: User role (anonymous, user, admin)
        
    Returns:
        Optional[str]: Rate limit string or None if no limit
    """
    # First check if we have a mapping for this endpoint
    limit_category = ENDPOINT_MAPPING.get(endpoint, 'default')
    
    # Get the limits for this category and role
    limits = RATE_LIMITS.get(limit_category, RATE_LIMITS['default'])
    return limits.get(role, limits.get('anonymous'))


def apply_endpoint_rate_limit(endpoint_name: str = None, keys: Optional[List[str]] = None):
    """
    Decorator factory to apply appropriate rate limits to an endpoint
    
    Args:
        endpoint_name: Optional override for endpoint name
        keys: Optional keys to use (as a list of strings)
        
    Returns:
        Decorator for view function
    """
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if _limiter:
                # Get the endpoint name (either provided or from Flask)
                endpoint = endpoint_name or request.endpoint
                
                # Get user role
                role = get_user_role()
                
                # Get limits for this endpoint and role
                limit_string = get_endpoint_limits(endpoint, role)
                
                # If we have a limit, apply it dynamically
                if limit_string:
                    # Apply limit with the proper key function
                    limiter = _limiter.limit(
                        limit_string,
                        key_func=get_rate_limit_identifier,
                        per_method=True,
                        methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'],
                        error_message=f"Rate limit exceeded for {endpoint}. Please try again later."
                    )
                    return limiter(f)(*args, **kwargs)
            
            # If no limiter or no limit, just call the function
            return f(*args, **kwargs)
        
        return wrapped
    
    return decorator


def handle_rate_limit_exceeded(e):
    """
    Handle rate limit exceeded error with user-friendly response
    
    Args:
        e: Rate limit exception
        
    Returns:
        Flask response with rate limit details
    """
    retry_after = 60
    if hasattr(e, 'description') and hasattr(e.description, 'retry_after'):
        retry_after = e.description.retry_after
    
    # Determine remaining time in a human-readable format
    if retry_after < 60:
        time_message = f"{retry_after} seconds"
    elif retry_after < 3600:
        minutes = retry_after // 60
        time_message = f"{minutes} minute{'s' if minutes > 1 else ''}"
    else:
        hours = retry_after // 3600
        time_message = f"{hours} hour{'s' if hours > 1 else ''}"
    
    # Get endpoint name
    endpoint = request.endpoint or "this resource"
    
    # Create user-friendly error response
    response = ApiResponse.error(
        message=f"Rate limit exceeded for {endpoint}",
        status_code=429,
        errors=[{
            "code": "rate_limit_exceeded",
            "message": f"You've made too many requests. Please try again in {time_message}.",
            "retry_after": retry_after,
            "limit_type": get_endpoint_limits(endpoint, get_user_role())
        }]
    )
    
    # Log the rate limit violation
    logger.warning(f"Rate limit exceeded: {get_rate_limit_identifier()} for {endpoint}")
    
    # Return the error response with necessary headers
    resp = jsonify(response.to_dict())
    resp.status_code = 429
    resp.headers['Retry-After'] = str(retry_after)
    return resp


def get_remaining_limit(endpoint: str = None) -> Dict:
    """
    Get remaining rate limit info for an endpoint
    
    Args:
        endpoint: Endpoint name (defaults to current request endpoint)
        
    Returns:
        Dict: Rate limit information
    """
    if not _limiter:
        return {"error": "Rate limiter not configured"}
    
    endpoint_name = endpoint or request.endpoint
    key = get_rate_limit_identifier()
    
    # Try to get limit info from storage
    redis_client = get_redis()
    if not redis_client:
        return {"error": "Redis not available"}
    
    try:
        # Get all keys for this endpoint
        pattern = f"flask-limiter/{key}/{endpoint_name}_*"
        limit_keys = []
        
        # Try Redis SCAN command
        cursor = 0
        while True:
            cursor, keys = redis_client.scan(cursor, match=pattern, count=100)
            limit_keys.extend(keys)
            if cursor == 0:
                break
        
        limits = []
        now = time.time()
        
        for key in limit_keys:
            # Get limit info
            count = redis_client.get(key)
            ttl = redis_client.ttl(key)
            
            if count is not None and ttl is not None:
                # Parse the key to get the limit info
                key_parts = key.decode('utf-8').split('_')
                if len(key_parts) >= 2:
                    limit_str = key_parts[-1]
                    amount, period = limit_str.split('/')
                    
                    limits.append({
                        "limit": int(amount),
                        "remaining": max(0, int(amount) - int(count)),
                        "reset": int(now + ttl),
                        "window": period
                    })
        
        return {
            "limits": limits,
            "identifier": key
        }
        
    except Exception as e:
        logger.error(f"Error getting rate limit info: {e}")
        return {"error": str(e)}


def reset_rate_limit(endpoint: str, key: str) -> bool:
    """
    Reset rate limit for a specific endpoint and key
    
    Args:
        endpoint: Endpoint name
        key: Rate limit key
        
    Returns:
        bool: Whether operation succeeded
    """
    if not _limiter:
        return False
    
    redis_client = get_redis()
    if not redis_client:
        return False
    
    try:
        # Get all keys for this endpoint and key
        pattern = f"flask-limiter/{key}/{endpoint}_*"
        
        # Try Redis SCAN command
        cursor = 0
        deleted = False
        
        while True:
            cursor, keys = redis_client.scan(cursor, match=pattern, count=100)
            if keys:
                redis_client.delete(*keys)
                deleted = True
            if cursor == 0:
                break
        
        return deleted
    except Exception as e:
        logger.error(f"Error resetting rate limit: {e}")
        return False


def create_rate_limit_blueprint() -> Blueprint:
    """
    Create a blueprint for rate limit management endpoints
    
    Returns:
        Blueprint: Flask blueprint with rate limit endpoints
    """
    bp = Blueprint('rate_limits', __name__)
    
    @bp.route('/api/rate-limits/status')
    @apply_endpoint_rate_limit('rate_limits.status')
    def rate_limit_status():
        """Get current rate limit status for the user"""
        endpoint = request.args.get('endpoint')
        limits = get_remaining_limit(endpoint)
        
        return jsonify({
            "status": "success",
            "data": limits
        })
    
    @bp.route('/api/rate-limits/reset', methods=['POST'])
    @apply_endpoint_rate_limit('rate_limits.reset')
    def reset_user_rate_limit():
        """Reset rate limit for a user (admin only)"""
        # Check if admin
        if not (hasattr(g, 'user') and g.user and hasattr(g.user, 'is_admin') and g.user.is_admin):
            return jsonify({
                "status": "error",
                "message": "Unauthorized"
            }), 403
        
        # Get parameters
        data = request.get_json() or {}
        endpoint = data.get('endpoint')
        user_id = data.get('user_id')
        
        if not endpoint or not user_id:
            return jsonify({
                "status": "error",
                "message": "Missing required parameters: endpoint, user_id"
            }), 400
        
        # Reset the rate limit
        key = f"user:{user_id}"
        success = reset_rate_limit(endpoint, key)
        
        if success:
            logger.info(f"Admin {g.user.id} reset rate limit for user {user_id} on {endpoint}")
            return jsonify({
                "status": "success",
                "message": f"Rate limit for {user_id} on {endpoint} reset successfully"
            })
        else:
            return jsonify({
                "status": "error",
                "message": "Failed to reset rate limit"
            }), 500
    
    return bp 