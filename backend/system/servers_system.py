"""
Servers System - Manages production WSGI servers (Waitress, Gunicorn)
Provides optimized server configurations for production environments
"""

import os
import sys
import logging
import multiprocessing
from typing import Dict, Any, Optional, Callable
from flask import Flask

# Get logger
logger = logging.getLogger('cryptonel')


def get_production_server(app: Flask, port: int) -> Optional[Callable]:
    """
    Get the appropriate production server (Waitress or Gunicorn)
    
    Args:
        app: Flask application instance
        port: Port to run the server on
        
    Returns:
        Optional[Callable]: Function to run the server or None if no server is available
    """
    # Try Waitress first
    waitress_server = _configure_waitress(app, port)
    if waitress_server:
        return waitress_server
    
    # Try Gunicorn next
    gunicorn_server = _configure_gunicorn(app, port)
    if gunicorn_server:
        return gunicorn_server
    
    # No production server available
    logger.warning("No production WSGI server (Waitress or Gunicorn) is available.")
    return None


def _configure_waitress(app: Flask, port: int) -> Optional[Callable]:
    """
    Configure Waitress server if available
    
    Args:
        app: Flask application instance
        port: Port to run the server on
        
    Returns:
        Optional[Callable]: Function to run Waitress or None if not available
    """
    try:
        from waitress import serve
        
        # Calculate optimal number of threads
        threads = min(max(multiprocessing.cpu_count() * 2, 4), 12)
        
        # Configure waitress options
        waitress_options = {
            'host': '0.0.0.0',
            'port': port,
            'threads': threads,
            'connection_limit': 1000,
            'channel_timeout': 30,
            'ident': 'Cryptonel Wallet (Waitress)'
        }
        
        def start_waitress():
            """Start Waitress server with configured options"""
            logger.info(f"Starting Waitress production server on port {port} with {threads} threads")
            serve(app, **waitress_options)
        
        return start_waitress
    
    except ImportError:
        logger.debug("Waitress not available, trying Gunicorn")
        return None


def _configure_gunicorn(app: Flask, port: int) -> Optional[Callable]:
    """
    Configure Gunicorn server if available
    
    Args:
        app: Flask application instance
        port: Port to run the server on
        
    Returns:
        Optional[Callable]: Function to run Gunicorn or None if not available
    """
    # Only attempt to use Gunicorn on Unix-based systems
    if sys.platform == "win32":
        logger.debug("Gunicorn not available on Windows")
        return None
    
    try:
        from gunicorn.app.base import BaseApplication
        
        # Define Gunicorn application class
        class GunicornApp(BaseApplication):
            """Gunicorn application wrapper for Flask"""
            
            def __init__(self, app, options=None):
                self.options = options or {}
                self.application = app
                super().__init__()
                
            def load_config(self):
                """Load Gunicorn configuration"""
                for key, value in self.options.items():
                    self.cfg.set(key, value)
                    
            def load(self):
                """Load the WSGI application"""
                return self.application
        
        # Calculate optimal number of workers
        workers = min(max(multiprocessing.cpu_count() * 2 + 1, 3), 12)
        
        # Configure Gunicorn options
        gunicorn_options = {
            'bind': f'0.0.0.0:{port}',
            'workers': workers,
            'worker_class': 'gevent',
            'worker_connections': 1000,
            'timeout': 30,
            'keepalive': 2,
            'graceful_timeout': 10,
            'max_requests': 1000,
            'max_requests_jitter': 50,
            'accesslog': os.path.join('logs', 'access.log'),
            'errorlog': os.path.join('logs', 'error.log'),
            'proc_name': 'cryptonel_wallet',
            'loglevel': 'info'
        }
        
        def start_gunicorn():
            """Start Gunicorn server with configured options"""
            # Ensure logs directory exists
            os.makedirs('logs', exist_ok=True)
            logger.info(f"Starting Gunicorn production server on port {port} with {workers} workers")
            GunicornApp(app, gunicorn_options).run()
        
        return start_gunicorn
    
    except ImportError:
        logger.debug("Gunicorn not available")
        return None


def get_server_settings() -> Dict[str, Any]:
    """
    Get server settings from environment variables
    
    Returns:
        Dict[str, Any]: Dictionary of server settings
    """
    return {
        'port': int(os.environ.get('PORT', 5000)),
        'host': os.environ.get('HOST', '0.0.0.0'),
        'debug': os.environ.get('FLASK_DEBUG', 'False').lower() in ('true', '1', 't'),
        'production': os.environ.get('PRODUCTION', 'False').lower() in ('true', '1', 't'),
        'workers': int(os.environ.get('WORKERS', multiprocessing.cpu_count() * 2 + 1)),
        'threads': int(os.environ.get('THREADS', multiprocessing.cpu_count() * 2))
    } 