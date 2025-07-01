#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Cryptonel - Main Server
-----------------------
تطبيق Flask الرئيسي لموقع Clyne الإلكتروني
"""

import os
import subprocess
import sys
import traceback
import importlib.util
import time
import signal
import threading
import atexit
from flask import Flask, send_from_directory, make_response, abort, request, jsonify, redirect, url_for, session, g, render_template
from flask_login import current_user
from werkzeug.middleware.proxy_fix import ProxyFix
from dotenv import load_dotenv
import datetime
import logging
import asyncio
import secrets
import pathlib
import shutil
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import random

# Simplified Redis initialization - Cloudflare doesn't need local Redis
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    print("Redis package not available, skipping Redis initialization")
    
# Set flag directly since we don't need the redis_manager anymore
REDIS_MANAGER_AVAILABLE = False

# Suppress the annoying asyncio IocpProactor error message in Windows
# This will prevent the "Task was destroyed but it is pending" error
if sys.platform.startswith('win'):
    # Create a filter to completely silence these errors
    class IocpProactorErrorFilter(logging.Filter):
        def filter(self, record):
            return not (
                'Task was destroyed but it is pending' in record.getMessage() and
                'IocpProactor.accept' in record.getMessage()
            )
    
    # Apply the filter to the asyncio logger
    asyncio_logger = logging.getLogger('asyncio')
    asyncio_logger.addFilter(IocpProactorErrorFilter())
    
    # Also silence the StreamServer close warning
    logging.getLogger("asyncio").setLevel(logging.ERROR)

# إعداد البيئة الآمنة ونقل الملفات تلقائيًا
try:
    from backend.utils import startup_utils, env_loader
    
    # تنفيذ إعداد البيئة الآمنة (ينشئ المجلدات وينقل الملفات تلقائيًا)
    setup_success = startup_utils.setup_secure_environment()
    
    # تحميل ملفات البيئة
    env_loaded = env_loader.load_secure_env_file('clyne.env')
    ip_env_loaded = env_loader.load_secure_env_file('ip.env')
    
    if env_loaded:
        print("✅ Environment settings loaded successfully from secure location.")
    else:
        print("⚠️ Failed to load environment settings!")
        
    if ip_env_loaded:
        print("✅ IP environment settings loaded successfully.")
except ImportError:
    print("⚠️ Environment management modules not found, using direct loading method...")
    secure_dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'secure_config', 'clyne.env')
    if os.path.exists(secure_dotenv_path):
        load_dotenv(secure_dotenv_path)
        print(f"Environment settings loaded from secure location: {secure_dotenv_path}")
    else:
        legacy_dotenv_path = os.path.join(os.path.dirname(__file__), 'clyne.env')
        if os.path.exists(legacy_dotenv_path):
            load_dotenv(legacy_dotenv_path)
            print(f"Warning: Using legacy environment file location: {legacy_dotenv_path}")
        else:
            print(f"Error: Settings file not found in secure or legacy locations")

# Determine environment
ENVIRONMENT = os.environ.get('FLASK_ENV', 'development')

# Import configuration
from backend.config import config_by_name

# Add JWT utilities for authentication restoration
from backend.jwt_utils import decode_token, refresh_access_token

# تهيئة Redis قبل بدء النظام - تم تبسيط الكود
if REDIS_AVAILABLE:
    print("Redis package available, but using simplified configuration")
    # Set basic Redis configuration for Cloudflare integration if needed
    os.environ['REDIS_HOST'] = os.environ.get('REDIS_HOST', 'localhost')
    os.environ['REDIS_PORT'] = os.environ.get('REDIS_PORT', '6379')
    os.environ['REDIS_DB'] = os.environ.get('REDIS_DB', '0')
    os.environ['REDIS_PASSWORD'] = os.environ.get('REDIS_PASSWORD', '')
else:
    print("⚠️ Redis unavailable. Using direct Cloudflare API calls.")

# Check for essential environment variables
for var in ['REDIS_PASSWORD', 'SECRET_KEY']:
    if not os.environ.get(var) and not hasattr(config_by_name[ENVIRONMENT], var):
        print(f"Warning: Missing important environment variable: {var}")

# Import memory manager
from memory_manager.manager import MemoryManager
from memory_manager.config import MemoryManagerConfig

# Define init_manager function locally to avoid import issues
def init_manager(app=None, config=None):
    """Initialize memory manager with application instance and config"""
    memory_manager = MemoryManager(app=app, config=config)
    return memory_manager

# Import system modules
from backend.system import logging_system
from backend.system import security_system
from backend.system import middleware_system
from backend.system import rate_limiting_system
from backend.system import error_handlers_system
from backend.system import build_system
from backend.system import servers_system

# Configurar modo de desarrollo de Cloudflare ANTES de importar los módulos
os.environ['CF_DEV_MODE'] = 'true'
os.environ['USE_CLOUDFLARE_EXCLUSIVELY'] = 'true'
print("[MODO DEV] Sistema en modo de simulación - sin API real")

# Import utility modules
from backend.utils import json_utils
from backend.utils import validation_utils 
from backend.utils import security_utils
from backend.utils import cache_utils
from backend.api import response_handler

# Check for APScheduler availability - needed for cleanup tasks
try:
    import apscheduler
    from apscheduler.schedulers.background import BackgroundScheduler
    APSCHEDULER_AVAILABLE = True
except ImportError:
    APSCHEDULER_AVAILABLE = False
    print("APScheduler not available, some scheduled tasks will be disabled")

# Import DDoS Protection System
try:
    from ddos_protection import load_config, DDoSProtectionSystem
    DDOS_PROTECTION_AVAILABLE = True
except ImportError:
    DDOS_PROTECTION_AVAILABLE = False
    print("DDoS Protection System not available, skipping initialization")

# Import Cloudflare integration
try:
    from ddos_protection.network.cloudflare import init_cloudflare_integration, cf_client, CLOUDFLARE_ENABLED
    CLOUDFLARE_INTEGRATION_AVAILABLE = True
    print(f"Cloudflare integration module found. Enabled: {CLOUDFLARE_ENABLED}")
except ImportError as e:
    CLOUDFLARE_INTEGRATION_AVAILABLE = False
    init_cloudflare_integration = None
    cf_client = None
    CLOUDFLARE_ENABLED = False
    print(f"Cloudflare integration module not available: {str(e)}")
except Exception as e:
    CLOUDFLARE_INTEGRATION_AVAILABLE = False
    init_cloudflare_integration = None
    cf_client = None
    CLOUDFLARE_ENABLED = False
    print(f"Error loading Cloudflare integration module: {str(e)}")

# Import utility for IP extraction
from ddos_protection.utils.utils import get_client_ip_from_request

# Configure logging
loggers = logging_system.configure_logging()
logger = loggers['main']
security_logger = loggers['security']

# Prevent duplicate logs for memory_manager
memory_logger = logging.getLogger("memory_manager")
memory_logger.propagate = False

# Initialize cache
cache_available = cache_utils.init_redis_cache()
if cache_available:
    logger.info("Redis cache initialized successfully")
else:
    # Redis not available - this is OK, we'll use in-memory fallbacks
    # To enable Redis, ensure it's installed and running on the configured host/port
    logger.warning("Redis cache not available, using in-memory fallbacks")

# Log initialization of utility modules
logger.info("JSON utilities initialized using: " + json_utils.dumps({"implementation": json_utils.HAS_ORJSON and "orjson" or (json_utils.HAS_UJSON and "ujson" or "json")}))
logger.info("Validation utilities initialized with schema support: " + str(validation_utils.HAS_JSONSCHEMA))
logger.info("Security utilities initialized")
logger.info("API response handler initialized")

# Check if running behind Nginx
def is_behind_proxy():
    """Check if application is running behind a proxy like Nginx"""
    # استخدم قيمة ثابتة أو قيمة من ملف الإعدادات بدلاً من request
    # لأننا نستدعي هذه الوظيفة خارج سياق الطلب
    if ENVIRONMENT == 'production':
        # في الإنتاج، نفترض دائمًا أننا خلف بروكسي
        return True
    
    # تحقق من متغيرات البيئة التي قد تشير إلى وجود بروكسي
    use_proxy = os.environ.get('USE_PROXY', 'false').lower() == 'true'
    
    return use_proxy

logger.info("Checking for reverse proxy environment...")

# Helper function to import modules
def import_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

# Import modules using helper function
auth = import_module("auth", os.path.join(os.path.dirname(__file__), "backend", "auth.py"))
login = import_module("login", os.path.join(os.path.dirname(__file__), "backend", "login.py"))
signup = import_module("signup", os.path.join(os.path.dirname(__file__), "backend", "signup.py"))
password_reset = import_module("password_reset", os.path.join(os.path.dirname(__file__), "backend", "password_reset.py"))
overview = import_module("overview", os.path.join(os.path.dirname(__file__), "backend", "cryptonel", "overview.py"))
transfers = import_module("transfers", os.path.join(os.path.dirname(__file__), "backend", "cryptonel", "transfers.py"))
email_sender = import_module("email_sender", os.path.join(os.path.dirname(__file__), "backend", "cryptonel", "email_sender.py"))
backup = import_module("backup", os.path.join(os.path.dirname(__file__), "backend", "cryptonel", "backup.py"))
security = import_module("security", os.path.join(os.path.dirname(__file__), "backend", "cryptonel", "security.py"))
mining = import_module("mining", os.path.join(os.path.dirname(__file__), "backend", "cryptonel", "mining", "mining.py"))
mining_security = import_module("mining_security", os.path.join(os.path.dirname(__file__), "backend", "cryptonel", "mining", "mining_security.py"))
privacy = import_module("privacy", os.path.join(os.path.dirname(__file__), "backend", "cryptonel", "privacy.py"))
transaction_history = import_module("transaction_history", os.path.join(os.path.dirname(__file__), "backend", "cryptonel", "transaction_history.py"))
leaderboard = import_module("leaderboard", os.path.join(os.path.dirname(__file__), "backend", "cryptonel", "leaderboard.py"))
session_devices = import_module("session_devices", os.path.join(os.path.dirname(__file__), "backend", "cryptonel", "session_devices.py"))
network_transactions = import_module("network_transactions", os.path.join(os.path.dirname(__file__), "backend", "cryptonel", "network_transactions", "__init__.py"))
# Import new server trading module
server_trade_crn = import_module("server_trade_crn", os.path.join(os.path.dirname(__file__), "backend", "server_trade_crn", "__init__.py"))

# Configure application
# Import Flask-SocketIO for real-time functionality
from flask_socketio import SocketIO

def create_app(config_name=ENVIRONMENT):
    # Create Flask application
    app = Flask(__name__, static_folder='build', static_url_path='/')
    
    # Apply configuration
    app.config.from_object(config_by_name[config_name])
    
    # Initialize SocketIO with the app a
    
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')
    app.socketio = socketio  # Store socketio instance on app for use in other modules
    
    # Increase session lifetime to 24 hours (in seconds)
    app.config['PERMANENT_SESSION_LIFETIME'] = datetime.timedelta(hours=24)
    
    # Make sessions permanent by default
    app.config['SESSION_PERMANENT'] = True
    
    # Use secure cookies in production and development behind proxy
    if ENVIRONMENT == 'production' or is_behind_proxy():
        app.config['SESSION_COOKIE_SECURE'] = True
        app.config['REMEMBER_COOKIE_SECURE'] = True
    
    # Configure session cookie with strict security settings
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['REMEMBER_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Strict'  # Upgraded from Lax
    
    # Set cookie path to root
    app.config['SESSION_COOKIE_PATH'] = '/'
    app.config['REMEMBER_COOKIE_PATH'] = '/'
    
    # Configure session to use filesystem instead of signed cookies
    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['SESSION_FILE_DIR'] = os.path.join(os.path.dirname(__file__), 'flask_session')
    app.config['SESSION_USE_SIGNER'] = True  # Sign session cookies
    os.makedirs(app.config['SESSION_FILE_DIR'], exist_ok=True)
    
    # Create Flask-Session
    try:
        from flask_session import Session
        Session(app)
        logger.info("Using Flask-Session for server-side sessions")
    except ImportError:
        logger.warning("Flask-Session not installed, using client-side sessions")
    
    return app

# Create the Flask application
app = create_app()

# Add middleware to fix proxy headers
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

# Configure security features
security_system.configure_security(app)

# Configure middleware
middleware_system.configure_middleware(app)

# Configure error handlers
error_handlers_system.configure_error_handlers(app)

# Initialize rate limiting system
limiter = rate_limiting_system.configure_rate_limiting(app)

# Create main Flask app
app = Flask(__name__, static_folder='dist')

# Load configuration based on environment
app.config.from_object(config_by_name[ENVIRONMENT])
logger.info(f"Application configured for {ENVIRONMENT} environment")

# Initialize memory manager with more advanced tracking
memory_config = MemoryManagerConfig()

# Enable advanced tracking features
memory_config.object_tracker.enabled = True
memory_config.heap_analyzer.enabled = True
memory_config.critical_section.enabled = True

# Initialize memory manager
memory_manager = init_manager(app=app, config=memory_config)

# Add memory manager to app context
app.memory_manager = memory_manager

# Configure memory critical point marking for important app events
@app.before_request
def mark_request_start():
    try:
        # First check if memory_manager exists
        if hasattr(app, 'memory_manager'):
            # Then check if Flask-Login is properly initialized and current_user is authenticated
            if hasattr(app, 'login_manager') and current_user and current_user.is_authenticated:
                # Mark authenticated requests as critical points for memory tracking
                app.memory_manager.mark_critical_point(
                    f"Request: {request.endpoint}",
                    {"user": current_user.id, "path": request.path, "method": request.method}
                )
    except Exception as e:
        # Log error but don't crash the request
        logger.error(f"Error in memory tracking: {e}")

# Apply middleware (compression, proxy fix)
middleware_system.configure_middleware(app)

# Configure security settings (CSP headers, CSRF)
security_system.configure_security(app)

# Function to make a synchronous wrapper for async code
def sync_wrapper(async_function):
    """Convert an async function to sync function"""
    def sync_function(*args, **kwargs):
        try:
            # First try to get the current running loop
            try:
                loop = asyncio.get_running_loop()
                # If we're already in an async context, create a task in the existing loop
                task = loop.create_task(async_function(*args, **kwargs))
                return task
            except RuntimeError:
                # No running loop exists, so create one
                if sys.platform.startswith('win'):
                    loop = asyncio.SelectorEventLoop()
                    asyncio.set_event_loop(loop)
                else:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                # Run the async function in the new loop
                return loop.run_until_complete(async_function(*args, **kwargs))
        finally:
            # Only close the loop if we created a new one
            if 'loop' in locals() and not sys.platform.startswith('win'):
                if not loop.is_running():
                    loop.close()
    return sync_function

# Initialize DDoS Protection System
ddos_protection = None
if DDOS_PROTECTION_AVAILABLE:
    try:
        # Check if DDoS protection is enabled in config
        ddos_config_path = os.path.join(os.path.dirname(__file__), 'ddos_protection', 'config', 'ddos.yaml')
        
        if os.path.exists(ddos_config_path):
            ddos_config = load_config(ddos_config_path)
            
            if ddos_config.enabled:
                # Create DDoS protection system
                ddos_system = DDoSProtectionSystem(config=ddos_config)
                
                # Start the system using a more reliable method
                try:
                    # Try to get the current running loop
                    try:
                        loop = asyncio.get_running_loop()
                        # Already in an async context, create a task
                        task = asyncio.create_task(ddos_system.start())
                        logger.info("DDoS Protection System started in existing loop")
                    except RuntimeError:
                        # No running loop, create one
                        logger.info("No running event loop, creating one for DDoS Protection")
                        
                        # Create and run in a thread to avoid blocking
                        def start_ddos_in_thread():
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            try:
                                loop.run_until_complete(ddos_system.start())
                                loop.run_forever()
                            except Exception as e:
                                logger.error(f"Error in DDoS thread: {e}")
                                logger.error(traceback.format_exc())
                            finally:
                                loop.close()
                        
                        # Start in thread
                        threading.Thread(target=start_ddos_in_thread, daemon=True).start()
                        
                    # Initialize Cloudflare integration (ONLY USE CLOUDFLARE)
                    try:
                        # Set cloudflare exclusive mode
                        os.environ['USE_CLOUDFLARE_EXCLUSIVELY'] = 'true'
                        
                        # Initialize Cloudflare with Flask app
                        if init_cloudflare_integration:
                            cloudflare_success = init_cloudflare_integration(app)
                            if cloudflare_success:
                                logger.info("Cloudflare integration initialized successfully")
                            else:
                                logger.warning("Cloudflare integration initialization failed")
                        else:
                            logger.warning("Cloudflare integration function not available")
                    except ImportError:
                        logger.warning("Cloudflare integration module not found")
                    except Exception as e:
                        logger.error(f"Error initializing Cloudflare: {e}")
                    
                    # Set global flag
                    ddos_protection = True
                    
                    # Register middleware
                    @app.before_request
                    def ddos_protection_middleware():
                        """DDoS protection middleware"""
                        try:
                            # Skip OPTIONS requests completely
                            if request.method == 'OPTIONS':
                                return None
                                
                            # Check if request should be blocked
                            try:
                                from ddos_protection.middleware import should_block_request
                                should_block, reason = should_block_request(request)
                                
                                if should_block:
                                    logger.warning(f"Blocked request: {reason}")
                                    return jsonify({"error": reason}), 403
                            except ImportError:
                                # Middleware module not available, use simplified check
                                logger.debug("Using simplified request blocking check (Cloudflare-only mode)")
                                # Check if IP is banned in Cloudflare cache
                                real_ip = getattr(request, 'real_ip', request.remote_addr)
                                try:
                                    from ddos_protection.network.cloudflare.api import blocked_ips_cache
                                    if real_ip in blocked_ips_cache:
                                        logger.warning(f"Blocked banned IP: {real_ip}")
                                        return jsonify({"error": "Access denied by DDoS protection"}), 403
                                except ImportError:
                                    pass
                            
                            return None
                        except Exception as e:
                            logger.error(f"Error in DDoS protection middleware: {e}")
                            return None
                            
                except Exception as e:
                    logger.error(f"Error initializing DDoS Protection System: {e}")
                    logger.error(traceback.format_exc())
    except Exception as e:
        logger.error(f"Error initializing DDoS protection: {e}")
        logger.error(traceback.format_exc())

# Add security headers from security_utils
@app.after_request
def add_security_headers(response):
    """Add security headers to all responses"""
    is_dev = app.debug
    response = security_utils.apply_security_headers(response, is_dev)
    
    # Add header to indicate the response was handled by Flask
    response.headers['X-Served-By'] = 'Flask'
    
    return response

# Add IP detection middleware
@app.before_request
def extract_real_ip():
    """
    Extract and store the real client IP in request.
    This allows more accurate IP detection for all components.
    """
    real_ip = get_client_ip_from_request(request)
    
    # Store the real IP in request object for other components to use
    setattr(request, 'real_ip', real_ip)
    
    # For stress testing, we want to treat local IPs as regular IPs to verify protection works
    # Only mark as local for administrative routes
    is_local = False
    if request.path.startswith('/admin') and (real_ip == '127.0.0.1' or real_ip == '::1'):
        is_local = True
    
    setattr(request, 'is_local_request', is_local)

# Create rate limiter
limiter = rate_limiting_system.configure_rate_limiting(app)

# Create auth app
auth_app = auth.create_auth_app()

# Configure the main app with auth settings - Use secure secret key
app.config.update(auth_app.config)

# وسيط رفض مبكر للطلبات من العناوين المحظورة - ينفذ قبل أي وسيط آخر
@app.before_request
def early_ip_rejection():
    """
    وسيط منخفض المستوى يرفض الطلبات من العناوين المحظورة قبل أي معالجة
    يعمل هذا على مستوى أقل من ddos_protection_middleware للتوقف الفوري
    """
    try:
        # Always allow OPTIONS requests without any checking
        if request.method == "OPTIONS":
            return None
            
        # الحصول على عنوان IP الحقيقي
        real_ip = getattr(request, 'real_ip', request.remote_addr)

        # Simple rate limiter cache
        if not hasattr(early_ip_rejection, 'rate_limit_cache'):
            early_ip_rejection.rate_limit_cache = {}
            early_ip_rejection.last_cleanup = time.time()
        
        # Clean up old records every 5 seconds
        current_time = time.time()
        if current_time - early_ip_rejection.last_cleanup > 5:
            early_ip_rejection.rate_limit_cache = {k: v for k, v in early_ip_rejection.rate_limit_cache.items() 
                                                if current_time - v['timestamp'] < 60}
            early_ip_rejection.last_cleanup = current_time
            
        # Check if IP is in rate limit cache
        if real_ip in early_ip_rejection.rate_limit_cache:
            cache_entry = early_ip_rejection.rate_limit_cache[real_ip]
            
            # If request count is too high, reject immediately
            if cache_entry['count'] > 1000:  # Extreme limit
                logger.warning(f"Early rejection of high-volume IP: {real_ip}")
                
                # Apply ban if needed - after 2000 requests, use Cloudflare only
                if cache_entry['count'] > 2000 and CLOUDFLARE_INTEGRATION_AVAILABLE:
                    try:
                        if cf_client:
                            # Create task to ban in Cloudflare
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            try:
                                loop.run_until_complete(cf_client.block_ip(real_ip, "Excessive request volume", 86400))
                                logger.warning(f"Banned high-volume IP in Cloudflare: {real_ip}")
                            finally:
                                loop.close()
                    except ImportError:
                        logger.error("Could not import Cloudflare client")
                
                return jsonify({"error": "Too Many Requests"}), 429
            
            # Increment request count
            cache_entry['count'] += 1
        else:
            # Add new entry to cache
            early_ip_rejection.rate_limit_cache[real_ip] = {
                'count': 1,
                'timestamp': current_time
            }
        
        # Check if IP is banned via Cloudflare
        if CLOUDFLARE_INTEGRATION_AVAILABLE:
            try:
                # Use cf_client directly
                if cf_client:
                    # Check if already in ban cache
                    from ddos_protection.network.cloudflare.api import blocked_ips_cache
                    if real_ip in blocked_ips_cache:
                        logger.warning(f"Blocked banned IP at early rejection: {real_ip} - Method: {request.method}")
                        return jsonify({"error": "Access denied by DDoS protection"}), 403
            except (ImportError, Exception) as e:
                # Log error and continue
                logger.error(f"Error in Cloudflare IP check: {e}")
        
        # Continue processing the request
        return None
    except Exception as e:
        logger.error(f"Error in early IP rejection: {e}")
        return None

# وسيط حماية CSRF للطلبات الحساسة
@app.before_request
def csrf_protect():
    """
    وسيط حماية من هجمات CSRF للطلبات الحساسة (POST, PUT, DELETE)
    يتحقق من وجود توكن CSRF في طلبات تعديل البيانات
    """
    # فحص فقط الطلبات التي تعدل البيانات
    if request.method in ['POST', 'PUT', 'DELETE']:
        # استثناء مسارات معينة من الحماية (مثل تسجيل الدخول والتسجيل)
        exempt_paths = ['/api/login', '/api/register', '/api/refresh-token', 
               # مسارات صفحات التقييم
               '/api/ratings/appearance', '/api/ratings/appearance/update', 
               '/api/ratings/appearance/update-all', '/api/ratings/appearance/reset',
               '/api/ratings/appearance/share-code', '/api/ratings/appearance/import',
               # مسارات الإعدادات والملف الشخصي
               '/api/ratings/settings', '/api/ratings/settings/update', 
               '/api/ratings/settings/update-all',
               '/api/ratings/profile', '/api/ratings/profile/update',
               # مسارات تقييم المستخدمين
               '/api/ratings/submit', '/api/ratings/user',
               # مسارات التحويلات الجديدة مع الحماية
               '/api/transfers/send', '/api/transfers/validate-address']
        if request.path in exempt_paths:
            return None
            
        # استثناء طلبات API المباشرة من الخدمات الخارجية التي تستخدم مفتاح API
        if request.headers.get('X-API-Key'):
            return None
            
        # استثناء ملف Security.tsx من حماية CSRF مؤقتاً
        if '/api/security/' in request.path:
            logger.info(f"CSRF protection skipped for security endpoint: {request.path}")
            return None
            
        # التحقق من توكن CSRF
        encrypted_csrf_token = request.headers.get('X-CSRF-Token')
        if not encrypted_csrf_token:
            logger.warning(f"CSRF token missing for {request.path}")
            return jsonify({
                "success": False,
                "error": "CSRF token missing",
                "message": "Security validation failed. Please refresh the page and try again."
            }), 403
        
        # Debug logging
        logger.info(f"CSRF check for {request.path}: encrypted_token_length={len(encrypted_csrf_token) if encrypted_csrf_token else 0}")
        
        # Add request tracking for debugging
        import time
        request_id = f"{time.time()}-{hash(request.remote_addr)}"
        logger.info(f"[{request_id}] CSRF validation request from {request.remote_addr} for {request.path}")
        
        # Decrypt the token from client
        try:
            import base64
            
            # Decode base64
            encrypted_bytes = base64.b64decode(encrypted_csrf_token)
            
            # XOR decryption
            server_key_raw = app.config.get('SECRET_KEY', 'default-secret-key')
            # Handle both string and bytes types for SECRET_KEY
            if isinstance(server_key_raw, bytes):
                server_key = server_key_raw
            else:
                server_key = str(server_key_raw).encode('utf-8')
            decrypted_token = bytearray()
            for i, byte in enumerate(encrypted_bytes):
                key_byte = server_key[i % len(server_key)]
                decrypted_token.append(byte ^ key_byte)
            
            # Convert back to string
            client_token = decrypted_token.decode('utf-8')
            
            # Debug logging
            logger.info(f"[{request_id}] CSRF decryption successful for {request.path}: client_token_length={len(client_token)}")
            
        except Exception as e:
            logger.warning(f"[{request_id}] Failed to decrypt CSRF token for {request.path}: {e}")
            return jsonify({
                "success": False,
                "error": "Invalid CSRF token format",
                "message": "Security validation failed. Please refresh the page and try again."
            }), 403
            
        # التحقق من صحة التوكن
        session_token = session.get('csrf_token')
        session_token_created = session.get('csrf_token_created')
        
        # Debug logging
        logger.info(f"[{request_id}] CSRF session check for {request.path}: session_token_exists={session_token is not None}, session_token_created={session_token_created is not None}")
        
        # Check if token exists and is not expired (7 days instead of 24 hours)
        if not session_token or not session_token_created:
            logger.warning(f"[{request_id}] No CSRF token in session for {request.path}")
            return jsonify({
                "success": False,
                "error": "No CSRF token in session",
                "message": "Security validation failed. Please refresh the page and try again."
            }), 403
        
        # Check token expiration (7 days instead of 24 hours)
        current_time = time.time()
        token_age = current_time - session_token_created
        max_token_age = 7 * 24 * 60 * 60  # 7 days in seconds
        
        if token_age > max_token_age:
            logger.warning(f"[{request_id}] CSRF token expired for {request.path}")
            # Clear expired token
            session.pop('csrf_token', None)
            session.pop('csrf_token_created', None)
            return jsonify({
                "success": False,
                "error": "CSRF token expired",
                "message": "Security token has expired. Please refresh the page and try again."
            }), 403
        
        # Use secure comparison to prevent timing attacks
        if not secrets.compare_digest(session_token, client_token):
            logger.warning(f"[{request_id}] Invalid CSRF token for {request.path}")
            logger.warning(f"[{request_id}] Session token: {session_token[:10]}...{session_token[-10:] if len(session_token) > 20 else session_token}")
            logger.warning(f"[{request_id}] Client token: {client_token[:10]}...{client_token[-10:] if len(client_token) > 20 else client_token}")
            logger.warning(f"[{request_id}] Token lengths - Session: {len(session_token)}, Client: {len(client_token)}")
            logger.warning(f"[{request_id}] Token comparison failed - tokens are different")
            return jsonify({
                "success": False,
                "error": "Invalid CSRF token",
                "message": "Security validation failed. Please refresh the page and try again."
            }), 403
        else:
            logger.info(f"[{request_id}] CSRF token validation successful for {request.path}")
    
    return None

# API for OPTIONS preflight requests
@app.route('/<path:path>', methods=['OPTIONS'])
def options_handler(path):
    """Handle OPTIONS requests for CORS preflight."""
    response = make_response()
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,X-Device-Fingerprint')
    response.headers.add('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE,OPTIONS')
    return response

# Register auth routes with main app - skip 'static' endpoint
for rule in auth_app.url_map.iter_rules():
    endpoint = auth_app.view_functions[rule.endpoint]
    # Skip the static endpoint to avoid conflicts
    if rule.endpoint != 'static':
        app.add_url_rule(str(rule), rule.endpoint, endpoint, **rule.defaults or {}, methods=rule.methods)

# Register modules
login.init_app(app)
signup.init_app(app)
password_reset.init_app(app)
overview.init_app(app)
transfers.init_app(app)
backup.init_app(app)
security.init_app(app)
mining.init_app(app)
mining_security.init_app(app)
privacy.init_app(app)
transaction_history.init_app(app)
leaderboard.init_app(app)
session_devices.init_app(app)
network_transactions.init_app(app)
# Initialize server trading module
server_trade_crn.init_app(app)

# Import and register premium authentication module
try:
    premium_auth = import_module("premium_auth", os.path.join(os.path.dirname(__file__), "backend", "premium_auth", "__init__.py"))
    premium_check = import_module("premium_check", os.path.join(os.path.dirname(__file__), "backend", "premium_auth", "premium_check.py"))
    csrf_helpers = import_module("csrf_helpers", os.path.join(os.path.dirname(__file__), "backend", "premium_auth", "csrf_helpers.py"))
    
    # Initialize modules
    premium_check.init_app(app)
    csrf_helpers.init_app(app)
    
    logger.info("Premium authentication module loaded successfully")
    logger.info("CSRF helpers module loaded successfully")
except ImportError as e:
    logger.error(f"Failed to load premium authentication module: {e}")

# Import and register quick_transfer module
quick_transfer = import_module("backend.cryptonel.quick_transfer", os.path.join(os.path.dirname(__file__), "backend", "cryptonel", "quick_transfer", "__init__.py"))
quick_transfer.init_app(app)

# Import and register custom_address module
custom_address = import_module("backend.cryptonel.custom_address", os.path.join(os.path.dirname(__file__), "backend", "cryptonel", "custom_address", "__init__.py"))
custom_address.init_app(app)

# Import and register ratings (public profile) module
ratings_module = import_module("backend.cryptonel.ratings", os.path.join(os.path.dirname(__file__), "backend", "cryptonel", "ratings", "__init__.py"))
ratings_module.init_app(app)

# Register error handlers
error_handlers_system.configure_error_handlers(app)

# Configure API URL prefix
API_PREFIX = '/api'

@app.route(f'{API_PREFIX}/', defaults={'path': ''})
@app.route(f'{API_PREFIX}/<path:path>')
def api_router(path):
    """
    Main API router that handles all API requests
    This is used when behind a reverse proxy to route all API requests correctly
    """
    # Log the API request
    logger.debug(f"API request: {path}")
    
    # This function can be expanded to route API requests dynamically
    return response_handler.ApiResponse.not_found(
        message=f"API endpoint not found: {path}"
    ).to_dict(), 404

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
@limiter.limit("100 per minute")
def serve(path):
    """Serve the application - Single page app"""
    # Check if this request should be blocked by Cloudflare
    try:
        # Get the real IP
        real_ip = getattr(request, 'real_ip', request.remote_addr)
        
        # Check with Cloudflare ban cache directly - simple approach
        from ddos_protection.network.cloudflare.api import blocked_ips_cache
        if real_ip in blocked_ips_cache:
            security_logger.warning(f"Blocked banned IP at serve handler: {real_ip}")
            return abort(403, description="Access denied by DDoS protection")
    except Exception as e:
        logger.error(f"Error in Cloudflare protection check: {e}")
    
    # السماح بصفحة إعادة تعيين كلمة المرور
    if path == "reset-password":
        # السماح بالوصول إلى صفحة إعادة تعيين كلمة المرور
        logger.info(f"Allowing access to reset password page: {path}")
    # Check if path is secure
    elif not security_system.secure_static_files_access(path):
        # Allow specific client-side routes to pass through the security check
        if path == "reset-password" or path.startswith('profile/'):
            logger.info(f"Allowing client-side route: {path}")
        # Allow asset files
        elif path.startswith('assets/') and (path.endswith('.js') or path.endswith('.css')):
            logger.info(f"Allowing access to asset file: {path}")
        else:
            logging_system.log_security_event(
                'blocked_access', 
                request.remote_addr, 
                path,
                'Blocked access to potentially sensitive file path'
            )
            return abort(403)
    
    # Serve files directly without modification
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        try:
            # Send file directly with appropriate cache headers
            response = send_from_directory(app.static_folder, path)
            
            # In development mode, disable caching for all files to allow hot-reloading
            if ENVIRONMENT == 'development':
                response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
                response.headers['Pragma'] = 'no-cache'
                response.headers['Expires'] = '0'
            else:
                # Production caching - only add for production
                if path.endswith(('.js', '.css')):
                    response.headers['Cache-Control'] = 'public, max-age=31536000'  # Cache for a year
                    response.headers['Vary'] = 'Accept-Encoding'
                elif path.endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', '.woff', '.woff2')):
                    response.headers['Cache-Control'] = 'public, max-age=31536000'  # Cache for a year
                    response.headers['Vary'] = 'Accept-Encoding'
            
            return response
        except Exception as e:
            logger.error(f"Error serving static file {path}: {e}")
            return abort(404)
    else:
        # For the main app
        response = make_response(send_from_directory(app.static_folder, 'index.html'))
        
        # In development mode, disable caching for index.html too
        if ENVIRONMENT == 'development':
            response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
        else:
            response.headers['Cache-Control'] = 'public, max-age=0'
        
        return response

# Add health check endpoint
@app.route('/health')
@limiter.exempt
def health_check():
    """Enhanced health check endpoint using the response handler"""
    # Check if we're behind a proxy to add to health data
    behind_proxy = is_behind_proxy()
    
    # Get basic system info
    health_data = {
        "status": "ok",
        "timestamp": json_utils.make_json_serializable(datetime.datetime.now()),
        "server": {
            "behind_proxy": behind_proxy,
            "remote_addr": request.remote_addr,
            "forwarded_for": request.headers.get('X-Forwarded-For', None),
            "app_name": "Cryptonel Wallet",
            "version": "1.0.0"
        },
        "cache": {
            "redis_available": cache_available
        },
        "scheduler": {
            "apscheduler_available": APSCHEDULER_AVAILABLE
        }
    }
    
    # Add memory monitoring data
    if memory_manager:
        health_data["memory"] = memory_manager.get_memory_status()
        
    # Add DDoS protection status if available
    if ddos_protection:
        health_data["ddos_protection"] = {
            "enabled": True,
            "version": "1.0.0"
        }
    
    # Add additional health data from response_handler
    additional_health = response_handler.health_check_response()
    health_data = json_utils.merge_dicts(health_data, additional_health)
    
    response = response_handler.ApiResponse.success(
        data=health_data,
        message="Service is operational"
    )
    return json_utils.dumps(response.to_dict()), 200, {'Content-Type': 'application/json'}

# Add CSRF token generation endpoint
@app.route('/api/csrf-token', methods=['GET'])
def get_csrf_token():
    """
    Generate a CSRF token and store it in the session
    
    This endpoint is used by the frontend to get a CSRF token for secure form submissions
    """
    try:
        # Import required modules at the top
        import time
        import hashlib
        import base64
        
        # Check if user is authenticated
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({"success": False, "error": "Not authenticated"}), 401
        
        # Check if we already have a valid CSRF token in session
        existing_token = session.get('csrf_token')
        token_created = session.get('csrf_token_created')
        
        # Check if token is still valid (24 hours)
        current_time = time.time()
        token_age = current_time - (token_created or 0)
        max_token_age = 24 * 60 * 60  # 24 hours in seconds
        
        # Add request tracking for debugging
        request_id = f"{current_time}-{hash(request.remote_addr)}"
        logger.info(f"[{request_id}] CSRF token request from {request.remote_addr} for user {user_id}")
        
        if existing_token and token_created and token_age < max_token_age:
            # Use existing token
            logger.info(f"[{request_id}] Using existing CSRF token for user {user_id} (age: {token_age:.1f}s, token: {existing_token[:10]}...{existing_token[-10:]})")
            
            # Encrypt the existing token for transmission
            server_key_raw = app.config.get('SECRET_KEY', 'default-secret-key')
            if isinstance(server_key_raw, bytes):
                server_key = server_key_raw
            else:
                server_key = str(server_key_raw).encode('utf-8')
            token_bytes = existing_token.encode('utf-8')
            
            # XOR encryption
            encrypted_token = bytearray()
            for i, byte in enumerate(token_bytes):
                key_byte = server_key[i % len(server_key)]
                encrypted_token.append(byte ^ key_byte)
            
            # Encode as base64 for safe transmission
            encrypted_token_b64 = base64.b64encode(encrypted_token).decode('utf-8')
            
            logger.info(f"[{request_id}] Returning existing encrypted token: {encrypted_token_b64[:20]}...")
            
            return jsonify({
                "success": True,
                "csrf_token": encrypted_token_b64,
                "expires_in": max_token_age - token_age
            })
        
        # Generate a new CSRF token using multiple entropy sources
        logger.info(f"[{request_id}] Generating new CSRF token for user {user_id}")
        
        # Combine multiple entropy sources for better security
        # Remove current_time from entropy sources to make tokens more stable
        entropy_sources = [
            secrets.token_hex(32),  # Random bytes
            str(user_id),           # User ID
            request.headers.get('User-Agent', ''),  # User agent
            request.remote_addr     # Client IP
        ]
        
        # Create a hash of all entropy sources
        combined_entropy = ''.join(entropy_sources).encode('utf-8')
        raw_token = hashlib.sha256(combined_entropy).hexdigest()
        
        # Encrypt the token before sending to client
        # Use a simple XOR encryption with a server-side key
        server_key_raw = app.config.get('SECRET_KEY', 'default-secret-key')
        # Handle both string and bytes types for SECRET_KEY
        if isinstance(server_key_raw, bytes):
            server_key = server_key_raw
        else:
            server_key = str(server_key_raw).encode('utf-8')
        token_bytes = raw_token.encode('utf-8')
        
        # XOR encryption
        encrypted_token = bytearray()
        for i, byte in enumerate(token_bytes):
            key_byte = server_key[i % len(server_key)]
            encrypted_token.append(byte ^ key_byte)
        
        # Encode as base64 for safe transmission
        encrypted_token_b64 = base64.b64encode(encrypted_token).decode('utf-8')
        
        # Store the original token in session for validation
        session['csrf_token'] = raw_token
        session['csrf_token_created'] = current_time
        
        # Debug logging
        logger.info(f"[{request_id}] New CSRF token generated for user {user_id}: token_length={len(raw_token)}, token={raw_token[:10]}...{raw_token[-10:]}, encrypted_length={len(encrypted_token_b64)}")
        
        # Return the encrypted token to the client
        return jsonify({
            "success": True,
            "csrf_token": encrypted_token_b64,
            "expires_in": max_token_age
        })
    except Exception as e:
        logger.error(f"Error generating CSRF token: {e}")
        return jsonify({"success": False, "error": "Error generating CSRF token"}), 500

# Add API error handling with response_handler
@app.errorhandler(400)
@response_handler.handle_api_error
def bad_request_error(error):
    """Handle bad request errors"""
    return response_handler.ApiResponse.bad_request(message=str(error))

@app.errorhandler(404)
def not_found_error(error):
    # Generate error ID
    error_id = f"{int(time.time())}-{hex(random.randint(0, 0xffffff))[2:]}"
    
    # Check if this is a build error (missing JS/CSS files)
    if request.path.endswith(('.js', '.css', '.map')):
        # Log the error to file
        log_error_to_file(f"404 - Build Error: {request.path}", error_id)
        return render_template('error.html', error_id=error_id), 404
        
    return render_template('404.html'), 404

@app.errorhandler(429)
def ratelimit_error(error):
    """Handle rate limit errors"""
    retry_after = 60  # Default retry time
    if hasattr(error, 'description') and hasattr(error.description, 'retry_after'):
        retry_after = error.description.retry_after
        
    # Check if this is a local request and log appropriately
    if hasattr(request, 'real_ip'):
        real_ip = request.real_ip
        is_local = request.is_local_request
        if is_local:
            logger.warning(f"Local request from {real_ip} hit rate limit! This should NOT happen.")
            
    return json_utils.dumps(response_handler.throttled_response(retry_after).to_dict()), 429, {'Content-Type': 'application/json'}

@app.errorhandler(500)
def internal_error(error):
    # Generate error ID
    error_id = f"{int(time.time())}-{hex(random.randint(0, 0xffffff))[2:]}"
    
    # Log the error
    app.logger.error(f"500 error: {str(error)} (ID: {error_id})")
    log_error_to_file(f"500 - Server Error: {str(error)}", error_id)
    
    return render_template('error.html', error_id=error_id), 500

def log_error_to_file(error_message, error_id):
    """Log error details to file"""
    try:
        # Ensure logs directory exists
        log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        # Format error message
        timestamp = datetime.datetime.now().isoformat()
        logged_message = f"""
[{timestamp}] ERROR ID: {error_id}
{error_message}
URL: {request.url}
Method: {request.method}
IP: {request.remote_addr}
User Agent: {request.headers.get('User-Agent')}
----------------------------------------------------------------------------------
"""
        
        # Write to server-errors.log
        with open(os.path.join(log_dir, 'server-errors.log'), 'a', encoding='utf-8') as f:
            f.write(logged_message)
            
    except Exception as e:
        print(f"Error logging to file: {str(e)}")

# Proper shutdown handler for asyncio tasks
def close_asyncio_tasks():
    """Close all running asyncio tasks gracefully."""
    try:
        # Check if there is a running event loop
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No running event loop
            logger.info("No running event loop found during cleanup, nothing to do")
            return
            
        # Get all running tasks
        tasks = [t for t in asyncio.all_tasks(loop) if t is not asyncio.current_task()]
        
        if not tasks:
            logger.info("No asyncio tasks to clean up")
            return
            
        logger.info(f"Gracefully shutting down {len(tasks)} asyncio tasks")
        
        # Cancel all tasks
        for task in tasks:
            if not task.done() and not task.cancelled():
                task.cancel()
        
        # Windows-specific fix for IocpProactor issues
        if sys.platform.startswith('win'):
            # Force close the event loop after short delay
            # This avoids Task destroyed but pending errors
            try:
                loop.run_until_complete(asyncio.sleep(0.1))
            except (RuntimeError, asyncio.CancelledError):
                # Ignore errors when the loop is closed or tasks are cancelled
                pass
            
            # Explicitly close the ProactorEventLoop to prevent IocpProactor errors
            if hasattr(loop, '_proactor'):
                # Silence the "abandon all hope" RuntimeError from proactor
                try:
                    if hasattr(loop._proactor, '_close'):
                        loop._proactor._close()
                except Exception:
                    pass
        else:
            # On Linux/Mac, wait for tasks to be cancelled
            try:
                # Use a short timeout to avoid blocking shutdown
                loop.run_until_complete(asyncio.wait(tasks, timeout=1.0))
            except (RuntimeError, asyncio.CancelledError, asyncio.TimeoutError):
                # Ignore expected errors during shutdown
                pass
        
        logger.info("All asyncio tasks have been cancelled")
    except Exception as e:
        logger.error(f"Error during asyncio cleanup: {e}")
        try:
            logger.error(traceback.format_exc())
        except Exception:
            pass

# Additional fix for race condition during shutdown
def patch_asyncio_for_ddos():
    """Apply additional patches for more reliable asyncio handling"""
    try:
        # Add shutdown handler
        import atexit
        atexit.register(close_asyncio_tasks)
        
        # Monkey patch asyncio.all_tasks to be more resilient
        original_all_tasks = asyncio.all_tasks
        def safe_all_tasks(loop=None):
            try:
                return original_all_tasks(loop)
            except RuntimeError:
                # Handle "no running event loop" error
                return set()
                
        asyncio.all_tasks = safe_all_tasks
        
        logger.info("Applied asyncio patches for better stability")
    except Exception as e:
        logger.error(f"Failed to apply asyncio patches: {e}")

# Apply patches at startup
patch_asyncio_for_ddos()

# Remove device fingerprinting functions - we're using Cloudflare exclusively

# Add API for device registration - Simplified to just return success
@app.route('/api/register-device', methods=['POST'])
def register_device():
    """
    API endpoint for compatibility - does nothing as we're using Cloudflare exclusively.
    """
    return jsonify({"status": "success"})

# Simplified Cloudflare status API
@app.route('/api/cloudflare/status', methods=['GET', 'OPTIONS'])
@limiter.exempt  # Exempt from rate limiting
def cloudflare_status():
    """
    Get status of Cloudflare integration.
    """
    # Handle OPTIONS request for CORS
    if request.method == 'OPTIONS':
        response = make_response()
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,OPTIONS')
        return response
    
    try:
        # Check Cloudflare API credentials
        cf_api_email = os.environ.get('CF_API_EMAIL', '')
        cf_api_key = os.environ.get('CF_API_KEY', '')
        cf_zone_id = os.environ.get('CF_ZONE_ID', '')
        
        # Check if any Cloudflare client is available
        cf_client_available = False
        try:
            if cf_client:
                cf_client_available = True
        except ImportError:
            pass
        
        return jsonify({
            "success": True,
            "cloudflare": {
                "configured": all([cf_api_email, cf_api_key, cf_zone_id]),
                "client_available": cf_client_available,
                "exclusive_mode": True
            }
        })
    except Exception as e:
        logger.error(f"Error checking Cloudflare status: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.before_request
def jwt_session_restore():
    """
    وسيط لاستعادة حالة المستخدم من الـ JWT تلقائيًا إذا كانت صالحة،
    حتى بعد إعادة تشغيل الخادم
    """
    try:
        # Skip OPTIONS requests
        if request.method == 'OPTIONS':
            return None
        
        # Skip if we're already handling a token-related request
        if request.path == '/api/refresh-token' or request.path == '/api/login' or request.path == '/api/jwt-logout':
            return None
            
        # Check if there's already a session
        if 'user_id' in session:
            return None
            
        # First check for JWT token in Authorization header
        auth_header = request.headers.get('Authorization')
        token = None
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
        
        # If no token in header, check cookies
        if not token:
            token = request.cookies.get('access_token')
            
        # If still no token, nothing to restore
        if not token:
            return None
            
        # Get fingerprint for verification if available
        fingerprint = request.headers.get('X-Device-Fingerprint')
        
        # Decode token with appropriate verification
        decoded = decode_token(token, expected_type="access", 
                            verify_fingerprint=fingerprint is not None)
        
        # If access token is invalid or expired, try refresh token
        if not decoded:
            refresh_token = request.cookies.get('refresh_token')
            
            if not refresh_token:
                return None
            
            # Use fingerprint when refreshing the token
            new_token_data = refresh_access_token(refresh_token, fingerprint)
            
            if new_token_data:
                # Send the new token in response headers
                g.new_access_token = new_token_data.get('access_token')
                g.token_expires_in = new_token_data.get('expires_in')
                
                # Also decode the new access token
                decoded = decode_token(new_token_data.get('access_token'), 
                                    expected_type="access",
                                    verify_fingerprint=fingerprint is not None)
            else:
                logger.warning("Failed to refresh token - invalid refresh token")
                return None
        
        if decoded and decoded.get('type') == 'access':
            # Set user_id in session
            session['user_id'] = decoded.get('sub')
            
            if 'premium' in decoded:
                session['premium'] = decoded.get('premium')
                
            if 'username' in decoded:
                session['username'] = decoded.get('username')
                
            # Set session to permanent if remember_me flag is in token
            if decoded.get('remember_me'):
                session.permanent = True
                
            # Log successful session restoration
            logger.info(f"JWT session restored for user {decoded.get('sub')}")
                
    except Exception as e:
        logger.error(f"Error restoring JWT session: {e}")
        logger.error(traceback.format_exc())
        
    return None

# Add logout route that invalidates tokens
@app.route('/api/jwt-logout', methods=['POST'])
def jwt_logout():
    """
    Logout endpoint that invalidates JWT tokens and clears session
    
    This ensures proper security by invalidating tokens on logout
    """
    try:
        # Clear Flask session
        session.clear()
        
        # Get auth token if provided
        auth_header = request.headers.get('Authorization')
        token = None
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            
        # Get refresh token from cookies
        refresh_token = request.cookies.get('refresh_token')
        
        # Invalidate both tokens if they exist
        tokens_invalidated = False
        if token:
            from backend.jwt_utils import invalidate_token
            invalidate_token(token)
            tokens_invalidated = True
            
        if refresh_token:
            from backend.jwt_utils import invalidate_token
            invalidate_token(refresh_token)
            tokens_invalidated = True
        
        # Create response
        response = jsonify({"success": True, "message": "Logged out successfully"})
        
        # Clear cookies
        response.delete_cookie('refresh_token')
        response.delete_cookie('access_token')
        response.delete_cookie('session')
        
        # Add secure cache control headers
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        
        return response
    except Exception as e:
        logger.error(f"Error during logout: {e}")
        return jsonify({"success": False, "error": "Error during logout"}), 500

@app.after_request
def add_cors_headers(response):
    """Add CORS headers and additional security headers to all responses"""
    # Allow client cookies to be sent with requests - only for specific origins
    if request.method == 'OPTIONS':
        response.headers.add('Access-Control-Allow-Origin', request.headers.get('Origin', '*'))
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization,X-Device-Fingerprint,X-Requested-With,X-CSRF-Token')
        response.headers.add('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE,OPTIONS')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        response.headers.add('Access-Control-Max-Age', '3600') # Cache preflight for 1 hour
    elif request.headers.get('Origin'):
        # For non-OPTIONS requests, only set the CORS headers if Origin is present
        response.headers.add('Access-Control-Allow-Origin', request.headers.get('Origin'))
        response.headers.add('Access-Control-Allow-Credentials', 'true')
    
    # Add security headers if not already present
    if 'Content-Security-Policy' not in response.headers:
        response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self' data:;"
    
    if 'X-Content-Type-Options' not in response.headers:
        response.headers['X-Content-Type-Options'] = 'nosniff'
    
    if 'X-Frame-Options' not in response.headers:
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    
    if 'X-XSS-Protection' not in response.headers:
        response.headers['X-XSS-Protection'] = '1; mode=block'
    
    if 'Referrer-Policy' not in response.headers:
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    
    # Add cache control for API responses
    if request.path.startswith('/api/') and 'Cache-Control' not in response.headers:
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
    
    return response

# Add token refresh endpoint
@app.route('/api/refresh-token', methods=['POST'])
def refresh_token_api():
    """
    Refresh API endpoint to get a new access token using refresh token
    
    This allows the client to get a new access token without logging in again
    """
    try:
        # Get refresh token from cookies or request body
        refresh_token = request.cookies.get('refresh_token')
        if not refresh_token:
            data = request.get_json()
            if data and 'refresh_token' in data:
                refresh_token = data['refresh_token']
        
        if not refresh_token:
            return jsonify({"error": "Refresh token is required"}), 400
        
        # Get fingerprint for verification
        fingerprint = request.headers.get('X-Device-Fingerprint')
        
        # Refresh the token
        from backend.jwt_utils import refresh_access_token
        new_token_data = refresh_access_token(refresh_token, fingerprint)
        
        if not new_token_data:
            return jsonify({"error": "Invalid or expired refresh token"}), 401
        
        # Create response
        response = jsonify({
            "success": True,
            "access_token": new_token_data.get("access_token"),
            "expires_in": new_token_data.get("expires_in"),
            "token_type": "Bearer"
        })
        
        # Add secure headers
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        
        return response
    except Exception as e:
        logger.error(f"Error refreshing token: {e}")
        return jsonify({"error": "Error refreshing token"}), 500

@app.after_request
def add_refreshed_token_headers(response):
    """Add refreshed tokens to response headers if they exist"""
    try:
        # Check if we have a new access token to include in the response
        new_access_token = getattr(g, 'new_access_token', None)
        token_expires_in = getattr(g, 'token_expires_in', None)
        
        if new_access_token:
            # Add token to response headers
            response.headers['X-New-Access-Token'] = new_access_token
            if token_expires_in:
                response.headers['X-Token-Expires-In'] = str(token_expires_in)
            
            # Also set as a cookie for better persistence
            response.set_cookie(
                'access_token', 
                new_access_token, 
                max_age=token_expires_in or 86400, 
                httponly=True,
                samesite='Lax',
                path='/'
            )
    except Exception as e:
        logger.error(f"Error adding token headers: {e}")
    
    return response

@app.route('/health/database')
@limiter.exempt
def database_health_check():
    """Check the health of the MongoDB connection"""
    try:
        # Import the connection info function
        from backend.db_connection import get_connection_status, get_connection_info
        
        # Check the connection status
        is_connected, status_message = get_connection_status()
        
        if is_connected:
            # Get detailed connection info
            connection_info = get_connection_info()
            
            return jsonify({
                "status": "healthy",
                "message": status_message,
                "connection_info": connection_info,
                "timestamp": datetime.datetime.now().isoformat()
            }), 200
        else:
            return jsonify({
                "status": "unhealthy",
                "message": status_message,
                "timestamp": datetime.datetime.now().isoformat()
            }), 500
            
    except Exception as e:
        logger.error(f"Database health check error: {e}")
        return jsonify({
            "status": "error",
            "message": f"Failed to check database health: {str(e)}",
            "timestamp": datetime.datetime.now().isoformat()
        }), 500

# Frontend development watcher class for hot reloading
class FrontendWatcher(FileSystemEventHandler):
    """Watches frontend files and triggers rebuild when changes are detected"""
    
    def __init__(self, app, frontend_dir, build_system):
        self.app = app
        self.frontend_dir = frontend_dir
        self.build_system = build_system
        self.last_build_time = 0
        self.build_debounce = 0.5  # خفض زمن الانتظار من 2 ثانية إلى 0.5 ثانية
        self.is_building = False
        self.build_lock = threading.Lock()
        
    def on_modified(self, event):
        # Skip directories and non-frontend files
        if event.is_directory:
            return
            
        # Only watch frontend source files
        path = pathlib.Path(event.src_path)
        extensions = ['.js', '.jsx', '.ts', '.tsx', '.css', '.scss', '.html', '.svg']
        if not any(path.match(f'*{ext}') for ext in extensions):
            return
            
        # Ignore changes in the dist or build directories
        if 'dist' in path.parts or 'build' in path.parts:
            return
            
        # Debounce to avoid multiple builds for the same changes
        current_time = time.time()
        if current_time - self.last_build_time < self.build_debounce:
            return
            
        # Set last build time
        self.last_build_time = current_time
        
        # Schedule the build to avoid blocking
        threading.Thread(target=self.trigger_build).start()
            
    def trigger_build(self):
        # Use lock to prevent multiple simultaneous builds
        if self.build_lock.acquire(blocking=False):
            try:
                # Prevent rebuilding if already in progress
                if self.is_building:
                    return
                    
                self.is_building = True
                logger.info("[WATCHER] Changes detected in frontend files, rebuilding...")
                
                # Call the build function
                success, error_message = self.build_system.build_react_app()
                
                if success:
                    logger.info("[WATCHER] Frontend rebuilt successfully")
                else:
                    logger.error(f"[WATCHER] Frontend build failed: {error_message}")
                    
                self.is_building = False
            finally:
                self.build_lock.release()
                
# Function to start frontend watcher
def start_frontend_watcher(app, build_system):
    """Start the frontend file watcher in development mode"""
    if ENVIRONMENT != 'development':
        return False
        
    # Determine frontend source directory
    frontend_dir = os.path.join(os.path.dirname(__file__), 'frontend')
    
    # Check if directory exists - try alternate locations if not found
    if not os.path.exists(frontend_dir):
        frontend_dir = os.path.join(os.path.dirname(__file__), 'src')
    
    # If still not found, look for common frontend folders
    if not os.path.exists(frontend_dir):
        for possible_dir in ['client', 'webapp', 'ui', 'react-app']:
            possible_path = os.path.join(os.path.dirname(__file__), possible_dir)
            if os.path.exists(possible_path):
                frontend_dir = possible_path
                break
                
    # If still not found, use current directory (might have flat structure)
    if not os.path.exists(frontend_dir):
        frontend_dir = os.path.dirname(__file__)
        
    # Check if frontend directory exists before starting watcher
    if not os.path.isdir(frontend_dir):
        logger.warning(f"[WATCHER] Frontend directory not found at {frontend_dir}")
        return False
        
    try:
        # Create event handler and observer
        event_handler = FrontendWatcher(app, frontend_dir, build_system)
        observer = Observer()
        
        # Schedule watching the directory
        observer.schedule(event_handler, frontend_dir, recursive=True)
        observer.start()
        
        # Register shutdown handler
        atexit.register(observer.stop)
        
        logger.info(f"[WATCHER] Frontend file watcher started for {frontend_dir}")
        return True
    except Exception as e:
        logger.error(f"[WATCHER] Error starting frontend watcher: {e}")
        return False

@app.route('/api/log/client-error', methods=['POST'])
def log_client_error():
    try:
        # Get error data from request
        error_data = request.json
        
        # Add timestamp if not present
        if 'timestamp' not in error_data:
            error_data['timestamp'] = datetime.datetime.now().isoformat()
            
        # Add client IP address
        error_data['ip_address'] = request.remote_addr
        
        # Format error message
        error_message = f"""
[{error_data.get('timestamp')}] CLIENT ERROR:
URL: {error_data.get('url')}
IP: {error_data.get('ip_address')}
Error: {error_data.get('error')}
Stack: {error_data.get('stack')}
Component Stack: {error_data.get('componentStack')}
User Agent: {request.headers.get('User-Agent')}
----------------------------------------------------------------------------------
"""
        
        # Ensure logs directory exists
        log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        # Write to client-errors.log
        with open(os.path.join(log_dir, 'client-errors.log'), 'a', encoding='utf-8') as f:
            f.write(error_message)
            
        return jsonify({'success': True})
    except Exception as e:
        print(f"Error logging client error: {str(e)}")
        return jsonify({'success': False}), 500

# Catch-all route for client-side routing
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def catch_all(path):
    # For API routes that don't exist, return JSON error
    if path.startswith('api/'):
        return jsonify({'error': 'API endpoint not found'}), 404
        
    # Try to serve from static files
    try:
        static_file = os.path.join(app.static_folder, path)
        if os.path.isfile(static_file):
            return send_from_directory(app.static_folder, path)
    except:
        pass
        
    # Otherwise serve the index.html file
    try:
        return send_from_directory(app.static_folder, 'index.html')
    except:
        # If index.html doesn't exist (during build errors), show the error page
        return send_from_directory('public', 'error.html')

# Add user IP endpoint
@app.route('/api/user/ip', methods=['GET'])
def get_user_ip():
    """
    Get the current user's IP address
    """
    try:
        # Get the real IP from request
        real_ip = getattr(request, 'real_ip', request.remote_addr)
        
        return jsonify({
            "success": True,
            "ip": real_ip
        })
    except Exception as e:
        logger.error(f"Error getting user IP: {e}")
        return jsonify({
            "success": False,
            "error": "Failed to get IP address"
        }), 500

if __name__ == '__main__':
    # Check required environment variables
    required_envs = ["SECRET_KEY", "DATABASE_URL"]
    missing_envs = [env for env in required_envs if not os.getenv(env)]
    if missing_envs:
        print(f"Error: Missing required environment variables: {', '.join(missing_envs)}")
        sys.exit(1)
    
    # Get server settings
    settings = servers_system.get_server_settings()
    port = settings['port']
    debug_mode = settings['debug']
    production_mode = settings['production']
    
    # Get SocketIO instance
    socketio = app.socketio if hasattr(app, 'socketio') else None
    
    # Ensure config directory exists and create ddos.yaml if not present
    config_dir = os.path.join(os.path.dirname(__file__), 'ddos_protection', 'config')
    ddos_config_path = os.path.join(config_dir, 'ddos.yaml')
    os.makedirs(config_dir, exist_ok=True)

    # Ya configurado en modo de desarrollo al inicio del archivo
    
    if not os.path.exists(ddos_config_path):
        try:
            from ddos_protection import Config
            import yaml
            
            # Create a simplified configuration focusing ONLY on Cloudflare
            config = Config()
            config.enabled = True
            config.bypass_on_error = True
            config.use_cloudflare_exclusively = True
            
            # Add whitelist directly to config instead of using detector
            config.whitelist = ["127.0.0.1", "::1", "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"]
            
            # Cloudflare configuration
            config.cloudflare = {
                "enabled": True,
                "api_email": os.environ.get('CF_API_EMAIL', ''),
                "api_key": os.environ.get('CF_API_KEY', ''), 
                "zone_id": os.environ.get('CF_ZONE_ID', '')
            }
            
            # Save the configuration
            with open(ddos_config_path, 'w') as f:
                yaml.dump(vars(config), f, default_flow_style=False)
                
            print(f"Created Cloudflare-only DDoS protection config at {ddos_config_path}")
        except (ImportError, Exception) as e:
            print(f"Warning: Could not create default DDoS protection config: {e}")
    
    # Start memory manager if it wasn't already started during initialization
    # Check if memory manager exists and monitoring is not already active to avoid "already running" warning
    if hasattr(app, 'memory_manager'):
        try:
            if not app.memory_manager.memory_monitor.is_monitoring:
                app.memory_manager.start()
                logger.info("Memory manager started")
            else:
                logger.info("Memory manager is already running, no need to start again")
        except Exception as e:
            logger.warning(f"Error checking memory manager status: {e}")
            # Try to start anyway as fallback
            try:
                app.memory_manager.start()
                logger.info("Memory manager started (fallback)")
            except:
                logger.error("Failed to start memory manager")
    
    # Build the React app before starting the server
    logger.info("[WRENCH] Starting build process...")
    success, error_message = build_system.build_react_app()
    
    if not success:
        logger.warning("[WARNING] Failed to build React app. Starting server with existing files if available.")
        build_system.create_error_page(app.static_folder, error_message)
    
    # Start frontend watcher in development mode
    if ENVIRONMENT == 'development':
        logger.info("[WATCHER] Setting up frontend file watcher for hot-reloading...")
        watcher_started = start_frontend_watcher(app, build_system)
        if watcher_started:
            logger.info("[WATCHER] Frontend file watcher is active - changes will auto-rebuild")
        else:
            logger.warning("[WATCHER] Could not start frontend watcher. Manual rebuilds required.")
    
    logger.info(f"[ROCKET] Server starting on port {port}")
    
    # Use SocketIO to run the app if available, otherwise fall back to Flask's run method
    if hasattr(app, 'socketio'):
        logger.info("Starting server with SocketIO support for real-time updates")
        # Run with eventlet for better WebSocket performance
        import eventlet
        eventlet.monkey_patch()
        app.socketio.run(app, host='0.0.0.0', port=port, debug=debug_mode, allow_unsafe_werkzeug=True)
    else:
        if production_mode:
            # Use production WSGI server
            server_func = servers_system.get_production_server(app, port)
            if server_func:
                server_func()
            else:
                logger.warning("No production server available, using Flask's development server")
                # When in production mode behind Nginx, bind only to localhost
                app.run(host='127.0.0.1', port=port, debug=False)
        else:
            # Use Flask development server
            app.run(host='0.0.0.0', port=port, debug=debug_mode)
