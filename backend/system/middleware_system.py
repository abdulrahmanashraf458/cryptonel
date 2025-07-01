"""
Middleware System - Manages application middleware components
Including compression, proxy fixes, and other performance enhancements
"""

from flask import Flask, Response
from flask_compress import Compress
from werkzeug.middleware.proxy_fix import ProxyFix


def configure_middleware(app: Flask) -> Flask:
    """
    Configure all middleware for the application
    
    Args:
        app: Flask application instance
        
    Returns:
        Flask: The configured Flask application
    """
    # Apply proxy fix for reverse proxies
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
    
    # Enable HTTP compression
    compress = Compress()
    compress.init_app(app)
    
    # Performance-related configuration
    app.config.update({
        'JSON_SORT_KEYS': False,  # Better performance for JSON responses
        'MAX_CONTENT_LENGTH': 10 * 1024 * 1024,  # 10MB max upload size
    })
    
    return app


def add_cache_headers(response: Response, path: str) -> Response:
    """
    Add appropriate cache headers to a response based on file type
    
    Args:
        response: Flask response object
        path: Path to the file being served
        
    Returns:
        Response: Modified response with cache headers
    """
    # Long-term caching for static assets
    if path.endswith(('.js', '.css')):
        response.headers['Cache-Control'] = 'public, max-age=31536000'  # Cache for a year
        response.headers['Vary'] = 'Accept-Encoding'
    elif path.endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', '.woff', '.woff2')):
        response.headers['Cache-Control'] = 'public, max-age=31536000'  # Cache for a year
        response.headers['Vary'] = 'Accept-Encoding'
    else:
        # Short-term caching for other content
        response.headers['Cache-Control'] = 'public, max-age=0'
    
    # Add ETag for efficient caching - but only if response is not in direct passthrough mode
    try:
        # Only add ETag if the response is not in direct passthrough mode
        response.add_etag()
    except RuntimeError:
        # Skip adding ETag if response is in direct passthrough mode
        pass
    
    return response 