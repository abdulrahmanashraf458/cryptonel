"""
Logging System - Configures and manages all application logging
Provides separate loggers for different application components with rotation and external integrations
"""

import os
import logging
import sys
import json
import socket
import codecs
from logging.handlers import RotatingFileHandler, SocketHandler
from typing import Dict, Any
import platform


class Utf8RotatingFileHandler(RotatingFileHandler):
    """Enhanced rotating file handler with UTF-8 support and automatic rotation"""
    
    def __init__(self, filename, mode='a', maxBytes=0, backupCount=0, encoding='utf-8', delay=False):
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        super().__init__(filename, mode, maxBytes, backupCount, encoding, delay)

    def emit(self, record):
        try:
            # Check if log rotation is needed
            if self.shouldRollover(record):
                self.doRollover()
                
            msg = self.format(record)
            stream = self.stream
            stream.write(msg + self.terminator)
            self.flush()
        except Exception:
            self.handleError(record)


class WindowsConsoleHandler(logging.StreamHandler):
    """Custom console handler for Windows that handles Unicode properly"""
    
    def __init__(self):
        if sys.platform == 'win32':
            # Fix encoding for Windows console
            try:
                import ctypes
                kernel32 = ctypes.windll.kernel32
                kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
            except Exception:
                pass
            
            # Use utf-8 for stdout
            if sys.stdout.encoding != 'utf-8':
                sys.stdout.reconfigure(encoding='utf-8')
                
        super().__init__(sys.stdout)

    def emit(self, record):
        try:
            msg = self.format(record)
            # Replace emojis with text equivalents on Windows if needed
            if sys.platform == 'win32':
                # Map common emojis to text equivalents
                emoji_map = {
                    '🔧': '[WRENCH]',
                    '📦': '[PACKAGE]',
                    '✅': '[CHECK]',
                    '❌': '[X]',
                    '⚠️': '[WARNING]',
                    '🚀': '[ROCKET]'
                }
                for emoji, text in emoji_map.items():
                    msg = msg.replace(emoji, text)
                    
            self.stream.write(msg + self.terminator)
            self.flush()
        except Exception:
            self.handleError(record)


class JsonFormatter(logging.Formatter):
    """JSON formatter for structured logging and ELK integration"""
    
    def __init__(self, include_hostname=True):
        super().__init__()
        self.include_hostname = include_hostname
        self.hostname = socket.gethostname() if include_hostname else None
        
    def format(self, record):
        log_data = {
            'timestamp': self.formatTime(record, '%Y-%m-%dT%H:%M:%S.%fZ'),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'line': record.lineno
        }
        
        if self.include_hostname:
            log_data['hostname'] = self.hostname
            
        if hasattr(record, 'user_id'):
            log_data['user_id'] = record.user_id
            
        if hasattr(record, 'ip_address'):
            log_data['ip_address'] = record.ip_address
            
        if hasattr(record, 'path'):
            log_data['path'] = record.path
            
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
            
        return json.dumps(log_data)


class ElkHandler(SocketHandler):
    """Handler for sending logs to ELK stack"""
    
    def __init__(self, host, port):
        super().__init__(host, port)
        self.formatter = JsonFormatter()
        
    def emit(self, record):
        try:
            msg = self.format(record)
            self.send(msg.encode('utf-8'))
        except Exception:
            self.handleError(record)


def get_log_level(env_level=None):
    """
    Get appropriate log level based on environment
    
    Args:
        env_level: Environment variable override for log level
        
    Returns:
        int: Logging level
    """
    if env_level:
        level_mapping = {
            'debug': logging.DEBUG,
            'info': logging.INFO,
            'warning': logging.WARNING,
            'error': logging.ERROR,
            'critical': logging.CRITICAL
        }
        return level_mapping.get(env_level.lower(), logging.INFO)
    
    # Default to DEBUG in development, INFO in production
    if os.environ.get('FLASK_DEBUG', 'False').lower() in ('true', '1', 't'):
        return logging.DEBUG
    return logging.INFO


def configure_logging() -> Dict[str, Any]:
    """
    Configure the logging system for the application
    
    Returns:
        dict: Dictionary of configured loggers
    """
    # Create logs directory if it doesn't exist
    logs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs')
    os.makedirs(logs_dir, exist_ok=True)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Configure formatter - we'll make it Unicode-safe on Windows
    is_windows = platform.system() == 'Windows'
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Fix for Windows console encoding issues
    if is_windows:
        # Configure console handler with Unicode support
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(logging.Formatter(log_format))
        
        # Replace any existing console handlers
        for handler in root_logger.handlers[:]:
            if isinstance(handler, logging.StreamHandler) and handler.stream in [sys.stdout, sys.stderr]:
                root_logger.removeHandler(handler)
        
        root_logger.addHandler(console_handler)
        
        # Set UTF-8 encoding for the console
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    
    # Configure file handler
    file_handler = logging.FileHandler(os.path.join(logs_dir, 'app.log'), encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter(log_format))
    root_logger.addHandler(file_handler)
    
    # Configure security logger
    security_logger = logging.getLogger('security')
    security_logger.setLevel(logging.INFO)
    security_file_handler = logging.FileHandler(os.path.join(logs_dir, 'security.log'), encoding='utf-8')
    security_file_handler.setFormatter(logging.Formatter(log_format))
    security_logger.addHandler(security_file_handler)
    
    # Configure main application logger
    main_logger = logging.getLogger('cryptonel')
    main_logger.setLevel(logging.INFO)
    
    # Log configuration info
    main_logger.info("Logging initialized with level: %s", logging.getLevelName(main_logger.level))
    main_logger.info("Log directory: %s", logs_dir)
    main_logger.info("JSON logging: Disabled")
    main_logger.info("ELK integration: Disabled")
    
    # Return configured loggers
    return {
        'main': main_logger,
        'security': security_logger
    }


def log_security_event(event_type: str, ip_address: str, path: str, details: str = None, user_id: str = None) -> None:
    """
    Log a security-related event with enhanced context
    
    Args:
        event_type: Type of security event (e.g., 'access_denied', 'path_traversal')
        ip_address: IP address making the request
        path: Path accessed
        details: Additional details about the event
        user_id: Optional user ID for authenticated users
    """
    security_logger = logging.getLogger('security')
    
    # Create a log record with extra fields
    extra = {
        'ip_address': ip_address,
        'path': path
    }
    
    if user_id:
        extra['user_id'] = user_id
    
    # Format the message
    message = f"{event_type} - IP: {ip_address} - Path: {path}"
    if details:
        message += f" - Details: {details}"
    if user_id:
        message += f" - User: {user_id}"
        
    # Log with extra context
    security_logger.warning(message, extra=extra)


def log_request(method: str, path: str, status_code: int, response_time: float, 
                ip_address: str, user_agent: str = None, user_id: str = None) -> None:
    """
    Log an HTTP request with performance metrics
    
    Args:
        method: HTTP method (GET, POST, etc.)
        path: Request path
        status_code: HTTP status code
        response_time: Response time in milliseconds
        ip_address: Client IP address
        user_agent: Client User-Agent
        user_id: Optional user ID for authenticated users
    """
    access_logger = logging.getLogger('access')
    
    # Create a log record with extra fields
    extra = {
        'method': method,
        'path': path,
        'status_code': status_code,
        'response_time': response_time,
        'ip_address': ip_address
    }
    
    if user_id:
        extra['user_id'] = user_id
    
    if user_agent:
        extra['user_agent'] = user_agent
    
    # Format the message
    message = f"{method} {path} {status_code} {response_time:.2f}ms - {ip_address}"
    if user_id:
        message += f" - User: {user_id}"
        
    # Use appropriate log level based on status code
    if status_code >= 500:
        access_logger.error(message, extra=extra)
    elif status_code >= 400:
        access_logger.warning(message, extra=extra)
    else:
        access_logger.info(message, extra=extra) 