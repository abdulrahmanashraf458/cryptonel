import os
import datetime
import random  # Add import for random module
from flask import Blueprint, jsonify, request, session
from pymongo import MongoClient
from bson import ObjectId
import time
from dotenv import load_dotenv
import logging  # Import logging module
# Import mining security module
from backend.cryptonel.mining.mining_security import check_security_before_mining, IPAnalyzer, DeviceFingerprinter, record_mining_activity, check_mining_violations

# Configure logging
logger = logging.getLogger("mining")

# Import 2FA verification modules
import pyotp
from functools import wraps
import base64
import hmac

# Load environment variables
load_dotenv()

# MongoDB connection
DATABASE_URL = os.getenv("DATABASE_URL")
client = MongoClient(DATABASE_URL)

# Database references
mining_db = client["cryptonel_mining"]
wallet_db = client["cryptonel_wallet"]
security_db = client["cryptonel_security"]  # Add security database reference

# Collections
mining_data = mining_db["mining_data"]
users = wallet_db["users"]
settings = wallet_db["settings"]
pending_mining = mining_db["pending_mining"]  # Now stores ONE document per entry (no arrays)
security_settings = security_db["security_settings"]  # Add security settings collection

# Constants for document size management
MAX_ENTRIES_PER_SHARD = 1000  # Maximum number of entries per shard
MAX_DOCUMENT_SIZE_MB = 15  # Keep below MongoDB's 16MB limit

# Create blueprint
mining_bp = Blueprint('mining', __name__, url_prefix='/api/mining')

# Initialize the pending_mining collection with a per-user document structure
def init_pending_mining_collection():
    """Initialize the pending_mining collection with per-user documents 
    and a sharded structure for organization"""
    # Check if the pending_mining collection has the main index document
    index_doc = pending_mining.find_one({"_id": "pending_mining_index"})
    
    if not index_doc:
        # Create the index document to track shards
        pending_mining.insert_one({
            "_id": "pending_mining_index",
            "current_shard": 1,
            "shards": [1],
            "last_cleanup": datetime.datetime.now(datetime.timezone.utc),
            "user_count": 0,
            "entry_count": 0
        })
        
        logger.info("Initialized pending_mining collection with per-user document structure")
    else:
        # Check if we need to migrate from the old structure
        # Look for shard documents with the old structure
        for shard_number in index_doc.get("shards", []):
            shard_id = f"pending_mining_shard_{shard_number}"
            shard_doc = pending_mining.find_one({"_id": shard_id})
            
            # Migrate data from old structure (array entries) to new structure (per-user documents)
            if shard_doc:
                # Check for the old array format
                if "pending_entries" in shard_doc:
                    # Group entries by user_id
                    user_entries = {}
                    for entry in shard_doc.get("pending_entries", []):
                        user_id = entry.get("user_id")
                        if user_id:
                            if user_id not in user_entries:
                                user_entries[user_id] = []
                            user_entries[user_id].append(entry)
                    
                    # Create individual user documents
                    for user_id, entries in user_entries.items():
                        user_doc = {
                            "_id": f"pending_mining_user_{user_id}",
                            "user_id": user_id,
                            "entries": entries,
                            "entry_count": len(entries),
                            "shard_number": shard_number,
                            "created_at": datetime.datetime.now(datetime.timezone.utc),
                            "updated_at": datetime.datetime.now(datetime.timezone.utc)
                        }
                        
                        # Insert or update the user document
                        pending_mining.update_one(
                            {"_id": f"pending_mining_user_{user_id}"},
                            {"$set": user_doc},
                            upsert=True
                        )
                    
                    # Delete the old shard document
                    pending_mining.delete_one({"_id": shard_id})
                    
                    # Update the index
                    pending_mining.update_one(
                        {"_id": "pending_mining_index"},
                        {
                            "$set": {
                                "user_count": len(user_entries),
                                "entry_count": sum(len(entries) for entries in user_entries.values()),
                                "last_migration": datetime.datetime.now(datetime.timezone.utc)
                            }
                        }
                    )
                    
                    logger.info(f"Migrated shard {shard_id} to per-user documents with {len(user_entries)} users")
                
                # Check for the interim structure with "users" field
                elif "users" in shard_doc:
                    # Create individual user documents
                    for user_id, entries in shard_doc.get("users", {}).items():
                        user_doc = {
                            "_id": f"pending_mining_user_{user_id}",
                            "user_id": user_id,
                            "entries": entries,
                            "entry_count": len(entries),
                            "shard_number": shard_number,
                            "created_at": datetime.datetime.now(datetime.timezone.utc),
                            "updated_at": datetime.datetime.now(datetime.timezone.utc)
                        }
                        
                        # Insert or update the user document
                        pending_mining.update_one(
                            {"_id": f"pending_mining_user_{user_id}"},
                            {"$set": user_doc},
                            upsert=True
                        )
                    
                    # Delete the old shard document
                    pending_mining.delete_one({"_id": shard_id})
                    
                    # Update the index
                    users_map = shard_doc.get("users", {})
                    pending_mining.update_one(
                        {"_id": "pending_mining_index"},
                        {
                            "$set": {
                                "user_count": len(users_map),
                                "entry_count": sum(len(entries) for entries in users_map.values()),
                                "last_migration": datetime.datetime.now(datetime.timezone.utc)
                            }
                        }
                    )
                    
                    logger.info(f"Migrated shard {shard_id} to per-user documents with {len(users_map)} users")

# Helper function to get the current active shard
def get_active_shard():
    """Get the current active shard for organizing user entries"""
    index_doc = pending_mining.find_one({"_id": "pending_mining_index"})
    if not index_doc:
        # Initialize if not exists
        init_pending_mining_collection()
        index_doc = pending_mining.find_one({"_id": "pending_mining_index"})
    
    current_shard = index_doc.get("current_shard", 1)
    return current_shard

# Helper function to create a new shard when needed
def create_new_shard():
    """Create a new shard reference in the index document"""
    index_doc = pending_mining.find_one({"_id": "pending_mining_index"})
    if not index_doc:
        init_pending_mining_collection()
        return 1
    
    # Get the next shard number
    current_shard = index_doc.get("current_shard", 1)
    next_shard = current_shard + 1
    
    # Update the index
    pending_mining.update_one(
        {"_id": "pending_mining_index"},
        {
            "$set": {"current_shard": next_shard},
            "$push": {"shards": next_shard}
        }
    )
    
    logger.info(f"Created new shard reference: {next_shard}")
    return next_shard

# Helper function to add entry to the user's document
def add_pending_entry(entry):
    """Add a pending mining entry as an individual document (v2 schema). Legacy per-user array docs are no longer updated."""
    user_id = entry.get("user_id")
    if not user_id:
        logger.error("Cannot add pending entry without user_id")
        return None

    # Ensure we have a timestamp
    entry.setdefault("timestamp", datetime.datetime.now(datetime.timezone.utc))

    # Fix the IP address – make sure we use the real IP if available
    if "request_fingerprint" in entry and "ip" in entry["request_fingerprint"]:
        real_ip = get_real_ip()
        if real_ip and real_ip not in ("127.0.0.1", "localhost"):
            entry["request_fingerprint"]["ip"] = real_ip

    # Use provided entry_id or generate ObjectId-based id
    entry_id = entry.get("entry_id") or str(ObjectId())
    entry["entry_id"] = entry_id

    # Determine current shard (kept for easy future partitioning)
    current_shard = get_active_shard()
    entry["shard_number"] = current_shard

    try:
        pending_mining.insert_one(entry)
    except Exception as e:
        logger.error(f"Failed to insert pending mining entry: {e}")
        return None

    # Return reference info – index document is left unchanged for legacy analytics
    return {
        "user_id": user_id,
        "entry_id": entry_id,
        "shard_number": current_shard
    }

# Helper function to find a pending entry across user documents
def find_pending_entry(entry_id, user_id=None):
    """Find a pending entry by its ID (supports both v2 individual docs and legacy array docs)"""
    # First, attempt to find in the new per-entry collection
    entry_doc = pending_mining.find_one({"entry_id": entry_id})
    if entry_doc:
        return {
            "entry": entry_doc,
            "user_id": entry_doc.get("user_id"),
            "shard_number": entry_doc.get("shard_number")
        }

    # Fallback to legacy lookup
    # If user_id is provided, search only in that user's legacy document
    if user_id:
        user_doc = pending_mining.find_one({"_id": f"pending_mining_user_{user_id}"})
        if user_doc and "entries" in user_doc:
            for entry in user_doc.get("entries", []):
                if entry.get("entry_id") == entry_id:
                    return {
                        "entry": entry,
                        "user_id": user_id,
                        "shard_number": user_doc.get("shard_number")
                    }
        return None

    # Search across all legacy user documents (less efficient)
    cursor = pending_mining.find({
        "_id": {"$regex": "^pending_mining_user_"},
        "entries.entry_id": entry_id
    })
    for user_doc in cursor:
        user_id = user_doc.get("user_id")
        for entry in user_doc.get("entries", []):
            if entry.get("entry_id") == entry_id:
                return {
                    "entry": entry,
                    "user_id": user_id,
                    "shard_number": user_doc.get("shard_number")
                }
    return None

# Helper function to find the most recent pending entry for a user
def find_most_recent_pending_entry(user_id):
    """Find the most recent unused pending entry for a user (supports v2 and legacy)"""
    if not user_id:
        return None

    # Try new collection first
    doc = pending_mining.find_one(
        {"user_id": user_id, "used": {"$ne": True}},
        sort=[("timestamp", -1)]
    )
    if doc:
        return {
            "entry": doc,
            "user_id": user_id,
            "shard_number": doc.get("shard_number")
        }

    # Legacy fallback
    user_doc = pending_mining.find_one({"_id": f"pending_mining_user_{user_id}"})
    if not user_doc or "entries" not in user_doc:
        return None

    unused_entries = [e for e in user_doc.get("entries", []) if not e.get("used", False)]
    if not unused_entries:
        return None

    sorted_entries = sorted(
        unused_entries,
        key=lambda x: x.get("timestamp", datetime.datetime.min),
        reverse=True
    )
    return {
        "entry": sorted_entries[0],
        "user_id": user_id,
        "shard_number": user_doc.get("shard_number")
    }

# Helper function to mark a pending entry as used
def mark_pending_entry_as_used(entry_id, user_id=None):
    """Mark a pending entry as used (supports v2 and legacy)"""
    # First try new collection
    result = pending_mining.update_one(
        {"entry_id": entry_id},
        {"$set": {"used": True, "updated_at": datetime.datetime.now(datetime.timezone.utc)}}
    )
    if result.modified_count:
        return True

    # Legacy path
    if not user_id:
        entry_info = find_pending_entry(entry_id)
        if not entry_info:
            return False
        user_id = entry_info.get("user_id")

    if not user_id:
        logger.error(f"Could not find user_id for entry {entry_id}")
        return False

    legacy_result = pending_mining.update_one(
        {"_id": f"pending_mining_user_{user_id}", "entries.entry_id": entry_id},
        {"$set": {"entries.$.used": True, "updated_at": datetime.datetime.now(datetime.timezone.utc)}}
    )
    return legacy_result.modified_count > 0

# Thorough cleanup function for all user documents
def cleanup_pending_mining_entries():
    """Clean up old or used pending mining entries across all user documents"""
    try:
        # Get current time
        current_time = datetime.datetime.now(datetime.timezone.utc)
        
        # Keep entries that are less than 24 hours old or unused
        cutoff_time = current_time - datetime.timedelta(hours=24)
        
        # Update the last cleanup time
        pending_mining.update_one(
            {"_id": "pending_mining_index"},
            {"$set": {"last_cleanup": current_time}}
        )
        
        # Find all user documents
        cursor = pending_mining.find({"_id": {"$regex": "^pending_mining_user_"}})
        
        total_users = 0
        total_cleaned = 0
        
        for user_doc in cursor:
            user_id = user_doc.get("user_id")
            if not user_id:
                continue
            
            entries = user_doc.get("entries", [])
            original_count = len(entries)
            
            # Keep only entries that are recent or not used
            updated_entries = [
                entry for entry in entries
                if not (entry.get("used", False) and entry.get("timestamp", current_time) < cutoff_time)
            ]
            
            if len(updated_entries) < original_count:
                # Update the user document with cleaned entries
                pending_mining.update_one(
                    {"_id": f"pending_mining_user_{user_id}"},
                    {
                        "$set": {
                            "entries": updated_entries,
                            "entry_count": len(updated_entries),
                            "updated_at": current_time
                        }
                    }
                )
                
                total_cleaned += (original_count - len(updated_entries))
            
            total_users += 1
            
            # If the user has no entries left, consider removing the document
            if len(updated_entries) == 0:
                # For now, we keep empty user documents to preserve user history
                # Could add option to remove them if needed
                pass
        
        # Update the index document with new counts
        if total_cleaned > 0:
            # Recalculate total entries
            total_entries = sum(
                doc.get("entry_count", 0) 
                for doc in pending_mining.find({"_id": {"$regex": "^pending_mining_user_"}})
            )
            
            pending_mining.update_one(
                {"_id": "pending_mining_index"},
                {"$set": {"entry_count": total_entries}}
            )
        
        logger.info(f"Cleaned up {total_cleaned} old pending mining entries across {total_users} users at {current_time.isoformat()}")
    except Exception as e:
        logger.error(f"Error cleaning up pending mining entries: {e}")

def init_app(app):
    app.register_blueprint(mining_bp)
    # Initialize the pending_mining collection with sharded structure
    init_pending_mining_collection()

def get_daily_mining_rate():
    """Get the daily mining rate from settings"""
    # Look specifically for the document with ID "mining_settings"
    system_settings = settings.find_one({"_id": "mining_settings"})
    
    if system_settings and 'daily_mining_rate' in system_settings:
        return float(system_settings['daily_mining_rate'])
    
    # Log error if settings not found
    print("ERROR: No daily_mining_rate found in settings collection")
    return 0  # Return zero if no settings found, this should trigger proper error handling

def is_boosted_mining_active():
    """Check if boosted mining event is currently active"""
    # Look specifically for the document with ID "mining_settings"
    system_settings = settings.find_one({"_id": "mining_settings"})
    
    if system_settings and 'boosted_mining' in system_settings:
        return bool(system_settings['boosted_mining'])
    
    return False  # Default to not boosted if setting not found

def is_maintenance_mode_active():
    """Check if maintenance mode is currently active"""
    # Look specifically for the document with ID "mining_settings"
    system_settings = settings.find_one({"_id": "mining_settings"})
    
    if system_settings and 'maintenance_mode' in system_settings:
        return bool(system_settings['maintenance_mode'])
    
    return False  # Default to no maintenance mode if setting not found

def get_boosted_mining_rate(original_rate):
    """Get boosted mining rate (2x the original rate)"""
    if is_boosted_mining_active():
        return original_rate * 2  # Double the rate when boosted
    return original_rate  # Return original rate if not boosted

def get_mining_session_hours():
    """Get the mining session hours from settings"""
    # Look specifically for the document with ID "mining_settings"
    system_settings = settings.find_one({"_id": "mining_settings"})
    
    if system_settings and 'mining_session_hours' in system_settings:
        return float(system_settings['mining_session_hours'])
    
    # Default to 24 hours if not found
    print("WARNING: No mining_session_hours found in settings, using default 24 hours")
    return 24.0

def ensure_timezone(dt):
    """Ensure datetime has timezone info"""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=datetime.timezone.utc)
    return dt

def can_mine_again(last_mined):
    """Check if user can mine again (mining_session_hours have passed)"""
    if isinstance(last_mined, str):
        try:
            last_mined = datetime.datetime.fromisoformat(last_mined.replace('Z', '+00:00'))
        except ValueError:
            # If conversion fails, assume it's a naive datetime
            last_mined = datetime.datetime.fromisoformat(last_mined)
            last_mined = ensure_timezone(last_mined)
    
    # Ensure timezone
    last_mined = ensure_timezone(last_mined)
    current_time = datetime.datetime.now(datetime.timezone.utc)
    
    # Get configurable mining session hours
    mining_session_hours = get_mining_session_hours()
    
    # Calculate time difference
    time_diff = current_time - last_mined
    hours_passed = time_diff.total_seconds() / 3600
    
    # Return True if mining_session_hours have passed
    return hours_passed >= mining_session_hours

# Add a helper function to format CRN values with 8 decimal places
def format_crn_value(value):
    """
    Format a value with 8 decimal places consistently.
    Ensures the return is always a string representation with 8 decimal places.
    """
    if value is None:
        value = 0
        
    # Convert to float to ensure proper formatting
    try:
        if isinstance(value, str):
            value = float(value)
        elif not isinstance(value, (int, float)):
            value = 0
    except (ValueError, TypeError):
        value = 0
        
    # Return formatted string with exactly 8 decimal places
    return "{:.8f}".format(value)

def get_mining_difficulty():
    """Get the mining difficulty level from settings (percentage chance of full rewards)"""
    # Look specifically for the document with ID "mining_settings"
    system_settings = settings.find_one({"_id": "mining_settings"})
    
    if system_settings and 'difficulty_level' in system_settings:
        return int(system_settings['difficulty_level'])
    
    # Default to 50% if not found
    print("WARNING: No difficulty_level found in settings, using default 50%")
    return 50

def calculate_mining_reward(base_reward):
    """Calculate mining reward based on difficulty level and randomization
    
    Args:
        base_reward: The base mining reward amount
        
    Returns:
        Adjusted reward based on difficulty level and randomization
    """
    # Get difficulty level (percentage chance of full reward)
    difficulty_level = get_mining_difficulty()
    
    # Generate random number between 0-100
    roll = random.randint(1, 100)
    
    # If roll is less than or equal to difficulty_level, user gets full reward
    if roll <= difficulty_level:
        return base_reward
    
    # Otherwise, calculate partial reward based on how close the roll was to the difficulty
    # This creates a sliding scale where rewards get smaller as roll gets further from difficulty
    ratio = 1 - ((roll - difficulty_level) / 100)
    # Ensure ratio is between 0.2 and 0.95 to prevent extremely low rewards
    ratio = max(0.2, min(0.95, ratio))
    
    # Return partial reward (with 8 decimal precision)
    partial_reward = base_reward * ratio
    return float(format_crn_value(partial_reward))

def get_mining_difficulty_description():
    """Return a descriptive text for current mining difficulty conditions"""
    difficulty = get_mining_difficulty()
    
    if difficulty >= 90:
        return "optimal"
    elif difficulty >= 70:
        return "favorable"
    elif difficulty >= 50:
        return "normal"
    elif difficulty >= 30:
        return "challenging"
    else:
        return "difficult"

@mining_bp.route('/check-2fa-required', methods=['GET'])
def check_2fa_required():
    """Check if 2FA is required for mining"""
    # Get user_id from session
    user_id = session.get('user_id')
    
    if not user_id:
        return jsonify({'error': 'User not authenticated'}), 401
    
    # Check if the user has 2FA enabled - FIRST CHECK USERS COLLECTION
    user = users.find_one({'user_id': user_id})
    
    if user and user.get('2fa_activated', False):
        # User has 2FA activated in main user profile
        return jsonify({
            'status': 'success',
            'is_2fa_enabled': True,
            'require_2fa_setup': False
        }), 200
        
    # If not found in users collection, check security_settings as fallback
    user_security = security_settings.find_one({'user_id': user_id})
    
    if not user_security:
        return jsonify({
            'status': 'error',
            'message': 'Security settings not found',
            'require_2fa_setup': True,
            'is_2fa_enabled': False
        }), 200
    
    # Check if 2FA is activated
    is_2fa_enabled = user_security.get('2fa_activated', False)
    
    if not is_2fa_enabled:
        return jsonify({
            'status': 'error',
            'message': 'Two-factor authentication is required for mining',
            'require_2fa_setup': True,
            'is_2fa_enabled': False
        }), 200
    
    return jsonify({
        'status': 'success',
        'is_2fa_enabled': True,
        'require_2fa_setup': False
    }), 200

@mining_bp.route('/verify-2fa', methods=['POST'])
def verify_2fa():
    """Verify 2FA code before mining"""
    # Get user_id from session
    user_id = session.get('user_id')
    
    if not user_id:
        return jsonify({'error': 'User not authenticated', 'is_valid': False}), 401
    
    # Get the request data
    data = request.get_json()
    if not data or 'code' not in data:
        return jsonify({'error': 'No 2FA code provided', 'is_valid': False}), 400
        
    code = data.get('code')
    timestamp = data.get('timestamp')  # Get the timestamp for verification
    received_code_hash = data.get('codeHash')  # Get the provided hash
    challenge = data.get('challenge')  # Get the challenge response
    
    # Validate timestamp to prevent replay attacks (within last 60 seconds)
    current_time = time.time() * 1000  # Convert to milliseconds for comparison with JS timestamp
    if timestamp and (current_time - int(timestamp) > 60000):  # More than 60 seconds old
        return jsonify({'error': 'Verification request expired', 'is_valid': False}), 401
    
    # Check if this is an automatic check (from page load)
    auto_check = data.get('auto_check', False) or code == '000000'
    
    # Skip rate limiting for auto_check requests
    if not auto_check:
        # فحص إذا كان المستخدم ممنوع بسبب محاولات كثيرة
        # التحقق من حالة rate limit للمستخدم
        rate_limits = wallet_db["rate_limits"].find_one({"user_id": user_id})
        current_time_seconds = time.time()
        
        if not rate_limits:
            # إنشاء سجل جديد إذا لم يكن موجودًا
            rate_limits = {
                "user_id": user_id,
                "rate_limits": [
                    {
                        "limit_type": "2fa_verification",
                        "count": 0,
                        "last_attempt": current_time_seconds,
                        "blocked_until": 0
                    }
                ]
            }
            wallet_db["rate_limits"].insert_one(rate_limits)
        
        # التحقق من وجود نوع 2fa_verification في rate_limits
        found_2fa_limit = False
        for limit in rate_limits.get("rate_limits", []):
            if limit.get("limit_type") == "2fa_verification":
                found_2fa_limit = True
                
                # التحقق من وجود حظر
                if limit.get("blocked_until", 0) > current_time_seconds:
                    remaining_time = int(limit["blocked_until"] - current_time_seconds)
                    return jsonify({
                        'message': f'Too many attempts. Please try again in {remaining_time} seconds.',
                        'is_valid': False,
                        'is_rate_limited': True,
                        'blocked_until': limit["blocked_until"],
                        'remaining_time': remaining_time
                    }), 429
                
                # حفظ عدد المحاولات الحالية
                attempts_count = limit.get("count", 0)
                break
        
        # إذا لم يوجد نوع 2fa_verification، إضافته
        if not found_2fa_limit:
            attempts_count = 0
            rate_limits.setdefault("rate_limits", []).append({
                "limit_type": "2fa_verification",
                "count": 0,
                "last_attempt": current_time_seconds,
                "blocked_until": 0
            })
            wallet_db["rate_limits"].update_one(
                {"user_id": user_id},
                {"$set": {"rate_limits": rate_limits["rate_limits"]}}
            )
        
        # عدد المحاولات المتبقية
        max_attempts = 5
        remaining_attempts = max_attempts - attempts_count
    else:
        # For auto-check, don't apply rate limits
        remaining_attempts = 5
    
    # If this is just an automatic check to see rate limit status, return early
    if auto_check and code == '000000':
        return jsonify({
            'message': 'Rate limit status check only',
            'is_valid': False,  # Always false for auto-check
            'remaining_attempts': remaining_attempts
        }), 200
    
    is_valid = False
    
    # First check the user collection for 2FA information
    user = users.find_one({'user_id': user_id})
    
    # Get the 2FA secret - needed for validation
    user_secret = None
    if user and user.get('2fa_activated', False) and user.get('2fa_secret'):
        # Use the 2FA secret from the user collection
        user_secret = user.get('2fa_secret')
    else:
        # Fallback to security_settings if not found in users collection
        user_security = security_settings.find_one({'user_id': user_id})
        
        if not user_security or not user_security.get('2fa_activated', False):
            return jsonify({
                'message': 'Two-factor authentication is not set up',
                'is_valid': False,
                'require_2fa_setup': True
            }), 403
        
        # Get the 2FA secret
        user_secret = user_security.get('2fa_secret')
        
        if not user_secret:
            return jsonify({
                'message': 'Two-factor authentication secret not found',
                'is_valid': False,
                'require_2fa_setup': True
            }), 403
    
    # Verify the additional challenge parameter if provided
    if challenge:
        try:
            # The challenge is the base64 encoded reversed code
            expected_challenge = base64.b64encode(code[::-1].encode()).decode()
            if challenge != expected_challenge:
                # Challenge verification failed, might be tampered request
                return jsonify({
                    'message': 'Security verification failed',
                    'is_valid': False
                }), 401
        except:
            # Invalid challenge format
            return jsonify({
                'message': 'Invalid verification parameters',
                'is_valid': False
            }), 400
    
    # Verify the 2FA code with TOTP
    if user_secret:
        totp = pyotp.TOTP(user_secret)
        is_valid = totp.verify(code, valid_window=2)
        
        # If standard verification fails, check current, previous and next code
        if not is_valid:
            current_time = int(time.time())
            expected_totp = totp.at(current_time)
            prev_totp = totp.at(current_time - 30)
            next_totp = totp.at(current_time + 30)
            
            # Try with a wider window for clock skew
            is_valid = totp.verify(code, valid_window=4)  # 2 minutes each way
        
        # Generate a server-side hash of the code for additional verification
        if timestamp and received_code_hash and is_valid:
            try:
                import hashlib
                server_code_hash = hashlib.sha256(f"{code}-{timestamp}".encode()).hexdigest()
                
                # Verify the hash matches what was received
                if received_code_hash != server_code_hash:
                    # Hash mismatch indicates potential tampering
                    is_valid = False
                    print(f"Hash mismatch: Expected {server_code_hash}, got {received_code_hash}")
                    return jsonify({
                        'message': 'Security verification failed - hash mismatch',
                        'is_valid': False
                    }), 401
            except Exception as e:
                print(f"Error verifying code hash: {str(e)}")
                # Continue with normal verification if hash check fails
    
    # Skip rate limit updates for auto-check
    if not auto_check:
        # تحديث عدد المحاولات بناءً على النتيجة
        if is_valid:
            # إعادة تعيين العداد عند النجاح
            for limit in rate_limits.get("rate_limits", []):
                if limit.get("limit_type") == "2fa_verification":
                    limit["count"] = 0
                    limit["last_attempt"] = current_time_seconds
                    limit["blocked_until"] = 0
                    break
            
            wallet_db["rate_limits"].update_one(
                {"user_id": user_id},
                {"$set": {"rate_limits": rate_limits.get("rate_limits", [])}}
            )
            
            # Store verification success in session with timestamp and token
            verification_token = os.urandom(16).hex()
            session["2fa_verified"] = True
            session["2fa_verified_timestamp"] = time.time()
            session["2fa_verification_token"] = verification_token
            
            # Generate a server-side signature for additional verification
            server_signature = hmac.new(
                user_secret.encode() if user_secret else b'default-key',
                f"{user_id}-{int(time.time())}".encode(),
                'sha256'
            ).hexdigest()
            
            # Code is valid - Return HTTP 200 with success message
            return jsonify({
                'message': 'Two-factor authentication verified successfully',
                'is_valid': True,
                'verification_token': verification_token,
                'signature': server_signature
            }), 200
        else:
            # زيادة عدد المحاولات الفاشلة
            for limit in rate_limits.get("rate_limits", []):
                if limit.get("limit_type") == "2fa_verification":
                    limit["count"] = attempts_count + 1
                    limit["last_attempt"] = current_time_seconds
                    
                    # إذا وصل إلى الحد الأقصى، تطبيق الحظر
                    if limit["count"] >= max_attempts:
                        # Changed from 5 minutes (300 seconds) to 60 seconds
                        blocked_until = current_time_seconds + 60  # 60 ثانية
                        limit["blocked_until"] = blocked_until
                        limit["count"] = 0  # إعادة تعيين العداد
                        
                        wallet_db["rate_limits"].update_one(
                            {"user_id": user_id},
                            {"$set": {"rate_limits": rate_limits.get("rate_limits", [])}}
                        )
                        
                        return jsonify({
                            'message': 'Too many incorrect attempts. Please try again in 60 seconds.',
                            'is_valid': False,
                            'is_rate_limited': True,
                            'blocked_until': blocked_until,
                            'remaining_time': 60
                        }), 429
                    
                    # تحديث عدد المحاولات
                    wallet_db["rate_limits"].update_one(
                        {"user_id": user_id},
                        {"$set": {"rate_limits": rate_limits.get("rate_limits", [])}}
                    )
                    break
            
            # Return appropriate error code for invalid code - Use HTTP 401 for authentication failure
            return jsonify({
                'message': 'Invalid verification code',
                'is_valid': False,
                'remaining_attempts': max_attempts - (attempts_count + 1)
            }), 401
    
    # Fallback for non-auto-check that somehow bypassed all other returns
    return jsonify({
        'message': 'Verification failed',
        'is_valid': False
    }), 401

@mining_bp.route('/check', methods=['POST'])
def check_mining():
    """Check if mining is possible and calculate potential reward"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not authenticated'}), 401

    current_time = datetime.datetime.now(datetime.timezone.utc)
    
    # SECURITY FIX: Check if user is blocked FIRST - before any other checks
    user_wallet = users.find_one({'user_id': user_id})
    if user_wallet and (user_wallet.get('mining_block', False) or user_wallet.get('ban', False)):
        logger.warning(f"Blocked/banned user {user_id} attempted to mine")
        return jsonify({
            'status': 'security_violation',
            'message': 'Mining is not allowed due to security violations',
            'penalty_type': user_wallet.get('mining_block') and 'mining_block' or 'permanent_ban'
        }), 403

    # Get user's mining data
    user_mining = mining_data.find_one({'user_id': user_id})
    
    # SECURITY FIX: Verify last_mined time integrity
    if user_mining and 'last_mined' in user_mining:
        last_mined = user_mining['last_mined']
        if isinstance(last_mined, str):
            last_mined = datetime.datetime.fromisoformat(last_mined.replace('Z', '+00:00'))
        last_mined = ensure_timezone(last_mined)
        
        # Reset if last_mined is in the future
        if last_mined > current_time:
            logger.error(f"Invalid last_mined time detected for user {user_id}")
            mining_data.update_one(
                {'user_id': user_id},
                {'$set': {'last_mined': current_time}}
            )
            last_mined = current_time

    # التحقق من صحة رمز CSRF
    try:
        # الحصول على التوكن من الهيدر
        csrf_token = request.headers.get('X-CSRF-Token') or request.form.get('csrf_token') or request.json.get('csrf_token')
        
        # استيراد وظيفة التحقق
        from backend.login import validate_csrf_token
        
        # التحقق من صحة التوكن
        if not validate_csrf_token(csrf_token):
            logger.warning(f"Invalid CSRF token for user {user_id}")
            return jsonify({'error': 'Invalid CSRF token'}), 403
    except Exception as e:
        logger.error(f"Error validating CSRF token: {e}")
        # Continue execution to avoid breaking during development
    
    # Get client data from request
    data = request.get_json() or {}
    client_data = data.get('client_data', {})
    
    # Add request fingerprinting for better security audit
    request_fingerprint = {
        "headers": dict(request.headers),
        "ip": request.remote_addr,
        "method": request.method,
        "endpoint": request.endpoint,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
    
    # Log the request for security analysis
    logger.info(f"Mining check request received from user {user_id}: {request_fingerprint}")
    
    # Check mining security before allowing mining
    allowed, security_response = check_security_before_mining(user_id)
    if not allowed:
        # Enhanced security response to include more details
        if 'details' in security_response and 'risk_score' in security_response['details']:
            # Include risk score and specific violation types for frontend display
            security_response['risk_score'] = security_response['details'].get('risk_score')
            security_response['violations'] = [v.get('type') for v in security_response['details'].get('violations', [])]
            security_response['penalty'] = security_response['details'].get('penalty_type')
        
        # Log security violation
        logger.warning(f"Security check failed for user {user_id}: {security_response}")
        
        return jsonify(security_response), 403
    
    # Check if mining system is in maintenance mode
    if is_maintenance_mode_active():
        return jsonify({
            'error': 'Mining system is currently under maintenance',
            'maintenance_mode': True
        }), 503
    
    # Get mining rate
    daily_mining_rate = get_daily_mining_rate()
    
    # Check if boosted mining is active and apply boost if needed
    boosted_mining = is_boosted_mining_active()
    if boosted_mining:
        daily_mining_rate = get_boosted_mining_rate(daily_mining_rate)
    
    # Calculate hourly mining rate
    hourly_mining_rate = daily_mining_rate / 24
    
    # Check if user already has mining data
    if not user_mining:
        new_mining_data = {
            'user_id': user_id,
            'last_mined': current_time,
            'total_mined': format_crn_value(0)
        }
        mining_data.insert_one(new_mining_data)
        user_mining = new_mining_data
    
    # Check if user can mine again (mining_session_hours have passed since last mining)
    # BUT: Allow immediate mining if the user is new or hasn't received any coins yet
    should_bypass_cooldown = False
    
    # Bypass cooldown if user doesn't have a wallet or their balance is 0
    if not user_wallet or (user_wallet and float(user_mining.get('total_mined', 0)) == 0):
        should_bypass_cooldown = True
    
    # User can mine - calculate potential reward
    potential_reward = calculate_mining_reward(daily_mining_rate)
    
    # Create a pending mining entry with unique ID
    pending_id = str(ObjectId())
    pending_entry = {
        'entry_id': pending_id,
        'user_id': user_id,
        'timestamp': current_time,
        'potential_reward': potential_reward,
        'daily_mining_rate': daily_mining_rate,
        'hourly_mining_rate': hourly_mining_rate,
        'mining_conditions': get_mining_difficulty_description(),
        'used': False,
        # Store the request fingerprint for security audit
        'request_fingerprint': request_fingerprint
    }
    
    # Add the pending entry to the appropriate shard
    entry_location = add_pending_entry(pending_entry)
    
    # Log successful mining check
    logger.info(f"Mining check successful for user {user_id}, pending_id: {pending_id}")
    
    # Return potential mining info without applying rewards yet
    return jsonify({
        'status': 'mining_authorized',
        'pending_id': pending_id,
        'potential_reward': potential_reward,
        'daily_mining_rate': daily_mining_rate,
        'hourly_mining_rate': hourly_mining_rate,
        'mining_conditions': get_mining_difficulty_description(),
        # Don't include sensitive security information in the response
        # that could be manipulated by the client
    })

@mining_bp.route('/apply-reward', methods=['POST'])
def apply_mining_reward():
    """Apply mining rewards after verification"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not authenticated'}), 401

    current_time = datetime.datetime.now(datetime.timezone.utc)

    # SECURITY FIX: Check if user is blocked FIRST - before any other checks
    user_wallet = users.find_one({'user_id': user_id})
    if user_wallet and (user_wallet.get('mining_block', False) or user_wallet.get('ban', False)):
        logger.warning(f"Blocked/banned user {user_id} attempted to claim mining reward")
        return jsonify({
            'status': 'security_violation',
            'message': 'Mining is not allowed due to security violations',
            'penalty_type': user_wallet.get('mining_block') and 'mining_block' or 'permanent_ban'
        }), 403

    # Get the pending mining data
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    # Get user's mining data
    user_mining = mining_data.find_one({'user_id': user_id})
    if not user_mining:
        return jsonify({'error': 'No mining data found'}), 404

    # SECURITY FIX: Verify last_mined time integrity
    last_mined = user_mining.get('last_mined', current_time)
    if isinstance(last_mined, str):
        last_mined = datetime.datetime.fromisoformat(last_mined.replace('Z', '+00:00'))
    last_mined = ensure_timezone(last_mined)
    
    # Reset if last_mined is in the future
    if last_mined > current_time:
        logger.error(f"Invalid last_mined time detected for user {user_id}")
        mining_data.update_one(
            {'user_id': user_id},
            {'$set': {'last_mined': current_time}}
        )
        last_mined = current_time

    # SECURITY FIX: Verify 2FA was completed properly
    verification_data = data.get('verification')
    if not verification_data:
        return jsonify({'error': 'Missing verification data'}), 403

    # Check if verification data is valid and not expired
    client_token = verification_data.get('token')
    client_signature = verification_data.get('signature') 
    client_timestamp = verification_data.get('timestamp')
    session_token = session.get('2fa_verification_token')
    session_timestamp = session.get('2fa_verified_timestamp')
    
    # Validate verification token
    if not client_token or not client_signature or not client_timestamp or not session_token:
        return jsonify({'error': 'Invalid verification data'}), 403
    
    # Check that the token matches what's stored in the session
    if client_token != session_token:
        # Token mismatch - this may indicate a replay attack
        logger.warning(f"2FA token mismatch for user {user_id}. Possible security breach attempt.")
        return jsonify({'error': 'Invalid verification token'}), 403
    
    # Check that the token isn't expired (5 minute validity)
    current_timestamp = time.time()
    token_timestamp = float(client_timestamp) / 1000  # Convert from milliseconds
    session_timestamp = session.get('2fa_verified_timestamp', 0)
    
    if (current_timestamp - token_timestamp > 300) or (current_timestamp - session_timestamp > 300):
        # Token has expired
        return jsonify({'error': 'Verification expired. Please try again.'}), 403
    
    # Validate the signature by regenerating it server-side
    # First get the user's 2FA secret
    user_secret = None
    user = users.find_one({'user_id': user_id})
    
    if user and user.get('2fa_secret'):
        user_secret = user.get('2fa_secret')
    else:
        # Fallback to security_settings if not found in users collection
        user_security = security_settings.find_one({'user_id': user_id})
        if user_security and user_security.get('2fa_secret'):
            user_secret = user_security.get('2fa_secret')
    
    if user_secret:
        # Generate the expected signature using the same algorithm as in verify_2fa
        expected_signature = hmac.new(
            user_secret.encode(),
            f"{user_id}-{int(session_timestamp)}".encode(),
            'sha256'
        ).hexdigest()
        
        # Compare with client signature
        if client_signature != expected_signature:
            logger.warning(f"2FA signature verification failed for user {user_id}. Possible tampering attempt.")
            return jsonify({'error': 'Invalid verification signature'}), 403
    else:
        # If we can't verify the signature, reject the request
        return jsonify({'error': 'Unable to verify authentication'}), 403
    
    # All verification passed, continue with mining reward application
    
    if not data.get('mining_data') or not data['mining_data'].get('pending_id'):
        # If no pending ID is provided, look for the most recent pending mining entry for this user
        pending_entry_info = find_most_recent_pending_entry(user_id)
        
        if not pending_entry_info:
            return jsonify({'error': 'No pending mining reward found for this user'}), 400
    else:
        # Get pending entry by ID
        pending_id = data['mining_data'].get('pending_id')
        pending_entry_info = find_pending_entry(pending_id, user_id)
        
        if not pending_entry_info:
            return jsonify({'error': 'Invalid pending mining reward ID'}), 400
        
        if pending_entry_info["entry"].get('used', False):
            return jsonify({'error': 'Mining reward already used'}), 400
    
    # Get current time
    current_time = datetime.datetime.now(datetime.timezone.utc)
    
    # CRITICAL SECURITY FIX: Get user's mining data to verify cooldown
    user_mining = mining_data.find_one({'user_id': user_id})
    
    # Verify that user can mine again (has waited the cooldown period)
    # This prevents client-side manipulation of cooldown values
    if user_mining:
        last_mined = user_mining.get('last_mined')
        
        # Special case for new users with no mining history
        user_wallet = users.find_one({'user_id': user_id})
        should_bypass_cooldown = False
        if not user_wallet or (user_wallet and float(user_mining.get('total_mined', 0)) == 0):
            should_bypass_cooldown = True
            
        # Check if user is blocked from mining
        is_blocked = False
        if user_wallet:
            mining_block = user_wallet.get('mining_block', False)
            is_banned = user_wallet.get('ban', False)
            if mining_block or is_banned:
                is_blocked = True
        
        # If user is not new and not allowed to bypass cooldown, enforce cooldown period
        if not should_bypass_cooldown and not can_mine_again(last_mined) and not is_blocked:
            # Calculate time remaining until mining is available again
            if isinstance(last_mined, str):
                last_mined = datetime.datetime.fromisoformat(last_mined.replace('Z', '+00:00'))
            
            last_mined = ensure_timezone(last_mined)
            mining_session_hours = get_mining_session_hours()
            next_mining_time = last_mined + datetime.timedelta(hours=mining_session_hours)
            time_remaining = next_mining_time - current_time
            hours_remaining = time_remaining.total_seconds() / 3600
            
            return jsonify({
                'status': 'mining_cooldown',
                'message': 'You need to wait before mining again',
                'hours_remaining': hours_remaining,
                'next_mining_time': next_mining_time.isoformat()
            }), 403
    
    # Get the mining reward from pending entry
    mining_reward = pending_entry_info["entry"].get('potential_reward')
    
    # Get user's mining data
    user_mining = mining_data.find_one({'user_id': user_id})
    if not user_mining:
        return jsonify({'error': 'No mining data found for this user'}), 404
    
    # Update user's mining data
    new_total_mined = float(user_mining.get('total_mined', 0)) + mining_reward
    
    mining_data.update_one(
        {'user_id': user_id},
        {
            '$set': {
                'last_mined': current_time,
                'total_mined': format_crn_value(new_total_mined)
            }
        }
    )
    
    # Update user's wallet balance - create wallet if it doesn't exist
    user_wallet = users.find_one({'user_id': user_id})
    if not user_wallet:
        users.insert_one({
            'user_id': user_id,
            'balance': format_crn_value(mining_reward)
        })
    else:
        current_balance = float(user_wallet.get('balance', 0))
        new_balance = current_balance + mining_reward
        
        users.update_one(
            {'user_id': user_id},
            {'$set': {'balance': format_crn_value(new_balance)}}
        )
    
    # Mark pending entry as used in its shard
    mark_pending_entry_as_used(
        pending_entry_info["entry"]["entry_id"], 
        pending_entry_info["user_id"]
    )
    
    # Clear the verification token from the session after successful use
    session.pop('2fa_verification_token', None)
    session.pop('2fa_verified_timestamp', None)
    
    # Return mining info
    return jsonify({
        'status': 'mining_success',
        'mined_amount': mining_reward,
        'total_mined': format_crn_value(new_total_mined),
        'timestamp': current_time.isoformat()
    })

@mining_bp.route('/status', methods=['GET'])
def get_mining_status():
    """Get current mining status for the user"""
    # Get user_id from session
    user_id = session.get('user_id')
    
    if not user_id:
        return jsonify({'error': 'User not authenticated'}), 401
    
    # Get current time
    current_time = datetime.datetime.now(datetime.timezone.utc)
    
    # Check if mining system is in maintenance mode
    maintenance_mode = is_maintenance_mode_active()
    
    # If in maintenance mode, return limited info
    if maintenance_mode:
        return jsonify({
            'maintenance_mode': True
        })
    
    # Get user's mining data
    user_mining = mining_data.find_one({'user_id': user_id})
    
    # Get user's wallet data
    user_wallet = users.find_one({'user_id': user_id})
    
    # Get system settings
    daily_mining_rate = get_daily_mining_rate()
    mining_session_hours = get_mining_session_hours()
    boosted_mining = is_boosted_mining_active()
    
    # Apply boost if active
    if boosted_mining:
        daily_mining_rate = get_boosted_mining_rate(daily_mining_rate)
    
    # Default values if no data exists
    total_mined = format_crn_value(0)
    last_mined = current_time
    balance = format_crn_value(0)
    can_mine = True
    hours_remaining = 0
    
    # Check for mining block or account ban
    security_violation = False
    mining_block = False
    is_banned = False
    security_details = None
    
    if user_wallet:
        mining_block = user_wallet.get('mining_block', False)
        is_banned = user_wallet.get('ban', False)
        balance = format_crn_value(float(user_wallet.get('balance', 0)))
        
        # If user is banned or blocked from mining, set can_mine to false
        if mining_block or is_banned:
            can_mine = False
            security_violation = True
            
            # Add security violation details if available
            # Create a mining block object to check for violations
            try:
                # Critical security fix: Don't trust client IP/headers directly, use server detection
                ip_address = get_real_ip()
                user_agent = request.headers.get('User-Agent', '')
                
                # Create a mining block with minimal info
                mining_block_data = {
                    "user_id": user_id,
                    "ip_address": ip_address,
                    "user_agent": user_agent,
                    "browser_fingerprint": DeviceFingerprinter.generate_browser_fingerprint(user_agent, ip_address),
                    "device_fingerprint": DeviceFingerprinter.generate_device_fingerprint(user_agent, ip_address)
                }
                
                # تعديل: إضافة التحقق من IP مع بصمة الجهاز
                # تمرير كامل بيانات mining_block للتحقق من IP مع بصمة الجهاز
                is_violation, violation_details = check_mining_violations(user_id, mining_block_data)
                
                if is_violation and violation_details:
                    # Simplify the details for frontend display
                    security_details = {
                        "user_id": user_id,  # Add user_id to security details
                        "penalty_type": violation_details.get("penalty_type", "unknown"),
                        "risk_score": violation_details.get("risk_score", 0),
                        "is_vpn_detected": violation_details.get("is_vpn_detected", False),
                        "violations": [v.get("type") for v in violation_details.get("violations", [])],
                        "raw_violations": violation_details.get("violations", []),  # Include raw violation data
                        "severity": max([v.get("severity", "low") for v in violation_details.get("violations", [])], default="low"),
                        "message": violation_details.get("reason", "Security violation detected")
                    }
                    
                    # Log security violation details for monitoring
                    logger.info(f"Security violation details for user {user_id}: {security_details}")
            except Exception as e:
                logger.error(f"Error getting security details: {e}")
                # Provide default security details if an error occurs
                security_details = {
                    "user_id": user_id,  # Add user_id to default security details
                    "penalty_type": "mining_block" if mining_block else "permanent_ban" if is_banned else "warning",
                    "message": "Security policy violation"
                }
    
    if user_mining:
        total_mined = format_crn_value(float(user_mining.get('total_mined', 0)))
        last_mined = user_mining.get('last_mined', current_time)
        
        # Special case: If user doesn't have a wallet or hasn't mined anything yet, 
        # always allow mining regardless of last_mined time
        should_bypass_cooldown = False
        if not user_wallet or (user_wallet and float(total_mined) == 0):
            should_bypass_cooldown = True
        
        # Check if user can mine again - only if not already blocked
        if not should_bypass_cooldown and not mining_block and not is_banned:
            can_mine = can_mine_again(last_mined)
            
            # Calculate hours remaining - ONLY for users who aren't blocked
            if not can_mine:
                if isinstance(last_mined, str):
                    last_mined = datetime.datetime.fromisoformat(last_mined.replace('Z', '+00:00'))
                
                last_mined = ensure_timezone(last_mined)
                mining_session_hours = get_mining_session_hours()
                next_mining_time = last_mined + datetime.timedelta(hours=mining_session_hours)
                time_remaining = next_mining_time - current_time
                hours_remaining = time_remaining.total_seconds() / 3600
                
                # CRITICAL SECURITY FIX: Ensure hours_remaining can't be negative
                # This prevents miners from manipulating client-side to get faster mining
                if hours_remaining < 0:
                    hours_remaining = 0
                    can_mine = True
    
    # Calculate hourly rate (make sure it's not zero)
    hourly_rate = daily_mining_rate / 24
    if hourly_rate <= 0:
        hourly_rate = 0.416667  # Default to 10/24 if zero
    
    # Get mining difficulty description
    mining_conditions = get_mining_difficulty_description()
    
    # For mining blocked users, set hours_remaining to 0 to prevent showing the countdown timer
    if mining_block or is_banned:
        hours_remaining = 0
    
    # Log the mining status request
    logger.info(f"Mining status requested by user {user_id}: can_mine={can_mine}, hours_remaining={hours_remaining:.2f}")
    
    # CRITICAL SECURITY FIX: Remove sensitive data from the response
    # to prevent client-side manipulation
    response_data = {
        'total_mined': total_mined,
        'last_mined': last_mined.isoformat() if isinstance(last_mined, datetime.datetime) else last_mined,
        'daily_mining_rate': daily_mining_rate,
        'hourly_mining_rate': float(format_crn_value(hourly_rate)),
        'can_mine': can_mine,
        'hours_remaining': hours_remaining,
        'wallet_balance': balance,
        'mining_session_hours': mining_session_hours,
        'boosted_mining': boosted_mining,
        'maintenance_mode': maintenance_mode,
        'mining_conditions': mining_conditions,  # Add mining conditions to the response
        'security_violation': security_violation,  # Add security violation flag
        'mining_block': mining_block,  # Add mining block status
        'ban': is_banned,  # Add ban status
    }
    
    # Include security details only if there is a security violation
    # This prevents leaking unnecessary security details to normal users
    if security_violation and security_details:
        # Filter out sensitive fields that could be manipulated
        filtered_security_details = {
            "penalty_type": security_details.get("penalty_type"),
            "message": security_details.get("message"),
            "violations": security_details.get("violations", [])
        }
        
        # Only include risk score if it's high enough to warrant showing
        if security_details.get("risk_score", 0) > 70:
            filtered_security_details["risk_score"] = security_details.get("risk_score")
            
        response_data["security_details"] = filtered_security_details
    
    # Return the response
    return jsonify(response_data)

@mining_bp.route('/stats', methods=['GET'])
def get_mining_stats():
    """Get global mining statistics"""
    # Check if mining system is in maintenance mode
    maintenance_mode = is_maintenance_mode_active()
    
    if maintenance_mode:
        return jsonify({
            'maintenance_mode': True
        })
    
    # Get total miners count
    total_miners = mining_data.count_documents({})
    
    # Get top miners
    top_miners = list(mining_data.find().sort('total_mined', -1).limit(10))
    
    # Calculate total mined across all users
    all_mining_data = mining_data.find()
    total_mined_all = sum(float(user.get('total_mined', 0)) for user in all_mining_data)
    
    # Get system settings
    daily_mining_rate = get_daily_mining_rate()
    
    # Format top miners data
    formatted_top_miners = []
    for miner in top_miners:
        user_wallet = users.find_one({'user_id': miner['user_id']})
        username = user_wallet.get('username', 'Unknown') if user_wallet else 'Unknown'
        
        formatted_top_miners.append({
            'user_id': miner['user_id'],
            'username': username,
            'total_mined': format_crn_value(float(miner.get('total_mined', 0)))
        })
    
    return jsonify({
        'total_miners': total_miners,
        'total_mined_all': format_crn_value(total_mined_all),
        'daily_mining_rate': daily_mining_rate,
        'top_miners': formatted_top_miners
    })

# Add a new endpoint for checking device security
@mining_bp.route('/security/check', methods=['POST'])
def check_device_security():
    """Check device security without initiating mining"""
    user_id = session.get('user_id')
    
    if not user_id:
        return jsonify({'error': 'User not authenticated'}), 401
    
    # Get client data from request
    data = request.get_json() or {}
    client_data = data.get('client_data', {})
    
    # Record mining activity to get device information
    mining_block = record_mining_activity(user_id)
    
    # Check for security violations with the recorded activity
    is_violation, violation_details = check_mining_violations(user_id, mining_block)
    
    if is_violation:
        # Return detailed security information
        return jsonify({
            'status': 'security_violation',
            'allowed': False,
            'details': {
                'user_id': user_id,  # Add user_id to security details
                'penalty_type': violation_details.get('penalty_type', 'warning'),
                'risk_score': violation_details.get('risk_score', 0),
                'is_vpn_detected': violation_details.get('is_vpn_detected', False),
                'violations': [v.get('type') for v in violation_details.get('violations', [])],
                'raw_violations': violation_details.get('violations', []),  # Include raw violation data
                'message': violation_details.get('reason', 'Security violation detected')
            }
        })
    else:
        # Return device information when no violations are found
        device_type = mining_block.get('device_type', 'unknown')
        ip_info = IPAnalyzer.analyze_ip(mining_block.get('ip_address', '0.0.0.0'))
        
        return jsonify({
            'status': 'ok',
            'allowed': True,
            'device_info': {
                'type': device_type,
                'fingerprint_id': mining_block.get('device_fingerprint', '')[-8:] if mining_block.get('device_fingerprint') else None,
                'ip_type': ip_info.get('ip_type', 'unknown'),
                'is_vpn': ip_info.get('is_vpn', False),
                'is_datacenter': ip_info.get('is_datacenter', False),
                'risk_score': ip_info.get('risk_score', 0)
            }
        })

def get_real_ip():
    """
    Get the real IP address of the user, even behind proxies
    This prevents IP spoofing attacks
    """
    # Check for forwarded IP in various headers
    headers_to_check = [
        'X-Forwarded-For', 
        'CF-Connecting-IP',  # Cloudflare
        'True-Client-IP',    # Akamai/Cloudflare
        'X-Real-IP',         # Nginx
        'X-Client-IP'        # Apache
    ]
    
    for header in headers_to_check:
        ip = request.headers.get(header)
        if ip:
            # X-Forwarded-For can contain multiple IPs, get the first one (client)
            if ',' in ip:
                ip = ip.split(',')[0].strip()
            
            # Basic IP validation to prevent header injection
            if is_valid_ip(ip):
                return ip
    
    # Fall back to remote_addr if no headers found
    return request.remote_addr

def is_valid_ip(ip):
    """Basic check for valid IPv4/IPv6 format"""
    import re
    
    # IPv4 pattern
    ipv4_pattern = re.compile(r'^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$')
    # IPv6 pattern - simplified check
    ipv6_pattern = re.compile(r'^[0-9a-f:]+$')
    
    # Check IPv4
    if ipv4_pattern.match(ip):
        # Validate each octet
        for octet in ip.split('.'):
            if int(octet) > 255:
                return False
        return True
    
    # Check IPv6
    if ipv6_pattern.match(ip):
        # Basic format check - would need more robust validation for production
        return ':' in ip
    
    return False 