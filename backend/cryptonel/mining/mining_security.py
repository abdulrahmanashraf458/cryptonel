import os
import json
import datetime
import ipaddress
from flask import Blueprint, jsonify, request, session
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import DuplicateKeyError
from dotenv import load_dotenv
import hashlib
import user_agents
import logging
import functools
import time
import re
import traceback
import requests
import socket
import ipinfo

# Configure logging with more details
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
)
logger = logging.getLogger("mining_security")

# Add ua-parser library
try:
    from ua_parser import user_agent_parser
    ua_parser_available = True
    logger.info("ua-parser library available for enhanced User-Agent parsing")
except ImportError:
    ua_parser_available = False
    logger.warning("ua-parser package not installed. Using regex-based User-Agent parsing instead.")

# Try to import pymemcache, but continue if not available
try:
    import pymemcache.client.base
    memcached_available = False  # تعطيل استخدام memcached حتى لو كان متاحًا
    logger.info("Pymemcache available but disabled for stability")
except ImportError:
    memcached_available = False
    logger.warning("pymemcache package not installed. Using local memory caching instead.")

# Load environment variables
load_dotenv()

# MongoDB connection
DATABASE_URL = os.getenv("DATABASE_URL")
client = MongoClient(DATABASE_URL)

# Database references
mining_db = client["cryptonel_mining"]
wallet_db = client["cryptonel_wallet"]

# Collections
mining_blocks = mining_db["mining_blocks"]
mining_violations = mining_db["mining_violations"]
settings = wallet_db["settings"]

# IPinfo.io API Configuration - Enhanced with dynamic token detection
IPINFO_API_TOKENS = []
token_index = 1
rate_limited_tokens = {}  # Track which tokens are rate limited
token_usage_stats = {}    # Track token usage statistics

# Dynamically detect all IPinfo API tokens from environment variables
while True:
    token_key = f"IPINFO_API_TOKEN_{token_index}"
    token = os.getenv(token_key)
    if token and token.strip():
        IPINFO_API_TOKENS.append(token.strip())
        # Initialize usage stats for this token
        token_usage_stats[token.strip()] = {
            "requests": 0,
            "successful_requests": 0,
            "rate_limits": 0,
            "last_used": None,
            "errors": 0
        }
    else:
        # No more tokens found, break the loop
        break
    token_index += 1

# Filter out None values and empty strings (redundant but kept for safety)
IPINFO_API_TOKENS = [token for token in IPINFO_API_TOKENS if token and token.strip()]
USE_IPINFO = len(IPINFO_API_TOKENS) > 0

if USE_IPINFO:
    logger.info(f"IPinfo.io API enabled with {len(IPINFO_API_TOKENS)} tokens for enhanced IP analysis")
    for i, token in enumerate(IPINFO_API_TOKENS, 1):
        # Log only the first 4 and last 4 characters of each token for security
        masked_token = f"{token[:4]}...{token[-4:]}" if len(token) > 8 else "****"
        logger.debug(f"Token {i}: {masked_token}")
else:
    logger.warning("IPinfo.io API not configured, using basic IP analysis only")

# إنشاء فهارس لتحسين أداء الاستعلامات
def create_indexes():
    """Create MongoDB indexes for better query performance"""
    try:
        # Check existing indexes to avoid conflicts
        existing_blocks_indexes = [idx.get('name') for idx in list(mining_blocks.list_indexes())]
        existing_violations_indexes = [idx.get('name') for idx in list(mining_violations.list_indexes())]
        
        # العثور على مستخدمين بواسطة user_id
        if not any('user_id' in idx_name for idx_name in existing_blocks_indexes):
            mining_blocks.create_index([("user_id", ASCENDING)], name="mining_blocks_user_id_idx")
            logger.info("Created mining_blocks user_id index")
        
        if not any('user_id' in idx_name for idx_name in existing_violations_indexes):
            mining_violations.create_index([("user_id", ASCENDING)], name="mining_violations_user_id_idx")
            logger.info("Created mining_violations user_id index")
        
        # العثور على مستخدمين بواسطة عنوان IP
        if not any('ip_address' in idx_name for idx_name in existing_blocks_indexes):
            mining_blocks.create_index([("activities.ip_address", ASCENDING)], name="mining_blocks_ip_idx")
            logger.info("Created mining_blocks ip_address index")
        
        # العثور على مستخدمين بواسطة بصمة المتصفح
        if not any('browser_fingerprint' in idx_name for idx_name in existing_blocks_indexes):
            mining_blocks.create_index([("activities.browser_fingerprint", ASCENDING)], name="mining_blocks_browser_idx")
            logger.info("Created mining_blocks browser_fingerprint index")
        
        # العثور على مستخدمين بواسطة بصمة الجهاز
        if not any('device_fingerprint' in idx_name for idx_name in existing_blocks_indexes):
            mining_blocks.create_index([("activities.device_fingerprint", ASCENDING)], name="mining_blocks_device_idx")
            logger.info("Created mining_blocks device_fingerprint index")
        
        # فهارس مركبة للبحث المتقدم
        if not any('ip_browser_compound' in idx_name for idx_name in existing_blocks_indexes):
            # Comprobar también si existe un índice con estos campos pero con otro nombre
            try:
                # Obtener todos los índices con sus campos completos para verificación profunda
                all_indexes = list(mining_blocks.list_indexes())
                compound_exists = False
                
                # Buscar un índice que tenga exactamente estos dos campos
                for idx in all_indexes:
                    idx_keys = idx.get('key', {})
                    # Verificar si el índice tiene los mismos campos
                    if 'activities.ip_address' in idx_keys and 'activities.browser_fingerprint' in idx_keys:
                        logger.info(f"Compound index for ip/browser already exists with different name: {idx.get('name')}")
                        compound_exists = True
                        break
                
                if not compound_exists:
                    mining_blocks.create_index([
                        ("activities.ip_address", ASCENDING),
                        ("activities.browser_fingerprint", ASCENDING)
                    ], name="mining_blocks_ip_browser_idx")
                    logger.info("Created mining_blocks compound index for ip/browser")
            except Exception as e:
                logger.warning(f"Could not create compound index: {e}")
        else:
            logger.info("Compound index for ip/browser already exists")
        
        # فهارس زمنية لفرز الأنشطة
        if not any('timestamp' in idx_name for idx_name in existing_blocks_indexes):
            mining_blocks.create_index([("activities.timestamp", DESCENDING)], name="mining_blocks_timestamp_idx")
            logger.info("Created mining_blocks timestamp index")
            
        if not any('timestamp' in idx_name for idx_name in existing_violations_indexes):
            mining_violations.create_index([("last_violation.timestamp", DESCENDING)], name="mining_violations_timestamp_idx")
            logger.info("Created mining_violations timestamp index")
        
        logger.info("MongoDB indexes created successfully or already exist")
    except Exception as e:
        logger.error(f"Error creating MongoDB indexes: {e}\n{traceback.format_exc()}")

# استدعاء دالة إنشاء الفهارس عند تشغيل الملف
create_indexes()

# Simple memory cache setup
ip_cache = {}  # IP address cache
fingerprint_cache = {}  # Fingerprint cache
first_miner_cache = {}  # First miner cache
ipinfo_cache = {}  # IPinfo.io API response cache
memcached_enabled = False  # Always use local cache

logger.info("Using local memory caching for performance optimization")

def memcached_cached(prefix, expire_seconds=300):
    """Simple local caching decorator"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                # Create a cache key
                key = f"{prefix}:{func.__name__}:{str(args)}:{str(kwargs)}"
                key_hash = hashlib.md5(key.encode()).hexdigest()
                
                # Select the appropriate cache dictionary
                local_cache = ip_cache if prefix == "ip" else fingerprint_cache if prefix == "fp" else first_miner_cache if prefix == "miners" else ipinfo_cache if prefix == "ipinfo" else {}
                
                # Check if we have a cached value
                current_time = time.time()
                if key_hash in local_cache and local_cache[key_hash]['expiry'] > current_time:
                    return local_cache[key_hash]['result']
                
                # Calculate result, cache it, and return
                result = func(*args, **kwargs)
                local_cache[key_hash] = {
                    'result': result,
                    'expiry': current_time + expire_seconds
                }
                return result
            except Exception as e:
                logger.error(f"Cache error in {func.__name__}: {e}\n{traceback.format_exc()}")
                # If caching fails, still return the function result without caching
                return func(*args, **kwargs)
        return wrapper
    return decorator

# Create blueprint
mining_security_bp = Blueprint('mining_security', __name__)

def init_app(app):
    """Initialize mining security module"""
    app.register_blueprint(mining_security_bp)
    
    try:
        # Ensure indexes for mining security collections - capture errors but continue
        try:
            create_indexes()
        except Exception as e:
            # Log error but continue with initialization
            logger.error(f"Error creating indexes during init_app: {e}")
            logger.info("Continuing with initialization despite index creation failure")
        
        # Create devices and networks collections
        if 'user_devices' not in mining_db.list_collection_names():
            mining_db.create_collection('user_devices')
            try:
                mining_db.user_devices.create_index([('user_id', 1)], unique=True, name="mining_security_devices_user_id_idx")
                logger.info("Created user_devices collection")
            except Exception as e:
                logger.warning(f"Could not create user_devices index: {e}")
        else:
            # Check if index exists and create if needed
            try:
                existing_device_indexes = [idx.get('name') for idx in list(mining_db.user_devices.list_indexes())]
                if not any('user_id' in idx_name for idx_name in existing_device_indexes):
                    mining_db.user_devices.create_index([('user_id', 1)], unique=True, name="mining_security_devices_user_id_idx")
                    logger.info("Created user_devices user_id index")
            except Exception as e:
                logger.warning(f"Could not verify or create user_devices index: {e}")
        
        if 'user_networks' not in mining_db.list_collection_names():
            mining_db.create_collection('user_networks')
            try:
                mining_db.user_networks.create_index([('user_id', 1)], unique=True, name="mining_security_networks_user_id_idx")
                logger.info("Created user_networks collection")
            except Exception as e:
                logger.warning(f"Could not create user_networks index: {e}")
        else:
            # Check if index exists and create if needed
            try:
                existing_network_indexes = [idx.get('name') for idx in list(mining_db.user_networks.list_indexes())]
                if not any('user_id' in idx_name for idx_name in existing_network_indexes):
                    mining_db.user_networks.create_index([('user_id', 1)], unique=True, name="mining_security_networks_user_id_idx")
                    logger.info("Created user_networks user_id index")
            except Exception as e:
                logger.warning(f"Could not verify or create user_networks index: {e}")
        
        # Check if security settings exist and create defaults if not
        settings_collection = mining_db["settings"]
        if "mining_security" not in [doc.get("type") for doc in settings_collection.find()]:
            security_settings = {
                "type": "mining_security",
                "settings": {
                    "anti_fraud_protection": True,
                    "fraud_protection_settings": {
                        "accounts_per_ip_enabled": True,
                        "accounts_per_ip": 5,  # Default to 5 accounts per IP
                        "accounts_per_device_enabled": True,
                        "accounts_per_device": 1,
                        "accounts_per_physical_device_enabled": True,
                        "accounts_per_physical_device": 1,
                        "devices_per_account_enabled": True,
                        "devices_per_account": 3,  # Allow 3 devices per account
                        "networks_per_account_enabled": True,
                        "networks_per_account": 10,  # Allow 10 networks per account
                        "penalty_enabled": True,
                        "warning_then_ban": True,
                        "permanent_ban": False,
                        "mining_block": True,
                        "mining_suspension": False
                    }
                },
                "updated_at": datetime.datetime.now(datetime.timezone.utc)
            }
            
            try:
                settings_collection.insert_one(security_settings)
                logger.info("Created default mining security settings")
            except DuplicateKeyError:
                logger.info("Mining security settings already exist")
    except Exception as e:
        logger.error(f"Error initializing mining security module: {e}\n{traceback.format_exc()}")

# Add function to reset stale token information
def reset_stale_tokens():
    """Periodically reset stale token rate limit information"""
    current_time = datetime.datetime.now(datetime.timezone.utc)
    stale_tokens = []
    
    # Check for tokens that should no longer be rate limited
    for token, expiry_time in rate_limited_tokens.items():
        if current_time > expiry_time:
            stale_tokens.append(token)
    
    # Remove stale tokens from rate_limited_tokens dictionary
    for token in stale_tokens:
        if token in rate_limited_tokens:
            logger.info(f"Token {token[:4]}...{token[-4:]} rate limit expired, marking as available again")
            del rate_limited_tokens[token]

@memcached_cached("ipinfo", 86400)  # Cache IPinfo responses for 24 hours
def get_ipinfo_data(ip_address):
    """
    Get detailed information about an IP address using IPinfo.io
    
    Args:
        ip_address: IP address to look up
        
    Returns:
        dict: IPinfo response or a minimal response with basic data if not available
    """
    # تجاهل عناوين IP المحلية
    if not ip_address or ip_address == "127.0.0.1" or ip_address == "::1" or ip_address == "localhost" or ip_address.startswith("192.168.") or ip_address.startswith("10."):
        return {"ip": ip_address, "bogon": True}
        
    # طباعة معلومات تشخيصية
    logger.debug(f"Getting IPinfo data for {ip_address}")
    
    # Try to get data with all available tokens
    max_retries = 2  # زيادة عدد المحاولات
    retry_delay = 1  # ثانية واحدة بين المحاولات
    
    for retry_attempt in range(max_retries):
        for token in IPINFO_API_TOKENS:
            try:
                # زيادة مهلة الاتصال من 5 ثوانٍ إلى 10 ثوانٍ
                handler = ipinfo.getHandler(token, cache_options={'ttl': 86400}, request_options={'timeout': 10})
                details = handler.getDetails(ip_address)
                result = details.all
                
                # Add source information
                result["source"] = "ipinfo"
                
                # Try to get privacy data
                try:
                    privacy_result = None
                    if privacy_result and isinstance(privacy_result, dict):
                        result["privacy"] = privacy_result
                    else:
                        # إضافة بيانات خصوصية افتراضية إذا فشل الحصول عليها
                        result["privacy"] = {
                            "vpn": False,
                            "proxy": False,
                            "tor": False,
                            "hosting": False
                        }
                except Exception as privacy_error:
                    logger.warning(f"IPinfo token {token[:4]}...{token[-4:]} failed privacy request: {privacy_error}")
                    logger.info(f"Trying alternative token for privacy data: {IPINFO_API_TOKENS[0][:4]}...{IPINFO_API_TOKENS[0][-4:]}")
                    
                    # Try with another token just for privacy
                    try:
                        alt_handler = ipinfo.getHandler(IPINFO_API_TOKENS[0], cache_options={'ttl': 86400}, request_options={'timeout': 10})
                        alt_details = alt_handler.getDetails(ip_address)
                        privacy_result = alt_details.all.get("privacy", None)
                        
                        if privacy_result:
                            result["privacy"] = privacy_result
                        else:
                            # إضافة بيانات خصوصية افتراضية
                            result["privacy"] = {
                                "vpn": False,
                                "proxy": False,
                                "tor": False,
                                "hosting": False
                            }
                    except Exception as alt_error:
                        logger.warning(f"Alternative token {IPINFO_API_TOKENS[0][:4]}...{IPINFO_API_TOKENS[0][-4:]} also lacks privacy permission")
                        # إضافة بيانات خصوصية افتراضية
                        result["privacy"] = {
                            "vpn": False,
                            "proxy": False,
                            "tor": False,
                            "hosting": False
                        }
                
                # التأكد من وجود البيانات الأساسية
                logger.info(f"Successfully retrieved IPinfo data for {ip_address}: {result.get('country', 'Unknown')}, {result.get('city', 'Unknown')}")
                
                # التأكد من تسجيل معلومات جغرافية حتى لو لم تكن كاملة
                if not result.get("loc") and (result.get("latitude") and result.get("longitude")):
                    result["loc"] = f"{result['latitude']},{result['longitude']}"
                
                # إضافة بيانات مفقودة إذا لزم الأمر
                if not result.get("privacy"):
                    result["privacy"] = {
                        "vpn": False,
                        "proxy": False,
                        "tor": False,
                        "hosting": False
                    }
                    
                # Update usage statistics
                if token in token_usage_stats:
                    token_usage_stats[token]["requests"] += 1
                    token_usage_stats[token]["successful_requests"] += 1
                    token_usage_stats[token]["last_used"] = datetime.datetime.now().isoformat()
                
                return result
            except Exception as e:
                # Check if this is a rate limit error
                if 'rate' in str(e).lower() and 'limit' in str(e).lower():
                    logger.warning(f"IPinfo token {token[:4]}...{token[-4:]} hit rate limit: {e}")
                    
                    # Mark this token as rate limited
                    rate_limited_tokens[token] = datetime.datetime.now()
                    
                    # Update usage statistics
                    if token in token_usage_stats:
                        token_usage_stats[token]["rate_limits"] += 1
                        token_usage_stats[token]["errors"] += 1
                        token_usage_stats[token]["last_used"] = datetime.datetime.now().isoformat()
                    
                    # Try next token
                    continue
                else:
                    logger.error(f"Error with IPinfo token {token[:4]}...{token[-4:]}: {e}")
                    
                    # Update usage statistics
                    if token in token_usage_stats:
                        token_usage_stats[token]["errors"] += 1
                        token_usage_stats[token]["last_used"] = datetime.datetime.now().isoformat()
                    
                    # Try next token
                    continue
        
        # If we've tried all tokens and we're not on the last retry, wait before trying again
        if retry_attempt < max_retries - 1:
            logger.warning(f"All tokens failed for IP {ip_address}, retrying in {retry_delay} seconds...")
            time.sleep(retry_delay)
    
    # All tokens failed after all retries, use multiple fallback methods
    logger.warning(f"All available tokens failed for IP {ip_address} after {max_retries} attempts, using fallback methods")
    
    # Try multiple public fallback APIs with increased timeout
    fallback_apis = [
        f"https://ipapi.co/{ip_address}/json/",
        f"https://ip-api.com/json/{ip_address}",
        f"https://ipinfo.io/{ip_address}/json",  # Try direct access without token
        f"https://freegeoip.app/json/{ip_address}"
    ]
    
    for api_url in fallback_apis:
        try:
            # Increase timeout from 5 to 10 seconds for reliability
            response = requests.get(api_url, timeout=10)
            if response.status_code == 200:
                fallback_data = response.json()
                
                # Convert to standardized format based on which API was used
                if "ipapi.co" in api_url:
                    result = {
                        "ip": ip_address,
                        "hostname": fallback_data.get("hostname", ""),
                        "city": fallback_data.get("city", ""),
                        "region": fallback_data.get("region", ""),
                        "country": fallback_data.get("country_code", ""),
                        "loc": f"{fallback_data.get('latitude', 0)},{fallback_data.get('longitude', 0)}",
                        "org": fallback_data.get("org", ""),
                        "postal": fallback_data.get("postal", ""),
                        "timezone": fallback_data.get("timezone", ""),
                        "source": "ipapi.co",
                        "privacy": {
                            "vpn": False,
                            "proxy": False,
                            "tor": False,
                            "hosting": False
                        }
                    }
                elif "ip-api.com" in api_url:
                    result = {
                        "ip": ip_address,
                        "hostname": fallback_data.get("isp", ""),
                        "city": fallback_data.get("city", ""),
                        "region": fallback_data.get("regionName", ""),
                        "country": fallback_data.get("countryCode", ""),
                        "loc": f"{fallback_data.get('lat', 0)},{fallback_data.get('lon', 0)}",
                        "org": fallback_data.get("org", fallback_data.get("isp", "")),
                        "timezone": fallback_data.get("timezone", ""),
                        "source": "ip-api.com",
                        "privacy": {
                            "vpn": False,
                            "proxy": fallback_data.get("proxy", False),
                            "tor": False,
                            "hosting": False
                        }
                    }
                else:
                    # Generic format for other APIs
                    result = {
                        "ip": ip_address,
                        "hostname": fallback_data.get("hostname", ""),
                        "city": fallback_data.get("city", ""),
                        "region": fallback_data.get("region", ""),
                        "country": fallback_data.get("country", fallback_data.get("countryCode", "")),
                        "source": api_url.split("//")[1].split("/")[0],
                        "privacy": {
                            "vpn": False,
                            "proxy": False,
                            "tor": False,
                            "hosting": False
                        }
                    }
                    
                    # Try to extract location from different possible formats
                    if "loc" in fallback_data:
                        result["loc"] = fallback_data["loc"]
                    elif "latitude" in fallback_data and "longitude" in fallback_data:
                        result["loc"] = f"{fallback_data['latitude']},{fallback_data['longitude']}"
                    elif "lat" in fallback_data and "lon" in fallback_data:
                        result["loc"] = f"{fallback_data['lat']},{fallback_data['lon']}"
                
                logger.info(f"Successfully retrieved fallback IP data from {api_url} for {ip_address}")
                return result
        except Exception as fallback_error:
            logger.error(f"Fallback IP data retrieval from {api_url} failed: {fallback_error}")
            continue
    
    # All fallbacks failed, return minimal data
    logger.warning(f"All IP data retrieval methods failed for {ip_address}, returning minimal data")
    return {
        "ip": ip_address,
        "source": "minimal",
        "privacy": {
            "vpn": False,
            "proxy": False,
            "tor": False,
            "hosting": False
        }
    }

# Utility Class for IP Analysis
class IPAnalyzer:
    # Expanded VPN prefix lists with more comprehensive coverage
    VPN_PREFIXES = [
        # Cloudflare
        "103.21.", "103.22.", "103.31.", "104.16.", "104.24.", "108.162.", "131.0.", "141.101.", 
        "162.158.", "172.64.", "173.245.", "188.114.", "190.93.", "197.234.", "198.41.",
        # NordVPN
        "5.253.", "31.13.", "45.134.", "82.102.", "89.187.", "84.17.", "194.127.", "194.242.",
        # ExpressVPN 
        "94.242.", "91.239.", "89.238.", "89.187.", "62.112.", "46.166.", "185.156.",
        # Proton VPN
        "185.159.", "185.107.", "185.70.", "185.1.", "185.242.", "194.60.", "194.126.",
        # PIA
        "209.58.", "108.61.", "216.131.", "38.132.", "185.180.", "185.242.", "185.244.", "185.246.", "185.147.",
        # IPVanish
        "209.197.", "216.98.", "185.232.", "46.19.", "64.145.", "89.187.", "82.102.", "98.143.", "209.107.",
        # Surfshark
        "89.33.", "179.61.", "138.199.", "185.242.", "109.205.", "37.120.", "37.19.", "45.87.", "45.130.",
        # CyberGhost
        "146.70.", "141.98.", "91.219.", "91.220.", "91.207.", "91.227.", "91.241.", "91.245.", "92.118.",
        # المزيد من عناوين VPN
        "212.102.", "212.103.", "193.176.", "193.177.", "193.178.", "185.230.", "46.246.", "185.217.", "188.241.",
        # DigitalOcean & Vultr (بعض الخدمات السحابية يستخدمها الناس كـ VPN)
        "104.131.", "104.236.", "159.65.", "157.230.", "45.55.", "178.62.", "206.189.", "165.227.", "128.199.",
        "66.42.", "45.63.", "139.180.", "95.179.", "45.77.", "140.82.", "149.28.", "144.202.", "207.246.",
        # Linode
        "45.33.", "45.56.", "45.79.", "50.116.", "66.175.", "66.228.", "69.164.", "72.14.", "96.126.",
        "97.107.", "104.200.", "106.187.", "109.74.", "139.162.", "173.230.", "173.255.", "178.79.", 
        "207.192.", "209.123.", "213.52.", "96.126.",
        # Vultr
        "45.32.", "45.63.", "45.76.", "45.77.", "66.42.", "95.179.", "149.28.", "207.246.", "208.167.",
        # OVH
        "51.68.", "51.75.", "51.83.", "51.89.", "51.91.", "51.195.", "51.222.", "51.254.", "51.255.",
        # DigitalRiver
        "91.223.", "91.227.", "91.236.", "146.88.", "146.148.", "185.152.", "185.209.", "93.95.",
        # Oracle Cloud
        "150.136.", "152.67.", "132.145.", "129.146.", "132.226.", "134.70.", "138.2.", "140.238.", "143.47.",
        # Choopa
        "45.63.", "45.32.", "45.76.", "45.77.", "66.42.", "108.61.", "173.199.", "173.244.", "173.245.",
        # Zenlayer
        "148.153.", "103.26.", "103.108.", "103.210.", "103.43.", "106.72.", "106.119.", "116.211.", "128.1.",
        # ColoCrossing
        "107.172.", "107.173.", "107.174.", "107.175.", "155.94.", "192.3.", "198.12.", "198.23.", "198.46.",
        # HostRoyale
        "91.211.", "91.195.", "91.200.", "93.115.", "95.110.", "95.181.", "95.215.", "95.216.", "95.217.",
        # Rackspace
        "104.130.", "108.166.", "120.136.", "146.20.", "160.11.", "161.47.", "162.209.", "162.221.", "162.242.",
        # HostPapa
        "192.162.", "192.169.", "192.175.", "192.151.", "192.208.", "192.40.", "192.64.", "216.108.", "216.158.",
        # Network Operations Center Inc.
        "199.168.", "198.55.", "198.50.", "192.154.", "192.200.", "158.222.", "104.218.", "104.219.", "104.245.",
        # RedStation Limited
        "179.60.", "179.61.", "45.252.", "45.253.", "45.249.", "45.248.", "179.43.", "31.44.", "46.166.",
        # Known VPS/VPN hosts
        "5.188.", "185.217.", "188.241.", "147.135.", "147.78.", "177.54.", "85.206."
    ]
    
    # Expanded TOR exit node prefixes
    TOR_PREFIXES = [
        "185.220.", "171.25.", "193.11.", "62.102.", "91.219.", "51.15.", "88.80.", "77.247.", "95.142.",
        "109.70.", "176.10.", "193.218.", "185.83.", "185.241.", "199.249.", "204.11.", "192.42.",
        "162.247.", "96.66.", "146.185.", "171.25.", "163.172.", "194.88.", "212.16.", "144.217.",
        "45.79.", "62.210.", "185.165.", "217.79.", "82.165.", "91.203.", "216.176.", "51.68.",
        "91.244.", "185.38.", "152.70.", "46.194.", "81.17.", "185.100.", "95.211.", "31.185.",
        "198.96.", "162.247.", "198.98.", "171.25.", "171.255.", "154.35.", "185.243."
    ]
    
    # Enhanced VPN keyword list
    VPN_KEYWORDS = [
        "vpn", "proxy", "proxifier", "tunnelbear", "nordvpn", "expressvpn", "privatevpn", "hidemyass",
        "vyprvpn", "ipvanish", "purevpn", "cyberghost", "privatetunnel", "torguard", "surfshark",
        "mullvad", "windscribe", "protonvpn", "avast secureline", "opera vpn", "tunnelbear",
        "hotspotshield", "zenmate", "strongvpn", "privatevpn", "airvpn", "ivpn", "ovpn", "hola", 
        "safervpn", "hide.me", "astrill", "goose vpn", "witopia", "switchvpn", "anonymizer", 
        "anonymous", "securepoint", "browserling", "beebeep", "guardster", "namecheap", "vpnhub",
        "anonymouse", "webproxy", "4everproxy", "proxysite", "unblocker", "unblockweb", "vpnbook",
        "ultravpn", "speedify", "buffer", "whoer", "zenvpn", "kproxy", "hideipvpn", "veepn",
        "fastestvpn", "privatix", "overplay", "urban vpn", "betternet", "trust.zone", "kaspersky vpn",
        "speedvpn", "zoogvpn", "anonvpn", "vpnsecure", "zenvpn", "unlocator", "vpngate", "spidervpn"
    ]
    
    # Expanded datacenter detection
    DATACENTER_PREFIXES = [
        # AWS
        "3.2.", "3.12.", "3.16.", "3.80.", "3.84.", "13.32.", "13.33.", "13.34.", "13.35.", "13.59.",
        "23.20.", "35.153.", "35.170.", "35.172.", "50.16.", "50.17.", "50.19.", "52.0.", "52.20.",
        "54.70.", "54.80.", "54.160.", "52.94.", "52.119.", "54.230.",
        # Google Cloud
        "8.34.", "34.64.", "34.68.", "34.90.", "34.96.", "34.102.", "34.104.", "34.126.", "34.142.",
        "35.184.", "35.186.", "35.189.", "35.190.", "35.192.", "35.194.", "35.196.", "35.198.", "35.199.",
        "35.200.", "35.205.", "35.209.", "35.220.", "35.231.", "35.239.", "35.240.", "35.244.",
        # Azure
        "13.64.", "13.65.", "13.66.", "13.67.", "13.68.", "13.69.", "13.70.", "13.71.", "13.72.",
        "13.73.", "13.74.", "13.75.", "13.76.", "13.77.", "13.78.", "13.104.", "13.105.", "13.106.",
        "40.64.", "40.65.", "40.66.", "40.67.", "40.68.", "40.69.", "40.70.", "40.71.", "40.74.",
        # Digital Ocean
        "45.55.", "64.225.", "67.205.", "104.131.", "128.199.", "134.122.", "138.68.", "139.59.",
        "143.110.", "157.230.", "159.203.", "159.65.", "159.89.", "161.35.", "162.243.", "165.22.",
        "167.99.", "174.138.", "192.34.", "198.199.", "209.97.",
        # Linode
        "45.33.", "45.56.", "45.79.", "50.116.", "66.175.", "66.228.", "69.164.", "72.14.", "96.126.",
        "97.107.", "104.200.", "106.187.", "109.74.", "139.162.", "173.230.", "173.255.", "178.79.", 
        "207.192.", "209.123.", "213.52.", "96.126.",
        # Vultr
        "45.32.", "45.63.", "45.76.", "45.77.", "66.42.", "95.179.", "149.28.", "207.246.", "208.167.",
        # OVH
        "51.68.", "51.75.", "51.83.", "51.89.", "51.91.", "51.195.", "51.222.", "51.254.", "51.255.",
        # DigitalRiver
        "91.223.", "91.227.", "91.236.", "146.88.", "146.148.", "185.152.", "185.209.", "93.95.",
        # Oracle Cloud
        "150.136.", "152.67.", "132.145.", "129.146.", "132.226.", "134.70.", "138.2.", "140.238.", "143.47.",
        # Choopa
        "45.63.", "45.32.", "45.76.", "45.77.", "66.42.", "108.61.", "173.199.", "173.244.", "173.245.",
        # Zenlayer
        "148.153.", "103.26.", "103.108.", "103.210.", "103.43.", "106.72.", "106.119.", "116.211.", "128.1.",
        # ColoCrossing
        "107.172.", "107.173.", "107.174.", "107.175.", "155.94.", "192.3.", "198.12.", "198.23.", "198.46.",
        # HostRoyale
        "91.211.", "91.195.", "91.200.", "93.115.", "95.110.", "95.181.", "95.215.", "95.216.", "95.217.",
        # Rackspace
        "104.130.", "108.166.", "120.136.", "146.20.", "160.11.", "161.47.", "162.209.", "162.221.", "162.242.",
        # HostPapa
        "192.162.", "192.169.", "192.175.", "192.151.", "192.208.", "192.40.", "192.64.", "216.108.", "216.158.",
        # Network Operations Center Inc.
        "199.168.", "198.55.", "198.50.", "192.154.", "192.200.", "158.222.", "104.218.", "104.219.", "104.245.",
        # RedStation Limited
        "179.60.", "179.61.", "45.252.", "45.253.", "45.249.", "45.248.", "179.43.", "31.44.", "46.166.",
        # Known VPS/VPN hosts
        "5.188.", "185.217.", "188.241.", "147.135.", "147.78.", "177.54.", "85.206."
    ]
    
    @staticmethod
    @memcached_cached("ip", 3600)  # Cache IP analysis for 1 hour
    def analyze_ip(ip_address):
        """
        Enhanced IP analysis with IPinfo.io integration and better VPN/proxy/datacenter detection
        Supports both IPv4 and IPv6 addresses
        """
        try:
            ip_info = {
                "address": ip_address,
                "is_vpn": False,
                "is_datacenter": False,
                "is_tor": False,
                "ip_type": "unknown",
                "ip_version": None,
                "confidence": 0,
                "risk_score": 0,  # New risk score field for more granular assessment
                "geo": {},        # Will contain geolocation information if available
                "provider": None  # Will contain ISP/ASN information if available
            }
            
            # First, check for localhost/private networks using ipaddress module
            try:
                ip = ipaddress.ip_address(ip_address)
                
                # Set IP version
                ip_info["ip_version"] = 6 if isinstance(ip, ipaddress.IPv6Address) else 4
                
                # Handle special addresses
                if ip.is_loopback:
                    ip_info["ip_type"] = "localhost"
                    ip_info["risk_score"] = 10  # Reduced risk for localhost to avoid false positives in development
                    return ip_info
                elif ip.is_private:
                    ip_info["ip_type"] = "private"
                    ip_info["risk_score"] = 70  # Private IPs can indicate circumvention
                    return ip_info
                elif ip.is_reserved:
                    ip_info["ip_type"] = "reserved"
                    ip_info["risk_score"] = 50
                    return ip_info
                elif ip.is_multicast:
                    ip_info["ip_type"] = "multicast"
                    ip_info["risk_score"] = 40
                    return ip_info
            except Exception as e:
                logger.error(f"IP address parsing error: {e} for IP: {ip_address}\n{traceback.format_exc()}")
                ip_info["ip_type"] = "invalid"
                ip_info["risk_score"] = 90  # Invalid IPs are highly suspicious
                return ip_info
            
            # Try to get information from IPinfo.io if enabled
            ipinfo_data = get_ipinfo_data(ip_address)
            
            if ipinfo_data:
                # Use IPinfo data for enhanced detection
                logger.debug(f"Using IPinfo data for {ip_address}")
                
                # Extract geolocation data
                ip_info["geo"] = {
                    "country": ipinfo_data.get("country"),
                    "region": ipinfo_data.get("region"),
                    "city": ipinfo_data.get("city"),
                    "location": ipinfo_data.get("loc"),
                    "postal": ipinfo_data.get("postal"),
                    "timezone": ipinfo_data.get("timezone")
                }
                
                # Extract provider information
                if "org" in ipinfo_data:
                    ip_info["provider"] = ipinfo_data.get("org")
                    # Check for datacenter/VPN in organization name using keywords
                    org_name = ip_info["provider"].lower()
                    
                    # Check for datacenter related keywords
                    if any(keyword in org_name for keyword in ["amazon", "google", "microsoft", "digital ocean", "digitalocean", "linode", 
                            "vultr", "azure", "aws", "cloud", "hosting", "vps", "server", "datacenter",
                            "hetzner", "ovh", "scaleway", "oracle", "alibaba", "tencent", "hostwinds",
                            "leaseweb", "choopa", "rackspace", "softlayer", "godaddy", "liquid web"]):
                        ip_info["is_datacenter"] = True
                        ip_info["confidence"] = 90
                        ip_info["risk_score"] += 60
                    
                    # Check for VPN related keywords
                    if any(keyword in org_name for keyword in
                          ["vpn", "proxy", "proxies", "anonymous", "hide", "masked", "mullvad", "nord", 
                           "express", "cyberghost", "private internet", "torguard", "ipvanish", "surfshark",
                           "purevpn", "hotspot shield", "windscribe", "vyprvpn", "strongvpn", "hidemyass",
                           "zenmate", "tunnel", "protonvpn", "ivpn", "airvpn", "privatevpn", "trust.zone",
                           "tefincom", "m247", "zenlayer", "datacamp", "cloudflare", "torghost", "psiph",
                           "perfect privacy", "veesp", "avira phantom", "avast secureline", "f-secure freedome",
                           "mozilla vpn", "kaspersky vpn", "hide.me", "privateinternetaccess", "pia",
                           "betternet", "tunnelbear", "opera vpn", "speedify", "safervpn", "astrill",
                           "bolehvpn", "hidester", "norton vpn", "switchvpn", "vpnsecure", "hotspotshield", 
                           "namecheap vpn", "cactusvpn", "keepsolid", "cryptostorm", "witopia", "tigervpn",
                           "goose vpn", "anonymizer", "spidervpn", "fastestvpn", "overplay", "surfeasy",
                           "ultrasurf", "urban vpn", "vpnhub", "privatix", "getflix", "unlocator", "vpngate", 
                           "browsec", "simplevisor", "privax", "buffered", "frootvpn", "totalvpn", "faceless",
                           "cloudvpn", "whoer", "hidemy", "bitdefender vpn", "tor"]):
                        ip_info["is_vpn"] = True
                        ip_info["confidence"] = 95
                        ip_info["risk_score"] += 80
                
                # Enhanced VPN detection based on privacy data
                if "privacy" in ipinfo_data:
                    privacy = ipinfo_data["privacy"]
                    
                    # Direct VPN/proxy detection from IPinfo
                    if privacy.get("vpn", False):
                        ip_info["is_vpn"] = True
                        ip_info["confidence"] = 95
                        ip_info["risk_score"] += 80
                    
                    if privacy.get("proxy", False):
                        ip_info["is_vpn"] = True
                        ip_info["confidence"] = 90
                        ip_info["risk_score"] += 75
                    
                    if privacy.get("tor", False):
                        ip_info["is_tor"] = True
                        ip_info["confidence"] = 95
                        ip_info["risk_score"] += 85
                    
                    if privacy.get("hosting", False):
                        ip_info["is_datacenter"] = True
                        ip_info["confidence"] = 90
                        ip_info["risk_score"] += 60
                
                # Set IP type based on the combined data
                if ip_info["is_vpn"]:
                    ip_info["ip_type"] = "vpn"
                elif ip_info["is_tor"]:
                    ip_info["ip_type"] = "tor"
                elif ip_info["is_datacenter"]:
                    ip_info["ip_type"] = "datacenter"
                else:
                    ip_info["ip_type"] = "residential"
            else:
                # Fall back to pattern-based detection if IPinfo is not available
                # IPv4 specific checks
                if ip_info["ip_version"] == 4:
                    # Check against expanded VPN prefixes
                    if any(ip_address.startswith(prefix) for prefix in IPAnalyzer.VPN_PREFIXES):
                        ip_info["is_vpn"] = True
                        ip_info["confidence"] = 80
                        ip_info["risk_score"] += 70
                    
                    # Check against datacenter prefixes
                    if any(ip_address.startswith(prefix) for prefix in IPAnalyzer.DATACENTER_PREFIXES):
                        ip_info["is_datacenter"] = True
                        ip_info["confidence"] = max(ip_info["confidence"], 75)
                        ip_info["risk_score"] += 60
                        
                    # TOR exit node check
                    if any(ip_address.startswith(prefix) for prefix in IPAnalyzer.TOR_PREFIXES):
                        ip_info["is_tor"] = True
                        ip_info["confidence"] = 90
                        ip_info["risk_score"] += 80
                        
                # IPv6 specific checks
                elif ip_info["ip_version"] == 6:
                    # Common IPv6 VPN/Datacenter patterns 
                    ipv6_patterns = [
                        # Cloudflare
                        r"^2606:4700",
                        # DigitalOcean
                        r"^2400:6180", 
                        # AWS
                        r"^2600:1f",
                        # Linode
                        r"^2600:3c",
                        # TOR exit nodes
                        r"^2a0b:f4c",
                        # Google Cloud
                        r"^2001:4860",
                        # Azure
                        r"^2603:1000",
                        # NordVPN
                        r"^2a02:f680",
                        # ProtonVPN
                        r"^2a0(0|2):(a|b|c|d|e|f)",
                        # Private Internet Access
                        r"^2602:fcbc",
                        # ExpressVPN
                        r"^2a01:4f8",
                        # Mullvad
                        r"^2a03:8600",
                        # IPVanish
                        r"^2a02:578",
                        # Surfshark
                        r"^2a0d:5600",
                        # CyberGhost
                        r"^2a02:2308",
                    ]
                    
                    for pattern in ipv6_patterns:
                        if re.match(pattern, ip_address):
                            ip_info["is_vpn"] = True
                            ip_info["is_datacenter"] = True
                            ip_info["confidence"] = 80
                            ip_info["risk_score"] += 65
                            break
                
                # Set IP type based on pattern detection
                if ip_info["is_vpn"]:
                    ip_info["ip_type"] = "vpn"
                elif ip_info["is_tor"]:
                    ip_info["ip_type"] = "tor"
                elif ip_info["is_datacenter"]:
                    ip_info["ip_type"] = "datacenter"
                else:
                    ip_info["ip_type"] = "residential"
            
            # Ensure risk score doesn't exceed 100
            ip_info["risk_score"] = min(100, ip_info["risk_score"])
                
            return ip_info
            
        except Exception as e:
            logger.error(f"IP Analysis error: {e} for IP: {ip_address}\n{traceback.format_exc()}")
            # Return a safe default in case of errors
            return {
                "address": ip_address,
                "is_vpn": False,
                "is_datacenter": False,
                "is_tor": False,
                "ip_type": "error",
                "ip_version": None,
                "confidence": 0,
                "risk_score": 30,  # Default risk for unknown
                "error": str(e)
            }

# Utility class for device fingerprinting
class DeviceFingerprinter:
    # Mobile device platforms for better detection
    MOBILE_PLATFORMS = [
        'android', 'iphone', 'ipad', 'ipod', 'windows phone', 'blackberry', 'nokia', 
        'symbian', 'ios', 'mobile', 'phone', 'smartphone'
    ]
    
    # Tablet device identifiers
    TABLET_PLATFORMS = [
        'ipad', 'tablet', 'kindle', 'surface', 'playbook', 'slate', 'tab'
    ]
    
    # VM and emulator detection keywords
    VM_KEYWORDS = [
        'virtual', 'vm', 'vmware', 'virtualbox', 'qemu', 'xen', 'parallels', 'hyper-v',
        'vbox', 'kvm', 'bhyve', 'emulator', 'android studio', 'genymotion', 'bluestacks', 
        'nox', 'andy', 'memu', 'ldplayer', 'sandbox', 'cuckoo', 'docker'
    ]
    
    # Spoofing detection keywords
    SPOOFING_KEYWORDS = [
        'fake', 'spoof', 'anon', 'anonymous', 'tamper', 'modified', 'useragent', 'switcher',
        'anonymox', 'user-agent switcher', 'random agent', 'change browser', 'browser changer'
    ]
    
    @staticmethod
    @memcached_cached("fp", 3600)  # Cache fingerprints for 1 hour
    def get_device_type(user_agent_string):
        """
        Enhanced device type detection with better categorization and spoofing detection
        Returns: "mobile", "tablet", "desktop", "vm", or "suspicious"
        """
        try:
            # First check for VMs or spoofing regardless of parsing method
            user_agent_lower = user_agent_string.lower()
            
            # Check for virtual machine or emulator
            for keyword in DeviceFingerprinter.VM_KEYWORDS:
                if keyword in user_agent_lower:
                    return "vm"
                    
            # Check for spoofing tools
            for keyword in DeviceFingerprinter.SPOOFING_KEYWORDS:
                if keyword in user_agent_lower:
                    return "suspicious"
            
            # Use ua-parser if available for more accurate parsing
            if ua_parser_available:
                try:
                    ua_parsed = user_agent_parser.Parse(user_agent_string)
                    
                    # Get structured information
                    os_family = ua_parsed["os"]["family"]
                    device_family = ua_parsed["device"]["family"]
                    browser_family = ua_parsed["user_agent"]["family"]
                    
                    # More accurately identify device types
                    if device_family != "Other" and device_family not in ["Desktop", "PC", "Computer"]:
                        # Mobile phone detection
                        if device_family in ["iPhone", "Android", "Windows Phone", "BlackBerry"]:
                            return "mobile"
                        # Tablet detection
                        elif device_family in ["iPad", "Kindle", "Surface", "Galaxy Tab", "Nexus 7"]:
                            return "tablet"
                    
                    # Check for inconsistencies that may indicate spoofing
                    if "Android" in os_family and "iPhone" in device_family:
                        return "suspicious"
                    if "iOS" in os_family and "Android" in device_family:
                        return "suspicious"
                    
                    # Check mobile OS
                    if os_family in ["Android", "iOS", "Windows Phone"]:
                        if device_family in ["iPad", "Kindle", "Surface", "Galaxy Tab"]:
                            return "tablet"
                        return "mobile"
                
                except Exception as e:
                    logger.debug(f"Error using ua-parser: {e}, falling back to regex detection")
                    # Fall back to regex method
            
            # Fallback to existing regex method
            # Check for tablet first (as some tablets also include "mobile" in UA)
            for keyword in DeviceFingerprinter.TABLET_PLATFORMS:
                if keyword in user_agent_lower:
                    return "tablet"
            
            # Then check for mobile
            for keyword in DeviceFingerprinter.MOBILE_PLATFORMS:
                if keyword in user_agent_lower:
                    return "mobile"
            
            # Detect inconsistencies that may indicate spoofing
            inconsistent = False
            
            # Mobile platform claims to be desktop
            if any(platform in user_agent_lower for platform in ['android', 'iphone']) and 'windows nt' in user_agent_lower:
                inconsistent = True
                
            # Mismatched OS and browser combinations
            if 'macintosh' in user_agent_lower and 'windows' in user_agent_lower:
                inconsistent = True
                
            # Implausible combinations
            if 'iphone' in user_agent_lower and 'firefox' in user_agent_lower:
                inconsistent = True
                
            if inconsistent:
                return "suspicious"
            
            # Default to desktop
            return "desktop"
        except Exception as e:
            logger.error(f"Error determining device type: {e}\n{traceback.format_exc()}")
            return "unknown"
    
    @staticmethod
    @memcached_cached("fp", 3600)  # Cache fingerprints for 1 hour
    def generate_device_fingerprint(user_agent_string, ip_address, headers=None):
        """
        توليد بصمة جهاز فريدة مع توازن بين خصائص الجهاز الفعلية وعنوان IP
        لمنع التحايل عبر VPN/البروكسي
        """
        try:
            # المكونات الأساسية للبصمة - نقسمها لبصمة ثابتة وبصمة شبكة
            device_components = []  # مكونات ثابتة للجهاز
            network_components = []  # مكونات الشبكة المتغيرة
            
            # 1. معلومات وكيل المستخدم والجهاز (ثابتة للجهاز الفعلي)
            user_agent = user_agent_string or "unknown"
            # تنظيف أرقام الإصدارات الدقيقة التي قد تتغير كثيراً
            for browser in ["Chrome", "Firefox", "Safari", "Edge", "Opera"]:
                if f"{browser}/" in user_agent:
                    import re
                    pattern = f"{browser}/\\d+\\.\\d+\\.\\d+\\.\\d+"
                    major_version = re.search(f"{browser}/(\\d+)", user_agent)
                    if major_version:
                        user_agent = re.sub(pattern, f"{browser}/{major_version.group(1)}", user_agent)
            
            device_components.append(f"ua:{user_agent}")
            
            # 2. نوع الجهاز - ثابت للجهاز الفعلي
            device_type = DeviceFingerprinter.get_device_type(user_agent_string)
            device_components.append(f"type:{device_type}")
            
            # 3. معلومات نظام التشغيل - ثابتة للجهاز
            os_info = ""
            if "Windows" in user_agent_string:
                if "Windows NT 10.0" in user_agent_string:
                    os_info = "Windows 10"
                elif "Windows NT 6.3" in user_agent_string:
                    os_info = "Windows 8.1"
                elif "Windows NT 6.2" in user_agent_string:
                    os_info = "Windows 8"
                elif "Windows NT 6.1" in user_agent_string:
                    os_info = "Windows 7"
                else:
                    os_info = "Windows"
            elif "Mac OS X" in user_agent_string:
                os_info = "MacOS"
            elif "Linux" in user_agent_string:
                if "Ubuntu" in user_agent_string:
                    os_info = "Ubuntu"
                elif "Fedora" in user_agent_string:
                    os_info = "Fedora"
                else:
                    os_info = "Linux"
            elif "Android" in user_agent_string:
                import re
                android_version = re.search(r"Android (\d+)", user_agent_string)
                if android_version:
                    os_info = f"Android {android_version.group(1)}"
                else:
                    os_info = "Android"
            elif "iPhone" in user_agent_string or "iPad" in user_agent_string:
                os_info = "iOS"
            
            if os_info:
                device_components.append(f"os:{os_info}")
            
            # 4. معلومات المتصفح - ثابتة للجهاز
            browser_info = ""
            if "Firefox/" in user_agent_string:
                browser_info = "Firefox"
            elif "Chrome/" in user_agent_string and "Edg/" not in user_agent_string:
                browser_info = "Chrome"
            elif "Safari/" in user_agent_string and "Chrome/" not in user_agent_string:
                browser_info = "Safari"
            elif "Edg/" in user_agent_string:
                browser_info = "Edge"
            elif "OPR/" in user_agent_string or "Opera/" in user_agent_string:
                browser_info = "Opera"
            
            if browser_info:
                device_components.append(f"browser:{browser_info}")
            
            # 5. معلومات الشاشة - ثابتة للجهاز
            if headers:
                if headers.get('X-Screen-Width') and headers.get('X-Screen-Height'):
                    width = headers.get('X-Screen-Width')
                    height = headers.get('X-Screen-Height')
                    device_components.append(f"screen:{width}x{height}")
            
            # إضافة فحص لخصائص الكانفاس والوب جي إل إذا كانت متوفرة
            if headers.get('X-Canvas-Fingerprint'):
                device_components.append(f"canvas:{headers.get('X-Canvas-Fingerprint')}")
            if headers.get('X-WebGL-Fingerprint'):
                device_components.append(f"webgl:{headers.get('X-WebGL-Fingerprint')}")
            if headers.get('X-Audio-Fingerprint'):
                device_components.append(f"audio:{headers.get('X-Audio-Fingerprint')}")
            
            # 6. اللغة والإعدادات - ثابتة للجهاز/المستخدم
            if headers:
                # لغة المتصفح 
                if headers.get('Accept-Language'):
                    # استخراج اللغة الرئيسية للمستخدم - تبقى ثابتة
                    lang = headers.get('Accept-Language').split(',')[0].split(';')[0]
                    device_components.append(f"lang:{lang}")
                
                # إعدادات المتصفح - تبقى ثابتة للجهاز
                if headers.get('Accept-Encoding'):
                    device_components.append(f"enc:{headers.get('Accept-Encoding')}")
                if headers.get('Sec-Ch-Ua'):
                    device_components.append(f"ua_brands:{headers.get('Sec-Ch-Ua')}")
                
                # معلومات المنطقة الزمنية - صعبة التغيير
                if headers.get('X-Timezone-Offset'):
                    device_components.append(f"tz:{headers.get('X-Timezone-Offset')}")
            
            # 7. معلومات إضافية عن مواصفات الجهاز (ثابتة)
            # فحص وجود plugins المتصفح
            if headers and headers.get('X-Browser-Plugins'):
                # استخدام فقط عدد الإضافات لتجنب التغييرات الصغيرة
                plugins = headers.get('X-Browser-Plugins').split(',')
                device_components.append(f"plugins_count:{len(plugins)}")
            
            # --------- معلومات الشبكة (متغيرة مع VPN) ----------
            
            # 8. عنوان IP - قد يتغير مع VPN
            if ip_address and ip_address not in ["127.0.0.1", "::1", "0.0.0.0"]:
                network_components.append(f"ip:{ip_address}")
                
                # 9. تحليل IP للحصول على معلومات البلد/الشبكة
                ip_analysis = IPAnalyzer.analyze_ip(ip_address)
                if ip_analysis:
                    # إضافة معلومات البلد
                    if "geo" in ip_analysis and ip_analysis["geo"].get("country"):
                        country = ip_analysis["geo"].get("country")
                        network_components.append(f"country:{country}")
                    
                    # إضافة معلومات المزود (ISP)
                    if ip_analysis.get("provider"):
                        provider = ip_analysis["provider"]
                        if provider.startswith("AS"):
                            import re
                            provider_name = re.sub(r"^AS\d+\s+", "", provider)
                            network_components.append(f"isp:{provider_name}")
                    
                    # إضافة نوع عنوان IP
                    if ip_analysis.get("ip_type"):
                        network_components.append(f"ip_type:{ip_analysis.get('ip_type')}")
                    
                    # مؤشر VPN - لزيادة الأمان
                    if ip_analysis.get("is_vpn") or ip_analysis.get("is_tor") or ip_analysis.get("is_datacenter"):
                        network_components.append("proxy:true")
            
            # 10. إنشاء البصمة المركبة (تجمع بين الجهاز والشبكة)
            
            # أولاً: بصمة الجهاز (ثابتة مع نفس الجهاز)
            device_str = "|".join(device_components)
            device_hash = hashlib.md5(device_str.encode('utf-8')).hexdigest()[:16]
            
            # ثانياً: بصمة الشبكة (تتغير مع VPN)
            network_str = "|".join(network_components)
            network_hash = hashlib.md5(network_str.encode('utf-8')).hexdigest()[:8] if network_components else "local"
            
            # دمج البصمتين معًا بنسبة 80% للجهاز و20% للشبكة (زيادة وزن الجهاز لمنع التحايل بالـ VPN)
            # هذا يجعل البصمة تتغير قليلاً فقط عند تغيير IP لكنها تحتفظ بطابع الجهاز
            combined_fingerprint = f"{device_hash}_{network_hash}"
            
            # استخدام SHA-256 للبصمة النهائية
            fingerprint_hash = hashlib.sha256(combined_fingerprint.encode('utf-8')).hexdigest()
            
            return fingerprint_hash
            
        except Exception as e:
            logger.error(f"Error generating device fingerprint: {e}\n{traceback.format_exc()}")
            # البصمة الاحتياطية في حالة حدوث خطأ
            try:
                backup_components = []
                if ip_address:
                    backup_components.append(f"ip:{ip_address}")
                if user_agent_string:
                    backup_components.append(user_agent_string[:50])
                
                backup_str = "|".join(backup_components)
                return hashlib.sha256(backup_str.encode('utf-8')).hexdigest()
            except:
                import uuid
                return hashlib.sha256(str(uuid.uuid4()).encode('utf-8')).hexdigest()
    
    @staticmethod
    @memcached_cached("fp", 3600)
    def generate_browser_fingerprint(user_agent_string, ip_address):
        """
        Enhanced browser fingerprinting to detect browser spoofing
        """
        try:
            # Extract browser information with more detail
            browser_info = ""
            browser_version = ""
            
            # Use ua-parser if available
            if ua_parser_available:
                try:
                    ua_parsed = user_agent_parser.Parse(user_agent_string)
                    browser_family = ua_parsed["user_agent"]["family"]
                    browser_version = f"{ua_parsed['user_agent']['major']}.{ua_parsed['user_agent']['minor']}"
                    browser_info = f"{browser_family} {browser_version}"
                    
                    # Check for inconsistencies using structured data
                    os_family = ua_parsed["os"]["family"]
                    device_family = ua_parsed["device"]["family"]
                    
                    # Safari only exists on Apple devices
                    if browser_family == "Safari" and os_family not in ["iOS", "Mac OS X"]:
                        browser_info += "|suspicious"
                        
                    # IE only exists on Windows
                    if browser_family == "IE" and os_family != "Windows":
                        browser_info += "|suspicious"
                        
                except Exception as e:
                    logger.debug(f"Error using ua-parser for browser fingerprint: {e}, falling back to regex detection")
                    # Fall back to existing method
            
            # Fallback to existing browser detection if ua-parser not available or failed
            if not browser_info:
                # Enhanced browser detection
                if "Chrome/" in user_agent_string:
                    if "Edg/" in user_agent_string:
                        browser_info = "Edge"
                        version_match = re.search(r"Edg/(\d+)", user_agent_string)
                        if version_match:
                            browser_version = version_match.group(1)
                    elif "OPR/" in user_agent_string:
                        browser_info = "Opera"
                        version_match = re.search(r"OPR/(\d+)", user_agent_string)
                        if version_match:
                            browser_version = version_match.group(1)
                    else:
                        browser_info = "Chrome"
                        version_match = re.search(r"Chrome/(\d+)", user_agent_string)
                        if version_match:
                            browser_version = version_match.group(1)
                elif "Firefox/" in user_agent_string:
                    browser_info = "Firefox"
                    version_match = re.search(r"Firefox/(\d+)", user_agent_string)
                    if version_match:
                        browser_version = version_match.group(1)
                elif "Safari/" in user_agent_string and "Chrome" not in user_agent_string:
                    browser_info = "Safari"
                    version_match = re.search(r"Version/(\d+)", user_agent_string)
                    if version_match:
                        browser_version = version_match.group(1)
                elif "MSIE " in user_agent_string or "Trident/" in user_agent_string:
                    browser_info = "Internet Explorer"
                    if "MSIE " in user_agent_string:
                        version_match = re.search(r"MSIE (\d+)", user_agent_string)
                        if version_match:
                            browser_version = version_match.group(1)
                    else:
                        version_match = re.search(r"rv:(\d+)", user_agent_string)
                        if version_match:
                            browser_version = version_match.group(1)
                else:
                    browser_info = "Unknown"
                
                # Check for inconsistencies that could indicate spoofing
                is_suspicious = False
                
                # Safari only exists on Apple devices
                if browser_info == "Safari" and "Macintosh" not in user_agent_string and "iPhone" not in user_agent_string and "iPad" not in user_agent_string:
                    is_suspicious = True
                    
                # IE only exists on Windows
                if browser_info == "Internet Explorer" and "Windows" not in user_agent_string:
                    is_suspicious = True
                    
                # Chrome has specific version patterns
                if browser_info == "Chrome" and browser_version:
                    try:
                        version_num = int(browser_version)
                        if version_num < 40 or version_num > 120:  # Unlikely version range
                            is_suspicious = True
                    except:
                        pass
            
            # Create fingerprint with additional data points
            fingerprint_data = user_agent_string + "|" + browser_info
            
            if browser_version and not browser_version in browser_info:
                fingerprint_data += "-" + browser_version
                
            if 'is_suspicious' in locals() and is_suspicious:
                fingerprint_data += "|suspicious"
            
            # Add OS info for more uniqueness
            os_info = ""
            if "Windows" in user_agent_string:
                os_info = "Windows"
            elif "Macintosh" in user_agent_string:
                os_info = "MacOS"
            elif "Linux" in user_agent_string:
                os_info = "Linux"
            elif "Android" in user_agent_string:
                os_info = "Android"
            elif "iPhone" in user_agent_string or "iPad" in user_agent_string:
                os_info = "iOS"
                
            if os_info:
                fingerprint_data += "|" + os_info
            
            # Add partial IP for additional entropy but maintain privacy
            if ip_address and ip_address not in ["127.0.0.1", "::1", "0.0.0.0"]:
                try:
                    ip = ipaddress.ip_address(ip_address)
                    if isinstance(ip, ipaddress.IPv4Address):
                        # Only use first two octets for privacy
                        ip_parts = ip_address.split('.')
                        partial_ip = f"{ip_parts[0]}.{ip_parts[1]}"
                    else:
                        # For IPv6, use first 2 blocks
                        ip_parts = ip_address.split(':')
                        partial_ip = f"{ip_parts[0]}:{ip_parts[1]}"
                    
                    fingerprint_data += "|" + partial_ip
                except:
                    pass
            
            # Use SHA-256 exclusively (no more MD5)
            fingerprint_hash = hashlib.sha256(fingerprint_data.encode('utf-8')).hexdigest()[:32]
            return fingerprint_hash
            
        except Exception as e:
            logger.error(f"Error generating browser fingerprint: {e}\n{traceback.format_exc()}")
            # Fallback fingerprint in case of error
            safe_string = (user_agent_string or "unknown")[:50]  # Limit length for safety
            return hashlib.sha256(safe_string.encode('utf-8')).hexdigest()[:32]
            
def get_security_settings():
    """Get mining security settings"""
    try:
        default_settings = {
            "anti_fraud_protection": True,
            "fraud_protection_settings": {
                "accounts_per_ip_enabled": True,
                "accounts_per_ip": 5,  # Increased from 1 to 5 to allow shared networks
                "accounts_per_device_enabled": True,
                "accounts_per_device": 1,
                "accounts_per_physical_device_enabled": True,
                "accounts_per_physical_device": 1,
                "devices_per_account_enabled": True,  # New setting
                "devices_per_account": 3,  # Allow 3 devices per account
                "networks_per_account_enabled": True,  # New setting
                "networks_per_account": 10,  # Allow 10 networks per account
                "penalty_enabled": True,
                "warning_then_ban": True,
                "permanent_ban": False,
                "mining_block": True,
                "mining_suspension": False
            }
        }
        
        # Try to get settings from wallet_db instead of creating in mining_db
        settings_doc = wallet_db["settings"].find_one({"type": "mining_security"})
        
        if not settings_doc:
            # If settings don't exist, create them with defaults in wallet_db
            try:
                wallet_db["settings"].insert_one({
                    "type": "mining_security",
                    "settings": default_settings,
                    "updated_at": datetime.datetime.now(datetime.timezone.utc)
                })
                logger.info("Created default mining security settings in wallet_db")
            except Exception as e:
                logger.error(f"Error creating default settings: {e}\n{traceback.format_exc()}")
            
            return default_settings
        
        return settings_doc.get("settings", default_settings)
    except Exception as e:
        logger.error(f"Error retrieving security settings: {e}\n{traceback.format_exc()}")
        # Return defaults as fallback
        return {
            "anti_fraud_protection": True,
            "fraud_protection_settings": {
                "accounts_per_ip": 1,
                "accounts_per_device": 1,
                "penalty_enabled": True,
                "mining_block": True
            }
        }

# Function to get real external IP address (to be called from other modules)
def get_real_ip_from_external():
    """
    Get the real external IP address using external services
    Used by other modules to ensure real IPs are stored
    
    Returns:
        str: Real external IP address or None if failed
    """
    try:
        # Try multiple IP detection services
        services = [
            'https://api.ipify.org',
            'https://ifconfig.me/ip',
            'https://api.my-ip.io/ip',
            'https://checkip.amazonaws.com'
        ]
        
        for service in services:
            try:
                response = requests.get(service, timeout=2)
                if response.status_code == 200:
                    ip = response.text.strip()
                    if ip and len(ip) > 7:  # Basic validation that it's an IP
                        logger.info(f"Retrieved real IP {ip} using {service}")
                        return ip
            except Exception:
                continue
        
        # As a last resort, try to use IPinfo services directly
        if USE_IPINFO and IPINFO_API_TOKENS:
            try:
                handler = ipinfo.getHandler(IPINFO_API_TOKENS[0])
                details = handler.getDetails()
                if details.ip and details.ip not in ["127.0.0.1", "::1"]:
                    logger.info(f"Retrieved real IP {details.ip} using IPinfo")
                    return details.ip
            except Exception:
                pass
                
        return None
    except Exception as e:
        logger.error(f"Error getting external IP: {e}")
        return None

def get_real_ip():
    """
    Enhanced function to get the real client IP address behind Cloudflare and Apache
    Correctly handles proxy headers to get actual client IPs
    """
    try:
        # Log all headers at debug level to help with troubleshooting
        try:
            all_headers = {k: v for k, v in request.headers.items()}
            logger.debug(f"Received request with headers: {all_headers}")
        except Exception:
            pass
        
        # Check most common proxy headers in order of reliability
        
        # 1. Cloudflare-specific header (highest priority)
        if 'CF-Connecting-IP' in request.headers:
            cf_ip = request.headers.get('CF-Connecting-IP')
            logger.info(f"Using Cloudflare IP: {cf_ip}")
            return cf_ip
            
        # 2. X-Forwarded-For header (common for most proxies)
        if 'X-Forwarded-For' in request.headers:
            # Get the first IP in the chain (client IP)
            forwarded_ips = request.headers.get('X-Forwarded-For').split(',')
            client_ip = forwarded_ips[0].strip()
            logger.info(f"Using X-Forwarded-For IP: {client_ip}")
            return client_ip
            
        # 3. Other common proxy headers
        for header in ['X-Real-IP', 'True-Client-IP', 'X-Client-IP']:
            if header in request.headers:
                ip = request.headers.get(header)
                logger.info(f"Using {header} IP: {ip}")
                return ip
        
        # 4. If headers don't provide an IP, use the remote address
        remote_ip = request.remote_addr
        
        # If IP is localhost/127.0.0.1, try to get real IP
        if remote_ip in ["127.0.0.1", "::1", "localhost", "0.0.0.0"] or remote_ip.startswith("192.168.") or remote_ip.startswith("10."):
            logger.warning(f"Local IP detected: {remote_ip}, attempting to get real IP")
            external_ip = get_real_ip_from_external()
            
            if external_ip:
                logger.info(f"Updated IP from local to external: {external_ip}")
                return external_ip
        
        logger.info(f"Using remote address: {remote_ip}")
        return remote_ip
        
    except Exception as e:
        logger.error(f"Error in get_real_ip(): {e}")
        # Fallback to remote_addr in case of errors
        return request.remote_addr

# Add a debug endpoint to check IP detection
@mining_security_bp.route('/debug-ip', methods=['GET'])
def debug_ip():
    """Debug endpoint to check IP detection accuracy"""
    try:
        # Get IP using our enhanced detection
        detected_ip = get_real_ip()
        
        # Get all proxy-related headers
        proxy_headers = {}
        for header in request.headers:
            header_key = header[0].lower()
            if any(key in header_key for key in ['forward', 'ip', 'client', 'cf-', 'true-', 'cluster']):
                proxy_headers[header[0]] = header[1]
        
        # Build comprehensive response
        response_data = {
            "detected_ip": detected_ip,
            "remote_addr": request.remote_addr,
            "proxy_headers": proxy_headers,
            "server_info": {
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "hostname": socket.gethostname() if hasattr(socket, 'gethostname') else "unknown"
            }
        }
        
        # Try to get IP geolocation info
        try:
            ip_info = IPAnalyzer.analyze_ip(detected_ip)
            response_data["ip_analysis"] = ip_info
        except Exception as e:
            response_data["ip_analysis_error"] = str(e)
        
        return jsonify(response_data)
    except Exception as e:
        logger.error(f"Error in debug-ip endpoint: {e}\n{traceback.format_exc()}")
        return jsonify({"error": "System error", "details": str(e)}), 500

# Add a new debug endpoint to check token status
@mining_security_bp.route('/ipinfo-tokens', methods=['GET'])
def ipinfo_tokens_status():
    """Debug endpoint to check the status of IPinfo tokens"""
    try:
        # Check if user is authenticated as admin
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({"error": "Not authenticated"}), 401
            
        # Get user info to check admin status
        user = wallet_db["users"].find_one({"user_id": user_id})
        if not user or not user.get("is_admin", False):
            return jsonify({"error": "Unauthorized access"}), 403
        
        # Reset any stale token rate limit information
        reset_stale_tokens()
        
        # Get status of all tokens
        token_status = []
        current_time = datetime.datetime.now(datetime.timezone.utc)
        
        for i, token in enumerate(IPINFO_API_TOKENS, 1):
            # Mask token for security
            masked_token = f"{token[:4]}...{token[-4:]}" if len(token) > 8 else "****"
            
            # Check if token is rate limited
            is_limited = token in rate_limited_tokens and rate_limited_tokens[token] > current_time
            time_remaining = None
            
            if is_limited:
                time_remaining = (rate_limited_tokens[token] - current_time).total_seconds() / 60  # Minutes
            
            # Get usage statistics
            usage_stats = token_usage_stats.get(token, {
                "requests": 0,
                "successful_requests": 0,
                "rate_limits": 0,
                "last_used": None,
                "errors": 0
            })
            
            # Calculate success rate
            success_rate = 0
            if usage_stats["requests"] > 0:
                success_rate = (usage_stats["successful_requests"] / usage_stats["requests"]) * 100
                
            token_status.append({
                "token_number": i,
                "token": masked_token,
                "status": "rate_limited" if is_limited else "available",
                "minutes_until_available": round(time_remaining, 1) if time_remaining else None,
                "available_at": rate_limited_tokens.get(token).isoformat() if token in rate_limited_tokens else None,
                "usage_stats": {
                    "total_requests": usage_stats["requests"],
                    "successful_requests": usage_stats["successful_requests"],
                    "rate_limits": usage_stats["rate_limits"],
                    "errors": usage_stats["errors"],
                    "success_rate": round(success_rate, 2),
                    "last_used": usage_stats["last_used"].isoformat() if usage_stats["last_used"] else None
                }
            })
        
        # Get available tokens count
        available_tokens = [token for token in IPINFO_API_TOKENS 
                           if token not in rate_limited_tokens or 
                           rate_limited_tokens[token] < current_time]
        
        return jsonify({
            "total_tokens": len(IPINFO_API_TOKENS),
            "available_tokens": len(available_tokens),
            "rate_limited_tokens": len(IPINFO_API_TOKENS) - len(available_tokens),
            "tokens": token_status,
            "timestamp": current_time.isoformat()
        })
    except Exception as e:
        logger.error(f"Error in ipinfo-tokens endpoint: {e}\n{traceback.format_exc()}")
        return jsonify({"error": "System error", "details": str(e)}), 500

def generate_hash(input_string):
    """
    Generate a SHA-256 hash of the input string
    """
    if not input_string:
        return hashlib.sha256("empty".encode()).hexdigest()
    return hashlib.sha256(str(input_string).encode()).hexdigest()

def get_advanced_fingerprint(user_id, request):
    """
    تكامل مع نظام البصمة المتقدم إذا كان متاحًا
    يستخدم النظام القديم كنظام احتياطي
    """
    try:
        # محاولة استخدام النظام الأساسي المباشر بدلاً من النظام المتقدم
        browser_fp = generate_hash(f"{request.headers.get('User-Agent', '')}|{request.headers.get('Accept-Language', '')}")
        device_fp = generate_hash(request.headers.get('User-Agent', ''))
        
        return {
            "user_id": user_id,
            "browser_fingerprint": browser_fp,
            "device_fingerprint": device_fp,
            "device_type": "desktop" if "mobile" not in request.headers.get('User-Agent', '').lower() else "mobile",
            "ip_address": get_real_ip(),
            "ip_detection_source": "basic_detection",
            "user_agent": request.headers.get('User-Agent', ''),
            "browser_language": request.headers.get('Accept-Language', ''),
            "timestamp": datetime.datetime.utcnow()
        }
    except Exception as e:
        logger.error(f"Advanced fingerprinting error: {e}")
    
    # Use the legacy system as fallback to ensure we always get something
    browser_fp = generate_hash(f"{request.headers.get('User-Agent', '')}|{request.headers.get('Accept-Language', '')}")
    device_fp = generate_hash(request.headers.get('User-Agent', ''))
    
    # النظام الاحتياطي: استخدام النظام القديم
    return {
        "user_id": user_id, 
        "browser_fingerprint": browser_fp,
        "device_fingerprint": device_fp,
        "device_type": "desktop" if "mobile" not in request.headers.get('User-Agent', '').lower() else "mobile",
        "ip_address": get_real_ip(),
        "ip_detection_source": "basic_detection",
        "user_agent": request.headers.get('User-Agent', ''),
        "browser_language": request.headers.get('Accept-Language', ''),
        "timestamp": datetime.datetime.utcnow()
    }

def record_mining_activity(user_id, discord_id=None):
    """Record mining activity with user and device information for security checks"""
    try:
        # Use the simplified fingerprint function
        fingerprint_data = get_advanced_fingerprint(user_id, request)
        
        # Get the real IP and ensure it's not localhost
        real_ip = fingerprint_data.get("ip_address")
        if real_ip in ["127.0.0.1", "::1", "localhost"] or real_ip.startswith("192.168.") or real_ip.startswith("10."):
            try:
                # Try to get external IP
                logger.warning(f"Local IP detected in mining activity: {real_ip}, attempting to get real IP")
                response = requests.get('https://api.ipify.org', timeout=3)
                if response.status_code == 200:
                    real_ip = response.text.strip()
                    logger.info(f"Updated IP from local to external: {real_ip}")
                    fingerprint_data["ip_address"] = real_ip
            except Exception as e:
                logger.error(f"Failed to get external IP: {e}")
        
        # Add Discord ID if available
        if discord_id:
            fingerprint_data["discord_id"] = discord_id
        
        # Create mining activity record
        new_activity = {
            "browser_fingerprint": fingerprint_data.get("browser_fingerprint"),
            "device_fingerprint": fingerprint_data.get("device_fingerprint"),
            "device_type": fingerprint_data.get("device_type"),
            "ip_address": fingerprint_data.get("ip_address"),
            "ip_detection_source": fingerprint_data.get("ip_detection_source", "basic"),
            "user_agent": fingerprint_data.get("user_agent"),
            "browser_language": request.headers.get('Accept-Language', ''),
            "timestamp": fingerprint_data.get("timestamp", datetime.datetime.now(datetime.timezone.utc))
        }
        
        # Get existing user record and current registered device fingerprint
        existing_record = mining_blocks.find_one({"user_id": user_id})
        
        # CRITICAL FIX: Check if user already has a registered device fingerprint
        # If yes, maintain it when updating to prevent "self-blocking" situations
        if existing_record and "activities" in existing_record and existing_record["activities"]:
            # Use the first activity's device fingerprint as the "official" one for this user
            first_activity = existing_record["activities"][0]
            if first_activity and first_activity.get("device_fingerprint"):
                original_device_fp = first_activity.get("device_fingerprint")
                
                # Keep original device fingerprint in the new activity to maintain consistency
                new_activity["device_fingerprint"] = original_device_fp
                logger.info(f"Maintained original device fingerprint for user {user_id}")
        
        # Store at max 5 activities, prioritizing unique sets
        if existing_record and "activities" in existing_record and existing_record["activities"]:
            last_activity = existing_record["activities"][-1]
            
            # Check if new activity is significantly different from last activity
            significant_change = (
                last_activity.get("ip_address") != new_activity["ip_address"] or
                last_activity.get("browser_fingerprint") != new_activity["browser_fingerprint"] or
                last_activity.get("device_type") != new_activity["device_type"]
            )
            
            # Update activities array only if there's a significant change or more than 12 hours passed
            if significant_change:
                logger.info(f"Significant change detected for user {user_id}, updating activities")
                
                # Get current activities
                current_activities = existing_record.get("activities", [])
                
                # Keep only the latest 5 activities (including new activity)
                if len(current_activities) >= 5:
                    current_activities = current_activities[-4:]
                
                # Add new activity
                current_activities.append(new_activity)
                
                # Update database with limited activities
                result = mining_blocks.update_one(
                    {"user_id": user_id},
                    {
                        "$set": {
                            "discord_id": discord_id or user_id,
                            "last_activity": new_activity,
                            "activities": current_activities,
                            "last_updated": datetime.datetime.now(datetime.timezone.utc)
                        },
                        "$setOnInsert": {
                            "created_at": datetime.datetime.now(datetime.timezone.utc)
                        }
                    },
                    upsert=True
                )
            else:
                # No significant change, just update last_activity without adding to activities array
                logger.debug(f"No significant change for user {user_id}, only updating last_activity")
                result = mining_blocks.update_one(
                    {"user_id": user_id},
                    {
                        "$set": {
                            "discord_id": discord_id or user_id,
                            "last_activity": new_activity,
                            "last_updated": datetime.datetime.now(datetime.timezone.utc)
                        },
                        "$setOnInsert": {
                            "created_at": datetime.datetime.now(datetime.timezone.utc)
                        }
                    },
                    upsert=True
                )
        else:
            # New user or no activities yet, create first record
            result = mining_blocks.update_one(
                {"user_id": user_id},
                {
                    "$set": {
                        "discord_id": discord_id or user_id,
                        "last_activity": new_activity,
                        "activities": [new_activity],
                        "last_updated": datetime.datetime.now(datetime.timezone.utc)
                    },
                    "$setOnInsert": {
                        "created_at": datetime.datetime.now(datetime.timezone.utc)
                    }
                },
                upsert=True
            )
        
        # Log the result for monitoring
        logger.debug(f"Mining activity recorded for user {user_id}: modified_count={result.modified_count}, matched_count={result.matched_count}")
        
        # Return activity info
        new_activity.update({
            "user_id": user_id,
            "discord_id": discord_id or user_id,
        })
        
        return new_activity
    except Exception as e:
        logger.error(f"Error recording mining activity: {e}\n{traceback.format_exc()}")
        # Return a minimal valid activity record to prevent further errors
        # Generate fallback fingerprints that are not "error"
        browser_fp = generate_hash(f"fallback_browser_{user_id}_{datetime.datetime.now().timestamp()}")
        device_fp = generate_hash(f"fallback_device_{user_id}_{datetime.datetime.now().timestamp()}")
        
        fallback_data = {
            "user_id": user_id,
            "discord_id": discord_id or user_id,
            "browser_fingerprint": browser_fp,
            "device_fingerprint": device_fp,
            "device_type": "unknown",
            "ip_address": get_real_ip(),
            "ip_detection_source": "fallback",
            "user_agent": request.headers.get('User-Agent', 'unknown'),
            "browser_language": request.headers.get('Accept-Language', ''),
            "timestamp": datetime.datetime.now(datetime.timezone.utc)
        }
        
        # At least attempt to store this fallback data
        try:
            mining_blocks.update_one(
                {"user_id": user_id},
                {
                    "$set": {
                        "discord_id": discord_id or user_id,
                        "last_activity": fallback_data,
                        "last_updated": datetime.datetime.now(datetime.timezone.utc)
                    },
                    "$push": {
                        "activities": fallback_data
                    },
                    "$setOnInsert": {
                        "created_at": datetime.datetime.now(datetime.timezone.utc)
                    }
                },
                upsert=True
            )
        except Exception as store_error:
            logger.error(f"Critical error storing fallback data: {store_error}")
            
        return fallback_data

@memcached_cached("miners", 300)  # Cache for 5 minutes (reverted from 1 hour)
def get_first_miner_by_device_fingerprint(fingerprint, ip_address=None):
    """
    Get the first user who mined from this device using aggregation for better performance
    Now also considers IP address to prevent false positives
    """
    try:
        if not fingerprint or fingerprint == "":
            logger.warning(f"Empty device fingerprint provided to get_first_miner_by_device_fingerprint")
            return None
            
        # إذا لم يتم تقديم عنوان IP، فلا يمكن إجراء تحقق موثوق
        if not ip_address or ip_address in ["127.0.0.1", "::1", "0.0.0.0"]:
            logger.warning("IP address not provided or is local, can't determine device ownership reliably")
            return None
            
        # تحسين أمان التحقق: نحن نتحقق الآن من تطابق الجهاز وIP معًا فقط
        logger.info(f"Enhanced security check: verifying device fingerprint AND IP match for {fingerprint[:8]}...")
        
        # البحث عن مستخدم بنفس بصمة الجهاز ونفس عنوان IP
        pipeline = [
            # Match documents with this device fingerprint in activities
            {"$match": {"activities.device_fingerprint": fingerprint}},
            # Unwind activities for filtering
            {"$unwind": "$activities"},
            # Match only the activities with this device fingerprint AND same IP
            {"$match": {
                "activities.device_fingerprint": fingerprint,
                "activities.ip_address": ip_address
            }},
            # Sort by timestamp (oldest first)
            {"$sort": {"activities.timestamp": 1}},
            # Limit to first record
            {"$limit": 1},
            # Project just what we need
            {"$project": {"user_id": 1, "_id": 0}}
        ]
        
        result = list(mining_blocks.aggregate(pipeline))
        if result:
            first_user = result[0]["user_id"]
            
            # تحقق إضافي: التأكد من أن المستخدم موجود في قاعدة البيانات
            user_exists = wallet_db["users"].find_one({"user_id": first_user})
            if not user_exists:
                logger.warning(f"User {first_user} found as first user for device {fingerprint[:8]} but doesn't exist in wallet_db")
                return None
            
            logger.info(f"Found user {first_user} matching device AND IP {ip_address}")
            return first_user
        else:
            # لم يتم العثور على تطابق بين بصمة الجهاز وعنوان IP
            logger.info(f"No user found with device fingerprint {fingerprint[:8]}... AND IP {ip_address}")
            return None
    
    except Exception as e:
        logger.error(f"Error getting first miner by device fingerprint: {e}\n{traceback.format_exc()}")
        return None

@memcached_cached("miners", 300)  # Cache for 5 minutes (reverted from 1 hour)
def get_first_miner_by_ip(ip_address):
    """Get the first user who mined from this IP address using aggregation for better performance"""
    try:
        # Replace the old approach with a more efficient MongoDB aggregation pipeline
        pipeline = [
            # Match documents with this IP in activities
            {"$match": {"activities.ip_address": ip_address}},
            # Unwind activities for sorting
            {"$unwind": "$activities"},
            # Match only the activities with this IP
            {"$match": {"activities.ip_address": ip_address}},
            # Sort by timestamp (oldest first)
            {"$sort": {"activities.timestamp": 1}},
            # Limit to first record
            {"$limit": 1},
            # Project just what we need
            {"$project": {"user_id": 1, "_id": 0}}
        ]
        
        result = list(mining_blocks.aggregate(pipeline))
        return result[0]["user_id"] if result else None
    except Exception as e:
        logger.error(f"Error getting first miner by IP: {e}\n{traceback.format_exc()}")
        return None

@memcached_cached("miners", 300)  # Cache for 5 minutes (reverted from 1 hour)
def get_first_miner_by_device(fingerprint):
    """Get the first user who mined from this device using aggregation for better performance"""
    try:
        # Use a similar approach with aggregation
        pipeline = [
            {"$match": {"activities.browser_fingerprint": fingerprint}},
            {"$unwind": "$activities"},
            {"$match": {"activities.browser_fingerprint": fingerprint}},
            {"$sort": {"activities.timestamp": 1}},
            {"$limit": 1},
            {"$project": {"user_id": 1, "_id": 0}}
        ]
        
        result = list(mining_blocks.aggregate(pipeline))
        return result[0]["user_id"] if result else None
    except Exception as e:
        logger.error(f"Error getting first miner by device: {e}\n{traceback.format_exc()}")
        return None

# دالة جديدة للحصول على جميع المستخدمين الذين يستخدمون نفس IP
@memcached_cached("miners", 300)  # Cache for 5 minutes
def get_all_miners_by_ip(ip_address, except_user_id=None):
    """Get all users who have mined from this IP address"""
    try:
        # تحسين الأداء باستخدام aggregate بدلاً من find كثيرًا
        pipeline = [
            {"$match": {"activities.ip_address": ip_address}},
            {"$project": {"user_id": 1, "_id": 0}}
        ]
        
        # إضافة استبعاد المستخدم الحالي إذا تم تحديده
        if except_user_id:
            pipeline[0]["$match"]["user_id"] = {"$ne": except_user_id}
        
        # تنفيذ الاستعلام
        results = list(mining_blocks.aggregate(pipeline))
        return [r["user_id"] for r in results]
    except Exception as e:
        logger.error(f"Error getting all miners by IP: {e}\n{traceback.format_exc()}")
        return []

# دالة جديدة للحصول على جميع المستخدمين الذين يستخدمون نفس المتصفح
@memcached_cached("miners", 300)  # Cache for 5 minutes
def get_all_miners_by_browser(fingerprint, except_user_id=None):
    """Get all users who have mined from this browser fingerprint"""
    try:
        # تحسين الأداء باستخدام aggregate
        pipeline = [
            {"$match": {"activities.browser_fingerprint": fingerprint}},
            {"$project": {"user_id": 1, "_id": 0}}
        ]
        
        # إضافة استبعاد المستخدم الحالي إذا تم تحديده
        if except_user_id:
            pipeline[0]["$match"]["user_id"] = {"$ne": except_user_id}
        
        # تنفيذ الاستعلام
        results = list(mining_blocks.aggregate(pipeline))
        return [r["user_id"] for r in results]
    except Exception as e:
        logger.error(f"Error getting all miners by browser: {e}\n{traceback.format_exc()}")
        return []

def detect_vpn_usage(mining_block, ip_analysis):
    """Enhanced VPN detection method with behavioral analysis and IPinfo.io integration"""
    try:
        ip_address = mining_block.get("ip_address", "")
        user_agent = mining_block.get("user_agent", "")
        
        # Special case: localhost (127.0.0.1) should not be flagged as VPN for development
        if ip_address in ["127.0.0.1", "::1", "localhost"]:
            # Return is_vpn = False for localhost
            return False
        
        # تعزيز اكتشاف VPN والبروكسي
        proxy_likelihood = 0  # مؤشر احتمالية استخدام VPN/بروكسي (0-100)
            
        # 1. أولاً تحقق من معلومات IPinfo.io - إعطاء أهمية أكبر لهذا المصدر
        if ip_analysis:
            # فحص علامات VPN المباشرة من IPinfo
            if ip_analysis.get("is_vpn", False):
                logger.warning(f"IP {ip_address} detected as VPN by IPinfo.io")
                proxy_likelihood += 90  # زيادة من 75 إلى 90
            
            if ip_analysis.get("is_tor", False):
                logger.warning(f"IP {ip_address} detected as TOR exit node")
                proxy_likelihood += 95  # زيادة من 85 إلى 95
                
            if ip_analysis.get("is_datacenter", False):
                logger.warning(f"IP {ip_address} belongs to datacenter/hosting provider")
                proxy_likelihood += 80  # زيادة من 60 إلى 80
                
            # تحقق من مؤشر المخاطر
            risk_score = ip_analysis.get("risk_score", 0)
            if risk_score > 50:
                proxy_likelihood += risk_score * 0.7  # زيادة من 0.5 إلى 0.7
                
            # تحقق من خصوصية IP
            if "privacy" in ip_analysis and isinstance(ip_analysis["privacy"], dict):
                privacy = ip_analysis["privacy"]
                if privacy.get("vpn", False) or privacy.get("proxy", False):
                    proxy_likelihood += 95  # زيادة من 80 إلى 95
                if privacy.get("tor", False):
                    proxy_likelihood += 95  # زيادة من 90 إلى 95
                if privacy.get("hosting", False):
                    proxy_likelihood += 85  # زيادة من 60 إلى 85
        
        # 2. فحص عناوين IP المعروفة - تحديث بقائمة أكبر من عناوين VPN
        # إضافة المزيد من نطاقات VPN الشائعة
        vpn_ranges = IPAnalyzer.VPN_PREFIXES + [
            # Added Nord VPN ranges
            "143.244.", "45.14.", "154.47.", "185.128.", "185.247.", "192.145.", "194.242.",
            # Added Surfshark ranges
            "143.244.", "185.252.", "31.13.", "179.43.", "91.132.", "195.181.",
            # Added Express VPN ranges
            "172.93.", "169.150.", "91.207.", "91.207.", "185.252.", "154.47.",
            # Added PIA VPN ranges
            "212.102.54.", "212.102.44.", "212.102.45.", "209.58.144.", "209.58.188.",
            # Added Mullvad ranges
            "193.138.218.", "193.32.127.", "148.251.151.", "194.127.167.", "217.170.204.",
            # Added ProtonVPN ranges
            "185.159.157.", "185.159.158.", "185.159.159.", "185.159.156.", "138.199.6.",
            # Ivacy VPN
            "5.180.62.", "162.217.", "185.183.", "172.241.", "193.9.114.", "156.146.",
            # Hide My Ass / Avast
            "31.6.58.", "31.6.59.", "83.142.224.", "89.187.176.", "89.187.177.", "89.187.178.",
            # Added CyberGhost ranges
            "212.102.49.", "91.207.102.", "91.207.170.", "91.219.236.", "91.219.237.", "146.70.42.",
            # Added TorGuard ranges
            "109.201.152.", "176.125.235.", "85.212.171.", "91.207.57.", "104.244.74.", "104.244.76.",
            # Added ZenMate ranges
            "91.230.199.", "37.221.172.", "191.96.73.", "192.200.158.", "217.138.205.",
            # Known Tor exits
            "195.176.3.", "131.188.40.", "94.230.208.", "65.181.123.", "18.27.197.", "171.25.193.",
            # Added IPVanish
            "209.58.188.", "209.58.184.", "205.185.208.", "205.185.216.", "170.178.178.", "89.238.186.",
            # Added more VPN/Tor providers
            "94.142.244.", "37.48.90.", "31.6.58.", "98.143.144.", "195.154.122.", "213.152.168."
        ]
        
        for vpn_prefix in vpn_ranges:
            if ip_address.startswith(vpn_prefix):
                logger.warning(f"IP {ip_address} matches known VPN prefix {vpn_prefix}")
                proxy_likelihood += 90  # زيادة من 80 إلى 90
                break
                
        # Expanded TOR detection
        tor_detected = False
        
        # 1. Check Tor prefixes first
        for tor_prefix in IPAnalyzer.TOR_PREFIXES:
            if ip_address.startswith(tor_prefix):
                logger.warning(f"IP {ip_address} matches known TOR prefix {tor_prefix}")
                proxy_likelihood += 95
                tor_detected = True
                break
                
        # 2. Additional Tor detection with port checking patterns
        if not tor_detected:
            tor_patterns = [
                # Common Tor exit node patterns
                r"exit[-.]\d+\.tor-", r"tor-exit", r"torix", r"torexit", r"tornode", 
                r"tor\.anonymizer", r"relay-\d+\.tor", r"tor-relay", r"torproject", 
                r"onion", r"anonymizing-proxy", r"msnbot-tor", r"tor\.not\.your\.network"
            ]
            
            # Check if hostname is available
            hostname = ip_analysis.get("hostname", "")
            if hostname:
                for pattern in tor_patterns:
                    if re.search(pattern, hostname, re.IGNORECASE):
                        logger.warning(f"IP {ip_address} hostname '{hostname}' matches Tor pattern")
                        proxy_likelihood += 95
                        tor_detected = True
                        break
                        
        # 3. Use provider info to detect Tor
        provider = ip_analysis.get("provider", "")
        if provider and not tor_detected:
            tor_provider_keywords = ["tor", "relay", "exit node", "torproject", "onion router"]
            for keyword in tor_provider_keywords:
                if keyword in provider.lower():
                    logger.warning(f"IP {ip_address} provider '{provider}' matches Tor keyword")
                    proxy_likelihood += 95
                    tor_detected = True
                    break
        
        # 3. فحص نوع IP
        ip_type = ip_analysis.get("ip_type", "unknown")
        if ip_type in ["vpn", "tor", "datacenter"]:
            proxy_likelihood += 85  # زيادة من 70 إلى 85
        
        # 4. فحص معلومات البلد/المزود
        if ip_analysis and "geo" in ip_analysis and ip_analysis["geo"].get("country"):
            country = ip_analysis["geo"].get("country")
            # بعض البلدان معروفة باستضافة خدمات VPN
            vpn_countries = ["PA", "VG", "KY", "SC", "BZ", "RO", "BG", "CH", "LU", "NL", "SE", "IS"]
            if country in vpn_countries:
                proxy_likelihood += 50  # زيادة من 30 إلى 50
                
        # 5. Enhanced user agent analysis for VPN detection
        vpn_detected_in_ua = False
        
        # 5.1 Check for VPN keywords in user agent
        for vpn_keyword in IPAnalyzer.VPN_KEYWORDS:
            if vpn_keyword in user_agent.lower():
                logger.warning(f"VPN keyword '{vpn_keyword}' found in user agent")
                proxy_likelihood += 90  # زيادة من 80 إلى 90
                vpn_detected_in_ua = True
                break
                
        # 5.2 Advanced port pattern analysis - check for typical VPN/proxy port patterns in hostname
        if not vpn_detected_in_ua and "hostname" in ip_analysis:
            hostname = ip_analysis.get("hostname", "")
            vpn_port_patterns = [
                r"\.socks\d*\.", r"\.proxy\d*\.", r"\.vpn\d*\.", r"\.pptp\.", r"\.openvpn\.", 
                r"\.l2tp\.", r"\.relay\d*\.", r"-p\d{2,5}-", r"proxy-\d{1,3}-\d{1,3}", 
                r"gateway-\d{1,3}", r"exit-\d{1,3}", r"outbound-\d{1,3}"
            ]
            
            for pattern in vpn_port_patterns:
                if re.search(pattern, hostname, re.IGNORECASE):
                    logger.warning(f"VPN port pattern '{pattern}' detected in hostname '{hostname}'")
                    proxy_likelihood += 85
                    break
                    
        # 5.3 Check for popular VPN provider hostnames
        if not vpn_detected_in_ua and "hostname" in ip_analysis:
            hostname = ip_analysis.get("hostname", "").lower()
            vpn_hostname_keywords = [
                "nordvpn", "expressvpn", "purevpn", "protonvpn", "surfshark", "cyberghost", 
                "ipvanish", "torguard", "privatevpn", "mullvad", "hidemyass", "vyprvpn", 
                "strongvpn", "privatetunnel", "tunnelbear", "windscribe", "safervpn", 
                "ivacy", "vpnunlimited", "hotspotshield", "avast-secure", "norton-secure",
                "kaspersky-secure", "f-secure", "zenvpn", "opera-vpn", "avg-secure",
                "vpnsecure", "anonvpn", "privatix", "hide-me", "trust-zone", "airvpn",
                "ovpn", "perfectprivacy", "proxy", "proxies", "anonymous", "hidden", "masked"
            ]
            
            for keyword in vpn_hostname_keywords:
                if keyword in hostname:
                    logger.warning(f"VPN provider keyword '{keyword}' found in hostname '{hostname}'")
                    proxy_likelihood += 90
                    break
        
        # 6. فحص التغيرات السريعة في عناوين IP
        try:
            user_id = mining_block.get("user_id")
            if user_id:
                # الحصول على سجل أنشطة المستخدم خلال الـ 24 ساعة الماضية
                recent_time = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=24)
                user_records = mining_blocks.find_one({"user_id": user_id})
                
                if user_records and "activities" in user_records:
                    # تجميع عناوين IP وبلدان مختلفة
                    recent_ips = set()
                    countries = set()
                    
                    for activity in user_records["activities"]:
                        if activity.get("timestamp", datetime.datetime.min.replace(tzinfo=datetime.timezone.utc)) > recent_time:
                            recent_ips.add(activity.get("ip_address", ""))
                    
                            # محاولة استخراج بلد النشاط
                            activity_ip = activity.get("ip_address", "")
                            if activity_ip:
                                ip_info = IPAnalyzer.analyze_ip(activity_ip)
                                if ip_info and "geo" in ip_info and ip_info["geo"].get("country"):
                                    countries.add(ip_info["geo"].get("country"))
                    
                    # تغيير IP أكثر من مرة في 24 ساعة مع اختلاف البلدان
                    if len(recent_ips) >= 2:
                        logger.warning(f"User {user_id} used {len(recent_ips)} different IPs in 24 hours")
                        proxy_likelihood += 60  # زيادة من 40 إلى 60
                        
                    # الاتصال من بلدان مختلفة خلال 24 ساعة مؤشر قوي على VPN
                    if len(countries) >= 2:
                        logger.warning(f"User {user_id} connected from {len(countries)} different countries in 24 hours")
                        proxy_likelihood += 85  # زيادة من 70 إلى 85
        except Exception as e:
            logger.debug(f"Error checking IP history: {e}")
        
        # تحديد النتيجة النهائية - تحسين دقة الكشف مع منح أولوية لنتائج IPinfo
        # إعطاء الأولوية لتحليل IPinfo إذا كان متوفراً وموثوقاً
        if ip_analysis and "is_vpn" in ip_analysis:
            # إذا كان IPinfo يؤكد أن العنوان ليس VPN، وهو عنوان سكني معروف
            if (ip_analysis.get("is_vpn") == False and 
                ip_analysis.get("is_datacenter") == False and 
                ip_analysis.get("is_tor") == False and
                ip_analysis.get("ip_type", "") == "residential" and
                ip_analysis.get("risk_score", 100) < 30):
                
                # التحقق من مزود خدمة الإنترنت للتعرف على الاستثناءات
                provider = ip_analysis.get("provider", "").lower()
                known_isps = ["paltel", "telecom", "etisalat", "zain", "ooredoo", "vodafone", "orange"]
                
                # التحقق من عنوان IP محدد للاستثناء (نطاق شركة PALTEL)
                if ((any(isp in provider for isp in known_isps) or
                     "palestine telecommunications" in provider) and 
                    ip_address.startswith("82.102.")):
                    
                    logger.info(f"IP {ip_address} identified as legitimate residential IP from Palestine Telecom")
                    # تخفيض قيمة الاحتمالية لتجنب الإيجابيات الكاذبة
                    proxy_likelihood = max(0, proxy_likelihood - 60)
        
        # تعديل العتبة لضمان توازن أفضل بين الدقة والحساسية
        # العتبة 55% تسمح بكشف المزيد من خدمات VPN مع تقليل الكشف الخاطئ
        is_vpn = proxy_likelihood >= 55
        
        # إضافة نتيجة احتمالية الكشف للتسجيل والتحليل
        logger.info(f"VPN detection likelihood for IP {ip_address}: {proxy_likelihood}%")
        
        if is_vpn:
            logger.warning(f"VPN/proxy detected for IP {ip_address} with likelihood {proxy_likelihood}%")
        
        return is_vpn
    except Exception as e:
        logger.error(f"Error detecting VPN usage: {e}\n{traceback.format_exc()}")
        return False

def check_mining_violations(user_id, mining_block):
    """
    Enhanced security violation detection with weighted risk assessment
    Returns:
    - (is_violation, violation_details)
    """
    start_time = time.time()
    
    try:
        # Get security settings
        security_settings = get_security_settings()
        
        # If anti-fraud protection is disabled, allow mining
        if not security_settings["anti_fraud_protection"]:
            logger.info(f"Anti-fraud protection disabled, allowing mining for user {user_id}")
            return False, None
        
        # Get fraud protection settings
        fraud_settings = security_settings["fraud_protection_settings"]
        ip_address = mining_block["ip_address"]
        browser_fingerprint = mining_block["browser_fingerprint"]
        device_fingerprint = mining_block.get("device_fingerprint")
        device_type = mining_block.get("device_type", "unknown")
        
        # Get detailed IP analysis first to use throughout the check
        ip_analysis = IPAnalyzer.analyze_ip(ip_address)
        
        # 1. فحص VPN/بروكسي أولاً - أهم خطوة!
        is_vpn = detect_vpn_usage(mining_block, ip_analysis)
        
        # سجل معلومات تحليل IP للفحص لاحقاً
        logger.info(f"IP analysis for {ip_address}: VPN={is_vpn}, type={ip_analysis.get('ip_type', 'unknown')}")
        
        # 2. تحسين استخراج بصمة الجهاز الأساسية (بدون معلومات الشبكة)
        # استخراج الجزء الأول من البصمة المركبة (الجزء الخاص بالجهاز فقط)
        device_part = device_fingerprint.split('_')[0] if device_fingerprint and '_' in device_fingerprint else device_fingerprint
        
        # 3. استراتيجية متعددة للبحث عن مستخدمين متعددين لنفس الجهاز
        device_users = []
        
        # 3.1 طريقة 1: البحث المباشر عن نفس بصمة الجهاز بالضبط
        if device_fingerprint:
            try:
                exact_matches = list(mining_blocks.find(
                    {"activities.device_fingerprint": device_fingerprint}
                ))
                
                for record in exact_matches:
                    record_user_id = record.get("user_id")
                    if record_user_id and record_user_id != user_id:
                        device_users.append(record_user_id)
                        logger.warning(f"Found user {record_user_id} using exact same device fingerprint as {user_id}")
            except Exception as e:
                logger.error(f"Error finding exact device matches: {e}")
        
        # 3.2 طريقة 2: البحث عن الجزء الأساسي من البصمة (بدون جزء الشبكة)
        if device_part and device_part != device_fingerprint:
            try:
                # استخدام regex للبحث عن البصمات التي تبدأ بنفس بصمة الجهاز الأساسية
                regex_pattern = f"^{device_part}_.*"
                part_matches = list(mining_blocks.find(
                    {"activities.device_fingerprint": {"$regex": regex_pattern}}
                ))
                
                for record in part_matches:
                    record_user_id = record.get("user_id")
                    if record_user_id and record_user_id != user_id and record_user_id not in device_users:
                        device_users.append(record_user_id)
                        logger.warning(f"Found user {record_user_id} using same physical device (base fingerprint) as {user_id}")
            except Exception as e:
                logger.error(f"Error finding device partial matches: {e}")
                
        # 3.3 طريقة 3: البحث عن بصمة المتصفح بدقة عالية
        if browser_fingerprint:
            try:
                browser_matches = list(mining_blocks.find(
                    {"activities.browser_fingerprint": browser_fingerprint}
                ))
                
                for record in browser_matches:
                    record_user_id = record.get("user_id")
                    if record_user_id and record_user_id != user_id and record_user_id not in device_users:
                        device_users.append(record_user_id)
                        logger.warning(f"Found user {record_user_id} using same browser as {user_id}")
            except Exception as e:
                logger.error(f"Error finding browser matches: {e}")
                
        # تسجيل عدد المستخدمين الذين تم العثور عليهم
        if device_users:
            logger.warning(f"Found total of {len(device_users)} other users sharing device with {user_id}: {device_users}")
        
        # 4. تحسين الكشف عن استخدام VPN - البحث عن المستخدم الرئيسي للجهاز
        primary_device_user = None
        recent_device_users = []
        
        # البحث عن المستخدم الرئيسي للجهاز (الأكثر نشاطًا)
        if device_users and device_fingerprint:
            try:
                # 4.1 البحث عن أنشطة المستخدمين في آخر 30 يوم
                thirty_days_ago = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=30)
                
                user_activity_counts = {}
                for other_user_id in device_users:
                    # إحصاء الأنشطة لكل مستخدم على هذا الجهاز
                    activities = mining_blocks.count_documents({
                        "user_id": other_user_id,
                        "activities.device_fingerprint": {"$regex": f"^{device_part}.*"},
                        "activities.timestamp": {"$gte": thirty_days_ago}
                    })
                    
                    user_activity_counts[other_user_id] = activities
                    
                    # التحقق من آخر نشاط للمستخدم على هذا الجهاز
                    last_activity = mining_blocks.find_one(
                        {
                            "user_id": other_user_id,
                            "activities.device_fingerprint": {"$regex": f"^{device_part}.*"}
                        },
                        {"activities": {"$slice": -1}}
                    )
                    
                    if last_activity and "activities" in last_activity and last_activity["activities"]:
                        last_ts = last_activity["activities"][0].get("timestamp")
                        # إذا كان النشاط في آخر 7 أيام، أضفه إلى المستخدمين الحاليين
                        if last_ts and last_ts > (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=7)):
                            recent_device_users.append(other_user_id)
                
                # تحديد المستخدم الرئيسي بناءً على عدد الأنشطة
                if user_activity_counts:
                    primary_device_user = max(user_activity_counts.items(), key=lambda x: x[1])[0]
                    logger.info(f"Identified primary user of device: {primary_device_user}, activity counts: {user_activity_counts}")
            except Exception as e:
                logger.error(f"Error finding primary device user: {e}")
        
        # 4.2 إذا كان المستخدم يستخدم VPN ولديه مستخدم رئيسي واحد فقط للجهاز
        original_owner = None
        
                # تحسين تحديد المالك الأصلي للجهاز بشكل أكثر ثباتًا
        # استخراج المزيد من خصائص الجهاز لتجاوز تأثير الشبكة
        device_base = None
        if device_fingerprint:
            # استخراج جزء أكثر ثباتًا من بصمة الجهاز (32 حرف أولى فقط - هاردوير الجهاز)
            device_base = device_fingerprint[:32] if len(device_fingerprint) >= 32 else device_fingerprint
        
        # محاولة العثور على المالك الأصلي حتى مع اختلاف بصمة الجهاز قليلاً
        try:
            # 1. البحث عن المستخدم الذي له أقدم سجل على هذا الجهاز (بالاعتماد على الجزء الثابت من البصمة)
            if device_base:
                # البحث بطريقة مرنة عن أي بصمة تحتوي على نفس بداية بصمة الهاردوير
                all_device_records = list(mining_blocks.find(
                    {"activities.device_fingerprint": {"$regex": f"^{device_base}"}},
                    {"user_id": 1, "activities": 1}
                ))
                
                # فرز جميع الأنشطة بترتيب تصاعدي بناءً على الوقت لتحديد أقدم نشاط
                all_activities = []
                for record in all_device_records:
                    user_id_record = record.get("user_id")
                    if user_id_record and "activities" in record:
                        for activity in record["activities"]:
                            if "timestamp" in activity and "device_fingerprint" in activity:
                                # التحقق من تطابق البصمة مع النمط المطلوب
                                if activity["device_fingerprint"].startswith(device_base):
                                    all_activities.append({
                                        "user_id": user_id_record,
                                        "timestamp": activity["timestamp"]
                                    })
                
                # فرز الأنشطة بترتيب تصاعدي حسب الوقت
                if all_activities:
                    all_activities.sort(key=lambda x: x["timestamp"])
                    # المستخدم الأول هو مالك الجهاز الأصلي
                    original_owner = all_activities[0]["user_id"]
                    logger.info(f"Identified true first owner of device: {original_owner}")
            
            # 2. إذا لم نجد مالكًا، نستخدم المستخدم الرئيسي كاحتياطي
            if not original_owner and primary_device_user and primary_device_user != user_id:
                original_owner = primary_device_user
                logger.info(f"Using primary user as device owner fallback: {original_owner}")
        except Exception as e:
            logger.error(f"Error finding device owner: {e}")
        
        # الآن نقوم بإنشاء الانتهاك فقط إذا كان هناك مالك أصلي واحد مختلف عن المستخدم الحالي
        if is_vpn and original_owner:
            logger.critical(f"User {user_id} is using VPN with a device originally owned by {original_owner}")
            
            violations = [{
                "type": "vpn_evasion",
                "message": "Using VPN to bypass device restrictions",
                "existing_users": [original_owner],  # مصفوفة تحتوي على المالك الأصلي فقط
                "severity": "critical",
                "risk_score": 100
            }]
            
            violation_points = 10  # أقصى عقوبة
            violation_risk_score = 100
            penalty_type = 'mining_block'
            
            # Apply mining block penalty
            try:
                if fraud_settings.get("penalty_enabled", True):
                    result = wallet_db["users"].update_one(
                        {"user_id": user_id},
                        {"$set": {"mining_block": True, "mining_block_reason": "Security policy violation: Using VPN to bypass device restrictions", "mining_blocked_at": datetime.datetime.now(datetime.timezone.utc)}}
                    )
                    if result.modified_count > 0:
                        logger.warning(f"User {user_id} has been blocked from mining (VPN evasion)")
            except Exception as e:
                logger.error(f"Error applying VPN evasion penalty to user {user_id}: {e}")
            
            # Create violation record
            violation_record = {
                "browser_fingerprint": browser_fingerprint,
                "device_fingerprint": device_fingerprint,
                "device_type": device_type,
                "ip_address": ip_address,
                "ip_analysis": ip_analysis,
                "user_agent": mining_block["user_agent"],
                "previous_user_id": device_users[0] if device_users else None,
                "timestamp": datetime.datetime.now(datetime.timezone.utc),
                "reason": "Using VPN to bypass device restrictions",
                "violations": violations,
                "violation_points": violation_points,
                "risk_score": violation_risk_score,
                "penalty_type": penalty_type,
                "is_vpn_detected": True,
                "check_time_ms": int((time.time() - start_time) * 1000)
            }
            
            # Record violation in database
            try:
                mining_violations.update_one(
                    {"user_id": user_id},
                    {
                        "$set": {
                            "discord_id": mining_block.get("discord_id", user_id),
                            "last_violation": violation_record
                        },
                        "$push": {
                            "violations": violation_record
                        },
                        "$setOnInsert": {
                            "created_at": datetime.datetime.now(datetime.timezone.utc)
                        }
                    },
                    upsert=True
                )
            except Exception as e:
                logger.error(f"Error recording VPN evasion violation for user {user_id}: {e}")
            
            return True, {
                "user_id": user_id,
                "discord_id": mining_block.get("discord_id", user_id),
                "reason": "Multiple accounts detected on same device with VPN/proxy evasion attempt",
                "violations": violations,
                "violation_points": violation_points,
                "risk_score": violation_risk_score,
                "penalty_type": penalty_type,
                "is_vpn_detected": True
            }
        
        # 5. تفحص إضافي: البحث عن أنماط اتصال مشبوهة (مثل الاتصال من بلدان مختلفة في وقت قصير)
        suspicious_patterns = False
        pattern_reason = ""
        
        try:
            # الحصول على سجل أنشطة المستخدم
            user_records = mining_blocks.find_one({"user_id": user_id})
            
            if user_records and "activities" in user_records:
                activities = user_records["activities"]
                
                # فحص التغيرات السريعة بين البلدان في آخر 12 ساعة
                recent_time = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=12)
                
                # جمع عناوين IP والبلدان والأوقات
                ip_country_data = []
                
                for activity in activities:
                    timestamp = activity.get("timestamp", datetime.datetime.min.replace(tzinfo=datetime.timezone.utc))
                    if timestamp > recent_time:
                        ip = activity.get("ip_address", "")
                        
                        if ip:
                            # استخراج معلومات البلد
                            country = None
                            ip_info = IPAnalyzer.analyze_ip(ip)
                            if ip_info and "geo" in ip_info and ip_info["geo"].get("country"):
                                country = ip_info["geo"].get("country")
                            
                            if country:
                                ip_country_data.append({
                                    "ip": ip,
                                    "country": country,
                                    "timestamp": timestamp
                                })
                
                # فرز البيانات حسب الوقت
                ip_country_data.sort(key=lambda x: x["timestamp"])
                
                # فحص التغييرات السريعة في البلدان
                if len(ip_country_data) >= 2:
                    distinct_countries = set(item["country"] for item in ip_country_data)
                    
                    # إذا كان هناك أكثر من بلدين في 12 ساعة
                    if len(distinct_countries) >= 2:
                        # حساب الوقت بين تغييرات البلد
                        for i in range(1, len(ip_country_data)):
                            if ip_country_data[i]["country"] != ip_country_data[i-1]["country"]:
                                time_diff = (ip_country_data[i]["timestamp"] - ip_country_data[i-1]["timestamp"]).total_seconds() / 60
                                
                                # إذا كان التغيير في أقل من 60 دقيقة، فهذا مريب جداً
                                if time_diff < 60:
                                    suspicious_patterns = True
                                    pattern_reason = f"Rapid country change: {ip_country_data[i-1]['country']} to {ip_country_data[i]['country']} in {time_diff:.1f} minutes"
                                    break
        except Exception as e:
            logger.error(f"Error checking connection patterns: {e}")
        
        # إذا وجدنا أنماط اتصال مشبوهة
        if suspicious_patterns:
            logger.warning(f"User {user_id} shows suspicious connection patterns: {pattern_reason}")
            
            violations = [{
                "type": "suspicious_connection_pattern",
                "message": f"Suspicious connection pattern: {pattern_reason}",
                "severity": "high",
                "risk_score": 90
            }]
            
            violation_points = 9
            violation_risk_score = 90
            penalty_type = 'mining_block'
            
            # Apply mining block penalty
            try:
                if fraud_settings.get("penalty_enabled", True):
                    result = wallet_db["users"].update_one(
                        {"user_id": user_id},
                        {"$set": {"mining_block": True, "mining_block_reason": f"Security policy violation: {pattern_reason}", "mining_blocked_at": datetime.datetime.now(datetime.timezone.utc)}}
                    )
            except Exception as e:
                logger.error(f"Error applying pattern violation penalty to user {user_id}: {e}")
            
            # Create violation record
            violation_record = {
                "browser_fingerprint": browser_fingerprint,
                "device_fingerprint": device_fingerprint,
                "device_type": device_type,
                "ip_address": ip_address,
                "ip_analysis": ip_analysis,
                "user_agent": mining_block["user_agent"],
                "previous_user_id": None,
                "timestamp": datetime.datetime.now(datetime.timezone.utc),
                "reason": f"Suspicious connection pattern detected: {pattern_reason}",
                "violations": violations,
                "violation_points": violation_points,
                "risk_score": violation_risk_score,
                "penalty_type": penalty_type,
                "is_vpn_detected": is_vpn,
                "check_time_ms": int((time.time() - start_time) * 1000)
            }
            
            # Record violation in database
            try:
                mining_violations.update_one(
                    {"user_id": user_id},
                    {
                        "$set": {
                            "discord_id": mining_block.get("discord_id", user_id),
                            "last_violation": violation_record
                        },
                        "$push": {
                            "violations": violation_record
                        },
                        "$setOnInsert": {
                            "created_at": datetime.datetime.now(datetime.timezone.utc)
                        }
                    },
                    upsert=True
                )
            except Exception as e:
                logger.error(f"Error recording pattern violation for user {user_id}: {e}")
            
            return True, {
                "user_id": user_id,
                "discord_id": mining_block.get("discord_id", user_id),
                "reason": f"Suspicious connection pattern detected: {pattern_reason}",
                "violations": violations,
                "violation_points": violation_points,
                "risk_score": violation_risk_score,
                "penalty_type": penalty_type,
                "is_vpn_detected": is_vpn
            }
        
        # 6. التحقق من استخدام VPN للمستخدمين الجدد (ليس لهم سجل سابق)
        if is_vpn:
            logger.warning(f"User {user_id} is using VPN/proxy - applying VPN policy")
            
            # فحص إذا كان المستخدم له سجل سابق من نفس عنوان IP
            user_record = mining_blocks.find_one({"user_id": user_id})
            
            known_user_ips = []
            if user_record and "activities" in user_record:
                for activity in user_record["activities"]:
                    if "ip_address" in activity:
                        known_user_ips.append(activity["ip_address"])
            
            # إذا كان المستخدم لديه سجل سابق من نفس عنوان IP، نسمح له باستخدام VPN
            has_previous_record = ip_address in known_user_ips
            
            # تحقق إضافي: حتى لو لم يكن هناك سجل سابق لنفس IP، تحقق من عدد الأنشطة
            # إذا كان المستخدم يملك أكثر من 10 أنشطة، نعتبره مستخدم معروف
            is_established_user = False
            if user_record and "activities" in user_record:
                if len(user_record["activities"]) > 10:
                    is_established_user = True
                    logger.info(f"User {user_id} has {len(user_record['activities'])} activities, considering as established user")
            
            if has_previous_record or is_established_user:
                logger.info(f"User {user_id} allowed to use VPN because they have previous mining activity from this IP or are an established user")
                return False, None
                
            # أما إذا كان يستخدم VPN بدون سجل سابق، نمنعه
            violations = [{
                "type": "vpn_usage",
                "message": "VPN/proxy usage detected during mining (without previous records)",
                "severity": "high",
                "risk_score": 85
            }]
            
            violation_points = 8
            violation_risk_score = 85
            penalty_type = 'mining_block'
            
            # Apply mining block penalty
            try:
                if fraud_settings.get("penalty_enabled", True):
                    result = wallet_db["users"].update_one(
                        {"user_id": user_id},
                        {"$set": {"mining_block": True, "mining_block_reason": "Security policy violation: VPN usage not allowed for new accounts", "mining_blocked_at": datetime.datetime.now(datetime.timezone.utc)}}
                    )
                    if result.modified_count > 0:
                        logger.warning(f"User {user_id} has been blocked from mining (VPN/proxy usage)")
            except Exception as e:
                logger.error(f"Error applying VPN penalty to user {user_id}: {e}\n{traceback.format_exc()}")
            
            # Create violation record
            violation_record = {
                "browser_fingerprint": browser_fingerprint,
                "device_fingerprint": device_fingerprint,
                "device_type": device_type,
                "ip_address": ip_address,
                "ip_analysis": ip_analysis,
                "user_agent": mining_block["user_agent"],
                "previous_user_id": None,
                "timestamp": datetime.datetime.now(datetime.timezone.utc),
                "reason": "Mining through VPN/proxy without previous activity",
                "violations": violations,
                "violation_points": violation_points,
                "risk_score": violation_risk_score,
                "penalty_type": penalty_type,
                "is_vpn_detected": True,
                "check_time_ms": int((time.time() - start_time) * 1000)
            }
            
            # Record violation in database
            try:
                mining_violations.update_one(
                    {"user_id": user_id},
                    {
                        "$set": {
                            "discord_id": mining_block.get("discord_id", user_id),
                            "last_violation": violation_record
                        },
                        "$push": {
                            "violations": violation_record
                        },
                        "$setOnInsert": {
                            "created_at": datetime.datetime.now(datetime.timezone.utc)
                        }
                    },
                    upsert=True
                )
            except Exception as e:
                logger.error(f"Error recording VPN violation for user {user_id}: {e}\n{traceback.format_exc()}")
            
            return True, {
                "user_id": user_id,
                "discord_id": mining_block.get("discord_id", user_id),
                "reason": "Mining through VPN/proxy is not allowed for new users without previous activity",
                "violations": violations,
                "violation_points": violation_points,
                "risk_score": violation_risk_score,
                "penalty_type": penalty_type,
                "is_vpn_detected": True
            }
        
        # 7. التحقق من بصمة الجهاز بناءً على عنوان IP معًا
        device_owner = None
        if device_fingerprint and ip_address and ip_address not in ["127.0.0.1", "::1", "0.0.0.0"]:
            # البحث عن المستخدم الأول الذي استخدم هذا الجهاز مع نفس عنوان IP
            pipeline = [
                {"$match": {"activities.device_fingerprint": device_fingerprint, "activities.ip_address": ip_address}},
                {"$unwind": "$activities"},
                {"$match": {"activities.device_fingerprint": device_fingerprint, "activities.ip_address": ip_address}},
                {"$sort": {"activities.timestamp": 1}},
                {"$limit": 1},
                {"$project": {"user_id": 1, "_id": 0}}
            ]
            
            result = list(mining_blocks.aggregate(pipeline))
            if result:
                device_owner = result[0]["user_id"]
                # التأكد من أن المستخدم موجود
                if wallet_db["users"].find_one({"user_id": device_owner}):
                    if user_id != device_owner:
                        logger.warning(f"User {user_id} is trying to use device already registered to {device_owner} with same IP {ip_address}")
                        
                        # إذا كان هناك مستخدم آخر لهذا الجهاز وليس المستخدم الحالي، فهذا انتهاك
                        violations = [{
                            "type": "device_violation",
                            "message": "Multiple accounts detected from same physical device on same IP",
                            "existing_users": [device_owner],
                            "first_user": device_owner,
                            "severity": "critical",
                            "risk_score": 95  # زيادة من 90 إلى 95
                        }]
                        
                        violation_points = 9
                        violation_risk_score = 95  # زيادة من 90 إلى 95
                        penalty_type = 'mining_block'
                        
                        # Apply mining block penalty
                        try:
                            if fraud_settings.get("penalty_enabled", True):
                                result = wallet_db["users"].update_one(
                                    {"user_id": user_id},
                                    {"$set": {"mining_block": True, "mining_block_reason": "Security policy violation: Multiple accounts on same device from same IP", "mining_blocked_at": datetime.datetime.now(datetime.timezone.utc)}}
                                )
                        except Exception as e:
                            logger.error(f"Error applying device penalty to user {user_id}: {e}")
                        
                        # Create violation record
                        violation_record = {
                            "browser_fingerprint": browser_fingerprint,
                            "device_fingerprint": device_fingerprint,
                            "device_type": device_type,
                            "ip_address": ip_address,
                            "ip_analysis": ip_analysis,
                            "user_agent": mining_block["user_agent"],
                            "previous_user_id": device_owner,
                            "timestamp": datetime.datetime.now(datetime.timezone.utc),
                            "reason": "Multiple accounts detected from same device from same IP",
                            "violations": violations,
                            "violation_points": violation_points,
                            "risk_score": violation_risk_score,
                            "penalty_type": penalty_type,
                            "is_vpn_detected": False,
                            "check_time_ms": int((time.time() - start_time) * 1000)
                        }
                        
                        # Record violation in database
                        try:
                            mining_violations.update_one(
                                {"user_id": user_id},
                                {
                                    "$set": {
                                        "discord_id": mining_block.get("discord_id", user_id),
                                        "last_violation": violation_record
                                    },
                                    "$push": {
                                        "violations": violation_record
                                    },
                                    "$setOnInsert": {
                                        "created_at": datetime.datetime.now(datetime.timezone.utc)
                                    }
                                },
                                upsert=True
                            )
                        except Exception as e:
                            logger.error(f"Error recording device violation for user {user_id}: {e}")
                        
                        return True, {
                            "user_id": user_id,
                            "discord_id": mining_block.get("discord_id", user_id),
                            "reason": "This device is already registered to another account on the same IP address",
                            "violations": violations,
                            "violation_points": violation_points,
                            "risk_score": violation_risk_score,
                            "penalty_type": penalty_type,
                            "is_vpn_detected": False
                        }
        
        # 8. التحقق من بصمة الجهاز الأساسية (بدون معلومات الشبكة)
        if device_part and device_users:
            logger.warning(f"User {user_id} is using same device as users {device_users} but with different IP")
            
            # لا نحظر المستخدم ولكن نراقبه بشدة
            logger.info(f"Monitoring user {user_id} for potential multi-accounting with different IPs")
            
            # في حالة المراقبة فقط، لا نعتبرها انتهاكًا صريحًا في الوقت الحالي
            return False, None
        
        # إذا وصلنا إلى هنا، فإن المستخدم يستخدم عنوان IP مختلف عن المستخدمين السابقين أو لا يستخدم VPN
        logger.info(f"No violations detected for user {user_id}")
        return False, None
    
    except Exception as e:
        # Catch-all exception handler for any errors during the violation check
        logger.error(f"Critical error in mining security check for user {user_id}: {e}\n{traceback.format_exc()}")
        
        # Create a safe violation record for tracking the error
        error_record = {
            "user_id": user_id,
            "timestamp": datetime.datetime.now(datetime.timezone.utc),
            "error": str(e),
            "status": "system_error"
        }
        
        # Try to record the error in the database
        try:
            mining_violations.update_one(
                {"user_id": user_id},
                {
                    "$push": {
                        "system_errors": error_record
                    }
                },
                upsert=True
            )
        except Exception as db_error:
            logger.error(f"Failed to record security system error: {db_error}")
        
        # Return no violation by default to avoid false positives in case of system errors
        return False, None

def check_device_limits(user_id, device_fingerprint, security_settings):
    """Check if user has exceeded device limits (supports v2 and legacy)"""
    global mining_db
    fraud_settings = security_settings.get("fraud_protection_settings", {})

    if not fraud_settings.get("devices_per_account_enabled", True):
        return False, None

    max_devices = fraud_settings.get("devices_per_account", 5)

    user_devices_collection = mining_db["user_devices"]

    try:
        # If device already registered for this user, ok
        if user_devices_collection.find_one({"user_id": user_id, "device_hash": device_fingerprint}):
            return False, None

        device_count = user_devices_collection.count_documents({"user_id": user_id})

        if device_count >= max_devices:
            return True, {
                "type": "too_many_devices",
                "message": f"Too many devices registered (maximum {max_devices})",
                "severity": "medium",
                "current_count": device_count,
                "max_allowed": max_devices
            }

        # Register new device
        user_devices_collection.insert_one({
            "user_id": user_id,
            "device_hash": device_fingerprint,
            "first_seen": datetime.datetime.now(datetime.timezone.utc)
        })

        return False, None
    except Exception as e:
        logger.error(f"Error checking device limits: {e}")
        return False, None

def check_network_limits(user_id, ip_address, security_settings):
    """Check if user has exceeded network limits (supports v2 and legacy)"""
    global mining_db
    fraud_settings = security_settings.get("fraud_protection_settings", {})

    if not fraud_settings.get("networks_per_account_enabled", True):
        return False, None

    max_networks = fraud_settings.get("networks_per_account", 20)

    # New individual collection
    user_networks_collection = mining_db["user_networks"]

    try:
        # Check if this IP is already registered for the user
        existing = user_networks_collection.find_one({"user_id": user_id, "ip_address": ip_address})
        if existing:
            return False, None

        # Count networks for user
        network_count = user_networks_collection.count_documents({"user_id": user_id})

        if network_count >= max_networks:
            return True, {
                "type": "too_many_networks",
                "message": f"Too many networks used (maximum {max_networks})",
                "severity": "low",
                "current_count": network_count,
                "max_allowed": max_networks
            }

        # Insert new record
        user_networks_collection.insert_one({
            "user_id": user_id,
            "ip_address": ip_address,
            "first_seen": datetime.datetime.now(datetime.timezone.utc)
        })

        return False, None
    except Exception as e:
        logger.error(f"Error checking network limits: {e}")
        # Fallback to legacy behaviour if any error
        return False, None

def is_blocked_from_mining(user_id):
    """Check if a user is blocked from mining due to security violations"""
    try:
        # Check if user exists in wallet database
        user = wallet_db["users"].find_one({"user_id": user_id})
        
        if not user:
            # User doesn't exist yet, not blocked
            return False
        
        # Check if user is banned or blocked from mining
        return user.get("ban", False) or user.get("mining_block", False)
    except Exception as e:
        logger.error(f"Error checking if user is blocked from mining: {e}\n{traceback.format_exc()}")
        # Default to not blocked in case of error - conservative approach
        return False

def check_security_before_mining(user_id):
    """
    Check if a user can mine based on security rules
    Returns (allowed, response) tuple
    """
    try:
        # Check if user is blocked from mining
        if is_blocked_from_mining(user_id):
            logger.warning(f"User {user_id} attempted to mine but is blocked")
            return False, {
                "status": "security_violation",
                "message": "You have been blocked from mining due to security violations"
            }
        
        # Record mining activity and check for violations
        mining_block = record_mining_activity(user_id)
        
        # Add logging to help troubleshoot
        logger.info(f"Mining activity recorded for user {user_id}, device_fp: {mining_block['device_fingerprint'][:8]}...")
        
        # Check for device ownership violations
        is_violation, violation_details = check_mining_violations(user_id, mining_block)
        
        if is_violation:
            # Get the original owner for clearer messaging
            original_owner = violation_details.get("previous_user_id", "another user")
            # تعديل: تمرير عنوان IP أيضًا للتحقق
            first_device_user = get_first_miner_by_device_fingerprint(
                mining_block.get("device_fingerprint"),
                mining_block.get("ip_address")
            )
            
            logger.warning(f"Security violation detected for user {user_id}, device belongs to {original_owner}")
            
            message = "This device is already registered to another account with the same IP address. Only the first account that mines from a device with a specific IP is allowed to continue using it."
            if first_device_user and first_device_user != user_id:
                message = f"This device is already registered to user {first_device_user} with the same IP address. Only the first account that mines from a device with a specific IP is allowed to continue using it."
            
            return False, {
                "status": "security_violation",
                "message": message,
                "details": violation_details
            }
        
        # User passed all security checks
        return True, {"status": "ok"}
    except Exception as e:
        logger.error(f"Security check error for user {user_id}: {e}\n{traceback.format_exc()}")
        # In case of system error, allow mining to prevent false positives
        # This is logged so admins can investigate, but we don't want to block legitimate users
        return True, {"status": "error", "message": "System error occurred"}

# API endpoint to check security status
@mining_security_bp.route('/status', methods=['GET'])
def get_security_status():
    """Get security status for current user"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({"error": "Not authenticated"}), 401
        
        # Check if user is blocked
        blocked = is_blocked_from_mining(user_id)
        
        # Get latest violation if any
        violation = mining_violations.find_one({"user_id": user_id})
        latest_violation = violation.get("last_violation") if violation else None
        
        return jsonify({
            "user_id": user_id,
            "is_blocked": blocked,
            "latest_violation": latest_violation
        })
    except Exception as e:
        logger.error(f"Error getting security status: {e}\n{traceback.format_exc()}")
        return jsonify({"error": "System error", "details": str(e)}), 500
        
# API endpoint to clean non-existent users
@mining_security_bp.route('/admin/clean-database', methods=['POST'])
def clean_database():
    """Clean database of non-existent users (admin only)"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({"error": "Not authenticated"}), 401
            
        # التحقق من أن المستخدم هو مدير
        is_admin = wallet_db["users"].find_one({"user_id": user_id, "is_admin": True})
        if not is_admin:
            logger.warning(f"Non-admin user {user_id} attempted to access admin endpoint")
            return jsonify({"error": "Not authorized"}), 403
            
        # تنظيف قاعدة البيانات
        result = clean_nonexistent_users()
        
        if result:
            return jsonify({
                "status": "success",
                "message": "Database cleaned successfully"
            })
        else:
            return jsonify({
                "status": "error",
                "message": "Failed to clean database"
            }), 500
    except Exception as e:
        logger.error(f"Error cleaning database: {e}\n{traceback.format_exc()}")
        return jsonify({"error": "System error", "details": str(e)}), 500

# Debugging route for IP detection
@mining_security_bp.route('/ip-test', methods=['GET'])
def test_ip_detection():
    """Test route to check IP detection accuracy"""
    try:
        # Get IP using our enhanced detection
        detected_ip = get_real_ip()
        
        # Get raw header information for debugging
        headers_dict = {k: v for k, v in request.headers.items()}
        
        # Try to get actual external IP for comparison
        external_ip = None
        try:
            response = requests.get('https://api.ipify.org', timeout=2)
            if response.status_code == 200:
                external_ip = response.text.strip()
        except Exception as e:
            logger.debug(f"Failed to get external IP for comparison: {e}")
        
        # Get IP info analysis
        ip_analysis = None
        try:
            ip_analysis = IPAnalyzer.analyze_ip(detected_ip)
        except Exception as e:
            logger.error(f"Error analyzing IP: {e}")
        
        # Check if this is coming through localhost
        is_local = detected_ip in ['127.0.0.1', '::1', 'localhost'] or detected_ip.startswith('192.168.') or detected_ip.startswith('10.')
        
        # Form comprehensive response
        response_data = {
            "detected_ip": detected_ip,
            "external_ip": external_ip,
            "is_local_network": is_local,
            "request_remote_addr": request.remote_addr,
            "relevant_headers": {
                header: headers_dict.get(header) for header in [
                    'X-Forwarded-For', 'CF-Connecting-IP', 'True-Client-IP', 
                    'X-Real-IP', 'X-Client-IP', 'Forwarded', 'X-Forwarded',
                    'X-Cluster-Client-IP', 'Fastly-Client-IP', 'X-Forwarded-Host'
                ] if header in headers_dict
            },
            "ip_analysis": ip_analysis
        }
        
        return jsonify(response_data)
    except Exception as e:
        logger.error(f"Error in IP test endpoint: {e}\n{traceback.format_exc()}")
        return jsonify({"error": "System error", "details": str(e)}), 500

# Define violation points for risk calculation
VIOLATION_POINTS = {
    "device_violation": 50,
    "browser_violation": 40,
    "ip_violation": 30,
    "same_ip_browser_violation": 60,
    "suspicious_device": 45,
    "repeat_violation": 70
}

def calculate_risk_score(violations):
    """Calculate a risk score from 0-100 based on violations found"""
    if not violations:
        return 0
            
    # Base points from violation types
    points = sum(VIOLATION_POINTS.get(v, 10) for v in violations)
    
    # Calculate final score (0-100 scale)
    risk_score = min(100, points)  # Cap at 100
    
    return risk_score

# Function to select the best available token based on usage statistics and rate limits
def select_best_token(ip_address=None, for_privacy=False):
    """
    Select the best available token based on usage statistics and rate limits.
    
    Args:
        ip_address: If provided, it will be used to distribute tokens based on IP hash.
        for_privacy: If True, prioritize tokens known to have privacy module access.
        
    Returns:
        The best token to use, or None if no tokens are available.
    """
    current_time = datetime.datetime.now(datetime.timezone.utc)
    
    # First, reset any stale token rate limit information
    reset_stale_tokens()
    
    # Get available tokens (not rate limited)
    available_tokens = [token for token in IPINFO_API_TOKENS 
                       if token not in rate_limited_tokens or 
                       rate_limited_tokens[token] < current_time]
    
    # If no tokens are available, use the one that will become available soonest
    if not available_tokens and rate_limited_tokens:
        # Get the token with the earliest expiry time
        next_available_token = min(rate_limited_tokens.items(), key=lambda x: x[1])[0]
        logger.warning(f"No available tokens, using the next available token {next_available_token[:4]}...{next_available_token[-4:]}")
        return next_available_token
    
    # If no tokens at all, return None
    if not available_tokens:
        logger.error("No IPinfo tokens available")
        return None
    
    # If prioritizing tokens with privacy module access
    if for_privacy:
        # Check token usage statistics to find tokens with successful privacy module access
        privacy_capable_tokens = []
        for token in available_tokens:
            stats = token_usage_stats.get(token, {})
            # Consider a token privacy-capable if it has more successful requests than errors
            if stats.get("successful_requests", 0) > stats.get("errors", 0):
                privacy_capable_tokens.append(token)
        
        # If we have tokens known to work with privacy module, use those
        if privacy_capable_tokens:
            available_tokens = privacy_capable_tokens
            logger.debug(f"Found {len(privacy_capable_tokens)} tokens with likely privacy module access")
    
    # If ip_address is provided, use it for consistent token selection
    if ip_address:
        # Use IP hash for consistent token selection to maintain cache efficiency
        token_index = hash(ip_address) % len(available_tokens)
        selected_token = available_tokens[token_index]
        logger.debug(f"Selected token {selected_token[:4]}...{selected_token[-4:]} for IP {ip_address} based on hash")
        return selected_token
    
    # Otherwise, use weighted selection based on success rate and usage
    token_scores = []
    for token in available_tokens:
        stats = token_usage_stats.get(token, {})
        requests = stats.get("requests", 0)
        successful_requests = stats.get("successful_requests", 0)
        errors = stats.get("errors", 0)
        rate_limits = stats.get("rate_limits", 0)
        
        # Calculate a score - higher is better
        # Prioritize tokens with fewer requests (load balancing)
        request_score = 1000 / (requests + 1)  # Add 1 to avoid division by zero
        
        # Prioritize tokens with higher success rates
        success_rate = successful_requests / (requests + 1)  # Add 1 to avoid division by zero
        success_score = success_rate * 500
        
        # Penalize tokens with many errors or rate limits
        error_penalty = (errors + rate_limits) * 10
        
        # Final score
        final_score = request_score + success_score - error_penalty
        
        token_scores.append((token, final_score))
    
    # Sort by score (highest first) and select the best token
    token_scores.sort(key=lambda x: x[1], reverse=True)
    selected_token = token_scores[0][0]
    
    logger.debug(f"Selected best token {selected_token[:4]}...{selected_token[-4:]} with score {token_scores[0][1]:.2f}")
    return selected_token

# Add an admin route to force refresh token status
@mining_security_bp.route('/ipinfo-tokens/refresh', methods=['POST'])
def refresh_token_status():
    """Admin route to force refresh token status"""
    try:
        # Check if user is authenticated as admin
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({"error": "Not authenticated"}), 401
            
        # Get user info to check admin status
        user = wallet_db["users"].find_one({"user_id": user_id})
        if not user or not user.get("is_admin", False):
            return jsonify({"error": "Unauthorized access"}), 403
        
        # Get request data
        data = request.get_json() or {}
        
        # Check if specific token should be refreshed
        token_number = data.get('token_number')
        all_tokens = data.get('all_tokens', False)
        
        if token_number is not None:
            # Validate token number
            if token_number < 1 or token_number > len(IPINFO_API_TOKENS):
                return jsonify({"error": f"Invalid token number. Valid range: 1-{len(IPINFO_API_TOKENS)}"}), 400
            
            # Get the token
            token = IPINFO_API_TOKENS[token_number - 1]
            
            # Remove from rate limited tokens if it exists
            if token in rate_limited_tokens:
                del rate_limited_tokens[token]
                logger.info(f"Admin {user_id} manually refreshed token {token_number}")
                
                return jsonify({
                    "success": True,
                    "message": f"Token {token_number} refreshed successfully",
                    "token": f"{token[:4]}...{token[-4:]}" if len(token) > 8 else "****"
                })
            else:
                return jsonify({
                    "success": False,
                    "message": f"Token {token_number} is not rate limited"
                })
        
        elif all_tokens:
            # Clear all rate limited tokens
            count = len(rate_limited_tokens)
            rate_limited_tokens.clear()
            logger.info(f"Admin {user_id} manually refreshed all tokens ({count} tokens)")
            
            return jsonify({
                "success": True,
                "message": f"All {count} rate-limited tokens refreshed successfully"
            })
        
        else:
            # Just return current status if no action specified
            return jsonify({
                "success": False,
                "message": "No action specified. Use token_number or all_tokens=true"
            }), 400
            
    except Exception as e:
        logger.error(f"Error in refresh-token endpoint: {e}\n{traceback.format_exc()}")
        return jsonify({"error": "System error", "details": str(e)}), 500

# Add an admin route to reset token usage statistics
@mining_security_bp.route('/ipinfo-tokens/reset-stats', methods=['POST'])
def reset_token_stats():
    """Admin route to reset token usage statistics"""
    try:
        # Check if user is authenticated as admin
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({"error": "Not authenticated"}), 401
            
        # Get user info to check admin status
        user = wallet_db["users"].find_one({"user_id": user_id})
        if not user or not user.get("is_admin", False):
            return jsonify({"error": "Unauthorized access"}), 403
        
        # Get request data
        data = request.get_json() or {}
        
        # Check if specific token should be reset
        token_number = data.get('token_number')
        all_tokens = data.get('all_tokens', False)
        
        if token_number is not None:
            # Validate token number
            if token_number < 1 or token_number > len(IPINFO_API_TOKENS):
                return jsonify({"error": f"Invalid token number. Valid range: 1-{len(IPINFO_API_TOKENS)}"}), 400
            
            # Get the token
            token = IPINFO_API_TOKENS[token_number - 1]
            
            # Reset usage statistics for this token
            token_usage_stats[token] = {
                "requests": 0,
                "successful_requests": 0,
                "rate_limits": 0,
                "last_used": None,
                "errors": 0
            }
            
            logger.info(f"Admin {user_id} reset usage statistics for token {token_number}")
            
            return jsonify({
                "success": True,
                "message": f"Usage statistics for token {token_number} reset successfully",
                "token": f"{token[:4]}...{token[-4:]}" if len(token) > 8 else "****"
            })
        
        elif all_tokens:
            # Reset all token usage statistics
            for token in IPINFO_API_TOKENS:
                token_usage_stats[token] = {
                    "requests": 0,
                    "successful_requests": 0,
                    "rate_limits": 0,
                    "last_used": None,
                    "errors": 0
                }
            
            logger.info(f"Admin {user_id} reset usage statistics for all tokens")
            
            return jsonify({
                "success": True,
                "message": f"Usage statistics for all {len(IPINFO_API_TOKENS)} tokens reset successfully"
            })
        
        else:
            # Just return current status if no action specified
            return jsonify({
                "success": False,
                "message": "No action specified. Use token_number or all_tokens=true"
            }), 400
            
    except Exception as e:
        logger.error(f"Error in reset-token-stats endpoint: {e}\n{traceback.format_exc()}")
        return jsonify({"error": "System error", "details": str(e)}), 500

def clean_nonexistent_users():
    """
    تنظيف قاعدة البيانات من الحسابات غير الموجودة
    هذه الوظيفة تقوم بإزالة سجلات الأنشطة التي تشير إلى حسابات غير موجودة في قاعدة البيانات
    """
    try:
        global mining_blocks, wallet_db
        
        # الحصول على قائمة بجميع المستخدمين في سجلات الأنشطة
        all_mining_users = mining_blocks.distinct("user_id")
        
        # التحقق من وجود كل مستخدم في قاعدة بيانات الحسابات
        for user_id in all_mining_users:
            user_exists = wallet_db["users"].find_one({"user_id": user_id})
            
            # إذا كان المستخدم غير موجود، نقوم بحذف سجلاته
            if not user_exists:
                logger.warning(f"Cleaning non-existent user {user_id} from mining records")
                
                # حذف سجلات الأنشطة
                mining_blocks.delete_one({"user_id": user_id})
                
                # حذف سجلات الانتهاكات
                mining_violations.delete_one({"user_id": user_id})
                
                # حذف سجلات الأجهزة
                mining_db.user_devices.delete_one({"user_id": user_id})
        
        logger.info("Completed cleaning of non-existent users from mining records")
        return True
    except Exception as e:
        logger.error(f"Error cleaning non-existent users: {e}\n{traceback.format_exc()}")
        return False

# سنقوم بتشغيل وظيفة التنظيف عند تهيئة النظام
def init_security_module():
    """
    تهيئة وحدة الأمان وتنظيف البيانات
    """
    try:
        # تنظيف المستخدمين غير الموجودين
        clean_nonexistent_users()
        logger.info("Security module initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize security module: {e}")
        
# تشغيل التهيئة
init_security_module()

# إضافة دالة لتنظيف بصمات الأجهزة القديمة من الذاكرة المؤقتة
def clear_device_fingerprints_cache():
    """
    تنظيف ذاكرة التخزين المؤقت للبصمات
    يجب استدعاء هذه الدالة عند تغيير طريقة توليد البصمات لضمان إعادة توليد البصمات
    """
    try:
        global fingerprint_cache
        fingerprint_cache = {}
        logger.info("Device fingerprints cache cleared successfully")
        return True
    except Exception as e:
        logger.error(f"Error clearing device fingerprints cache: {e}")
        return False

# استدعاء دالة تنظيف الذاكرة المؤقتة عند بدء تشغيل الخادم
clear_device_fingerprints_cache()

@mining_security_bp.route('/clear-cache', methods=['POST'])
def clear_fingerprints_cache():
    """
    واجهة برمجية لتنظيف ذاكرة التخزين المؤقت للبصمات
    يمكن استدعاؤها من لوحة التحكم لإعادة توليد البصمات بعد تحديث النظام
    """
    try:
        # التحقق من أن المستخدم مسؤول
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({"error": "Not authenticated"}), 401
            
        # التحقق من صلاحيات المستخدم
        user = wallet_db["users"].find_one({"user_id": user_id})
        if not user or not user.get("is_admin", False):
            return jsonify({"error": "Unauthorized access"}), 403
        
        # تنظيف ذاكرة التخزين المؤقت
        clear_device_fingerprints_cache()
        
        return jsonify({
            "success": True,
            "message": "Device fingerprints cache cleared successfully"
        })
    except Exception as e:
        logger.error(f"Error clearing fingerprints cache: {e}")
        return jsonify({"error": "System error", "details": str(e)}), 500

def init_security_module():
    """Initialize mining security module"""
    try:
        # Ensure we have a clean cache
        clear_device_fingerprints_cache()
        
        # Create device fingerprints version record
        fingerprint_version = {
            "type": "fingerprint_version",
            "version": 6,  # رفع رقم الإصدار بعد تحديث خوارزمية البصمة وقوائم VPN
            "updated_at": datetime.datetime.now(datetime.timezone.utc),
            "algorithm": "enhanced_device_network_fingerprint_with_vpn_detection"
        }
        
        # Update or create the fingerprint version record
        try:
            wallet_db["settings"].update_one(
                {"type": "fingerprint_version"},
                {"$set": fingerprint_version},
                upsert=True
            )
            logger.info("Fingerprint version updated to v6 (enhanced detection with expanded VPN database)")
            
            # تنظيف ذاكرة التخزين المؤقت للبصمات والتحليلات
            try:
                # تفريغ ذاكرة التخزين المؤقت لعناوين IP
                global ip_cache, fingerprint_cache, first_miner_cache, ipinfo_cache
                ip_cache = {}
                fingerprint_cache = {}
                first_miner_cache = {}
                ipinfo_cache = {}
                logger.info("All caches cleared successfully to apply security updates")
                
                # إعادة تهيئة المستخدمين المحظورين خطأ
                reset_blocked_users()
            except Exception as reset_error:
                logger.error(f"Error resetting caches: {reset_error}")
                
        except Exception as e:
            logger.error(f"Error updating fingerprint version: {e}")
            
    except Exception as e:
        logger.error(f"Error initializing security module: {e}")

# دالة جديدة لإعادة تهيئة المستخدمين المحظورين عند التحديث
def reset_blocked_users():
    """
    إعادة تهيئة المستخدمين المحظورين خطأ بسبب تحديث النظام
    يتم استخدام هذه الدالة عند تحديث خوارزمية الكشف عن VPN
    """
    try:
        # البحث عن المستخدمين المحظورين بسبب VPN
        blocked_users = wallet_db["users"].find({
            "mining_block": True,
            "mining_block_reason": {"$regex": "VPN|vpn"}
        })
        
        # عدد المستخدمين الذين تم فك الحظر عنهم
        unblocked_count = 0
        
        # فك الحظر عن المستخدمين المحظورين بسبب VPN خلال الأسبوع الماضي
        one_week_ago = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=7)
        
        for user in blocked_users:
            user_id = user["user_id"]
            block_time = user.get("mining_blocked_at", datetime.datetime.min.replace(tzinfo=datetime.timezone.utc))
            
            # فك الحظر فقط عن المستخدمين الذين تم حظرهم خلال الأسبوع الماضي
            if block_time > one_week_ago:
                try:
                    # إعادة تعيين بصمة الجهاز
                    reset_device_fingerprint(user_id)
                    unblocked_count += 1
                    logger.info(f"Unblocked user {user_id} after security update")
                except Exception as reset_error:
                    logger.error(f"Error resetting user {user_id} after update: {reset_error}")
        
        logger.info(f"Successfully unblocked {unblocked_count} users after security update")
        return unblocked_count
    except Exception as e:
        logger.error(f"Error resetting blocked users: {e}")
        return 0

# تشغيل التهيئة على الفور لتطبيق التغييرات
clear_device_fingerprints_cache()
init_security_module()

# إضافة دالة لإعادة تعيين بصمة جهاز لمستخدم محدد
def reset_device_fingerprint(user_id):
    """
    إعادة تعيين بصمة جهاز لمستخدم محدد
    يتم استخدام هذه الدالة عندما يتم حظر المستخدم بالخطأ بسبب اشتراك بصمة الجهاز
    """
    try:
        # التحقق من وجود المستخدم
        user = wallet_db["users"].find_one({"user_id": user_id})
        if not user:
            logger.warning(f"User {user_id} not found when trying to reset device fingerprint")
            return False, "User not found"
        
        # البحث عن سجل المستخدم في قاعدة بيانات التعدين
        mining_record = mining_blocks.find_one({"user_id": user_id})
        if not mining_record:
            logger.warning(f"No mining record found for user {user_id}")
            return False, "No mining record found"
        
        # توليد بصمة جهاز جديدة فريدة
        import uuid
        import hashlib
        import datetime
        
        # إنشاء بصمة فريدة باستخدام معرف المستخدم والوقت الحالي
        unique_string = f"{user_id}_{uuid.uuid4()}_{datetime.datetime.now().timestamp()}"
        new_fingerprint = hashlib.sha256(unique_string.encode('utf-8')).hexdigest()[:32]
        
        # تحديث بصمة الجهاز في جميع الأنشطة
        activities = mining_record.get("activities", [])
        for activity in activities:
            activity["device_fingerprint"] = new_fingerprint
        
        # تحديث آخر نشاط أيضًا
        last_activity = mining_record.get("last_activity", {})
        if last_activity:
            last_activity["device_fingerprint"] = new_fingerprint
        
        # حفظ التغييرات
        mining_blocks.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "activities": activities,
                    "last_activity": last_activity,
                    "last_updated": datetime.datetime.now(datetime.timezone.utc)
                }
            }
        )
        
        # إزالة حظر التعدين إذا كان موجودًا
        wallet_db["users"].update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "mining_block": False,
                    "mining_block_reason": None,
                    "mining_unblocked_at": datetime.datetime.now(datetime.timezone.utc)
                }
            }
        )
        
        logger.info(f"Successfully reset device fingerprint for user {user_id}")
        return True, "Device fingerprint reset successfully"
    except Exception as e:
        logger.error(f"Error resetting device fingerprint for user {user_id}: {e}\n{traceback.format_exc()}")
        return False, f"Error: {str(e)}"

# إضافة نقطة نهاية API لإعادة تعيين بصمة الجهاز
@mining_security_bp.route('/reset-device-fingerprint', methods=['POST'])
def api_reset_device_fingerprint():
    """واجهة برمجية لإعادة تعيين بصمة جهاز لمستخدم محدد"""
    try:
        # التحقق من أن المستخدم مسؤول
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({"error": "Not authenticated"}), 401
            
        # التحقق من صلاحيات المستخدم
        user = wallet_db["users"].find_one({"user_id": user_id})
        if not user or not user.get("is_admin", False):
            return jsonify({"error": "Unauthorized access"}), 403
        
        # الحصول على معرف المستخدم المراد إعادة تعيين بصمة جهازه
        data = request.get_json()
        if not data or not data.get("target_user_id"):
            return jsonify({"error": "Missing target_user_id parameter"}), 400
            
        target_user_id = data.get("target_user_id")
        
        # إعادة تعيين بصمة الجهاز
        success, message = reset_device_fingerprint(target_user_id)
        
        if success:
            return jsonify({
                "success": True,
                "message": message
            })
        else:
            return jsonify({
                "success": False,
                "message": message
            }), 400
    except Exception as e:
        logger.error(f"Error in reset-device-fingerprint API: {e}\n{traceback.format_exc()}")
        return jsonify({"error": "System error", "details": str(e)}), 500

# إضافة نقطة نهاية API للمستخدم لإعادة تعيين بصمة جهازه الخاص
@mining_security_bp.route('/reset-my-device', methods=['POST'])
def api_reset_my_device():
    """واجهة برمجية للمستخدم لإعادة تعيين بصمة جهازه الخاص"""
    try:
        # التحقق من المصادقة
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({"error": "Not authenticated"}), 401
        
        # إعادة تعيين بصمة الجهاز
        success, message = reset_device_fingerprint(user_id)
        
        if success:
            return jsonify({
                "success": True,
                "message": "تم إعادة تعيين بصمة جهازك بنجاح"
            })
        else:
            return jsonify({
                "success": False,
                "message": message
            }), 400
    except Exception as e:
        logger.error(f"Error in reset-my-device API: {e}\n{traceback.format_exc()}")
        return jsonify({"error": "System error", "details": str(e)}), 500