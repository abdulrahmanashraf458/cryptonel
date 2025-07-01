"""
Security System - Handles all security-related configurations for the application
Including CSP, Talisman, and other security headers
"""

import os
import hashlib
import base64
import logging
import re
from flask import Flask, request, abort, jsonify, session
from flask_talisman import Talisman
from flask_wtf.csrf import CSRFProtect
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv

# إعداد السجلات
logger = logging.getLogger('cryptonel')
security_logger = logging.getLogger('cryptonel.security')

# استيراد وتحميل المتغيرات البيئية باستخدام المكتبة الآمنة
try:
    from backend.utils.env_loader import load_secure_env_file
    env_loaded = load_secure_env_file('clyne.env')
    if env_loaded:
        logger.info("Security settings loaded successfully from secure location")
    else:
        logger.warning("Failed to load security environment settings using secure loader")
except ImportError:
    logger.warning("Environment loader module not found, using direct loading")
    # تحميل المتغيرات البيئية من المسار الآمن الجديد
    secure_dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'secure_config', 'clyne.env')
    if os.path.exists(secure_dotenv_path):
        load_dotenv(secure_dotenv_path)
        logger.info(f"Security settings loaded from secure location")
    else:
        # محاولة التحميل من الموقع القديم كاحتياطي
        legacy_dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'clyne.env')
        if os.path.exists(legacy_dotenv_path):
            load_dotenv(legacy_dotenv_path)
            logger.warning(f"Using legacy environment file location for security settings. Please move to secure location.")

def get_script_hash(script_content: str) -> str:
    """
    Generate a CSP hash for inline script content
    
    Args:
        script_content: The content of the script
        
    Returns:
        str: Base64-encoded SHA-256 hash for CSP
    """
    script_hash = hashlib.sha256(script_content.encode('utf-8')).digest()
    return f"'sha256-{base64.b64encode(script_hash).decode('utf-8')}'"


def get_csp_config(env: str = 'production') -> Dict[str, List[str]]:
    """
    Get Content Security Policy configuration based on environment
    
    Args:
        env: Environment (development/production)
        
    Returns:
        Dict[str, List[str]]: CSP configuration
    """
    # Base CSP for all environments
    csp = {
        'default-src': ["'self'"],
        # Use hash instead of unsafe-inline when possible
        'script-src': [
            "'self'", 
            # Common CDNs for framework scripts
            'https://cdn.jsdelivr.net',
            'https://cdnjs.cloudflare.com'
        ],
        'style-src': [
            "'self'",
            # Allow inline styles (ideally, these should be removed in production)
            "'unsafe-inline'",
            # Common CDNs for CSS frameworks
            'https://cdn.jsdelivr.net',
            'https://fonts.googleapis.com'
        ],
        'img-src': [
            "'self'", 
            'data:',
            'https://cdn.discordapp.com',
            'https://cdn.jsdelivr.net'
        ],
        'font-src': [
            "'self'",
            'https://fonts.gstatic.com',
            'https://cdn.jsdelivr.net'
        ],
        'connect-src': ["'self'"],
        'frame-src': ["'self'"],
        'object-src': ["'none'"],
        'base-uri': ["'self'"],
        'form-action': ["'self'"],
        'frame-ancestors': ["'none'"],
        'upgrade-insecure-requests': []
    }
    
    # Add development-specific rules if needed
    if env == 'development':
        # Allow more relaxed rules in development mode
        csp['script-src'].append("'unsafe-eval'")  # For debugging/development tools
        csp['connect-src'].append('ws://*')  # For WebSocket connections in dev
        csp['connect-src'].append('wss://*')  # For secure WebSocket connections in dev
    
    return csp


def configure_security(app: Flask) -> Flask:
    """
    Configure security settings for the application
    
    Args:
        app: Flask application
        
    Returns:
        Flask: Configured Flask application
    """
    # قراءة الإعدادات من ملف البيئة
    csrf_enabled = os.environ.get('CSRF_ENABLED', 'true').lower() in ('true', '1', 't')
    csrf_time_limit = int(os.environ.get('CSRF_TIME_LIMIT', '3600'))
    csrf_ssl_strict = os.environ.get('CSRF_SSL_STRICT', 'true').lower() in ('true', '1', 't')
    session_timeout = int(os.environ.get('SESSION_TIMEOUT', '86400'))
    force_https = os.environ.get('FORCE_HTTPS', 'true').lower() in ('true', '1', 't')
    
    # Configure the secret key
    app.secret_key = os.environ.get('SECRET_KEY', os.urandom(32))
    
    # Configure security-related settings
    app.config.update({
        'SESSION_COOKIE_SECURE': True,
        'SESSION_COOKIE_HTTPONLY': True,
        'SESSION_COOKIE_SAMESITE': 'Lax',
        'PERMANENT_SESSION_LIFETIME': session_timeout,  # session timeout from env file
        'WTF_CSRF_ENABLED': csrf_enabled,  # Read from environment
        'WTF_CSRF_TIME_LIMIT': csrf_time_limit,  # Read from environment
        'WTF_CSRF_SSL_STRICT': csrf_ssl_strict,  # Read from environment
    })
    
    # Apply CSRF protection
    csrf = CSRFProtect()
    csrf.init_app(app)
    
    # Determine environment for CSP configuration
    env = 'development' if os.environ.get('FLASK_DEBUG', 'False').lower() in ('true', '1', 't') else 'production'
    
    # Get CSP configuration
    csp = get_csp_config(env)
    
    # Enable TLS settings
    ssl_settings = {
        'enabled': force_https,
        'redirect': True,
        'preload': True,
        'max_age': 31536000,  # 1 year
        'include_subdomains': True
    }
    
    # Define stricter referrer policy
    referrer_policy = 'strict-origin-when-cross-origin'
    
    # Enable security headers with Talisman
    talisman = Talisman(
        app,
        content_security_policy=csp,
        content_security_policy_nonce_in=['script-src'],
        force_https=ssl_settings['enabled'],
        force_https_permanent=ssl_settings['redirect'],
        strict_transport_security=True,
        strict_transport_security_preload=ssl_settings['preload'],
        strict_transport_security_max_age=ssl_settings['max_age'],
        strict_transport_security_include_subdomains=ssl_settings['include_subdomains'],
        session_cookie_secure=True,
        session_cookie_http_only=True,
        referrer_policy=referrer_policy,
        feature_policy={
            'geolocation': "'none'",
            'microphone': "'none'",
            'camera': "'none'",
            'payment': "'none'",
            'usb': "'none'",
            'fullscreen': "'self'",
            'display-capture': "'self'"
        }
    )
    
    # Log security configuration
    logger.info(f"Security configured: HTTPS {'enabled' if ssl_settings['enabled'] else 'disabled'}")
    logger.info(f"Content Security Policy: {len(csp)} directives configured")
    logger.info(f"CSRF Protection: {'enabled' if csrf_enabled else 'disabled'}")
    
    return app


def secure_static_files_access(path: str) -> bool:
    """
    Check if a file path is allowed to be accessed
    Using whitelist approach and multiple security checks
    
    Args:
        path: Path to check
        
    Returns:
        bool: True if access is allowed, False otherwise
    """
    # Log the path for debugging
    security_logger.debug(f"Checking secure access for path: {path}")
    
  
    sensitive_env_files = ['clyne.env', 'ip.env', '.env', 'config.env', 'secrets.env', 
                          'database.env', 'api.env', 'credentials.env', 'jwt.env']
    
    # Check if the path contains any sensitive env file
    for env_file in sensitive_env_files:
        if env_file in path.lower():
            security_logger.warning(f"Blocked access to sensitive env file: {path}")
            return False
    
   
    sensitive_folders = ['secure_config', '.git', 'node_modules', 'venv', 'backend/cryptonel/mining/security',
                        'backend/system', 'backend/utils', 'memory_manager', 'ddos_protection']
    
    # Check if the path contains any sensitive folder
    for folder in sensitive_folders:
        if folder in path:
            security_logger.warning(f"Blocked access to sensitive folder: {path}")
            return False
    
    
    dangerous_extensions = ['.py', '.pyc', '.sh', '.bat', '.exe', '.php', '.env', '.ini', '.conf', '.config',
                           '.db', '.sqlite', '.sqlite3', '.sql', '.log', '.passwd', '.htaccess', '.htpasswd']
    
    # Check file extension
    _, ext = os.path.splitext(path)
    if ext.lower() in dangerous_extensions:
        security_logger.warning(f"Blocked access to dangerous file type: {path}")
        return False
    
    # Define allowed file extensions (whitelist approach)
    allowed_extensions = {
        # Web essentials
        '.html', '.css', '.js', '.json', 
        # Images
        '.jpg', '.jpeg', '.png', '.gif', '.svg', '.ico', '.webp',
        # Fonts
        '.woff', '.woff2', '.ttf', '.eot', '.otf',
        # Documents
        '.pdf',
        # Media
        '.mp3', '.mp4', '.webm'
    }
    
    # Allow common routes for SPA frontend
    allowed_routes = {
        '', 'login', 'signup', 'dashboard', 'overview', 'mining', 'dashboardselect',
        'wallet', 'transfers', 'transfer', 'history', 'leaderboard', 'callback'
    }
    
    # Block paths that contain semicolons used for path traversal or command injection
    if ';' in path:
        security_logger.warning(f"Blocked path with semicolon: {path}")
        return False
    
    # Block paths that contain suspicious characters or patterns
    suspicious_chars = ['\\', '&', '|', '`', '$', '#', '*', '>', '<', ':', '?', '"', "'"]
    if any(char in path for char in suspicious_chars):
        security_logger.warning(f"Blocked path with suspicious characters: {path}")
        return False
    
    # منع محاولات الخروج من المجلد الحالي (path traversal)
    if '..' in path or '%2e%2e' in path.lower() or '%252e' in path.lower():
        security_logger.warning(f"Blocked path traversal attempt: {path}")
        return False
    
    # Check if it's a known frontend route
    if path in allowed_routes:
        return True
    
    # Check if it's a nested route of an allowed route (like wallet/settings)
    for route in allowed_routes:
        if route and path.startswith(f"{route}/"):
            return True
        
    # Block if no extension or not allowed
    if not path or '.' not in path:
        return False
        
    # Get file extension
    extension = '.' + path.split('.')[-1].lower()
    if extension not in allowed_extensions:
        security_logger.warning(f"Blocked file with disallowed extension: {extension}")
        return False
    
    # Block path traversal attempts
    if '..' in path or '/.' in path:
        security_logger.warning(f"Blocked path traversal attempt: {path}")
        return False
    
    # Block sensitive paths with expanded patterns
    sensitive_patterns = (
        'node_modules', 'backend', '.git', '.env', 'env', 
        'config', 'secrets', 'logs', '.htaccess',
        'actuator', 'swagger', 'api-docs', 'management',
        'admin', 'phpmyadmin', 'mysql', 'db', 'database',
        'wp-admin', 'wp-content', 'wp-includes',
        'phpinfo', 'shell', 'cmd', 'console', 'jenkins'
    )
    
    if any(pattern in path.lower() for pattern in sensitive_patterns):
        security_logger.warning(f"Blocked access to sensitive path: {path}")
        return False
    
    return True


def validate_input(data: Dict[str, Any], schema: Dict[str, Any]) -> Optional[Dict[str, str]]:
    """
    Validate input data against a schema
    
    Args:
        data: Input data to validate
        schema: Validation schema with field types and requirements
        
    Returns:
        Optional[Dict[str, str]]: Dictionary of errors or None if valid
    """
    errors = {}
    
    for field, requirements in schema.items():
        # Check required fields
        if requirements.get('required', False) and (field not in data or data[field] is None):
            errors[field] = 'This field is required'
            continue
            
        # Skip validation for missing optional fields
        if field not in data or data[field] is None:
            continue
            
        value = data[field]
        field_type = requirements.get('type')
        
        # Type validation
        if field_type == 'string' and not isinstance(value, str):
            errors[field] = 'Must be a string'
        elif field_type == 'integer' and not (isinstance(value, int) or (isinstance(value, str) and value.isdigit())):
            errors[field] = 'Must be an integer'
        elif field_type == 'float' and not (isinstance(value, (int, float)) or (isinstance(value, str) and value.replace('.', '', 1).isdigit())):
            errors[field] = 'Must be a number'
        elif field_type == 'boolean' and not isinstance(value, bool) and value not in ('true', 'false', '0', '1'):
            errors[field] = 'Must be a boolean'
        elif field_type == 'email' and not validate_email(value):
            errors[field] = 'Must be a valid email address'
            
        # Length validation for strings
        if isinstance(value, str):
            min_length = requirements.get('min_length')
            max_length = requirements.get('max_length')
            
            if min_length is not None and len(value) < min_length:
                errors[field] = f'Must be at least {min_length} characters'
            if max_length is not None and len(value) > max_length:
                errors[field] = f'Must be no more than {max_length} characters'
                
        # Range validation for numbers
        if isinstance(value, (int, float)) or (isinstance(value, str) and value.replace('.', '', 1).isdigit()):
            num_value = float(value)
            minimum = requirements.get('minimum')
            maximum = requirements.get('maximum')
            
            if minimum is not None and num_value < minimum:
                errors[field] = f'Must be at least {minimum}'
            if maximum is not None and num_value > maximum:
                errors[field] = f'Must be no more than {maximum}'
                
        # Regex pattern validation
        pattern = requirements.get('pattern')
        if pattern and isinstance(value, str):
            if not re.match(pattern, value):
                errors[field] = requirements.get('pattern_error', 'Invalid format')
                
    return errors if errors else None


def validate_email(email: str) -> bool:
    """
    Validate an email address format
    
    Args:
        email: Email address to validate
        
    Returns:
        bool: True if email is valid, False otherwise
    """
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email)) 