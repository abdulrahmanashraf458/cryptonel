import os
import time
import secrets
import uuid
import re  # إضافة regex للتحقق من المدخلات
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, session, redirect, url_for
from pymongo import MongoClient
from dotenv import load_dotenv
from bson.objectid import ObjectId
import logging
import hmac
import json
import pyotp  # Import for 2FA verification
from functools import wraps
import random
import requests

# Import JWT utilities
from backend.jwt_utils import create_tokens

# Load environment variables directly
try:
    # Try to load from secure_config
    secure_env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'secure_config', 'clyne.env')
    if os.path.exists(secure_env_path):
        load_dotenv(secure_env_path, override=True)
        print(f"Loaded environment from: {secure_env_path}")
except Exception as e:
    print(f"Error loading environment: {e}")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Get MongoDB connection string with fallback - NEVER LOG FULL CONNECTION STRING
MONGODB_URI = os.environ.get("DATABASE_URL")
if not MONGODB_URI:
    logger.warning("DATABASE_URL not found in environment, using backup connection method")
    # Use backup connection from environment or fail safely
    MONGODB_URI = "mongodb://localhost:27017" # Default to local development instance

# Log only non-sensitive part of the connection string
connection_info = "mongodb+srv://<credentials>@" + MONGODB_URI.split('@')[-1] if '@' in MONGODB_URI else "<connection-url-masked>"
logger.info(f"Connecting to MongoDB database: {connection_info}")

# MongoDB connection
try:
    client = MongoClient(MONGODB_URI)
    db = client["cryptonel_wallet"]
    users_collection = db["users"]
    csrf_tokens_collection = db["csrf_tokens"]
    rate_limits_collection = db["rate_limits"]
    blacklist_tokens_collection = db["blacklist_tokens"]  # مجموعة جديدة لتخزين الرموز المحظورة
    suspicious_activity_collection = db["suspicious_activity"]  # مجموعة للأنشطة المشبوهة
    user_login_history_collection = db["user_login_history"]  # مجموعة جديدة لتاريخ تسجيل الدخول
    
    # Check connection without using ping
    test_collection = db.list_collection_names()
    logger.info("Successfully connected to MongoDB")
except Exception as e:
    logger.error(f"Failed to connect to MongoDB: {e}")
    raise

# Create blueprint
login_bp = Blueprint('login', __name__)

# Custom rate limiter using MongoDB
def check_rate_limit(user_id, limit_type, max_attempts=5, block_duration=900):
    """
    Check and update rate limits for a user
    
    Parameters:
    - user_id: The user's ID
    - limit_type: Type of rate limit (e.g. 'login', '2fa_verification')
    - max_attempts: Maximum number of attempts allowed before blocking
    - block_duration: Duration of block in seconds (default: 15 minutes)
    
    Returns:
    - (is_allowed, retry_after): Tuple with boolean indicating if request is allowed,
      and seconds until retry is allowed (0 if allowed)
    """
    current_time = time.time()
    
    # تنظيف البيانات القديمة: إعادة ضبط أي محاولات منتهية الصلاحية
    try:
        rate_limits_collection.update_many(
            {"rate_limits.blocked_until": {"$lt": current_time, "$gt": 0}},
            {"$set": {"rate_limits.$.count": 0, "rate_limits.$.blocked_until": 0}}
        )
    except Exception as e:
        logger.error(f"Error cleaning up expired rate limits: {e}")
    
    # Find user's rate limits document
    user_limits = rate_limits_collection.find_one({"user_id": user_id})
    
    # If no document exists, create one
    if not user_limits:
        user_limits = {
            "user_id": user_id,
            "rate_limits": [
                {
                    "limit_type": limit_type,
                    "count": 0,
                    "last_attempt": current_time,
                    "blocked_until": 0
                }
            ]
        }
        rate_limits_collection.insert_one(user_limits)
        return True, 0
    
    # Find the specific limit in the array
    limit_entry = None
    for entry in user_limits.get("rate_limits", []):
        if entry.get("limit_type") == limit_type:
            limit_entry = entry
            break
    
    # If limit type not found, add it
    if not limit_entry:
        limit_entry = {
            "limit_type": limit_type,
            "count": 0,
            "last_attempt": current_time,
            "blocked_until": 0
        }
        user_limits["rate_limits"].append(limit_entry)
        rate_limits_collection.update_one(
            {"user_id": user_id},
            {"$set": {"rate_limits": user_limits["rate_limits"]}}
        )
        return True, 0
    
    # تحقق تلقائي: إذا كان زمن الحظر قد انتهى، قم بإعادة ضبط العداد
    if limit_entry.get("blocked_until", 0) > 0 and limit_entry.get("blocked_until", 0) < current_time:
        rate_limits_collection.update_one(
            {"user_id": user_id, "rate_limits.limit_type": limit_type},
            {"$set": {
                "rate_limits.$.count": 0,
                "rate_limits.$.blocked_until": 0
            }}
        )
        limit_entry["count"] = 0
        limit_entry["blocked_until"] = 0
    
    # Check if user is blocked
    if limit_entry.get("blocked_until", 0) > current_time:
        retry_after = int(limit_entry["blocked_until"] - current_time)
        return False, retry_after
    
    # Update attempt count
    new_count = limit_entry.get("count", 0) + 1
    
    # Check if should be blocked
    should_block = new_count >= max_attempts
    blocked_until = current_time + block_duration if should_block else 0
    
    # Reset count if not blocked
    if not should_block:
        rate_limits_collection.update_one(
            {"user_id": user_id, "rate_limits.limit_type": limit_type},
            {"$set": {
                "rate_limits.$.count": new_count,
                "rate_limits.$.last_attempt": current_time,
                "rate_limits.$.blocked_until": blocked_until
            }}
        )
        return True, 0
    else:
        # Block the user
        rate_limits_collection.update_one(
            {"user_id": user_id, "rate_limits.limit_type": limit_type},
            {"$set": {
                "rate_limits.$.count": new_count,
                "rate_limits.$.last_attempt": current_time,
                "rate_limits.$.blocked_until": blocked_until
            }}
        )
        return False, block_duration

def reset_rate_limit(user_id, limit_type):
    """Reset rate limit counter for specific user and limit type"""
    rate_limits_collection.update_one(
        {"user_id": user_id, "rate_limits.limit_type": limit_type},
        {"$set": {
            "rate_limits.$.count": 0,
            "rate_limits.$.blocked_until": 0
        }}
    )

# Rate limit decorator
def rate_limit(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # For anonymous users, use IP address as ID
        user_id = session.get('user_id', request.remote_addr)
        
        # Check login rate limit
        is_allowed, retry_after = check_rate_limit(user_id, 'login')
        
        if not is_allowed:
            response = jsonify({
                "error": "Too many login attempts. Please try again later.",
                "retry_after": retry_after
            })
            response.status_code = 429
            return response
            
        return f(*args, **kwargs)
    return decorated_function

# Define a consistent response time to prevent timing attacks
def secure_response_time():
    """Add a small delay to prevent timing attacks"""
    time.sleep(0.05)  # تقليل التأخير من 0.2 إلى 0.05 ثانية

# Constant-time comparison to prevent timing attacks
def constant_time_compare(a, b):
    """Compare two strings in constant time to prevent timing attacks"""
    # تأكد من أن a و b من نوع bytes
    if a is None or b is None:
        return False
        
    if isinstance(a, str):
        a = a.encode('utf-8')
    elif not isinstance(a, bytes):
        return False
        
    if isinstance(b, str):
        b = b.encode('utf-8')
    elif not isinstance(b, bytes):
        return False
        
    return hmac.compare_digest(a, b)

# Functions for CSRF token management
def generate_csrf_token():
    """Generate a new CSRF token and store it in session"""
    import hashlib
    import time
    import base64
    
    # Combine multiple entropy sources for better security
    # Remove current_time from entropy sources to make tokens more stable
    entropy_sources = [
        secrets.token_hex(32),  # Random bytes
        str(session.get('user_id', 'anonymous')),  # User ID
        request.headers.get('User-Agent', ''),  # User agent
        request.remote_addr     # Client IP
    ]
    
    # Create a hash of all entropy sources
    combined_entropy = ''.join(entropy_sources).encode('utf-8')
    raw_token = hashlib.sha256(combined_entropy).hexdigest()
    
    # Store the original token in session for validation
    session['csrf_token'] = raw_token
    session['csrf_token_created'] = time.time()
    
    # Encrypt the token before sending to client
    # Use a simple XOR encryption with a server-side key
    from flask import current_app
    server_key_raw = current_app.config.get('SECRET_KEY', 'default-secret-key')
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
    
    return encrypted_token_b64

def validate_csrf_token(token):
    """Validate the CSRF token from the request against the one in session"""
    # تحقق إذا كان تفعيل CSRF متاح في ملف الإعدادات
    csrf_enabled = os.environ.get('CSRF_ENABLED', 'true').lower() in ('true', '1', 't')
    
    # إذا كان CSRF معطل، إرجاع True دائمًا
    if not csrf_enabled:
        return True
        
    # فحص إذا كان التوكن فارغ
    if not token:
        return False
        
    stored_token = session.get('csrf_token')
    if not stored_token:
        return False
    
    # Decrypt the token from client
    try:
        import base64
        
        # Decode base64
        encrypted_bytes = base64.b64decode(token)
        
        # XOR decryption
        from flask import current_app
        server_key_raw = current_app.config.get('SECRET_KEY', 'default-secret-key')
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
        
    except Exception as e:
        logger.warning(f"Failed to decrypt CSRF token: {e}")
        return False
        
    # استخدام المقارنة بثبات الوقت لمنع هجمات التوقيت
    return constant_time_compare(stored_token, client_token)

# Security helper functions
def is_input_safe(input_str, pattern=r'^[a-zA-Z0-9_\-\.@]+$', max_length=50):
    """التحقق من أن المدخلات آمنة وتتبع نمطاً محدداً"""
    if not input_str or not isinstance(input_str, str):
        return False
    if len(input_str) > max_length:
        return False
    return bool(re.match(pattern, input_str))

def blacklist_token(token, user_id, reason="logout"):
    """إضافة رمز JWT إلى القائمة السوداء"""
    if not token:
        return False
    try:
        # تخزين التوكن في القائمة السوداء مع وقت انتهاء صلاحية
        blacklist_tokens_collection.insert_one({
            "token": token,
            "user_id": user_id,
            "created_at": datetime.utcnow(),
            "reason": reason,
            "expires_at": datetime.utcnow() + timedelta(days=7)  # تخزين لمدة أسبوع بعد انتهاء الصلاحية
        })
        return True
    except Exception as e:
        logger.error(f"Error blacklisting token: {e}")
        return False

def is_token_blacklisted(token):
    """التحقق مما إذا كان الرمز موجوداً في القائمة السوداء"""
    return blacklist_tokens_collection.find_one({"token": token}) is not None

def log_suspicious_activity(user_id, activity_type, details):
    """تسجيل الأنشطة المشبوهة في مصفوفة واحدة لكل مستخدم"""
    try:
        # بيانات النشاط المشبوه الجديد
        new_activity = {
            "ip_address": request.remote_addr,
            "user_agent": request.headers.get("User-Agent", "Unknown"),
            "activity_type": activity_type,
            "details": details,
            "timestamp": datetime.utcnow()
        }
        
        # البحث عن سجل موجود أو إنشاء واحد جديد
        result = suspicious_activity_collection.update_one(
            {"user_id": user_id},
            {
                "$push": {"activities": new_activity},
                "$setOnInsert": {"created_at": datetime.utcnow()},
                "$set": {"last_updated": datetime.utcnow()}
            },
            upsert=True
        )
        
        # التحقق من عدد الأنشطة المشبوهة خلال الـ 24 ساعة الماضية
        suspicious_user = suspicious_activity_collection.find_one({"user_id": user_id})
        if suspicious_user:
            # حساب عدد الأنشطة خلال الـ 24 ساعة الماضية
            time_threshold = datetime.utcnow() - timedelta(hours=24)
            recent_activities = [
                activity for activity in suspicious_user.get("activities", [])
                if activity.get("timestamp") >= time_threshold
            ]
            
            # إذا كان هناك 10 أنشطة مشبوهة أو أكثر في الـ 24 ساعة الماضية
            if len(recent_activities) >= 10:
                users_collection.update_one(
                    {"user_id": user_id},
                    {"$set": {"ban": True, "ban_reason": "Suspicious activity detected"}}
                )
                logger.warning(f"User {user_id} automatically banned due to suspicious activity")
                
    except Exception as e:
        logger.error(f"Error logging suspicious activity: {e}")

# Middleware decorator to require HTTPS
def require_https(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # تحقق من إعدادات FORCE_HTTPS في ملف البيئة
        force_https = os.environ.get('FORCE_HTTPS', 'false').lower() in ('true', '1', 't')
        
        # تطبيق التحقق فقط إذا كان FORCE_HTTPS مفعل
        if force_https and not request.is_secure and os.getenv("FLASK_ENV") == "production":
            response = jsonify({"error": "HTTPS is required for security"})
            response.status_code = 403
            return response
        return f(*args, **kwargs)
    return decorated_function

# Security headers function
def add_security_headers_to_response(response):
    """Add security headers to an existing response"""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'; upgrade-insecure-requests;"
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    return response

def add_security_headers():
    """Create a response with security headers"""
    response = jsonify({})
    return add_security_headers_to_response(response)

# User authentication tracking in separate collection
def track_user_login(user_id, success=True, reason=None):
    """تتبع محاولات تسجيل الدخول بطريقة ذكية، تجمع حسب المستخدم وعنوان IP"""
    try:
        ip_address = request.remote_addr
        user_agent_string = request.headers.get("User-Agent", "Unknown")
        current_time = datetime.utcnow()
        
        # Get the real IP address if behind proxy
        real_ip = ip_address
        if request.headers.get('X-Forwarded-For'):
            real_ip = request.headers.get('X-Forwarded-For').split(',')[0].strip()
            
        # If IP is localhost or internal, try to get real external IP
        if real_ip in ['127.0.0.1', 'localhost'] or real_ip.startswith('192.168.') or real_ip.startswith('10.'):
            try:
                # Try external IP detection services in order
                try:
                    ip_response = requests.get('https://api.ipify.org?format=json', timeout=3)
                    if ip_response.status_code == 200:
                        real_ip = ip_response.json().get('ip')
                except:
                    pass
                
                # If first service fails, try backup
                if real_ip in ['127.0.0.1', 'localhost'] or real_ip.startswith('192.168.') or real_ip.startswith('10.'):
                    try:
                        ip_response = requests.get('https://api64.ipify.org?format=json', timeout=3)
                        if ip_response.status_code == 200:
                            real_ip = ip_response.json().get('ip')
                    except:
                        pass
                
                # Try third service if needed
                if real_ip in ['127.0.0.1', 'localhost'] or real_ip.startswith('192.168.') or real_ip.startswith('10.'):
                    try:
                        ip_response = requests.get('https://ifconfig.me/ip', timeout=3)
                        if ip_response.status_code == 200:
                            real_ip = ip_response.text.strip()
                    except:
                        pass
            except Exception as e:
                logger.error(f"Error detecting external IP: {e}")
                
        # Get location info based on IP
        location_info = "Unknown Location"
        try:
            # Get API tokens from environment variables
            api_tokens = [
                os.environ.get('IPINFO_API_TOKEN_1', ''),
                os.environ.get('IPINFO_API_TOKEN_2', ''),
                os.environ.get('IPINFO_API_TOKEN_3', '')
            ]
            
            # Choose a random valid token
            token = random.choice([t for t in api_tokens if t])
            
            if token:
                # Get location data
                response = requests.get(f'https://ipinfo.io/{real_ip}/json?token={token}', timeout=3)
                if response.status_code == 200:
                    ip_data = response.json()
                    country = ip_data.get('country', '')
                    city = ip_data.get('city', '')
                    if country and city:
                        location_info = f"{city}, {country}"
                    elif country:
                        location_info = country
        except Exception as e:
            logger.error(f"Error getting location info: {e}")

        # Parse user agent to extract device and browser information
        device_info = "Unknown Device"
        try:
            # Extract OS information
            os_info = "Unknown OS"
            if "Windows" in user_agent_string:
                os_info = "Windows PC"
            elif "Macintosh" in user_agent_string:
                os_info = "Mac"
            elif "iPhone" in user_agent_string:
                os_info = "iPhone"
            elif "iPad" in user_agent_string:
                os_info = "iPad"
            elif "Android" in user_agent_string:
                if "Mobile" in user_agent_string:
                    os_info = "Android Phone"
                else:
                    os_info = "Android Tablet"
            elif "Linux" in user_agent_string:
                os_info = "Linux"

            # Extract browser information
            browser_info = "Unknown Browser"
            if "Chrome" in user_agent_string and "Edg" in user_agent_string:
                browser_info = "Edge"
            elif "Chrome" in user_agent_string and "OPR" in user_agent_string:
                browser_info = "Opera"
            elif "Chrome" in user_agent_string and "Safari" in user_agent_string and "Brave" not in user_agent_string:
                browser_info = "Chrome"
            elif "Firefox" in user_agent_string:
                browser_info = "Firefox"
            elif "Safari" in user_agent_string and "Chrome" not in user_agent_string:
                browser_info = "Safari"
            elif "Brave" in user_agent_string:
                browser_info = "Brave"
            elif "Edg" in user_agent_string:
                browser_info = "Edge"

            # Combine all information
            device_info = f"{os_info} - {browser_info} | {location_info} | IP: {real_ip}"
        except Exception as e:
            logger.error(f"Error parsing user agent: {e}")
            # Fall back to Unknown Device

        # بيانات محاولة تسجيل الدخول الجديدة
        new_login_attempt = {
            "timestamp": current_time,
            "success": success,
            "reason": reason,
            "user_id": user_id,  # حفظ معرف المستخدم في المحاولة لسهولة الفرز والتحليل
            "device_info": device_info,  # Add device info to the login attempt
            "ip_address": real_ip,
            "location": location_info
        }
        
        # البحث عن سجل موجود بناءً على عنوان IP والمتصفح
        # هذا يساعد في تتبع محاولات التخمين من نفس المصدر
        login_record = user_login_history_collection.find_one({
            "ip_address": ip_address,
            "user_agent": user_agent_string,
            "last_updated": {"$gte": current_time - timedelta(hours=24)}  # نبحث في نطاق 24 ساعة
        })
        
        if login_record:
            # تحديث السجل الموجود - نفس مصدر المحاولات
            user_login_history_collection.update_one(
                {"_id": login_record["_id"]},
                {
                    "$push": {"login_attempts": new_login_attempt},
                    "$set": {"last_updated": current_time}
                }
            )
            
            # فحص للمحاولات المتكررة من نفس المصدر
            if not success and len(login_record.get("login_attempts", [])) > 5:
                # توثيق نشاط مشبوه بسبب محاولات متكررة من نفس IP
                log_suspicious_activity(
                    user_id,
                    "multiple_failed_attempts",
                    f"Multiple failed login attempts from same IP: {ip_address}"
                )
        else:
            # إنشاء سجل جديد
            user_login_history_collection.insert_one({
                "ip_address": ip_address,
                "user_agent": user_agent_string,
                "created_at": current_time,
                "last_updated": current_time,
                "login_attempts": [new_login_attempt]
            })
        
        # Return login information for successful logins
        if success:
            return device_info, real_ip, location_info
        
    except Exception as e:
        logger.error(f"Error tracking user login: {e}")
        return "Unknown Device", "", ""

# Add a function to verify 2FA codes similar to transfers.py
def verify_2fa_code(secret, verification_code):
    """
    Verify a 2FA code against a secret
    Returns True if valid, False otherwise
    
    This is a utility function used in login/authentication flows.
    It's important to note that the API endpoints themselves need to
    return appropriate HTTP status codes (401, 403) rather than just
    returning True/False or is_valid flags in the response body.
    
    See other verification endpoints for proper usage patterns.
    """
    if not secret:
        return False
    
    # Convert verification_code to string if it's not already
    verification_code = str(verification_code)
    
    # Create a TOTP object with the user's secret
    totp = pyotp.TOTP(secret)
    
    # Get current time
    current_time = int(time.time())
    
    # First try with a tight window for maximum security
    if totp.verify(verification_code, valid_window=2):
        logger.info("2FA code verified with tight window")
        return True
        
    # If failed, check if it's a clock skew issue by checking previous and next codes
    expected_totp = totp.at(current_time)
    prev_totp = totp.at(current_time - 30)
    next_totp = totp.at(current_time + 30)
    
    logger.info(f"2FA Debug: User provided: {verification_code}, Expected: {expected_totp}, Previous: {prev_totp}, Next: {next_totp}, Timestamp: {current_time}")
    
    # For slightly out-of-sync clocks, try with a slightly larger window as fallback
    # valid_window=4 allows for 2 minutes each way (4 periods of 30 seconds)
    # This balances security with usability for users with clock sync issues
    return totp.verify(verification_code, valid_window=4)

def validate_login_restrictions(user_data):
    """
    Validate if the login request can proceed based on time, geo, and IP restrictions
    Returns: (is_allowed, error_message)
    """
    # If user is not premium, skip these checks
    if not user_data.get('premium', False):
        return True, None
        
    # Check time-based access restriction
    time_based_access = user_data.get('time_based_access', {})
    if time_based_access.get('enabled', False):
        # Get the timezone from user data or default to UTC
        user_timezone = time_based_access.get('timezone', 'UTC')
        
        try:
            # Import necessary modules for timezone handling
            from datetime import datetime
            import pytz
            
            # Get current time in user's timezone
            utc_now = datetime.now(pytz.UTC)
            user_tz = pytz.timezone(user_timezone)
            local_now = utc_now.astimezone(user_tz)
            current_time = local_now.strftime('%H:%M')
            
            # Get access time window
            start_time = time_based_access.get('start_time', '07:00')
            end_time = time_based_access.get('end_time', '19:00')
            
            # Convert to 12-hour format for display in error message
            def to_12h_format(time_24h):
                hour, minute = map(int, time_24h.split(':'))
                period = "AM" if hour < 12 else "PM"
                hour = hour % 12
                if hour == 0:
                    hour = 12
                return f"{hour}:{minute:02d} {period}"
            
            start_time_12h = to_12h_format(start_time)
            end_time_12h = to_12h_format(end_time)
            
            # Compare times
            if current_time < start_time or current_time > end_time:
                return False, f"Access denied: Your wallet is only accessible between {start_time_12h} and {end_time_12h} in your local time ({user_timezone})"
        except Exception as e:
            # Log the error but don't block access in case of time calculation failure
            logging.error(f"Error checking time-based access: {e}")
    
    # Check geo-location restriction
    geo_lock = user_data.get('geo_lock', {})
    if geo_lock.get('enabled', False):
        # Get user's IP address - using same IP detection method as IP whitelist
        ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        
        # If IP is localhost or internal, try to get real external IP
        if ip in ['127.0.0.1', 'localhost'] or ip.startswith('192.168.') or ip.startswith('10.'):
            try:
                # Try external IP detection services in order
                try:
                    ip_response = requests.get('https://api.ipify.org?format=json', timeout=3)
                    if ip_response.status_code == 200:
                        ip = ip_response.json().get('ip')
                except:
                    pass
                
                # If first service fails, try backup
                if ip in ['127.0.0.1', 'localhost'] or ip.startswith('192.168.') or ip.startswith('10.'):
                    try:
                        ip_response = requests.get('https://api64.ipify.org?format=json', timeout=3)
                        if ip_response.status_code == 200:
                            ip = ip_response.json().get('ip')
                    except:
                        pass
                
                # Try third service if needed
                if ip in ['127.0.0.1', 'localhost'] or ip.startswith('192.168.') or ip.startswith('10.'):
                    try:
                        ip_response = requests.get('https://ifconfig.me/ip', timeout=3)
                        if ip_response.status_code == 200:
                            ip = ip_response.text.strip()
                    except:
                        pass
                        
                logging.info(f"External IP detection for geo-lock check: {ip}")
            except Exception as e:
                logging.error(f"Error detecting external IP for geo-lock: {e}")
        
        # Use IPinfo.io to get country information
        api_tokens = os.environ.get('IPINFO_API_TOKEN_1', ''), os.environ.get('IPINFO_API_TOKEN_2', ''), os.environ.get('IPINFO_API_TOKEN_3', '')
        token = random.choice([t for t in api_tokens if t])  # Choose a random valid token
        
        try:
            response = requests.get(f'https://ipinfo.io/{ip}?token={token}')
            if response.status_code == 200:
                ip_data = response.json()
                user_country = ip_data.get('country', '')
                
                # Check for countries list (new format)
                allowed_countries = geo_lock.get('countries', [])
                
                # Check for country field (old format) for backward compatibility
                if not allowed_countries and geo_lock.get('country'):
                    allowed_countries = [geo_lock.get('country')]
                
                # Get country details for better error message
                country_details = geo_lock.get('country_details', [])
                country_names = [detail.get('country_name', code) for detail, code in 
                               zip(country_details, allowed_countries) if detail.get('country_code') == code]
                country_names = [name for name in country_names if name]  # Filter out empty names
                
                # If we have names, use them, otherwise use codes
                display_countries = country_names if country_names else allowed_countries
                
                # Log for debugging
                logging.info(f"GeoLock check: User country={user_country}, Allowed countries={allowed_countries}")
                
                if user_country and allowed_countries and user_country not in allowed_countries:
                    if len(display_countries) == 1:
                        return False, f"Access denied: Your wallet is only accessible from {display_countries[0]}"
                    else:
                        countries_str = ", ".join(display_countries[:-1]) + " or " + display_countries[-1]
                        return False, f"Access denied: Your wallet is only accessible from {countries_str}"
        except Exception as e:
            # Log the error but don't block access in case of API failure
            logging.error(f"Error checking geo-location: {e}")
    
    # Check IP whitelist restriction
    ip_whitelist = user_data.get('ip_whitelist', {})
    if ip_whitelist.get('enabled', False) and ip_whitelist.get('ips'):
        # Get user's IP address - try multiple methods to get real external IP
        ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        
        # If IP is localhost or internal, try to get real external IP
        if ip in ['127.0.0.1', 'localhost'] or ip.startswith('192.168.') or ip.startswith('10.'):
            try:
                # Try external IP detection services in order
                try:
                    ip_response = requests.get('https://api.ipify.org?format=json', timeout=3)
                    if ip_response.status_code == 200:
                        ip = ip_response.json().get('ip')
                except:
                    pass
                
                # If first service fails, try backup
                if ip in ['127.0.0.1', 'localhost'] or ip.startswith('192.168.') or ip.startswith('10.'):
                    try:
                        ip_response = requests.get('https://api64.ipify.org?format=json', timeout=3)
                        if ip_response.status_code == 200:
                            ip = ip_response.json().get('ip')
                    except:
                        pass
                
                # Try third service if needed
                if ip in ['127.0.0.1', 'localhost'] or ip.startswith('192.168.') or ip.startswith('10.'):
                    try:
                        ip_response = requests.get('https://ifconfig.me/ip', timeout=3)
                        if ip_response.status_code == 200:
                            ip = ip_response.text.strip()
                    except:
                        pass
                        
                logging.info(f"External IP detection for whitelist check: {ip}")
            except Exception as e:
                logging.error(f"Error detecting external IP: {e}")
        
        # Check if IP is in whitelist
        allowed_ips = ip_whitelist.get('ips', [])
        logging.info(f"IP Whitelist check: User IP={ip}, Allowed IPs={allowed_ips}")
        if ip not in allowed_ips:
            return False, f"Access denied: Your IP address ({ip}) is not whitelisted"
    
    # All checks passed
    return True, None

@login_bp.route('/api/login', methods=['POST'])
@rate_limit
@require_https
def login():
    """Handle wallet login with username and password"""
    # Check if the request contains JSON data
    if not request.is_json:
        response = jsonify({"error": "Invalid request format"})
        add_security_headers_to_response(response)
        return response, 400
    
    # Get user IP or ID for rate limiting
    user_id = session.get('user_id', request.remote_addr)
    
    # Validate CSRF token
    csrf_token = request.headers.get('X-CSRF-Token')
    if not validate_csrf_token(csrf_token):
        new_token = generate_csrf_token()
        response = jsonify({
            'error': 'Invalid or missing CSRF token',
            'csrf_token': new_token
        })
        add_security_headers_to_response(response)
        return response, 403
        
    # Get credentials from request
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        password = data.get('password', '')
        verification_code = data.get('verification_code')
        secret_word = data.get('secret_word')
        remember_me = data.get('remember_me', False)  # Get the remember_me parameter
    except Exception as e:
        logger.warning(f"Failed to parse login request: {e}")
        log_suspicious_activity(user_id, "invalid_json", "Failed to parse login request")
        response = jsonify({"error": "Invalid request data"})
        return add_security_headers_to_response(response), 400
    
    # Validate input
    if not username or not password:
        log_suspicious_activity(user_id, "empty_credentials", "Empty username or password")
        response = jsonify({"error": "Invalid credentials"})
        return add_security_headers_to_response(response), 400
    
    # Input validation - التحقق من صحة المدخلات لمنع حقن NoSQL
    if not is_input_safe(username) or len(password) > 100:
        log_suspicious_activity(user_id, "injection_attempt", f"Invalid input format: username={username[:10]}...")
        response = jsonify({"error": "Invalid credentials"})
        return add_security_headers_to_response(response), 400
    
    try:
        # Check if user exists and password matches
        user = users_collection.find_one({"username": username})
        
        if not user:
            # Use generic error message that doesn't reveal if username exists
            logger.info(f"Failed login attempt: Username '{username}' not found")
            secure_response_time()  # Add delay to prevent timing attacks
            # Track failed login attempt in separate collection
            track_user_login(username, success=False, reason="user_not_found")
            response = jsonify({"error": "Invalid credentials"})
            return add_security_headers_to_response(response), 401
        
        # Check if the user is authenticated with Discord and attempting to use another wallet
        discord_user_id = session.get('user_id')
        is_discord_auth = session.get('discord_authenticated', False)
        
        # If user is authenticated with Discord, ensure they're only using their own wallet
        if is_discord_auth and discord_user_id and discord_user_id != user.get('user_id'):
            logger.warning(f"Discord user {discord_user_id} attempted to access wallet of user {user.get('user_id')}")
            log_suspicious_activity(discord_user_id, "wallet_mismatch", 
                                   f"Discord user attempted to access different wallet: {username}")
            
            # Track failed login attempt
            track_user_login(discord_user_id, success=False, reason="wallet_mismatch")
            
            secure_response_time()  # Add delay to prevent timing attacks
            response = jsonify({"error": "Invalid credentials"})
            return add_security_headers_to_response(response), 401
        
        # Verify password (keeping it unencrypted as requested)
        if user.get('password') != password:
            # Use generic error message
            logger.info(f"Failed login attempt: Incorrect password for user '{username}'")
            log_suspicious_activity(user_id, "wrong_password", f"Failed login attempt for user: {username}")
            # Track failed login attempt in separate collection
            track_user_login(user['user_id'], success=False, reason="wrong_password")
            secure_response_time()  # Add delay to prevent timing attacks
            response = jsonify({"error": "Invalid credentials"})
            return add_security_headers_to_response(response), 401
        
        # Username and password are correct, reset the rate limit counter
        # This prevents the rate limit from blocking on additional auth steps
        reset_rate_limit(user_id, 'login')
        
        # Check if account is banned
        if user.get('ban'):
            secure_response_time()  # Add delay to prevent timing attacks
            response = jsonify({"error": "This account has been temporarily suspended. Please contact support."})
            return add_security_headers_to_response(response), 403
        
        # Check if wallet is locked
        if user.get('wallet_lock'):
            secure_response_time()  # Add delay to prevent timing attacks
            response = jsonify({"error": "Your wallet is currently locked. Please contact support."})
            return add_security_headers_to_response(response), 403
        
        # Check time-based, geo-lock, and IP whitelist restrictions
        # Only if all other credentials are valid and this is not a 2FA or secret_word step
        if not verification_code and not secret_word:
            is_allowed, error_message = validate_login_restrictions(user)
            if not is_allowed:
                log_suspicious_activity(user['user_id'], "access_restriction", error_message)
                response = jsonify({"error": error_message})
                return add_security_headers_to_response(response), 403
        
        # Store the authenticated user ID in session to prevent rate limiting on 2FA steps
        session['authenticated_user_id'] = user['user_id']
        
        # Check for additional authentication requirements
        login_auth = user.get('login_auth', {'none': True, '2fa': False, 'secret_word': False})
        
        # If 2FA is enabled and verification code is not provided
        if login_auth.get('2fa', False) and not verification_code:
            response = jsonify({
                "message": "2FA required",
                "requires_2fa": True,
                "user_id": user['user_id'],
                "partial_auth": True
            })
            return add_security_headers_to_response(response), 200
            
        # If 2FA is enabled and verification code is provided, verify it
        if login_auth.get('2fa', False) and verification_code:
            # Check if user has 2FA activated
            if not user.get('2fa_activated', False) or not user.get('2fa_secret'):
                response = jsonify({"error": "Invalid credentials"})
                return add_security_headers_to_response(response), 400
                
            # Verify the 2FA code using the proper verification method
            if not verify_2fa_code(user['2fa_secret'], verification_code):
                # Track failed login attempt
                track_user_login(user['user_id'], success=False, reason="invalid_2fa")
                log_suspicious_activity(user_id, "invalid_2fa", f"Failed 2FA verification for user: {username}")
                response = jsonify({"error": "Invalid credentials"})
                return add_security_headers_to_response(response), 401
                
            # 2FA is valid, check restrictions now if we haven't checked yet
            is_allowed, error_message = validate_login_restrictions(user)
            if not is_allowed:
                log_suspicious_activity(user['user_id'], "access_restriction", error_message)
                response = jsonify({"error": error_message})
                return add_security_headers_to_response(response), 403
        
        # If secret word is enabled and not provided
        if login_auth.get('secret_word', False) and not secret_word:
            response = jsonify({
                "message": "Secret word required",
                "requires_secret_word": True,
                "user_id": user['user_id'],
                "partial_auth": True
            })
            return add_security_headers_to_response(response), 200
            
        # If secret word is enabled and provided, verify it
        if login_auth.get('secret_word', False) and secret_word:
            # Check if user has a secret word
            if not user.get('secret_word'):
                response = jsonify({"error": "Invalid credentials"})
                return add_security_headers_to_response(response), 400
                
            # Verify the secret word using exact comparison (as in transfers.py)
            if secret_word != user['secret_word']:
                # Track failed login attempt
                track_user_login(user['user_id'], success=False, reason="invalid_secret_word")
                log_suspicious_activity(user_id, "invalid_secret_word", f"Failed secret word verification for user: {username}")
                response = jsonify({"error": "Invalid credentials"})
                return add_security_headers_to_response(response), 401
                
            # Secret word is valid, check restrictions now if we haven't checked yet
            is_allowed, error_message = validate_login_restrictions(user)
            if not is_allowed:
                log_suspicious_activity(user['user_id'], "access_restriction", error_message)
                response = jsonify({"error": error_message})
                return add_security_headers_to_response(response), 403
        
        # If we get to a successful login point:
        # Check for user's auto_signin preference if remember_me isn't explicitly set
        if not remember_me and user.get('auto_signin', {}).get('enabled', False):
            # Use the user's auto_signin settings
            remember_me = True
            logger.info(f"Using auto sign-in preference for user {username}")
        
        # User authenticated successfully
        # Reset rate limit on successful login - (already done above now)
        
        # Track successful login in separate collection instead of updating user document
        # The track_user_login function now returns login information for successful logins
        device_info, login_ip, login_location = track_user_login(user['user_id'], success=True)
        
        # Update last login timestamp and device info
        timestamp = datetime.utcnow().isoformat() + "Z"
        users_collection.update_one(
            {"_id": user["_id"]},
            {"$set": {
                "last_login": timestamp,
                "last_device_info": device_info,
                "last_login_ip": login_ip,
                "last_login_location": login_location
            }}
        )
        
        # Register device in session devices system
        try:
            # Import the session_devices module
            from backend.cryptonel.session_devices import register_current_device
            
            # Register the current device for this user
            register_current_device(user['user_id'])
        except Exception as e:
            logger.error(f"Failed to register device session: {e}")
        
        # Set wallet authentication flag in session
        session['wallet_authenticated'] = True
        
        # Create JWT tokens with remember_me parameter
        tokens = create_tokens(
            user_id=user['user_id'],
            username=user.get('username'),
            premium=user.get('premium', False),
            remember_me=remember_me  # Pass the remember_me parameter
        )
        
        # Return tokens in response
        response = jsonify({
            "message": "Authentication successful",
            "access_token": tokens['access_token'],
            "refresh_token": tokens['refresh_token'],
            "user": {
                "user_id": user['user_id'],
                "username": user['username'],
                "wallet_id": user.get('wallet_id'),
                "balance": user.get('balance', "0.00"),
                "premium": user.get('premium', False),
                "membership": user.get('membership', "Standard"),
                "account_type": user.get('account_type', "Cryptonel Client")
            }
        })
        return add_security_headers_to_response(response), 200
    
    except Exception as e:
        logger.error(f"Login error: {e}")
        response = jsonify({"error": "An error occurred during authentication"})
        return add_security_headers_to_response(response), 500

# Logout endpoint
@login_bp.route('/api/logout', methods=['POST'])
@require_https
def logout():
    """تسجيل خروج المستخدم وإلغاء الرمز"""
    # التحقق من وجود الرمز في الطلب
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        response = jsonify({"error": "Authorization token is required"})
        return add_security_headers_to_response(response), 401
    
    token = auth_header.split(' ')[1]
    user_id = session.get('user_id', request.remote_addr)
    
    try:
        # Bulk operations for improved performance
        operations = []
        
        # 1. إضافة الرمز إلى القائمة السوداء (ضروري لأمان النظام)
        if blacklist_token(token, user_id):
            # 2. Bulk update: تحديث حالة كل الأجهزة المرتبطة بالمستخدم الحالي
            try:
                # دمج عمليات تسجيل الخروج مع تحديث الجلسات في MongoDB
                from backend.cryptonel.session_devices import device_sessions_collection
                
                # Get current device ID from session
                current_device_id = session.get('device_id')
                
                if current_device_id:
                    # تحديث الجهاز الحالي فقط كـ "logged_out"
                    device_sessions_collection.update_one(
                        {"user_id": user_id, "devices.device_id": current_device_id},
                        {"$set": {
                            "devices.$.status": "logged_out",
                            "devices.$.logout_time": datetime.utcnow().isoformat() + "Z"
                        }}
                    )
                    
                    # تنظيف مفاتيح التخزين المؤقت للجهاز
                    try:
                        from backend.utils import cache_utils
                        # Clear device cache
                        session_id = session.get('session_id')
                        if session_id:
                            cache_utils.cache_delete(f"device_session:{user_id}:{session_id}")
                        
                        # Clear device list cache
                        cache_utils.cache_delete(f"device_list:{user_id}")
                        
                        # Clear last activity cache
                        if session_id:
                            cache_utils.cache_delete(f"last_activity_update:{user_id}:{session_id}")
                    except Exception as e:
                        logger.error(f"Error clearing device caches: {e}")
                
            except (ImportError, Exception) as e:
                logger.error(f"Error updating device sessions during logout: {e}")
            
            # مسح الجلسة
            session.clear()
            response = jsonify({"message": "Successfully logged out"})
            return add_security_headers_to_response(response), 200
        else:
            response = jsonify({"error": "Failed to logout"})
            return add_security_headers_to_response(response), 500
    except Exception as e:
        logger.error(f"Exception during logout: {e}")
        response = jsonify({"error": "Failed to logout"})
        return add_security_headers_to_response(response), 500

# Reset lockout endpoint
@login_bp.route('/api/login/reset-lockout', methods=['POST'])
@require_https
def reset_lockout():
    """Reset login attempt counters and lockout for a user"""
    try:
        # Get user IP or ID for rate limiting
        user_id = session.get('user_id', request.remote_addr)
        
        # Validate CSRF token
        csrf_token = request.headers.get('X-CSRF-Token')
        if not validate_csrf_token(csrf_token):
            new_token = generate_csrf_token()
            response = jsonify({
                'error': 'Invalid or missing CSRF token',
                'csrf_token': new_token
            })
            add_security_headers_to_response(response)
            return response, 403
        
        # Reset rate limit for the user
        reset_rate_limit(user_id, 'login')
        
        # Log this action
        logger.info(f"Rate limit reset requested for user/IP: {user_id}")
        
        # Return success response
        response = jsonify({"message": "Lockout has been reset successfully"})
        return add_security_headers_to_response(response), 200
    except Exception as e:
        logger.error(f"Error resetting lockout: {e}")
        response = jsonify({"error": "An error occurred while resetting lockout"})
        return add_security_headers_to_response(response), 500

# Check rate limit status
@login_bp.route('/api/auth/check-rate-limit', methods=['GET'])
@require_https
def check_rate_limit_status():
    """Check if the current user is rate limited"""
    try:
        # Get user ID or IP address
        user_id = session.get('user_id', request.remote_addr)
        
        # Find user's rate limits document
        user_limits = rate_limits_collection.find_one({"user_id": user_id})
        
        if not user_limits:
            # No rate limit document - user is not limited
            return jsonify({"is_limited": False, "retry_after": 0}), 200
        
        # Look for login rate limit
        current_time = time.time()
        is_limited = False
        retry_after = 0
        
        for limit in user_limits.get("rate_limits", []):
            if limit.get("limit_type") == "login" and limit.get("blocked_until", 0) > current_time:
                is_limited = True
                retry_after = int(limit.get("blocked_until") - current_time)
                break
        
        # If we found a rate limit, return the status
        return jsonify({
            "is_limited": is_limited,
            "retry_after": retry_after
        }), 200
    
    except Exception as e:
        logger.error(f"Error checking rate limit status: {e}")
        return jsonify({"error": "An error occurred while checking rate limit status"}), 500

# Add a new endpoint to get authentication methods for a user
@login_bp.route('/api/login/auth-methods', methods=['POST'])
@require_https
def get_auth_methods():
    """Get authentication methods for a user"""
    if not request.is_json:
        response = jsonify({"error": "Invalid request format"})
        return add_security_headers_to_response(response), 400
        
    # Validate CSRF token
    csrf_token = request.headers.get('X-CSRF-Token')
    if not validate_csrf_token(csrf_token):
        new_token = generate_csrf_token()
        response = jsonify({
            'error': 'Invalid or missing CSRF token',
            'csrf_token': new_token
        })
        return add_security_headers_to_response(response), 403
        
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        
        if not username:
            response = jsonify({"error": "Username is required"})
            return add_security_headers_to_response(response), 400
            
        if not is_input_safe(username):
            response = jsonify({"error": "Invalid username format"})
            return add_security_headers_to_response(response), 400
            
        # Find user and get their auth methods
        user = users_collection.find_one({"username": username})
        
        if not user:
            # Don't reveal if username exists or not
            secure_response_time()
            response = jsonify({"requires_password": True})
            return add_security_headers_to_response(response), 200
            
        # Get login auth methods, default to password only if not specified
        login_auth = user.get('login_auth', {'none': True, '2fa': False, 'secret_word': False})
        
        response = jsonify({
            "requires_password": True,
            "requires_2fa": login_auth.get('2fa', False),
            "requires_secret_word": login_auth.get('secret_word', False)
        })
        return add_security_headers_to_response(response), 200
        
    except Exception as e:
        logger.error(f"Error getting auth methods: {e}")
        response = jsonify({"error": "An error occurred"})
        return add_security_headers_to_response(response), 500

# Define a different decorator for 2FA/second-factor operations to prevent rate limiting conflicts
def second_factor_rate_limit(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # If user is already authenticated with username/password, skip rate limit
        if session.get('authenticated_user_id'):
            return f(*args, **kwargs)
            
        # Otherwise apply regular rate limit
        user_id = session.get('user_id', request.remote_addr)
        is_allowed, retry_after = check_rate_limit(user_id, 'login')
        
        if not is_allowed:
            response = jsonify({
                "error": "Too many attempts. Please try again later.",
                "retry_after": retry_after
            })
            response.status_code = 429
            return response
            
        return f(*args, **kwargs)
    return decorated_function

def get_location_info(ip_address):
    """
    Get location information from IP address
    Enhanced with multiple fallbacks and better error handling
    """
    try:
        # Skip for local IPs
        if ip_address == '127.0.0.1' or ip_address == 'localhost' or ip_address.startswith('192.168.') or ip_address.startswith('10.'):
            return {"country": "Local", "city": "Development", "location": "Local Environment"}
            
        # Try multiple services with increased timeout and retries
        services = [
            # Try ipinfo.io with multiple tokens
            {"url": "https://ipinfo.io/{ip}/json?token=ec2560bf0ec1b2", "timeout": 10},
            {"url": "https://ipinfo.io/{ip}/json", "timeout": 10},  # Fallback without token
            {"url": "https://ipapi.co/{ip}/json/", "timeout": 10},
            {"url": "https://ip-api.com/json/{ip}", "timeout": 10},
            {"url": "https://freegeoip.app/json/{ip}", "timeout": 10}
        ]
        
        # Try each service with up to 2 retries
        max_retries = 2
        
        for service in services:
            for attempt in range(max_retries):
                try:
                    url = service["url"].format(ip=ip_address)
                    timeout = service["timeout"]
                    
                    response = requests.get(url, timeout=timeout)
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        # Extract location data based on the API format
                        if "ipinfo.io" in url:
                            return {
                                "country": data.get("country", "Unknown"),
                                "city": data.get("city", "Unknown"),
                                "region": data.get("region", "Unknown"),
                                "location": data.get("loc", "Unknown"),
                                "timezone": data.get("timezone", "Unknown"),
                                "source": "ipinfo.io"
                            }
                        elif "ipapi.co" in url:
                            return {
                                "country": data.get("country_name", "Unknown"),
                                "city": data.get("city", "Unknown"),
                                "region": data.get("region", "Unknown"),
                                "location": f"{data.get('latitude', 0)},{data.get('longitude', 0)}",
                                "timezone": data.get("timezone", "Unknown"),
                                "source": "ipapi.co"
                            }
                        elif "ip-api.com" in url:
                            return {
                                "country": data.get("country", "Unknown"),
                                "city": data.get("city", "Unknown"),
                                "region": data.get("regionName", "Unknown"),
                                "location": f"{data.get('lat', 0)},{data.get('lon', 0)}",
                                "timezone": data.get("timezone", "Unknown"),
                                "source": "ip-api.com"
                            }
                        else:
                            # Generic extraction for other APIs
                            location = "Unknown"
                            if "loc" in data:
                                location = data["loc"]
                            elif "latitude" in data and "longitude" in data:
                                location = f"{data['latitude']},{data['longitude']}"
                            elif "lat" in data and "lon" in data:
                                location = f"{data['lat']},{data['lon']}"
                                
                            return {
                                "country": data.get("country", data.get("country_name", "Unknown")),
                                "city": data.get("city", "Unknown"),
                                "region": data.get("region", data.get("regionName", "Unknown")),
                                "location": location,
                                "timezone": data.get("timezone", "Unknown"),
                                "source": url.split("//")[1].split("/")[0]
                            }
                except Exception as e:
                    # Log the error but continue to next attempt or service
                    if attempt == max_retries - 1:  # Only log on last attempt
                        logger.warning(f"Failed to get location from {service['url']} (attempt {attempt+1}/{max_retries}): {str(e)}")
                    
                    # Wait before retrying
                    if attempt < max_retries - 1:
                        time.sleep(1)  # 1 second delay between retries
                    continue
        
        # If all services fail, return default data
        logger.error(f"All location services failed for IP {ip_address}")
        return {"country": "Unknown", "city": "Unknown", "location": "Unknown"}
    except Exception as e:
        logger.error(f"Error getting location info: {str(e)}")
        return {"country": "Error", "city": "Error", "location": "Error"}

def init_app(app):
    """Initialize the login blueprint with the Flask app"""
    # Set session lifetime
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)  # Changed from 1 hour to 24 hours
    app.config['SESSION_COOKIE_SECURE'] = True
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    
    # إنشاء فهرس TTL لإزالة التوكن المنتهية تلقائياً من blacklist
    try:
        blacklist_tokens_collection.create_index("expires_at", expireAfterSeconds=0)
        logger.info("Created TTL index for blacklisted tokens")
    except Exception as e:
        logger.warning(f"Could not create TTL index: {e}")
    
    # تنظيف البيانات منتهية الصلاحية عند بدء التشغيل
    try:
        # حذف توكن منتهية الصلاحية
        blacklist_tokens_collection.delete_many({"expires_at": {"$lt": datetime.utcnow()}})
        logger.info("Cleaned up expired blacklisted tokens")
    except Exception as e:
        logger.error(f"Error cleaning up expired data: {e}")
    
    # إضافة دالة تنظيف قبل كل طلب (مرة واحدة كل ساعة)
    cleanup_last_run = [0]  # استخدام قائمة لتخزين الوقت

    @app.before_request
    def cleanup_expired_tokens():
        # تنفيذ التنظيف مرة واحدة كل ساعة فقط
        current_time = time.time()
        if current_time - cleanup_last_run[0] > 3600:  # 3600 ثانية = ساعة واحدة
            try:
                blacklist_tokens_collection.delete_many({"expires_at": {"$lt": datetime.utcnow()}})
                cleanup_last_run[0] = current_time
            except Exception as e:
                logger.error(f"Error in periodic cleanup: {e}")
    
    # Register blueprint
    app.register_blueprint(login_bp)