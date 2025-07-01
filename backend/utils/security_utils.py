"""
Security Utilities - Enhanced HTTPS, security headers, and input validation

This module provides security utilities for protecting API services, including:
- HTTPS/TLS configuration
- Security headers for HTTP responses
- Input validation and sanitization
- Rate limiting and IP blocking
- Token handling and validation
"""

import re
import uuid
import time
import logging
import secrets
import ipaddress
from typing import Dict, List, Any, Optional, Union, Callable, TypeVar, Set
from urllib.parse import urlparse, quote

# Configure logging
logger = logging.getLogger(__name__)
T = TypeVar('T')

# Secure headers that should be applied to all responses
SECURE_HEADERS = {
    # Prevent browsers from interpreting files as a different MIME type
    'X-Content-Type-Options': 'nosniff',
    
    # Prevent embedding in iframes on other domains to avoid clickjacking
    'X-Frame-Options': 'DENY',
    
    # Enable browser XSS protection
    'X-XSS-Protection': '1; mode=block',
    
    # Restrict browser features and APIs
    'Feature-Policy': "camera 'none'; microphone 'none'; geolocation 'none'",
    'Permissions-Policy': "camera=(), microphone=(), geolocation=()",
    
    # Set a strict Content Security Policy
    'Content-Security-Policy': "default-src 'self'; script-src 'self'; object-src 'none'; "
                             "style-src 'self'; img-src 'self' data:; "
                             "font-src 'self'; connect-src 'self'; "
                             "frame-ancestors 'none'; form-action 'self'; "
                             "base-uri 'self'; frame-src 'none'",
    
    # Cache control to prevent sensitive information caching
    'Cache-Control': 'no-store, max-age=0',
    'Pragma': 'no-cache',
    
    # Referrer policy to limit information passed to other websites
    'Referrer-Policy': 'strict-origin-when-cross-origin',
}

# Headers that should be added to local development only
DEV_HEADERS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization',
}

# HTTPS/TLS configuration
TLS_CONFIG = {
    # Minimum TLS version (1.2 is considered secure as of 2023)
    'min_version': 'TLSv1.2',
    
    # Recommended cipher suites in order of preference
    'ciphers': [
        'TLS_AES_256_GCM_SHA384',
        'TLS_CHACHA20_POLY1305_SHA256',
        'TLS_AES_128_GCM_SHA256',
        'ECDHE-ECDSA-AES256-GCM-SHA384',
        'ECDHE-RSA-AES256-GCM-SHA384',
        'ECDHE-ECDSA-CHACHA20-POLY1305',
        'ECDHE-RSA-CHACHA20-POLY1305',
        'ECDHE-ECDSA-AES128-GCM-SHA256',
        'ECDHE-RSA-AES128-GCM-SHA256'
    ],
    
    # Set HSTS (HTTP Strict Transport Security) max-age to 1 year in seconds
    'hsts_max_age': 31536000,
    
    # Whether to enable OCSP stapling
    'ocsp_stapling': True,
    
    # Disable TLS compression (to prevent CRIME attack)
    'compression': False,
    
    # Ephemeral key generation parameters
    'dhparam_size': 2048,
    
    # Certificate settings
    'cert_key_size': 4096
}


def get_secure_headers(is_dev: bool = False) -> Dict[str, str]:
    """
    Get security headers to apply to HTTP responses
    
    Args:
        is_dev: Whether the application is running in development mode
        
    Returns:
        Dictionary of security headers
    """
    headers = SECURE_HEADERS.copy()
    
    # Add HSTS header if not in development
    if not is_dev:
        headers['Strict-Transport-Security'] = f'max-age={TLS_CONFIG["hsts_max_age"]}; includeSubDomains; preload'
    else:
        # Add development-specific headers
        headers.update(DEV_HEADERS)
        
    return headers


def apply_security_headers(response: Any, is_dev: bool = False) -> Any:
    """
    Apply security headers to an HTTP response object
    
    This function is framework-agnostic and works with various web frameworks
    by checking for the presence of common header-setting methods.
    
    Args:
        response: Response object from web framework (Flask, FastAPI, etc.)
        is_dev: Whether the application is running in development mode
        
    Returns:
        Response with security headers applied
    """
    headers = get_secure_headers(is_dev)
    
    # Try different approaches based on the response type
    if hasattr(response, 'headers'):
        # Flask, Django, FastAPI style
        for key, value in headers.items():
            response.headers[key] = value
    elif hasattr(response, 'set_header'):
        # Tornado style
        for key, value in headers.items():
            response.set_header(key, value)
    elif isinstance(response, dict) and 'headers' in response:
        # AWS Lambda/API Gateway style
        if not response['headers']:
            response['headers'] = {}
        response['headers'].update(headers)
        
    return response


# Regular expressions for validating common input patterns
VALIDATION_PATTERNS = {
    'email': re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'),
    'username': re.compile(r'^[a-zA-Z0-9_-]{3,32}$'),
    'phone': re.compile(r'^\+?[0-9]{10,15}$'),
    'url': re.compile(r'^https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+(/[-\w%!$&\'()*+,;=:]+)*(?:\?[-\w%!$&\'()*+,;=:/?]+)?$'),
    'uuid': re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.I),
    'alpha': re.compile(r'^[a-zA-Z]+$'),
    'alphanumeric': re.compile(r'^[a-zA-Z0-9]+$'),
    'integer': re.compile(r'^-?[0-9]+$'),
    'decimal': re.compile(r'^-?[0-9]+(\.[0-9]+)?$'),
    'date': re.compile(r'^\d{4}-\d{2}-\d{2}$'),
    'datetime': re.compile(r'^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?$'),
    'ipv4': re.compile(r'^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$'),
    'ipv6': re.compile(r'^([0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$|^::$|^::1$'),
    'hex': re.compile(r'^[0-9a-fA-F]+$'),
}


def validate_input(value: str, pattern_name: str) -> bool:
    """
    Validate input string against a predefined pattern
    
    Args:
        value: String to validate
        pattern_name: Name of pattern to use (from VALIDATION_PATTERNS)
        
    Returns:
        True if valid, False otherwise
    """
    if pattern_name not in VALIDATION_PATTERNS:
        raise ValueError(f"Unknown validation pattern: {pattern_name}")
        
    if not isinstance(value, str):
        return False
        
    pattern = VALIDATION_PATTERNS[pattern_name]
    return bool(pattern.match(value))


def sanitize_html(html_str: str) -> str:
    """
    Sanitize HTML to prevent XSS attacks
    
    This is a basic implementation. For production use, consider using
    libraries like bleach or html-sanitizer.
    
    Args:
        html_str: HTML string to sanitize
        
    Returns:
        Sanitized HTML string
    """
    # Replace characters that could be used in XSS attacks
    replacements = {
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#x27;',
        '/': '&#x2F;',
        '\\': '&#x5C;',
        '&': '&amp;',
    }
    
    for char, entity in replacements.items():
        html_str = html_str.replace(char, entity)
        
    return html_str


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename to prevent path traversal attacks
    
    Args:
        filename: Filename to sanitize
        
    Returns:
        Sanitized filename
    """
    # Replace potentially dangerous characters
    sanitized = re.sub(r'[^\w\.-]', '_', filename)
    
    # Remove path traversal components
    sanitized = re.sub(r'\.+[/\\]', '', sanitized)
    sanitized = sanitized.lstrip('.')
    
    # Ensure the filename is not empty after sanitization
    if not sanitized:
        sanitized = f"file_{uuid.uuid4().hex[:8]}"
        
    return sanitized


def is_safe_url(url: str, allowed_hosts: Optional[List[str]] = None) -> bool:
    """
    Check if a URL is safe to redirect to
    
    Args:
        url: URL to check
        allowed_hosts: List of allowed hostnames
        
    Returns:
        True if URL is safe, False otherwise
    """
    if not url:
        return False
        
    # Parse the URL
    parsed = urlparse(url)
    
    # Check that the URL is either relative or matches an allowed host
    if not parsed.netloc:
        return True
        
    if allowed_hosts is None:
        return False
        
    return parsed.netloc in allowed_hosts


def escape_sql(value: str) -> str:
    """
    Escape a string for safe use in SQL queries
    
    This is a basic implementation. For production use, always use
    parameterized queries instead of string formatting.
    
    Args:
        value: String to escape
        
    Returns:
        Escaped string
    """
    # Replace single quotes with double quotes and backslashes with double backslashes
    return value.replace("'", "''").replace("\\", "\\\\")


class RateLimiter:
    """Rate limiter to prevent abuse of API endpoints"""
    
    def __init__(self, max_requests: int = 100, time_window: int = 60,
                max_tokens: int = 100, refill_rate: float = 1.0):
        """
        Initialize a rate limiter using the token bucket algorithm
        
        Args:
            max_requests: Maximum requests per time window
            time_window: Time window in seconds
            max_tokens: Maximum tokens in bucket
            refill_rate: Rate at which tokens refill per second
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.max_tokens = max_tokens
        self.refill_rate = refill_rate
        
        # Track requests by IP
        self.request_counts = {}
        self.token_buckets = {}
        self.last_refill_time = {}
        
        # Set of temporarily blocked IPs
        self.blocked_ips = set()
        self.block_duration = 300  # 5 minutes
        self.block_times = {}
        
    def _refill_tokens(self, ip: str) -> None:
        """Refill tokens in the bucket based on elapsed time"""
        now = time.time()
        
        if ip not in self.last_refill_time:
            self.token_buckets[ip] = self.max_tokens
            self.last_refill_time[ip] = now
            return
            
        elapsed = now - self.last_refill_time[ip]
        self.last_refill_time[ip] = now
        
        # Calculate tokens to add
        new_tokens = elapsed * self.refill_rate
        self.token_buckets[ip] = min(self.max_tokens, 
                                    self.token_buckets.get(ip, 0) + new_tokens)
                                    
    def check_rate_limit(self, ip: str) -> bool:
        """
        Check if request from IP is within rate limits
        
        Args:
            ip: IP address of the request
            
        Returns:
            True if request is allowed, False if rate limited
        """
        now = time.time()
        
        # Check if IP is blocked
        if ip in self.blocked_ips:
            block_time = self.block_times.get(ip, 0)
            if now - block_time >= self.block_duration:
                # Unblock IP
                self.blocked_ips.remove(ip)
                self.block_times.pop(ip, None)
            else:
                return False
                
        # Simple rate limiting by count
        if ip not in self.request_counts:
            self.request_counts[ip] = {"count": 0, "start_time": now}
            
        data = self.request_counts[ip]
        
        # Reset counter if time window has passed
        if now - data["start_time"] > self.time_window:
            data["count"] = 0
            data["start_time"] = now
            
        # Check token bucket
        self._refill_tokens(ip)
        if self.token_buckets.get(ip, 0) < 1:
            # No tokens available
            return False
            
        # Increment count and decrement tokens
        data["count"] += 1
        self.token_buckets[ip] = self.token_buckets.get(ip, 0) - 1
        
        # Block IP if repeatedly hitting rate limit
        if data["count"] > self.max_requests * 2:
            self.blocked_ips.add(ip)
            self.block_times[ip] = now
            logger.warning(f"IP {ip} blocked for excessive requests")
            return False
            
        return data["count"] <= self.max_requests
        
    def reset(self, ip: Optional[str] = None) -> None:
        """
        Reset rate limiting for a specific IP or all IPs
        
        Args:
            ip: IP to reset, or None to reset all
        """
        if ip:
            self.request_counts.pop(ip, None)
            self.token_buckets.pop(ip, None)
            self.last_refill_time.pop(ip, None)
            self.blocked_ips.discard(ip)
            self.block_times.pop(ip, None)
        else:
            self.request_counts.clear()
            self.token_buckets.clear()
            self.last_refill_time.clear()
            self.blocked_ips.clear()
            self.block_times.clear()


def generate_secure_token(byte_length: int = 32) -> str:
    """
    Generate a cryptographically secure random token
    
    Args:
        byte_length: Length of token in bytes
        
    Returns:
        Secure token as hexadecimal string
    """
    return secrets.token_hex(byte_length)


def constant_time_compare(val1: str, val2: str) -> bool:
    """
    Compare two strings in constant time to prevent timing attacks
    
    Args:
        val1: First string
        val2: Second string
        
    Returns:
        True if strings are equal, False otherwise
    """
    if len(val1) != len(val2):
        return False
        
    return secrets.compare_digest(val1, val2)


def is_valid_ip(ip: str) -> bool:
    """
    Check if a string is a valid IP address (IPv4 or IPv6)
    
    Args:
        ip: IP address to validate
        
    Returns:
        True if valid IP, False otherwise
    """
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False


def mask_sensitive_data(data: Dict[str, Any], 
                        sensitive_fields: List[str] = None) -> Dict[str, Any]:
    """
    Mask sensitive data in a dictionary for logging
    
    Args:
        data: Dictionary containing data
        sensitive_fields: List of field names to mask
        
    Returns:
        Dictionary with sensitive fields masked
    """
    if sensitive_fields is None:
        sensitive_fields = ["password", "token", "secret", "key", "auth", 
                           "credit_card", "ssn", "social", "security",
                           "access_token", "refresh_token", "authorization"]
                           
    result = {}
    
    for key, value in data.items():
        # Check if this key matches any sensitive field pattern
        is_sensitive = any(
            sensitive in key.lower() for sensitive in sensitive_fields
        )
        
        if is_sensitive:
            # Mask the value but preserve the beginning and end
            if isinstance(value, str) and len(value) > 6:
                result[key] = f"{value[:2]}{'*' * (len(value) - 4)}{value[-2:]}"
            else:
                result[key] = "********"
        elif isinstance(value, dict):
            # Recursively process nested dictionaries
            result[key] = mask_sensitive_data(value, sensitive_fields)
        elif isinstance(value, list) and value and isinstance(value[0], dict):
            # Recursively process lists of dictionaries
            result[key] = [
                mask_sensitive_data(item, sensitive_fields) 
                if isinstance(item, dict) else item
                for item in value
            ]
        else:
            result[key] = value
            
    return result


def setup_https_context(cert_file: str, key_file: str) -> Any:
    """
    Create an HTTPS context with secure settings
    
    Args:
        cert_file: Path to certificate file
        key_file: Path to key file
        
    Returns:
        SSL context object (type varies by implementation)
    """
    try:
        import ssl
        
        context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        context.load_cert_chain(cert_file, key_file)
        
        # Set minimum TLS version
        if hasattr(ssl, 'PROTOCOL_TLS'):
            context.protocol = ssl.PROTOCOL_TLS
        else:
            context.protocol = ssl.PROTOCOL_TLSv1_2
            
        # Explicitly disable older protocols
        context.options |= ssl.OP_NO_SSLv2
        context.options |= ssl.OP_NO_SSLv3
        context.options |= ssl.OP_NO_TLSv1
        context.options |= ssl.OP_NO_TLSv1_1
        
        # Set cipher list
        if TLS_CONFIG['ciphers']:
            context.set_ciphers(':'.join(TLS_CONFIG['ciphers']))
            
        return context
        
    except (ImportError, FileNotFoundError) as e:
        logger.error(f"Error setting up HTTPS context: {e}")
        raise 