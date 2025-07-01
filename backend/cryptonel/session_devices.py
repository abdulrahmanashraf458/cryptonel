import os
import time
import datetime
import uuid
import requests
import random
from flask import Blueprint, jsonify, request, session
from pymongo import MongoClient
from dotenv import load_dotenv
from datetime import timedelta

# Import cache utilities
from backend.utils import cache_utils

# Load environment variables
load_dotenv()

# Create Blueprint for Session Devices endpoints
session_devices_bp = Blueprint('session_devices', __name__)

# MongoDB connection
MONGODB_URI = os.getenv("DATABASE_URL")
client = MongoClient(MONGODB_URI)
db = client["cryptonel_wallet"]
users_collection = db["users"]
device_sessions_collection = db["device_sessions"]

# Configure TTL index to automatically remove inactive sessions after 30 days
try:
    # Create TTL index based on last_active field
    device_sessions_collection.create_index(
        [("devices.last_active", 1)],
        expireAfterSeconds=30 * 24 * 60 * 60,  # 30 days in seconds
        background=True
    )
    
    # Create compound index for faster queries
    device_sessions_collection.create_index(
        [("user_id", 1), ("devices.session_id", 1)],
        background=True
    )
except Exception as e:
    print(f"Error setting up MongoDB indexes: {e}")

# Redis cache keys and configurations
DEVICE_CACHE_PREFIX = "device_session:"
DEVICE_LIST_CACHE_PREFIX = "device_list:"
DEVICE_CACHE_TTL = 60 * 15  # 15 minutes
ACTIVITY_UPDATE_INTERVAL = 15 * 60  # 15 minutes in seconds

# Helper function to get user device sessions
def get_user_devices(user_id):
    """Get all device sessions for a user"""
    # Try to get from cache first
    cache_key = f"{DEVICE_LIST_CACHE_PREFIX}{user_id}"
    cached_devices = cache_utils.cache_get(cache_key)
    
    if cached_devices:
        return cached_devices
        
    # If not in cache, get from database
    device_sessions = device_sessions_collection.find_one({"user_id": user_id})
    if not device_sessions:
        # Create initial empty device sessions document
        device_sessions = {
            "user_id": user_id,
            "devices": []
        }
        device_sessions_collection.insert_one(device_sessions)
    
    # Store in cache
    cache_utils.cache_set(cache_key, device_sessions, DEVICE_CACHE_TTL)
    
    return device_sessions

# Function to detect device details
def detect_device_details(user_agent_string, ip_address=None):
    """Detect device information and location from user agent and IP"""
    # Default values
    device_info = {
        "browser": "Unknown Browser",
        "os": "Unknown OS",
        "ip_address": ip_address or request.remote_addr,
        "country": "Unknown",
        "city": "Unknown",
        "last_active": datetime.datetime.utcnow().isoformat() + "Z"
    }
    
    # Check if we already have a real IP from headers
    if request.headers.get('X-Forwarded-For'):
        device_info["ip_address"] = request.headers.get('X-Forwarded-For').split(',')[0].strip()
        
    # If the IP is localhost or internal, try to get real external IP
    if device_info["ip_address"] in ['127.0.0.1', 'localhost'] or device_info["ip_address"].startswith('192.168.') or device_info["ip_address"].startswith('10.'):
        try:
            # Try external IP detection services
            ip_services = [
                'https://api.ipify.org?format=json',
                'https://api64.ipify.org?format=json',
                'https://ifconfig.me/ip'
            ]
            for service in ip_services:
                try:
                    response = requests.get(service, timeout=3)
                    if response.status_code == 200:
                        if service.endswith('json'):
                            device_info["ip_address"] = response.json().get('ip')
                        else:
                            device_info["ip_address"] = response.text.strip()
                        break
                except:
                    continue
        except Exception as e:
            print(f"Error detecting external IP: {e}")
    
    # Try to detect device type and OS
    if "iPhone" in user_agent_string:
        device_info["device_type"] = "iPhone"
        device_info["os"] = "iOS"
    elif "iPad" in user_agent_string:
        device_info["device_type"] = "iPad"
        device_info["os"] = "iOS"
    elif "Android" in user_agent_string:
        if "Mobile" in user_agent_string:
            device_info["device_type"] = "Android Phone"
        else:
            device_info["device_type"] = "Android Tablet"
        device_info["os"] = "Android"
    elif "Windows" in user_agent_string:
        device_info["device_type"] = "Windows PC"
        device_info["os"] = "Windows"
    elif "Macintosh" in user_agent_string:
        device_info["device_type"] = "Mac"
        device_info["os"] = "macOS"
    elif "Linux" in user_agent_string:
        device_info["device_type"] = "Linux PC"
        device_info["os"] = "Linux"
        
    # Detect browser
    if "Chrome" in user_agent_string and "Edg" in user_agent_string:
        device_info["browser"] = "Edge"
    elif "Chrome" in user_agent_string and "OPR" in user_agent_string:
        device_info["browser"] = "Opera"
    elif "Chrome" in user_agent_string and "Safari" in user_agent_string and "Brave" not in user_agent_string:
        device_info["browser"] = "Chrome"
    elif "Firefox" in user_agent_string:
        device_info["browser"] = "Firefox"
    elif "Safari" in user_agent_string and "Chrome" not in user_agent_string:
        device_info["browser"] = "Safari"
    elif "Brave" in user_agent_string:
        device_info["browser"] = "Brave"
    
    # Get geolocation data from IP
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
            response = requests.get(f'https://ipinfo.io/{device_info["ip_address"]}/json?token={token}', timeout=3)
            if response.status_code == 200:
                ip_data = response.json()
                device_info["country"] = ip_data.get('country', '')
                device_info["region"] = ip_data.get('region', '')
                device_info["city"] = ip_data.get('city', '')
                
                # Format location for display
                if ip_data.get('city') and ip_data.get('country'):
                    device_info["location"] = f"{ip_data.get('city')}, {ip_data.get('country')}"
                elif ip_data.get('country'):
                    device_info["location"] = ip_data.get('country')
                    
                # Store timezone
                device_info["timezone"] = ip_data.get('timezone', '')
    except Exception as e:
        print(f"Error getting location info: {e}")
    
    # Generate a device fingerprint to identify unique devices
    # This combines device type, OS, browser and IP for uniqueness
    device_fingerprint = f"{device_info.get('device_type','Unknown')}|{device_info.get('os','Unknown')}|{device_info.get('browser','Unknown')}|{device_info.get('ip_address','Unknown')}"
    
    # Create a deterministic device ID based on the fingerprint
    import hashlib
    device_hash = hashlib.md5(device_fingerprint.encode()).hexdigest()
    device_info["device_id"] = f"dev_{device_hash}"
    
    return device_info

# Function to check if we should update last activity time
def should_update_activity(session_id, user_id):
    """Check if we should update the last activity time based on the configured interval"""
    # Cache key for last update time
    last_update_key = f"last_activity_update:{user_id}:{session_id}"
    
    # Check when this session was last updated
    last_update_time = cache_utils.cache_get(last_update_key)
    current_time = time.time()
    
    # If no record of last update or update interval has passed, allow update
    if last_update_time is None or (current_time - last_update_time) > ACTIVITY_UPDATE_INTERVAL:
        # Store current time as last update
        cache_utils.cache_set(last_update_key, current_time, ACTIVITY_UPDATE_INTERVAL * 2)
        return True
    
    return False

# Function to register current device
def register_current_device(user_id):
    """Register the current device for a user"""
    # Get current user agent
    user_agent = request.headers.get("User-Agent", "Unknown")
    
    # Get device info
    device_info = detect_device_details(user_agent)
    
    # Generate or retrieve session_id
    session_id = session.get('session_id')
    if not session_id:
        session_id = str(uuid.uuid4())
        session['session_id'] = session_id
    
    # Add session_id to the device info
    device_info["session_id"] = session_id
    
    # Store the device_id in the session for future reference
    session['device_id'] = device_info["device_id"]
    
    # First check if device exists in cache
    device_cache_key = f"{DEVICE_CACHE_PREFIX}{user_id}:{device_info['device_id']}"
    cached_device = cache_utils.cache_get(device_cache_key)
    
    # Get user's device sessions
    user_devices = get_user_devices(user_id)
    
    # Find if we already have this device based on device_id
    existing_device = None
    
    # We'll check both the session_id and device_id to ensure proper detection
    for device in user_devices.get("devices", []):
        if device.get("device_id") == device_info["device_id"]:
            existing_device = device
            # Update the session_id if it has changed
            if device.get("session_id") != session_id:
                device_info["session_id"] = session_id
            break
    
    # If device exists, only update it if enough time has passed
    if existing_device:
        # Update cache first
        cache_utils.cache_set(device_cache_key, device_info, DEVICE_CACHE_TTL)
        
        # Only update database if update interval has passed
        if should_update_activity(device_info["device_id"], user_id):
            # Update last active timestamp and any changed details
            device_sessions_collection.update_one(
                {"user_id": user_id, "devices.device_id": device_info["device_id"]},
                {"$set": {
                    "devices.$.last_active": device_info["last_active"],
                    "devices.$.ip_address": device_info["ip_address"],
                    "devices.$.country": device_info["country"],
                    "devices.$.city": device_info["city"],
                    "devices.$.location": device_info.get("location", ""),
                    "devices.$.session_id": device_info["session_id"]  # Update session ID if changed
                }}
            )
            
            # Invalidate the device list cache to reflect changes
            list_cache_key = f"{DEVICE_LIST_CACHE_PREFIX}{user_id}"
            cache_utils.cache_delete(list_cache_key)
    else:
        # Check if we have any device with the same fingerprint but different session
        similar_devices_exist = False
        for device in user_devices.get("devices", []):
            # Compare device type, OS, browser and IP to find similar devices
            if (device.get("device_type") == device_info.get("device_type") and
                device.get("os") == device_info.get("os") and
                device.get("browser") == device_info.get("browser") and
                device.get("ip_address") == device_info.get("ip_address")):
                # Remove the duplicate device
                device_sessions_collection.update_one(
                    {"user_id": user_id},
                    {"$pull": {"devices": {"device_id": device.get("device_id")}}}
                )
                similar_devices_exist = True
        
        # Add new device to the list in database
        device_sessions_collection.update_one(
            {"user_id": user_id},
            {"$push": {"devices": device_info}},
            upsert=True
        )
        
        # Update cache for this device
        cache_utils.cache_set(device_cache_key, device_info, DEVICE_CACHE_TTL)
        
        # Invalidate the device list cache
        list_cache_key = f"{DEVICE_LIST_CACHE_PREFIX}{user_id}"
        cache_utils.cache_delete(list_cache_key)
    
    return device_info

# Routes
@session_devices_bp.route('/api/devices', methods=['GET'])
def get_devices():
    """Get all devices for the currently authenticated user"""
    # Check if user is authenticated
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Not authenticated"}), 401
    
    # Get device sessions
    user_devices = get_user_devices(user_id)
    
    # Get current device id
    current_device_id = session.get('device_id')
    
    # Mark current device
    devices = user_devices.get("devices", [])
    for device in devices:
        device["is_current"] = (device.get("device_id") == current_device_id)
    
    # Sort devices by last active timestamp (most recent first)
    devices.sort(key=lambda x: x.get("last_active", ""), reverse=True)
    
    return jsonify({
        "devices": devices,
        "count": len(devices),
        "current_device_id": current_device_id
    })

@session_devices_bp.route('/api/devices/<device_id>', methods=['DELETE'])
def remove_device(device_id):
    """Remove a device for the currently authenticated user"""
    # Check if user is authenticated
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Not authenticated"}), 401
    
    # Check if trying to remove current device
    current_device_id = session.get('device_id')
    if device_id == current_device_id:
        return jsonify({
            "error": "Cannot remove current device. Please log out instead."
        }), 400
    
    # Get device session_id from cached devices
    list_cache_key = f"{DEVICE_LIST_CACHE_PREFIX}{user_id}"
    user_devices = cache_utils.cache_get(list_cache_key)
    
    # If not in cache, fetch from database
    if not user_devices:
        user_devices = device_sessions_collection.find_one({"user_id": user_id})
    
    # Find session_id for this device_id
    session_id = None
    if user_devices and "devices" in user_devices:
        for device in user_devices["devices"]:
            if device.get("device_id") == device_id:
                session_id = device.get("session_id")
                break
    
    # Remove device from the user's device sessions
    result = device_sessions_collection.update_one(
        {"user_id": user_id},
        {"$pull": {"devices": {"device_id": device_id}}}
    )
    
    # Clear caches
    if session_id:
        device_cache_key = f"{DEVICE_CACHE_PREFIX}{user_id}:{session_id}"
        cache_utils.cache_delete(device_cache_key)
    
    cache_utils.cache_delete(list_cache_key)
    
    if result.modified_count == 0:
        return jsonify({"error": "Device not found"}), 404
    
    return jsonify({
        "message": "Device removed successfully",
        "device_id": device_id
    })

# Function to clean up old device sessions
def cleanup_old_sessions(days=30):
    """Remove device sessions that haven't been active for a specified number of days"""
    cutoff_date = datetime.datetime.utcnow() - timedelta(days=days)
    cutoff_date_str = cutoff_date.isoformat() + "Z"
    
    try:
        # Find all documents with devices older than cutoff date
        result = device_sessions_collection.update_many(
            {},
            {"$pull": {"devices": {"last_active": {"$lt": cutoff_date_str}}}}
        )
        
        # Remove empty device sessions documents
        device_sessions_collection.delete_many({"devices": {"$size": 0}})
        
        print(f"Cleaned up {result.modified_count} old device sessions")
        return True
    except Exception as e:
        print(f"Error cleaning up old sessions: {e}")
        return False

# Initialize Blueprint
def init_app(app):
    app.register_blueprint(session_devices_bp)
    
    # Register cleanup task to run periodically
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        scheduler = BackgroundScheduler()
        
        # Add job to clean up old sessions once a day
        scheduler.add_job(cleanup_old_sessions, 'interval', days=1)
        
        # Start the scheduler
        scheduler.start()
    except ImportError:
        print("APScheduler not available, skipping automatic cleanup scheduler")
        
    return app 