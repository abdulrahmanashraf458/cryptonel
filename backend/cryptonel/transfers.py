import os
import json
import uuid
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request, session
from pymongo import MongoClient
from dotenv import load_dotenv
from bson import ObjectId
import time
import pyotp
import threading
import logging

# Configure logger
logger = logging.getLogger(__name__)

# Import our custom email sender module
from backend.cryptonel.email_sender import send_transaction_emails, send_rating_notification_email

# Import JWT utilities
from backend.jwt_utils import token_required, decode_token

# Load environment variables
load_dotenv()

# Create Blueprint for Transfers endpoints
transfers_bp = Blueprint('transfers', __name__)

# MongoDB connection
MONGODB_URI = os.getenv("DATABASE_URL")
client = MongoClient(MONGODB_URI)
db = client["cryptonel_wallet"]
users_collection = db["users"]
# The same collection will now be used for both old and new formats
user_transactions_collection = db["user_transactions"]
settings_collection = db["settings"]

# Rating system collections
user_rating_stats_collection = db["user_rating_stats"]  # Collection for user rating statistics
ratings_collection = db["ratings"]  # Collection for individual ratings

rate_limits_collection = db["rate_limits"]  # New collection for rate limits

# Cache variables for memoization
tax_settings_cache = None
tax_settings_cache_time = 0
user_address_cache = {}
user_address_cache_times = {}

# Add data structure to track validation attempts
# This would normally be in a Redis cache or database in production
address_validation_attempts = {}  # Store attempts by user_id

# Add data structure to track 2FA attempts
# This would normally be in a Redis cache or database in production
twofa_verification_attempts = {}  # Store attempts by user_id

# Add data structure to track restricted account attempts
# This is for tracking attempts to transfer to banned/locked wallets
restricted_account_attempts = {}  # Store attempts by user_id

# Add data structure to track last transfer time
# This would normally be in a Redis cache or database in production
last_transfer_time = {}  # Store last transfer timestamp by user_id

# Add data structure to track transfer frequency
# This would normally be in a Redis cache or database in production
transfer_frequency_cache = {}  # Store transfer attempts by user_id

# Add data structure to track daily transfers to same recipient
daily_transfers_to_recipient = {}  # Store daily transfers by user_id -> recipient_id

# Add function to check and update rate limits using MongoDB with Array
def check_rate_limit(user_id):
    """
    Check if a user has exceeded their rate limit for address validation.
    Returns a tuple (is_rate_limited, attempts_remaining, reset_time)
    """
    current_time = time.time()
    
    # Get user's rate limits record
    user_rate_limits = rate_limits_collection.find_one({"user_id": user_id})
    
    # Initialize if not exists
    if not user_rate_limits:
        user_rate_limits = {
            "user_id": user_id,
            "rate_limits": []
        }
        rate_limits_collection.insert_one(user_rate_limits)
    
    # Find the address validation limit in the array
    address_validation = None
    if "rate_limits" in user_rate_limits:
        for limit in user_rate_limits["rate_limits"]:
            if limit.get("limit_type") == "address_validation":
                address_validation = limit
                break
    
    # If no address validation limit exists
    if not address_validation:
        return False, 5, 0
    
    # Check if user is currently blocked
    blocked_until = address_validation.get('blocked_until', 0)
    if blocked_until > current_time:
        # User is rate limited
        seconds_remaining = int(blocked_until - current_time)
        return True, 0, seconds_remaining
    
    # If it's been more than 10 minutes since the last attempt, reset counter
    last_attempt = address_validation.get('last_attempt', 0)
    if current_time - last_attempt > 600:  # 10 minutes in seconds
        # Reset attempt count in DB
        rate_limits_collection.update_one(
            {"user_id": user_id, "rate_limits.limit_type": "address_validation"},
            {"$set": {"rate_limits.$.count": 0, "rate_limits.$.last_attempt": current_time}}
        )
        return False, 5, 0
    
    # User is not blocked, return attempts remaining
    count = address_validation.get('count', 0)
    attempts_remaining = 5 - count
    return False, attempts_remaining, 0

# Update rate limit tracking after an attempt
def update_rate_limit(user_id, is_valid):
    """Update rate limit tracking after an address validation attempt"""
    current_time = time.time()
    
    # Get user's rate limits record
    user_rate_limits = rate_limits_collection.find_one({"user_id": user_id})
    
    # Initialize if not exists
    if not user_rate_limits:
        user_rate_limits = {
            "user_id": user_id,
            "rate_limits": []
        }
        rate_limits_collection.insert_one(user_rate_limits)
    
    # Find the address validation limit in the array
    address_validation = None
    has_limit = False
    if "rate_limits" in user_rate_limits:
        for i, limit in enumerate(user_rate_limits["rate_limits"]):
            if limit.get("limit_type") == "address_validation":
                address_validation = limit
                has_limit = True
                break
    
    # If valid, reset counter
    if is_valid:
        if has_limit:
            # Update existing limit
            rate_limits_collection.update_one(
                {"user_id": user_id, "rate_limits.limit_type": "address_validation"},
                {"$set": {"rate_limits.$.count": 0, "rate_limits.$.last_attempt": current_time}}
            )
        else:
            # Add new limit to array
            rate_limits_collection.update_one(
                {"user_id": user_id},
                {"$push": {"rate_limits": {
                    "limit_type": "address_validation",
                    "count": 0,
                    "last_attempt": current_time,
                    "blocked_until": 0
                }}}
            )
        return
    
    # Get current count
    count = 0
    if address_validation:
        count = address_validation.get('count', 0)
    
    # Increment attempt counter
    new_count = count + 1
    new_blocked_until = 0
    
    # If max attempts reached, block for 60 seconds
    if new_count >= 5:
        new_blocked_until = current_time + 60  # Block for 60 seconds
        new_count = 0  # Reset counter for next window
    
    if has_limit:
        # Update existing limit
        rate_limits_collection.update_one(
            {"user_id": user_id, "rate_limits.limit_type": "address_validation"},
            {"$set": {
                "rate_limits.$.count": new_count,
                "rate_limits.$.last_attempt": current_time,
                "rate_limits.$.blocked_until": new_blocked_until
            }}
        )
    else:
        # Add new limit to array
        rate_limits_collection.update_one(
            {"user_id": user_id},
            {"$push": {"rate_limits": {
                "limit_type": "address_validation",
                "count": new_count,
                "last_attempt": current_time,
                "blocked_until": new_blocked_until
            }}}
        )

# Add function to check and update restricted account rate limits
def check_restricted_rate_limit(user_id):
    """
    Check if a user has exceeded their rate limit for restricted account attempts.
    Returns a tuple (is_rate_limited, attempts_remaining, reset_time)
    """
    current_time = time.time()
    
    # Get user's rate limits record
    user_rate_limits = rate_limits_collection.find_one({"user_id": user_id})
    
    # Initialize if not exists
    if not user_rate_limits:
        return False, 3, 0
    
    # Find the restricted account limit in the array
    restricted_account = None
    if "rate_limits" in user_rate_limits:
        for limit in user_rate_limits["rate_limits"]:
            if limit.get("limit_type") == "restricted_account":
                restricted_account = limit
                break
    
    # If no restricted account limit exists
    if not restricted_account:
        return False, 3, 0
    
    # Check if user is currently blocked
    blocked_until = restricted_account.get('blocked_until', 0)
    if blocked_until > current_time:
        # User is rate limited
        seconds_remaining = int(blocked_until - current_time)
        return True, 0, seconds_remaining
    
    # If it's been more than 15 minutes since the last attempt, reset counter
    last_attempt = restricted_account.get('last_attempt', 0)
    if current_time - last_attempt > 900:  # 15 minutes in seconds
        # Reset attempt count in DB
        rate_limits_collection.update_one(
            {"user_id": user_id, "rate_limits.limit_type": "restricted_account"},
            {"$set": {"rate_limits.$.count": 0, "rate_limits.$.last_attempt": current_time}}
        )
        return False, 3, 0
    
    # User is not blocked, return attempts remaining
    count = restricted_account.get('count', 0)
    attempts_remaining = 3 - count
    return False, attempts_remaining, 0

# Update restricted account rate limit tracking
def update_restricted_rate_limit(user_id):
    """Update rate limit tracking after an attempt to transfer to a restricted account"""
    current_time = time.time()
    
    # Get user's rate limits record
    user_rate_limits = rate_limits_collection.find_one({"user_id": user_id})
    
    # Initialize if not exists
    if not user_rate_limits:
        user_rate_limits = {
            "user_id": user_id,
            "rate_limits": []
        }
        rate_limits_collection.insert_one(user_rate_limits)
    
    # Find the restricted account limit in the array
    restricted_account = None
    has_limit = False
    if "rate_limits" in user_rate_limits:
        for limit in user_rate_limits["rate_limits"]:
            if limit.get("limit_type") == "restricted_account":
                restricted_account = limit
                has_limit = True
                break
    
    # Get current count
    count = 0
    if restricted_account:
        count = restricted_account.get('count', 0)
    
    # Increment attempt counter
    new_count = count + 1
    new_blocked_until = 0
    
    # If max attempts reached, block for 120 seconds (2 minutes) - stricter limit
    if new_count >= 3:
        new_blocked_until = current_time + 120  # Block for 120 seconds
        new_count = 0  # Reset counter for next window
    
    if has_limit:
        # Update existing limit
        rate_limits_collection.update_one(
            {"user_id": user_id, "rate_limits.limit_type": "restricted_account"},
            {"$set": {
                "rate_limits.$.count": new_count,
                "rate_limits.$.last_attempt": current_time,
                "rate_limits.$.blocked_until": new_blocked_until
            }}
        )
    else:
        # Add new limit to array
        rate_limits_collection.update_one(
            {"user_id": user_id},
            {"$push": {"rate_limits": {
                "limit_type": "restricted_account",
                "count": new_count,
                "last_attempt": current_time,
                "blocked_until": new_blocked_until
            }}}
        )

# Add function to check and update 2FA rate limits
def check_2fa_rate_limit(user_id):
    """
    Check if a user has exceeded their rate limit for 2FA verification.
    Returns a tuple (is_rate_limited, attempts_remaining, reset_time)
    """
    current_time = time.time()
    
    # Get user's rate limits record
    user_rate_limits = rate_limits_collection.find_one({"user_id": user_id})
    
    # Initialize if not exists
    if not user_rate_limits:
        return False, 5, 0
    
    # Find the 2FA verification limit in the array
    twofa_verification = None
    if "rate_limits" in user_rate_limits:
        for limit in user_rate_limits["rate_limits"]:
            if limit.get("limit_type") == "2fa_verification":
                twofa_verification = limit
                break
    
    # If no 2FA verification limit exists
    if not twofa_verification:
        return False, 5, 0
    
    # Check if user is currently blocked
    blocked_until = twofa_verification.get('blocked_until', 0)
    if blocked_until > current_time:
        # User is rate limited
        seconds_remaining = int(blocked_until - current_time)
        return True, 0, seconds_remaining
    
    # If it's been more than 10 minutes since the last attempt, reset counter
    last_attempt = twofa_verification.get('last_attempt', 0)
    if current_time - last_attempt > 600:  # 10 minutes in seconds
        # Reset attempt count in DB
        rate_limits_collection.update_one(
            {"user_id": user_id, "rate_limits.limit_type": "2fa_verification"},
            {"$set": {"rate_limits.$.count": 0, "rate_limits.$.last_attempt": current_time}}
        )
        return False, 5, 0
    
    # User is not blocked, return attempts remaining
    count = twofa_verification.get('count', 0)
    attempts_remaining = 5 - count
    return False, attempts_remaining, 0

# Update 2FA rate limit tracking after an attempt
def update_2fa_rate_limit(user_id, is_valid):
    """Update rate limit tracking after a 2FA verification attempt"""
    current_time = time.time()
    
    # Get user's rate limits record
    user_rate_limits = rate_limits_collection.find_one({"user_id": user_id})
    
    # Initialize if not exists
    if not user_rate_limits:
        user_rate_limits = {
            "user_id": user_id,
            "rate_limits": []
        }
        rate_limits_collection.insert_one(user_rate_limits)
    
    # Find the 2FA verification limit in the array
    twofa_verification = None
    has_limit = False
    if "rate_limits" in user_rate_limits:
        for limit in user_rate_limits["rate_limits"]:
            if limit.get("limit_type") == "2fa_verification":
                twofa_verification = limit
                has_limit = True
                break
    
    # If valid, reset counter
    if is_valid:
        if has_limit:
            # Update existing limit
            rate_limits_collection.update_one(
                {"user_id": user_id, "rate_limits.limit_type": "2fa_verification"},
                {"$set": {"rate_limits.$.count": 0, "rate_limits.$.last_attempt": current_time}}
            )
        else:
            # Add new limit to array
            rate_limits_collection.update_one(
                {"user_id": user_id},
                {"$push": {"rate_limits": {
                    "limit_type": "2fa_verification",
                    "count": 0,
                    "last_attempt": current_time,
                    "blocked_until": 0
                }}}
            )
        return
    
    # Get current count
    count = 0
    if twofa_verification:
        count = twofa_verification.get('count', 0)
    
    # Increment attempt counter
    new_count = count + 1
    new_blocked_until = 0
    
    # If max attempts reached, block for 60 seconds
    if new_count >= 5:
        new_blocked_until = current_time + 60  # Block for 60 seconds
        new_count = 0  # Reset counter for next window
    
    if has_limit:
        # Update existing limit
        rate_limits_collection.update_one(
            {"user_id": user_id, "rate_limits.limit_type": "2fa_verification"},
            {"$set": {
                "rate_limits.$.count": new_count,
                "rate_limits.$.last_attempt": current_time,
                "rate_limits.$.blocked_until": new_blocked_until
            }}
        )
    else:
        # Add new limit to array
        rate_limits_collection.update_one(
            {"user_id": user_id},
            {"$push": {"rate_limits": {
                "limit_type": "2fa_verification",
                "count": new_count,
                "last_attempt": current_time,
                "blocked_until": new_blocked_until
            }}}
        )

# Add function to check transfer frequency limits
def check_transfer_frequency_limit(user_id):
    """
    Check if a user has exceeded transfer frequency limits (3 per minute)
    Returns a tuple (is_limited, attempts_remaining, reset_time)
    """
    current_time = time.time()
    
    # Get user's rate limits record
    user_rate_limits = rate_limits_collection.find_one({"user_id": user_id})
    
    # Initialize if not exists
    if not user_rate_limits:
        return False, 3, 0
    
    # Find the transfer frequency limit in the array
    transfer_frequency = None
    if "rate_limits" in user_rate_limits:
        for limit in user_rate_limits["rate_limits"]:
            if limit.get("limit_type") == "transfer_frequency":
                transfer_frequency = limit
                break
    
    # If no transfer frequency limit exists
    if not transfer_frequency:
        return False, 3, 0
    
    # Check if user is currently blocked
    blocked_until = transfer_frequency.get('blocked_until', 0)
    if blocked_until > current_time:
        # User is rate limited
        seconds_remaining = int(blocked_until - current_time)
        return True, 0, seconds_remaining
    
    # If it's been more than 1 minute since the last attempt, reset counter
    last_attempt = transfer_frequency.get('last_attempt', 0)
    if current_time - last_attempt > 60:  # 1 minute in seconds
        # Reset attempt count in DB
        rate_limits_collection.update_one(
            {"user_id": user_id, "rate_limits.limit_type": "transfer_frequency"},
            {"$set": {"rate_limits.$.count": 0, "rate_limits.$.last_attempt": current_time}}
        )
        return False, 3, 0
    
    # User is not blocked, return attempts remaining
    count = transfer_frequency.get('count', 0)
    attempts_remaining = 3 - count
    return False, attempts_remaining, 0

# Update transfer frequency tracking after a transfer
def update_transfer_frequency_limit(user_id):
    """Update transfer frequency tracking after a transfer"""
    current_time = time.time()
    
    # Get user's rate limits record
    user_rate_limits = rate_limits_collection.find_one({"user_id": user_id})
    
    # Initialize if not exists
    if not user_rate_limits:
        user_rate_limits = {
            "user_id": user_id,
            "rate_limits": []
        }
        rate_limits_collection.insert_one(user_rate_limits)
    
    # Find the transfer frequency limit in the array
    transfer_frequency = None
    has_limit = False
    if "rate_limits" in user_rate_limits:
        for limit in user_rate_limits["rate_limits"]:
            if limit.get("limit_type") == "transfer_frequency":
                transfer_frequency = limit
                has_limit = True
                break
    
    # Get current count
    count = 0
    if transfer_frequency:
        count = transfer_frequency.get('count', 0)
    
    # Increment attempt counter
    new_count = count + 1
    new_blocked_until = 0
    
    # If max attempts reached (3 per minute), block for 5 minutes
    if new_count >= 3:
        new_blocked_until = current_time + 300  # Block for 5 minutes
        new_count = 0  # Reset counter for next window
    
    if has_limit:
        # Update existing limit
        rate_limits_collection.update_one(
            {"user_id": user_id, "rate_limits.limit_type": "transfer_frequency"},
            {"$set": {
                "rate_limits.$.count": new_count,
                "rate_limits.$.last_attempt": current_time,
                "rate_limits.$.blocked_until": new_blocked_until
            }}
        )
    else:
        # Add new limit to array
        rate_limits_collection.update_one(
            {"user_id": user_id},
            {"$push": {"rate_limits": {
                "limit_type": "transfer_frequency",
                "count": new_count,
                "last_attempt": current_time,
                "blocked_until": new_blocked_until
            }}}
        )

# Add function to check daily transfers to same recipient
def check_daily_transfers_to_recipient(user_id, recipient_id):
    """
    Check if a user has exceeded daily transfers to the same recipient (10 per day)
    Returns a tuple (is_limited, attempts_remaining, reset_time)
    """
    current_time = time.time()
    
    # Get user's rate limits record
    user_rate_limits = rate_limits_collection.find_one({"user_id": user_id})
    
    # Initialize if not exists
    if not user_rate_limits:
        return False, 10, 0
    
    # Find the daily transfers to recipient limit in the array
    daily_transfers = None
    if "rate_limits" in user_rate_limits:
        for limit in user_rate_limits["rate_limits"]:
            if limit.get("limit_type") == f"daily_transfers_{recipient_id}":
                daily_transfers = limit
                break
    
    # If no daily transfers limit exists
    if not daily_transfers:
        return False, 10, 0
    
    # Check if user is currently blocked
    blocked_until = daily_transfers.get('blocked_until', 0)
    if blocked_until > current_time:
        # User is rate limited
        seconds_remaining = int(blocked_until - current_time)
        return True, 0, seconds_remaining
    
    # If it's been more than 24 hours since the last attempt, reset counter
    last_attempt = daily_transfers.get('last_attempt', 0)
    if current_time - last_attempt > 86400:  # 24 hours in seconds
        # Reset attempt count in DB
        rate_limits_collection.update_one(
            {"user_id": user_id, "rate_limits.limit_type": f"daily_transfers_{recipient_id}"},
            {"$set": {"rate_limits.$.count": 0, "rate_limits.$.last_attempt": current_time}}
        )
        return False, 10, 0
    
    # User is not blocked, return attempts remaining
    count = daily_transfers.get('count', 0)
    attempts_remaining = 10 - count
    return False, attempts_remaining, 0

# Update daily transfers to recipient tracking
def update_daily_transfers_to_recipient(user_id, recipient_id):
    """Update daily transfers to recipient tracking after a transfer"""
    current_time = time.time()
    
    # Get user's rate limits record
    user_rate_limits = rate_limits_collection.find_one({"user_id": user_id})
    
    # Initialize if not exists
    if not user_rate_limits:
        user_rate_limits = {
            "user_id": user_id,
            "rate_limits": []
        }
        rate_limits_collection.insert_one(user_rate_limits)
    
    # Find the daily transfers to recipient limit in the array
    daily_transfers = None
    has_limit = False
    if "rate_limits" in user_rate_limits:
        for limit in user_rate_limits["rate_limits"]:
            if limit.get("limit_type") == f"daily_transfers_{recipient_id}":
                daily_transfers = limit
                has_limit = True
                break
    
    # Get current count
    count = 0
    if daily_transfers:
        count = daily_transfers.get('count', 0)
    
    # Increment attempt counter
    new_count = count + 1
    new_blocked_until = 0
    
    # If max attempts reached (10 per day), block permanently and ban
    if new_count >= 10:
        new_blocked_until = current_time + 86400 * 365  # Block for 1 year (effectively permanent)
        new_count = 0  # Reset counter for next window
        
        # Apply permanent ban and transfer block
        users_collection.update_one(
            {"user_id": user_id},
            {"$set": {
                "transfers_block": True,
                "ban": True
            }}
        )
        
        logger.warning(f"User {user_id} banned for excessive transfers to {recipient_id} (10+ per day)")
    
    if has_limit:
        # Update existing limit
        rate_limits_collection.update_one(
            {"user_id": user_id, "rate_limits.limit_type": f"daily_transfers_{recipient_id}"},
            {"$set": {
                "rate_limits.$.count": new_count,
                "rate_limits.$.last_attempt": current_time,
                "rate_limits.$.blocked_until": new_blocked_until
            }}
        )
    else:
        # Add new limit to array
        rate_limits_collection.update_one(
            {"user_id": user_id},
            {"$push": {"rate_limits": {
                "limit_type": f"daily_transfers_{recipient_id}",
                "count": new_count,
                "last_attempt": current_time,
                "blocked_until": new_blocked_until
            }}}
        )

# Add function to check and apply transfer frequency protection
def apply_transfer_frequency_protection(user_id, recipient_id):
    """
    Apply comprehensive transfer frequency protection
    Returns a tuple (is_blocked, error_message, block_type)
    """
    # Check transfer frequency limit (3 per minute)
    is_frequency_limited, frequency_attempts_remaining, frequency_reset_time = check_transfer_frequency_limit(user_id)
    
    if is_frequency_limited:
        minutes_remaining = frequency_reset_time // 60
        seconds = frequency_reset_time % 60
        return True, f"Transfer frequency limit exceeded. Try again in {minutes_remaining}m {seconds}s", "frequency"
    
    # Check daily transfers to same recipient (10 per day)
    is_daily_limited, daily_attempts_remaining, daily_reset_time = check_daily_transfers_to_recipient(user_id, recipient_id)
    
    if is_daily_limited:
        hours_remaining = daily_reset_time // 3600
        minutes = (daily_reset_time % 3600) // 60
        return True, f"Daily transfer limit to this recipient exceeded. Try again in {hours_remaining}h {minutes}m", "daily"
    
    return False, None, None

# Helper functions
def get_user_balance(user_id):
    """Fetch user balance from MongoDB by user_id"""
    # Use projection to return only balance field
    user = users_collection.find_one(
        {"user_id": user_id},
        {"balance": 1, "_id": 0}
    )
    if not user:
        return None
    
    return user.get("balance", "0")

def get_user_limit_info(user_id):
    """Fetch user's wallet limit settings and manage 24-hour reset"""
    # Use projection to return only needed fields
    user = users_collection.find_one(
        {"user_id": user_id},
        {
            "wallet_lock": 1,
            "wallet_limit": 1,
            "daily_limit_used": 1,
            "daily_limit_last_reset": 1,
            "_id": 0
        }
    )
    if not user:
        return None
    
    # Get wallet lock status and limit
    wallet_lock = user.get("wallet_lock", False)
    wallet_limit = user.get("wallet_limit", None)
    
    # Get or initialize daily usage tracking
    daily_used = user.get("daily_limit_used", 0)
    last_reset = user.get("daily_limit_last_reset", None)
    
    # Check if we need to reset the daily limit (24 hours have passed)
    now = datetime.now()
    if last_reset:
        # If last_reset is a string, convert to datetime
        if isinstance(last_reset, str):
            try:
                last_reset = datetime.fromisoformat(last_reset)
            except ValueError:
                last_reset = now
        
        # Check if 24 hours have passed since last reset
        time_diff = now - last_reset
        if time_diff.total_seconds() >= 86400:  # 24 hours in seconds
            # Reset daily usage
            daily_used = 0
            users_collection.update_one(
                {"user_id": user_id},
                {"$set": {
                    "daily_limit_used": 0,
                    "daily_limit_last_reset": now
                }}
            )
    else:
        # Initialize the last reset time
        users_collection.update_one(
            {"user_id": user_id},
            {"$set": {"daily_limit_last_reset": now}}
        )
    
    # Calculate remaining limit
    remaining_limit = None
    if wallet_limit is not None:
        remaining_limit = float(wallet_limit) - daily_used
        if remaining_limit < 0:
            remaining_limit = 0
    
    return {
        "has_limit": wallet_lock,
        "limit_amount": wallet_limit,
        "remaining_limit": remaining_limit,
        "today_used": daily_used,
        "last_reset": last_reset.isoformat() if isinstance(last_reset, datetime) else None
    }

def get_user_by_private_address(private_address):
    """Find a user by their private address with caching"""
    current_time = time.time()
    
    # Check cache first (valid for 10 seconds)
    if (private_address in user_address_cache and 
        current_time - user_address_cache_times.get(private_address, 0) < 10):
        return user_address_cache[private_address]
    
    # Cache miss or expired, fetch from database
    user = users_collection.find_one(
        {"private_address": private_address},
        {
            "user_id": 1,
            "username": 1,
            "public_address": 1,
            "private_address": 1,
            "balance": 1,
            "ban": 1,
            "wallet_lock": 1,
            "frozen": 1,
            "premium": 1,
            "email": 1,  # Add email field for notifications
            "_id": 1  # Keep _id since it might be needed
        }
    )
    
    # Update cache
    user_address_cache[private_address] = user
    user_address_cache_times[private_address] = current_time
    
    # Limit cache size (remove oldest entries if more than 1000)
    if len(user_address_cache) > 1000:
        oldest_keys = sorted(user_address_cache_times.keys(), 
                            key=lambda k: user_address_cache_times[k])[:100]
        for key in oldest_keys:
            user_address_cache.pop(key, None)
            user_address_cache_times.pop(key, None)
    
    return user

def get_tax_settings():
    """Get tax settings from the database with caching"""
    global tax_settings_cache, tax_settings_cache_time
    current_time = time.time()
    
    # Use cached value if less than 60 seconds old
    if tax_settings_cache and (current_time - tax_settings_cache_time < 60):
        return tax_settings_cache
    
    # Cache miss or expired, fetch from database
    settings = settings_collection.find_one({"_id": "transfer_settings"})
    if not settings:
        result = {
            "tax_rate": "0.05",  # Default tax rate
            "tax_enabled": True,  # Default tax enabled
            "maintenance_mode": False,  # Default maintenance mode disabled
            "min_amount": None,  # No default value for min amount
            "max_amount": None,   # No default value for max amount
            "cooldown_minutes": None,  # No default, fetch only from database
            "premium_enabled": False,  # Default premium features disabled
            "premium_settings": {
                "tax_exempt": False,
                "tax_exempt_enabled": False,
                "cooldown_reduction": 0,
                "cooldown_reduction_enabled": False
            }
        }
    else:
        # Get premium settings or set defaults if not present
        premium_enabled = settings.get("premium_enabled", False)
        premium_settings = settings.get("premium_settings", {})
        if not premium_settings:
            premium_settings = {
                "tax_exempt": False,
                "tax_exempt_enabled": False,
                "cooldown_reduction": 0,
                "cooldown_reduction_enabled": False
            }
        
        result = {
            "tax_rate": settings.get("tax_rate", "0.05"),
            "tax_enabled": settings.get("tax_enabled", True),
            "maintenance_mode": settings.get("maintenance_mode", False),
            "min_amount": settings.get("min_amount", None),
            "max_amount": settings.get("max_amount", None),
            "cooldown_minutes": settings.get("cooldown_minutes"),  # No default value
            "premium_enabled": premium_enabled,
            "premium_settings": premium_settings
        }
    
    # Update cache
    tax_settings_cache = result
    tax_settings_cache_time = current_time
    
    return result

def check_transfer_cooldown(user_id):
    """
    Check if a user is in cooldown period after a transfer.
    Returns a tuple (is_in_cooldown, seconds_remaining)
    """
    current_time = time.time()
    
    # Get user's rate limits record
    user_rate_limits = rate_limits_collection.find_one({"user_id": user_id})
    
    # If no record, they're not in cooldown
    if not user_rate_limits:
        return False, 0
    
    # Find the transfer cooldown in the array
    transfer_cooldown = None
    if "rate_limits" in user_rate_limits:
        for limit in user_rate_limits["rate_limits"]:
            if limit.get("limit_type") == "transfer_cooldown":
                transfer_cooldown = limit
                break
    
    # If no transfer cooldown exists or no last_transfer
    if not transfer_cooldown or 'last_transfer' not in transfer_cooldown:
        return False, 0
    
    # Get tax settings for cooldown period
    settings = get_tax_settings()
    cooldown_minutes = settings.get("cooldown_minutes")
    
    # If no cooldown is set in database, don't apply cooldown
    if cooldown_minutes is None:
        return False, 0
    
    # Check if user is premium and eligible for cooldown reduction
    user = users_collection.find_one({"user_id": user_id})
    is_premium = user and user.get("premium", False)
    
    # Apply cooldown reduction for premium users if enabled
    if is_premium and settings.get("premium_enabled", False):
        premium_settings = settings.get("premium_settings", {})
        if premium_settings.get("cooldown_reduction_enabled", False):
            cooldown_reduction = premium_settings.get("cooldown_reduction", 0)
            
            # If cooldown_reduction is 0 and enabled, it means no cooldown for premium users
            if cooldown_reduction == 0:
                return False, 0
            
            # Otherwise apply the reduced cooldown
            cooldown_minutes = max(0, int(cooldown_minutes) - cooldown_reduction)
            if cooldown_minutes <= 0:
                return False, 0
    
    # Convert to integer and calculate seconds
    cooldown_minutes = int(cooldown_minutes)
    cooldown_seconds = cooldown_minutes * 60
    
    # Calculate time since last transfer
    last_transfer_time = transfer_cooldown.get('last_transfer')
    elapsed_seconds = current_time - last_transfer_time
    
    # Check if cooldown period has passed
    if elapsed_seconds >= cooldown_seconds:
        return False, 0
    
    # Still in cooldown, calculate remaining time
    seconds_remaining = int(cooldown_seconds - elapsed_seconds)
    return True, seconds_remaining

def update_last_transfer_time(user_id):
    """Update the timestamp of user's last transfer"""
    current_time = time.time()
    
    # Get user's rate limits record
    user_rate_limits = rate_limits_collection.find_one({"user_id": user_id})
    
    # Initialize if not exists
    if not user_rate_limits:
        user_rate_limits = {
            "user_id": user_id,
            "rate_limits": []
        }
        rate_limits_collection.insert_one(user_rate_limits)
    
    # Find the transfer cooldown in the array
    has_cooldown = False
    if "rate_limits" in user_rate_limits:
        for limit in user_rate_limits["rate_limits"]:
            if limit.get("limit_type") == "transfer_cooldown":
                has_cooldown = True
                break
    
    if has_cooldown:
        # Update existing cooldown
        rate_limits_collection.update_one(
            {"user_id": user_id, "rate_limits.limit_type": "transfer_cooldown"},
            {"$set": {"rate_limits.$.last_transfer": current_time}}
        )
    else:
        # Add new cooldown to array
        rate_limits_collection.update_one(
            {"user_id": user_id},
            {"$push": {"rate_limits": {
                "limit_type": "transfer_cooldown",
                "last_transfer": current_time
            }}}
        )

def validate_transfer(from_user_id, to_private_address, amount, transfer_reason=None):
    """
    Validate all conditions for a transfer
    
    Returns:
        tuple: (is_valid, error_message, sender, recipient, amount_float, fee)
    """
    # Step 1: Basic input validation
    if not from_user_id or not to_private_address:
        return False, "Missing sender or recipient", None, None, 0, 0
        
    # Step 2: Validate amount format
    try:
        amount_float = float(amount)
    except (ValueError, TypeError):
        return False, "Invalid amount format", None, None, 0, 0
        
    # Step 3: Check if amount is positive and reasonable
    if amount_float <= 0:
        return False, "Amount must be greater than zero", None, None, 0, 0
        
    if amount_float > 1000000000:  # 1 billion limit as a sanity check
        return False, "Amount exceeds maximum allowed value", None, None, 0, 0
        
    # Step 4: Check transfer reason
    if not transfer_reason or transfer_reason.strip() == "":
        return False, "Transfer reason is required", None, None, 0, 0
        
    # Step 5: Find sender - use projection for needed fields only
    sender = users_collection.find_one(
        {"user_id": from_user_id},
        {
            "balance": 1,
            "ban": 1,
            "wallet_lock": 1,
            "frozen": 1,
            "transfers_block": 1,
            "wallet_limit": 1,
            "daily_limit_used": 1,
            "premium": 1,
            "username": 1,
            "public_address": 1,
            "private_address": 1,
            "email": 1,  # Add email field for notifications
            "_id": 0
        }
    )
    if not sender:
        return False, "Sender not found", None, None, 0, 0
        
    # Step 6: Check sender's account restrictions
    if sender.get("ban", False):
        return False, "Your account has been banned. Transfers are disabled.", sender, None, 0, 0
        
    if sender.get("wallet_lock", False):
        return False, "Your wallet is locked. Transfers are disabled.", sender, None, 0, 0
        
    if sender.get("frozen", False):
        return False, "Your wallet is currently frozen. You cannot send transfers while your wallet is frozen.", sender, None, 0, 0
        
    # SECURITY FIX: Add mandatory check for transfers_block
    if sender.get("transfers_block", False):
        logger.warning(f"Blocked transfer attempt from user {from_user_id} - transfers_block is active")
        return False, "Your account has outgoing transfer restrictions. You cannot send funds at this time.", sender, None, 0, 0
        
    # Step 7: Check sender's balance
    sender_balance = float(sender.get("balance", "0"))
    if sender_balance < amount_float:
        return False, "Insufficient balance", sender, None, 0, 0
        
    # Step 8: Find recipient
    recipient = get_user_by_private_address(to_private_address)
    if not recipient:
        return False, "Recipient not found", sender, None, 0, 0
        
    # Step 9: Prevent self-transfers
    if recipient.get("user_id") == from_user_id:
        return False, "Cannot transfer to yourself", sender, recipient, 0, 0
        
    # Step 10: Check recipient's account restrictions
    if recipient.get("ban", False):
        return False, "Transfer failed. The recipient's account has been banned.", sender, recipient, 0, 0
        
    if recipient.get("wallet_lock", False):
        return False, "Transfer failed. The recipient's wallet is locked.", sender, recipient, 0, 0
        
    if recipient.get("frozen", False):
        return False, "Transfer failed. The recipient's wallet is currently frozen and cannot receive transfers.", sender, recipient, 0, 0
        
    # Step 11: Apply transfer frequency protection
    recipient_id = recipient.get("user_id")
    is_frequency_blocked, frequency_error, block_type = apply_transfer_frequency_protection(from_user_id, recipient_id)
    
    if is_frequency_blocked:
        if block_type == "daily":
            # For daily limit violations, apply permanent ban
            users_collection.update_one(
                {"user_id": from_user_id},
                {"$set": {
                    "transfers_block": True,
                    "ban": True
                }}
            )
            logger.warning(f"User {from_user_id} permanently banned for daily transfer limit violation to {recipient_id}")
            return False, "Your account has been permanently banned for excessive transfers to this recipient.", sender, recipient, 0, 0
        else:
            # For frequency violations, just block temporarily
            users_collection.update_one(
                {"user_id": from_user_id},
                {"$set": {"transfers_block": True}}
            )
            logger.warning(f"User {from_user_id} transfer blocked for frequency limit violation")
            return False, frequency_error, sender, recipient, 0, 0
        
    # Step 12: Calculate fee
    tax_settings = get_tax_settings()
    tax_rate = float(tax_settings["tax_rate"])
    tax_enabled = tax_settings["tax_enabled"]
    
    fee = 0
    
    # Check if user is premium
    is_premium = sender.get("premium", False)
    
    # Premium users don't pay fees if premium tax exemption is enabled
    premium_exempt = False
    if is_premium and tax_settings.get("premium_enabled", False):
        premium_settings = tax_settings.get("premium_settings", {})
        if premium_settings.get("tax_exempt_enabled", False) and premium_settings.get("tax_exempt", False):
            premium_exempt = True
    
    # Apply fee if not premium exempt and tax is enabled
    if not premium_exempt and tax_enabled:
        fee = amount_float * tax_rate
        
    # Step 13: Check daily limits
    if sender.get("wallet_limit", None) is not None and sender.get("wallet_lock", False):
        limit_info = get_user_limit_info(from_user_id)
        
        if limit_info["remaining_limit"] is not None and amount_float > limit_info["remaining_limit"]:
            return False, f"Daily limit exceeded. Remaining limit: {limit_info['remaining_limit']} CRN", sender, recipient, 0, 0
            
    # Step 14: Check for maintenance mode
    if tax_settings.get("maintenance_mode", False):
        return False, "System is currently in maintenance mode. Transfers are temporarily disabled.", sender, recipient, 0, 0
    
    # If min/max amount limits are set in settings, check them
    min_amount = tax_settings.get("min_amount")
    if min_amount is not None and float(min_amount) > 0 and amount_float < float(min_amount):
        return False, f"Transfer amount is below the minimum allowed: {min_amount} CRN", sender, recipient, 0, 0
        
    max_amount = tax_settings.get("max_amount")
    if max_amount is not None and float(max_amount) > 0 and amount_float > float(max_amount):
        return False, f"Transfer amount exceeds the maximum allowed: {max_amount} CRN", sender, recipient, 0, 0
    
    # All validation passed
    return True, None, sender, recipient, amount_float, fee

def process_transfer(from_user_id, to_private_address, amount, transfer_reason=None, skip_auth=False):
    """
    Process a transfer between users
    """
    # Start performance tracking
    tx_start_time = time.time()
    validation_start_time = time.time()
    
    # SECURITY FIX: Check for transfer block first
    sender = users_collection.find_one({"user_id": from_user_id})
    if not sender:
        return {"success": False, "error": "Sender not found"}
        
    if sender.get("transfers_block", False):
        logger.warning(f"Blocked transfer attempt from user {from_user_id} - transfers_block is active")
        return {"success": False, "error": "Your account has outgoing transfer restrictions. You cannot send funds at this time."}
    
    # Validate the transfer
    is_valid, error_message, sender, recipient, amount_float, fee = validate_transfer(
        from_user_id, to_private_address, amount, transfer_reason
    )
    
    validation_time = time.time() - validation_start_time
    logger.info(f"[PERF] Validation completed in {validation_time:.4f}s - Valid: {is_valid}")
    
    if not is_valid:
        return {"success": False, "error": error_message}
    
    # Update transfer frequency tracking
    recipient_id = recipient.get("user_id")
    update_transfer_frequency_limit(from_user_id)
    update_daily_transfers_to_recipient(from_user_id, recipient_id)
    
    # Start timing for the entire process
    process_start_time = time.time()
    print(f"[PERF] Transfer started: from={from_user_id}, to={to_private_address}, amount={amount}")
    
    # Start timing for data preparation
    prep_start_time = time.time()
    
    # Unpack data from validation
    recipient_id = recipient.get("user_id")
    recipient_balance = float(recipient.get("balance", "0"))
    sender_balance = float(sender.get("balance", "0"))
    
    # Calculate amount after fee
    amount_after_fee = amount_float - fee
    
    # Calculate new balances
    new_sender_balance = sender_balance - amount_float
    new_recipient_balance = recipient_balance + amount_after_fee
    
    # Get tax settings for response data
    tax_settings = get_tax_settings()
    tax_rate = float(tax_settings.get("tax_rate", "0.05"))
    tax_enabled = tax_settings.get("tax_enabled", True)
    
    # Check premium status for response data
    is_premium = sender.get("premium", False)
    premium_exempt = False
    if is_premium and tax_settings.get("premium_enabled", False):
        premium_settings = tax_settings.get("premium_settings", {})
        if premium_settings.get("tax_exempt_enabled", False) and premium_settings.get("tax_exempt", False):
            premium_exempt = True
    
    # Get public addresses and usernames
    sender_public_address = sender.get("public_address", "Unknown")
    recipient_public_address = recipient.get("public_address", "Unknown")
    recipient_username = recipient.get("username", "User")
    sender_username = sender.get("username", "Unknown")
    
    # Generate transaction ID
    tx_id = str(uuid.uuid4())
    
    # Record timestamp for transaction
    now = datetime.now()
    
    # Create transaction data for both users (FOR OLD ARRAY-BASED APPROACH)
    sender_transaction = {
        "tx_id": tx_id,
        "type": "sent",
        "amount": f"{amount_float:.8f}",
        "timestamp": now,
        "counterparty_address": to_private_address,
        "counterparty_public_address": recipient_public_address,
        "counterparty_id": recipient_id,
        "counterparty_username": recipient_username,
        "sender_username": sender_username,
        "sender_id": from_user_id,
        "status": "completed",
        "fee": f"{fee:.8f}",
        "reason": transfer_reason or "Not specified"
    }
    
    recipient_transaction = {
        "tx_id": tx_id,
        "type": "received",
        "amount": f"{amount_after_fee:.8f}",
        "timestamp": now,
        "counterparty_address": sender.get("private_address", "Unknown"),
        "counterparty_public_address": sender_public_address,
        "counterparty_id": from_user_id,
        "counterparty_username": sender_username,
        "recipient_username": recipient_username,
        "recipient_id": recipient_id,
        "status": "completed",
        "fee": f"{fee:.8f}",
        "reason": transfer_reason or "Not specified"
    }
    
    # Create detailed transaction documents with complete wallet information
    # This document represents the sender's perspective
    sender_tx_document = {
        "tx_id": tx_id,
        "type": "sent",
        "amount": f"{amount_float:.8f}",
        "timestamp": now,
        "fee": f"{fee:.8f}",
        "amount_after_fee": f"{amount_float:.8f}",  # Same as amount for sender
        "reason": transfer_reason or "Not specified",
        "status": "completed",
        "document_type": "transaction",  # Flag to identify document-based transactions
        
        # Sender complete information
        "user_id": from_user_id,  # The user this transaction belongs to
        "sender_id": from_user_id,
        "sender_username": sender_username,
        "sender_public_address": sender_public_address,
        "sender_private_address": sender.get("private_address", "Unknown"),
        "sender_balance_before": f"{sender_balance:.8f}",
        "sender_balance_after": f"{new_sender_balance:.8f}",
        "sender_premium": sender.get("premium", False),
        
        # Recipient complete information
        "recipient_id": recipient_id,
        "recipient_username": recipient_username,
        "recipient_public_address": recipient_public_address,
        "recipient_private_address": to_private_address,
        "recipient_balance_before": f"{recipient_balance:.8f}",
        "recipient_balance_after": f"{new_recipient_balance:.8f}",
        "recipient_premium": recipient.get("premium", False),
        
        # Counterparty references (for backward compatibility and convenient querying)
        "counterparty_id": recipient_id,
        "counterparty_username": recipient_username,
        "counterparty_address": to_private_address,
        "counterparty_public_address": recipient_public_address,
        
        # Additional metadata
        "tax_rate": f"{tax_rate:.4f}",
        "tax_enabled": tax_enabled,
        "premium_exempt": premium_exempt,
        "created_at": now,
        "updated_at": now
    }
    
    # This document represents the recipient's perspective
    recipient_tx_document = {
        "tx_id": tx_id,
        "type": "received",
        "amount": f"{amount_after_fee:.8f}",
        "timestamp": now,
        "fee": f"{fee:.8f}",
        "amount_after_fee": f"{amount_after_fee:.8f}",  # After fee deduction
        "reason": transfer_reason or "Not specified",
        "status": "completed",
        "document_type": "transaction",  # Flag to identify document-based transactions
        
        # Recipient complete information
        "user_id": recipient_id,  # The user this transaction belongs to
        "recipient_id": recipient_id,
        "recipient_username": recipient_username,
        "recipient_public_address": recipient_public_address,
        "recipient_private_address": to_private_address,
        "recipient_balance_before": f"{recipient_balance:.8f}",
        "recipient_balance_after": f"{new_recipient_balance:.8f}",
        "recipient_premium": recipient.get("premium", False),
        
        # Sender complete information
        "sender_id": from_user_id,
        "sender_username": sender_username,
        "sender_public_address": sender_public_address,
        "sender_private_address": sender.get("private_address", "Unknown"),
        "sender_balance_before": f"{sender_balance:.8f}",
        "sender_balance_after": f"{new_sender_balance:.8f}",
        "sender_premium": sender.get("premium", False),
        
        # Counterparty references (for backward compatibility and convenient querying)
        "counterparty_id": from_user_id,
        "counterparty_username": sender_username,
        "counterparty_address": sender.get("private_address", "Unknown"),
        "counterparty_public_address": sender_public_address,
        
        # Additional metadata
        "tax_rate": f"{tax_rate:.4f}",
        "tax_enabled": tax_enabled,
        "premium_exempt": premium_exempt,
        "created_at": now,
        "updated_at": now
    }
    
    # Record data preparation time
    prep_time = time.time() - prep_start_time
    print(f"[PERF] Data preparation completed in {prep_time:.4f}s")
    
    # Start timing for database operations
    db_start_time = time.time()
    
    # First try using MongoDB transaction for atomic operations
    transaction_success = False
    try:
        # Start timing for transaction
        tx_start_time = time.time()
        
        with client.start_session() as session:
            with session.start_transaction():
                # Update sender's balance
                users_collection.update_one(
                    {"user_id": from_user_id},
                    {"$set": {"balance": f"{new_sender_balance:.8f}"}},
                    session=session
                )
                
                # Update recipient's balance
                users_collection.update_one(
                    {"user_id": recipient_id},
                    {"$set": {"balance": f"{new_recipient_balance:.8f}"}},
                    session=session
                )
                
                # No longer updating old array structure - only using document-based approach
                
                # NEW APPROACH: Insert individual transaction documents in the same collection
                user_transactions_collection.insert_one(
                    sender_tx_document,
                    session=session
                )
                
                user_transactions_collection.insert_one(
                    recipient_tx_document,
                    session=session
                )
                
                # After successful transfer, update the daily limit usage
                if sender.get("wallet_limit", None) is not None:
                    # Get current usage
                    current_usage = sender.get("daily_limit_used", 0)
                    # Add the new transaction amount
                    new_usage = current_usage + amount_float
                    # Update in database
                    users_collection.update_one(
                        {"user_id": from_user_id},
                        {"$set": {"daily_limit_used": new_usage}},
                        session=session
                    )
                
                # Update the last transfer time for cooldown in the transaction
                rate_limits_collection.update_one(
                    {"user_id": from_user_id, "rate_limits.limit_type": "transfer_cooldown"},
                    {"$set": {"rate_limits.$.last_transfer": time.time()}},
                    session=session,
                    upsert=False
                )
        
        # Record transaction time
        tx_time = time.time() - tx_start_time
        print(f"[PERF] MongoDB transaction completed in {tx_time:.4f}s")
        
        # If we reach here, transaction was successful
        transaction_success = True
        
    except Exception as e:
        # If error mentions transactions not supported or replica set required
        print(f"[PERF] Transaction error: {e}")
        transaction_success = False
        
    # If transaction failed, fall back to non-transactional operations
    if not transaction_success:
        try:
            fallback_start_time = time.time()
            print("[PERF] Falling back to non-transactional operations")
            
            # Update sender's balance
            users_collection.update_one(
                {"user_id": from_user_id},
                {"$set": {"balance": f"{new_sender_balance:.8f}"}}
            )
            
            # Update recipient's balance
            users_collection.update_one(
                {"user_id": recipient_id},
                {"$set": {"balance": f"{new_recipient_balance:.8f}"}}
            )
            
            # No longer updating old array structure - only using document-based approach
            
            # NEW APPROACH: Insert individual transaction documents in the same collection
            user_transactions_collection.insert_one(sender_tx_document)
            user_transactions_collection.insert_one(recipient_tx_document)
            
            # After successful transfer, update the daily limit usage
            if sender.get("wallet_limit", None) is not None:
                # Get current usage
                current_usage = sender.get("daily_limit_used", 0)
                # Add the new transaction amount
                new_usage = current_usage + amount_float
                # Update in database
                users_collection.update_one(
                    {"user_id": from_user_id},
                    {"$set": {"daily_limit_used": new_usage}}
                )
            
            # Update the last transfer time for cooldown
            update_last_transfer_time(from_user_id)
            
            # Record fallback time
            fallback_time = time.time() - fallback_start_time
            print(f"[PERF] Fallback operations completed in {fallback_time:.4f}s")
            
        except Exception as fallback_error:
            print(f"[PERF] Fallback operation error: {fallback_error}")
            db_time = time.time() - db_start_time
            print(f"[PERF] Database operations failed after {db_time:.4f}s")
            process_time = time.time() - process_start_time
            print(f"[PERF] Transfer process failed in {process_time:.4f}s")
            return {"success": False, "error": "Transfer failed. Please try again."}
    
    # Record database operation time
    db_time = time.time() - db_start_time
    print(f"[PERF] Database operations completed in {db_time:.4f}s")
    
    # Start timing for response preparation
    response_start_time = time.time()
    
    # Create transaction data for the response
    transaction_data = {
        "id": tx_id,
        "amount": f"{amount_float:.8f}",
        "amount_simple": str(int(amount_float) if amount_float.is_integer() else amount_float),
        "timestamp": now.isoformat(),
        "sender": from_user_id,
        "sender_username": sender_username,
        "sender_public_address": sender_public_address,
        "recipient": recipient_id,
        "recipient_username": recipient_username,
        "recipient_public_address": recipient_public_address,
        "recipient_address": to_private_address,
        "fee": f"{fee:.8f}",
        "amount_after_fee": f"{amount_after_fee:.8f}",
        "tax_rate": str(tax_rate),
        "tax_enabled": tax_enabled,
        "is_premium": is_premium,
        "premium_exempt": premium_exempt,
        "reason": transfer_reason or "Not specified"
    }
    
    # Record response time
    response_time = time.time() - response_start_time
    print(f"[PERF] Response preparation completed in {response_time:.4f}s")
    
    # Start timing for email sending
    email_start_time = time.time()
    
    # Send email notifications in a background thread
    threading.Thread(
        target=send_transaction_emails,
        args=(sender, recipient, transaction_data, users_collection),
        daemon=True
    ).start()
    
    # Since email is sent in a background thread, we just measure thread creation time
    email_time = time.time() - email_start_time
    print(f"[PERF] Email notification thread started in {email_time:.4f}s")
    
    # Record total process time
    process_time = time.time() - process_start_time
    print(f"[PERF] Transfer process completed in {process_time:.4f}s")
    
    # Add performance metrics to the response for debugging in development
    performance_metrics = {
        "validation_time": round(validation_time, 4),
        "preparation_time": round(prep_time, 4),
        "database_time": round(db_time, 4),
        "response_time": round(response_time, 4),
        "email_thread_time": round(email_time, 4),
        "total_time": round(process_time, 4)
    }
    
    return {
        "success": True,
        "transaction": transaction_data,
        "performance": performance_metrics
    }

# Add route to get paginated transactions from document-based approach
@transfers_bp.route('/api/wallet/sharded-transactions', methods=['GET'])
@token_required
def get_sharded_transactions(user_id=None, **kwargs):
    """Get paginated transactions using document-based approach for the authenticated user"""
    # If user_id is None, fall back to session-based auth
    if user_id is None:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({"error": "Not authenticated"}), 401
            
    # Get page and limit parameters
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 20, type=int)
    
    # Cap limit to reasonable value
    if limit > 100:
        limit = 100
        
    # Get user transactions
    result = get_user_sharded_transactions(user_id, page, limit)
    
    return jsonify(result)

# Add a function to verify 2FA codes
def verify_2fa_code(user, verification_code):
    """
    Verify a 2FA code against a user's secret
    Returns True if valid, False otherwise
    """
    if not user or not user.get('2fa_activated', False):
        # If user doesn't have 2FA enabled, consider it valid
        return True
    
    # Get the user's 2FA secret
    secret = user.get('2fa_secret')
    if not secret:
        # If no secret is set but 2FA is enabled, something is wrong
        # In a real app, you might log this inconsistency
        return False
    
    # Convert verification_code to string if it's not already
    verification_code = str(verification_code)
    
    # Create a TOTP object with the user's secret
    totp = pyotp.TOTP(secret)
    
    # Get current time
    current_time = int(time.time())
    
    # First try with a tight window for maximum security
    if totp.verify(verification_code, valid_window=2):
        print(f"DEBUG: 2FA code verified with tight window")
        return True
        
    # If failed, check if it's a clock skew issue by checking previous and next codes
    expected_totp = totp.at(current_time)
    prev_totp = totp.at(current_time - 30)
    next_totp = totp.at(current_time + 30)
    
    print(f"DEBUG: User provided: {verification_code}, Expected: {expected_totp}, Previous: {prev_totp}, Next: {next_totp}, Timestamp: {current_time}")
    
    # For slightly out-of-sync clocks, try with a slightly larger window as fallback
    # valid_window=4 allows for 2 minutes each way (4 periods of 30 seconds)
    # This balances security with usability for users with clock sync issues
    return totp.verify(verification_code, valid_window=4)

# Rating system functions
def get_user_ratings(recipient_id):
    """
    Get a user's ratings information
    Returns a dictionary with rating stats
    """
    # Find user ratings document from the stats collection
    user_rating_stats = user_rating_stats_collection.find_one({"user_id": recipient_id})
    
    # If user has no ratings document yet, create default stats
    if not user_rating_stats:
        default_stats = {
            "user_id": recipient_id,
            "total_ratings": 0,
            "average_rating": 0,
            "rating_counts": {
                "1": 0,
                "2": 0,
                "3": 0,
                "4": 0,
                "5": 0
            }
        }
        return default_stats
    
    # Get recent ratings (last 50)
    recent_ratings = list(ratings_collection.find(
        {"recipient_id": recipient_id}
    ).sort("timestamp", -1).limit(50))
    
    # Add the recent ratings to the response
    result = user_rating_stats.copy()
    result["ratings"] = recent_ratings
    
    # Convert ObjectIds to strings for JSON serialization
    for rating in result["ratings"]:
        if "_id" in rating and isinstance(rating["_id"], ObjectId):
            rating["_id"] = str(rating["_id"])
    
    return result

def calculate_average_rating(ratings):
    """
    Calculate the average rating from an array of ratings
    """
    if not ratings or len(ratings) == 0:
        return 0
    
    total = sum(rating["stars"] for rating in ratings)
    return round(total / len(ratings), 1)  # Round to 1 decimal place

def update_user_rating(rater_id, recipient_id, stars, comment=None):
    """
    Add or update a rating for a user
    If the rater has already rated this user, replace the old rating
    """
    # Get current timestamp
    now = datetime.now()
    
    # Get rater information
    rater = users_collection.find_one({"user_id": rater_id})
    if not rater:
        return {"success": False, "error": "Rater not found"}
    
    # Get recipient information
    recipient = users_collection.find_one({"user_id": recipient_id})
    if not recipient:
        return {"success": False, "error": "Recipient not found"}
    
    # Get rater's username
    rater_username = rater.get("username", "Unknown")
    recipient_username = recipient.get("username", "Unknown")
    
    # Check if rater has already rated this user
    existing_rating = ratings_collection.find_one({
        "rater_id": rater_id,
        "recipient_id": recipient_id
    })
    
    # Prepare the rating document
    rating_document = {
        "rater_id": rater_id,
        "rater_username": rater_username,
        "recipient_id": recipient_id,
        "recipient_username": recipient_username,
        "stars": stars,
        "comment": comment,
        "timestamp": now,
        "updated_at": now
    }
    
    is_first_rating = False
    if existing_rating:
        # Update existing rating
        old_stars = existing_rating.get("stars", 0)
        
        # Update the rating document
        ratings_collection.update_one(
            {"_id": existing_rating["_id"]},
            {"$set": {
                "stars": stars,
                "comment": comment,
                "updated_at": now
            }}
        )
        
        # Update the stats collection - decrement old rating count, increment new rating count
        user_rating_stats_collection.update_one(
            {"user_id": recipient_id},
            {
                "$inc": {
                    f"rating_counts.{old_stars}": -1,
                    f"rating_counts.{stars}": 1
                }
            }
        )
    else:
        # Add new rating
        ratings_collection.insert_one(rating_document)
        is_first_rating = True
        
        # Update or create the stats document
        user_rating_stats_collection.update_one(
            {"user_id": recipient_id},
            {
                "$inc": {
                    "total_ratings": 1,
                    f"rating_counts.{stars}": 1
                },
                "$setOnInsert": {
                    "username": recipient_username,
                    "first_rating_at": now
                }
            },
            upsert=True
        )
    
    # Recalculate average rating
    pipeline = [
        {"$match": {"recipient_id": recipient_id}},
        {"$group": {
            "_id": "$recipient_id",
            "average_rating": {"$avg": "$stars"},
            "total_ratings": {"$sum": 1}
        }}
    ]
    
    result = list(ratings_collection.aggregate(pipeline))
    
    if result:
        average_rating = round(result[0]["average_rating"], 1)
        
        # Update average rating in stats collection
        user_rating_stats_collection.update_one(
            {"user_id": recipient_id},
            {"$set": {"average_rating": average_rating}}
        )
    else:
        average_rating = stars
    
    # Send email notification to recipient about the new rating ONLY if first rating
    if is_first_rating:
        try:
            from backend.cryptonel.email_sender import send_rating_notification_email
            threading.Thread(
                target=send_rating_notification_email,
                args=(recipient, rater, stars, comment, average_rating),
                daemon=True
            ).start()
        except Exception as e:
            print(f"Error sending rating notification email: {e}")
    
    return {"success": True}

# Add a function to verify secret word
def verify_secret_word(user, secret_word):
    """
    Verify a secret word against a user's stored secret word
    Returns True if valid, False otherwise
    """
    if not user:
        return False
    
    # If user has 2FA enabled, they shouldn't be using secret word
    if user.get('2fa_activated', False):
        return False
    
    # Get the user's stored secret word
    stored_secret = user.get('secret_word')
    if not stored_secret:
        # If no secret word is set, something is wrong
        return False
    
    # Exact match comparison
    return secret_word == stored_secret

def get_user_for_2fa(user_id):
    """Get user record with only 2FA relevant fields"""
    return users_collection.find_one(
        {"user_id": user_id},
        {
            "user_id": 1, 
            "2fa_activated": 1,
            "2fa_secret": 1,
            "premium": 1,  # For logging/response
            "username": 1,  # For logging/response
            "_id": 0
        }
    )

def get_user_for_secret_word(user_id):
    """Get user record with only secret word relevant fields"""
    return users_collection.find_one(
        {"user_id": user_id},
        {
            "user_id": 1,
            "2fa_activated": 1, 
            "secret_word": 1,
            "premium": 1,  # For logging/response
            "username": 1,  # For logging/response
            "_id": 0
        }
    )

# Routes
@transfers_bp.route('/api/wallet/balance', methods=['GET'])
@token_required
def get_balance(user_id=None, **kwargs):
    """Get wallet balance for the authenticated user"""
    # If user_id is None, fall back to session-based auth
    if user_id is None:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({"error": "Not authenticated"}), 401
    
    # Get user balance
    balance = get_user_balance(user_id)
    if balance is None:
        return jsonify({"error": "User not found"}), 404
    
    return jsonify({"balance": balance})

@transfers_bp.route('/api/wallet/limit', methods=['GET'])
@token_required
def get_limit(user_id=None, **kwargs):
    """Get wallet daily limit information for the authenticated user"""
    # If user_id is None, fall back to session-based auth
    if user_id is None:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({"error": "Not authenticated"}), 401
    
    # Get limit information
    limit_info = get_user_limit_info(user_id)
    if limit_info is None:
        return jsonify({"error": "User not found"}), 404
    
    return jsonify(limit_info)

@transfers_bp.route('/api/transfers/validate-address', methods=['POST'])
@token_required
def validate_address(user_id=None, **kwargs):
    """Validate if a private address exists"""
    # If user_id is None, fall back to session-based auth
    if user_id is None:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({"error": "Not authenticated"}), 401
    
    # Check if sender has transfer restrictions
    sender = users_collection.find_one({"user_id": user_id})
    if sender and sender.get("transfers_block", False):
        return jsonify({
            "valid": False,
            "error": "Your account has outgoing transfer restrictions. You cannot send funds at this time.",
            "transfer_blocked": True
        }), 403
    
    # Check if sender's wallet is frozen
    if sender and sender.get("frozen", False):
        return jsonify({
            "valid": False,
            "error": "Your wallet is currently frozen. You cannot send or receive transfers while your wallet is frozen.",
            "wallet_frozen": True
        }), 403
    
    # Check rate limit
    is_limited, attempts_remaining, seconds_remaining = check_rate_limit(user_id)
    if is_limited:
        return jsonify({
            "valid": False,
            "error": f"Rate limit exceeded. Try again in {seconds_remaining} seconds.",
            "rate_limited": True,
            "seconds_remaining": seconds_remaining
        }), 429
    
    # Check restricted account rate limit
    is_restricted_limited, restricted_attempts_remaining, restricted_seconds_remaining = check_restricted_rate_limit(user_id)
    if is_restricted_limited:
        return jsonify({
            "valid": False,
            "error": f"Too many attempts to transfer to restricted accounts. Try again in {restricted_seconds_remaining} seconds.",
            "rate_limited": True,
            "seconds_remaining": restricted_seconds_remaining
        }), 429
    
    # Get private address from request
    data = request.json
    # Try to get private address from all possible parameter names
    private_address = data.get('privateAddress') or data.get('private_address') or data.get('toAddress')
    
    if not private_address:
        return jsonify({"error": "Private address not provided"}), 400
    
    # Debug logging
    print(f"Validating address: {private_address}")
    
    # Find user with this private address
    recipient = get_user_by_private_address(private_address)
    
    # Debug logging
    if recipient:
        print(f"Recipient found: {recipient.get('username')}")
    else:
        print("No recipient found with this address")
    
    # Don't allow transfers to self
    if recipient and recipient.get('user_id') == user_id:
        is_valid = False
        update_rate_limit(user_id, is_valid)
        return jsonify({
            "valid": False, 
            "error": "Cannot transfer to yourself",
            "attempts_remaining": attempts_remaining - 1
        }), 400
    
    # Check if address is valid (recipient exists)
    is_valid = recipient is not None
    
    # If recipient exists, check for restrictions and apply frequency protection
    if is_valid:
        recipient_id = recipient.get("user_id")
        
        # SECURITY: Apply transfer frequency protection even during validation
        is_frequency_blocked, frequency_error, block_type = apply_transfer_frequency_protection(user_id, recipient_id)
        
        if is_frequency_blocked:
            if block_type == "daily":
                # For daily limit violations, apply permanent ban
                users_collection.update_one(
                    {"user_id": user_id},
                    {"$set": {
                        "transfers_block": True,
                        "ban": True
                    }}
                )
                logger.warning(f"User {user_id} permanently banned for daily transfer limit violation to {recipient_id}")
                return jsonify({
                    "valid": False,
                    "error": "Your account has been permanently banned for excessive transfers to this recipient.",
                    "permanently_banned": True
                }), 403
            else:
                # For frequency violations, just block temporarily
                users_collection.update_one(
                    {"user_id": user_id},
                    {"$set": {"transfers_block": True}}
                )
                logger.warning(f"User {user_id} transfer blocked for frequency limit violation")
                return jsonify({
                    "valid": False,
                    "error": frequency_error,
                    "transfer_blocked": True
                }), 429
        
        # Check if recipient is banned
        if recipient.get("ban", False):
            is_valid = False
            update_rate_limit(user_id, is_valid)
            # Update restricted account attempts
            update_restricted_rate_limit(user_id)
            # Get updated attempts remaining
            _, restricted_attempts_remaining, _ = check_restricted_rate_limit(user_id)
            return jsonify({
                "valid": False,
                "error": "Transfer not allowed. This user's account has been banned.",
                "restricted": True,
                "restricted_attempts_remaining": restricted_attempts_remaining
            }), 400
        
        # Check if recipient's wallet is locked
        if recipient.get("wallet_lock", False):
            is_valid = False
            update_rate_limit(user_id, is_valid)
            # Update restricted account attempts
            update_restricted_rate_limit(user_id)
            # Get updated attempts remaining
            _, restricted_attempts_remaining, _ = check_restricted_rate_limit(user_id)
            return jsonify({
                "valid": False,
                "error": "Transfer not allowed. This user's wallet is locked.",
                "restricted": True,
                "restricted_attempts_remaining": restricted_attempts_remaining
            }), 400
            
        # Check if recipient's wallet is frozen
        if recipient.get("frozen", False):
            is_valid = False
            update_rate_limit(user_id, is_valid)
            # Update restricted account attempts
            update_restricted_rate_limit(user_id)
            # Get updated attempts remaining
            _, restricted_attempts_remaining, _ = check_restricted_rate_limit(user_id)
            return jsonify({
                "valid": False,
                "error": "Transfer not allowed. This user's wallet is frozen and cannot receive transfers.",
                "restricted": True,
                "recipient_frozen": True,
                "restricted_attempts_remaining": restricted_attempts_remaining
            }), 400
    
    # Update rate limit tracking
    update_rate_limit(user_id, is_valid)
    
    # If valid, just return valid response
    if is_valid:
        return jsonify({"valid": True})
    
    # If invalid, check rate limit again to get updated attempts remaining
    _, attempts_remaining, _ = check_rate_limit(user_id)
    
    # Return response with attempts remaining
    return jsonify({
        "valid": False,
        "error": "Invalid address. No recipient found with this address.",
        "attempts_remaining": attempts_remaining
    })

@transfers_bp.route('/api/transfers/auth-method', methods=['GET'])
@token_required
def get_transfer_auth_method(user_id=None, **kwargs):
    """Get the user's configured transfer authentication method"""
    # If user_id is None, fall back to session-based auth
    if user_id is None:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({"error": "Not authenticated"}), 401
    
    # Get the user's transfer authentication settings
    user = users_collection.find_one(
        {"user_id": user_id},
        {"transfer_auth": 1, "_id": 0}
    )
    
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    # Get transfer authentication method settings with defaults
    transfer_auth = user.get("transfer_auth", {"password": False, "2fa": False, "secret_word": True})
    
    # Ensure we always return a valid object with all required fields
    if not transfer_auth:
        transfer_auth = {"password": False, "2fa": False, "secret_word": True}
    else:
        # Ensure all fields exist in the object
        if "password" not in transfer_auth:
            transfer_auth["password"] = False
        if "2fa" not in transfer_auth:
            transfer_auth["2fa"] = False
        if "secret_word" not in transfer_auth:
            transfer_auth["secret_word"] = True
    
    return jsonify({
        "transfer_auth": transfer_auth
    })

@transfers_bp.route('/api/transfers/send', methods=['POST'])
@token_required
def send_transfer(user_id=None, **kwargs):
    """Process a transfer from the authenticated user to another user"""
    # If user_id is None, fall back to session-based auth
    if user_id is None:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({"error": "Not authenticated"}), 401
    
    # SECURITY: Check transfer frequency protection first
    # Get recipient ID from request to check daily limits
    data = request.json
    to_private_address = data.get('toAddress')
    
    if to_private_address:
        # Find recipient to get their user_id
        recipient = get_user_by_private_address(to_private_address)
        if recipient:
            recipient_id = recipient.get("user_id")
            
            # Apply transfer frequency protection
            is_frequency_blocked, frequency_error, block_type = apply_transfer_frequency_protection(user_id, recipient_id)
            
            if is_frequency_blocked:
                if block_type == "daily":
                    # For daily limit violations, apply permanent ban
                    users_collection.update_one(
                        {"user_id": user_id},
                        {"$set": {
                            "transfers_block": True,
                            "ban": True
                        }}
                    )
                    logger.warning(f"User {user_id} permanently banned for daily transfer limit violation to {recipient_id}")
                    return jsonify({
                        "error": "Your account has been permanently banned for excessive transfers to this recipient.",
                        "permanently_banned": True
                    }), 403
                else:
                    # For frequency violations, just block temporarily
                    users_collection.update_one(
                        {"user_id": user_id},
                        {"$set": {"transfers_block": True}}
                    )
                    logger.warning(f"User {user_id} transfer blocked for frequency limit violation")
                    return jsonify({
                        "error": frequency_error,
                        "transfer_blocked": True
                    }), 429
    
    # Check if user is in transfer cooldown
    is_in_cooldown, seconds_remaining = check_transfer_cooldown(user_id)
    if is_in_cooldown:
        minutes_remaining = seconds_remaining // 60
        seconds = seconds_remaining % 60
        return jsonify({
            "error": f"Please wait {minutes_remaining}m {seconds}s before making another transfer",
            "in_cooldown": True,
            "seconds_remaining": seconds_remaining
        }), 429
    
    # Get transfer details from request
    data = request.json
    to_private_address = data.get('toAddress')
    amount = data.get('amount')
    verification_code = data.get('verificationCode')  # For 2FA verification
    secret_word = data.get('secretWord')  # For secret word verification
    transfer_password = data.get('transferPassword')  # For transfer password verification
    transfer_reason = data.get('transferReason')  # Get transfer reason
    
    # Validate input
    if not all([to_private_address, amount]):
        return jsonify({"error": "Missing required fields"}), 400
    
    # Validate transfer reason
    if not transfer_reason:
        return jsonify({"error": "Transfer reason is required"}), 400
    
    try:
        amount_float = float(amount)
        if amount_float <= 0:
            return jsonify({"error": "Amount must be greater than zero"}), 400
    except ValueError:
        return jsonify({"error": "Invalid amount format"}), 400
    
    # Get user with auth settings
    user = users_collection.find_one(
        {"user_id": user_id},
        {
            "transfer_auth": 1, 
            "2fa_activated": 1, 
            "2fa_secret": 1,
            "secret_word": 1,
            "transfer_password": 1,
            "_id": 0
        }
    )
    
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    # Get transfer authentication method settings with defaults
    transfer_auth = user.get("transfer_auth", {"password": False, "2fa": False, "secret_word": True})
    
    # Check authentication based on user's settings
    if transfer_auth.get("2fa", False):
        # Verify 2FA is enabled for this user
        has_2fa = user.get("2fa_activated", False)
        if not has_2fa:
            return jsonify({"error": "2FA is required but not set up for this account"}), 400
            
        # Check 2FA rate limit
        is_limited, attempts_remaining, seconds_remaining = check_2fa_rate_limit(user_id)
        if is_limited:
            return jsonify({
                "error": f"Rate limit exceeded. Try again in {seconds_remaining} seconds.",
                "requires_2fa": True,
                "rate_limited": True,
                "seconds_remaining": seconds_remaining
            }), 429
        
        # Validate the 2FA code
        if not verification_code:
            return jsonify({
                "error": "2FA code required", 
                "requires_2fa": True,
                "attempts_remaining": attempts_remaining
            }), 400
            
        # Verify the 2FA code
        is_valid = verify_2fa_code(user, verification_code)
        update_2fa_rate_limit(user_id, is_valid)
        
        if not is_valid:
            # Check attempts remaining after update
            _, attempts_remaining, _ = check_2fa_rate_limit(user_id)
            return jsonify({
                "error": "Invalid 2FA code", 
                "requires_2fa": True,
                "attempts_remaining": attempts_remaining
            }), 400
            
    elif transfer_auth.get("secret_word", False):
        # Verify the secret word was provided
        if not secret_word:
            return jsonify({
                "error": "Secret word required",
                "requires_secret_word": True
            }), 400
            
        # Verify the secret word
        stored_secret = user.get('secret_word')
        if not stored_secret or secret_word != stored_secret:
            return jsonify({
                "error": "Invalid secret word",
                "requires_secret_word": True
            }), 400
            
    elif transfer_auth.get("password", False):
        # Verify the transfer password was provided
        if not transfer_password:
            return jsonify({
                "error": "Transfer password required",
                "requires_transfer_password": True
            }), 400
            
        # Verify the transfer password
        stored_password = user.get('transfer_password')
        if not stored_password or transfer_password != stored_password:
            return jsonify({
                "error": "Invalid transfer password",
                "requires_transfer_password": True
            }), 400
    
    # Process the transfer
    result = process_transfer(user_id, to_private_address, amount, transfer_reason)
    
    if not result["success"]:
        return jsonify({"error": result["error"]}), 400
    
    return jsonify({"success": True, "transaction": result["transaction"]})

@transfers_bp.route('/api/transfers/tax-settings', methods=['GET'])
@token_required
def get_tax_settings_endpoint(user_id=None, **kwargs):
    """API endpoint to fetch tax settings from database"""
    # If user_id is None, fall back to session-based auth
    if user_id is None:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({"error": "Not authenticated"}), 401
    
    # Get tax settings
    settings = get_tax_settings()
    
    # Get user's premium status
    user = users_collection.find_one({"user_id": user_id})
    if user:
        is_premium = user.get("premium", False)
        membership = user.get("membership", "Standard")
    else:
        is_premium = False
        membership = "Standard"
    
    # Add premium info to the response
    settings["is_premium"] = is_premium
    settings["membership"] = membership
    
    # Return tax settings with premium info
    return jsonify(settings)

# Add a route to check if a user has 2FA enabled
@transfers_bp.route('/api/user/2fa-status', methods=['GET'])
@token_required
def get_2fa_status(user_id=None, **kwargs):
    """Check if the user has 2FA enabled"""
    # If user_id is None, fall back to session-based auth
    if user_id is None:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({"error": "Not authenticated"}), 401
    
    # Get the user record with only 2FA status
    user = users_collection.find_one(
        {"user_id": user_id},
        {"2fa_activated": 1, "_id": 0}
    )
    
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    # Return 2FA status
    return jsonify({
        "2fa_enabled": user.get("2fa_activated", False)
    })

# Add API endpoint to check cooldown status
@transfers_bp.route('/api/transfers/cooldown-status', methods=['GET'])
@token_required
def get_cooldown_status(user_id=None, **kwargs):
    """Get the current cooldown status for the authenticated user"""
    # If user_id is None, fall back to session-based auth
    if user_id is None:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({"error": "Not authenticated"}), 401
    
    # Check if user is in cooldown
    is_in_cooldown, seconds_remaining = check_transfer_cooldown(user_id)
    
    # Get cooldown settings
    settings = get_tax_settings()
    cooldown_minutes = settings.get("cooldown_minutes")
    
    # Get user info for premium status
    user = users_collection.find_one({"user_id": user_id})
    is_premium = user and user.get("premium", False)
    
    # Check premium benefits
    premium_benefits = {
        "has_premium": is_premium,
        "premium_enabled": settings.get("premium_enabled", False),
        "cooldown_reduction_enabled": False,
        "cooldown_reduction": 0,
        "no_cooldown": False
    }
    
    if is_premium and settings.get("premium_enabled", False):
        premium_settings = settings.get("premium_settings", {})
        premium_benefits["cooldown_reduction_enabled"] = premium_settings.get("cooldown_reduction_enabled", False)
        premium_benefits["cooldown_reduction"] = premium_settings.get("cooldown_reduction", 0)
        premium_benefits["no_cooldown"] = (
            premium_benefits["cooldown_reduction_enabled"] and 
            premium_benefits["cooldown_reduction"] == 0
        )
    
    return jsonify({
        "in_cooldown": is_in_cooldown,
        "seconds_remaining": seconds_remaining,
        "cooldown_minutes": cooldown_minutes,
        "premium_benefits": premium_benefits
    })

# Rating system API endpoints
@transfers_bp.route('/api/ratings/submit', methods=['POST'])
@token_required
def submit_rating(user_id=None, **kwargs):
    """Submit a rating for a user"""
    # If user_id is None, fall back to session-based auth
    if user_id is None:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({"error": "Not authenticated"}), 401
    
    # Use user_id as rater_id
    rater_id = user_id
    
    # Get rating details from request
    data = request.json
    recipient_id = data.get('recipient_id')
    stars = data.get('stars')
    comment = data.get('comment', "")  # Optional comment
    
    # Validate input
    if not recipient_id:
        return jsonify({"error": "Recipient ID is required"}), 400
    
    if not stars or not isinstance(stars, int) or stars < 1 or stars > 5:
        return jsonify({"error": "Rating must be between 1 and 5 stars"}), 400
    
    # Don't allow rating yourself
    if recipient_id == rater_id:
        return jsonify({"error": "You cannot rate yourself"}), 400
    
    # Validate comment length - maximum 300 characters
    MAX_COMMENT_LENGTH = 300
    if comment and len(comment) > MAX_COMMENT_LENGTH:
        return jsonify({"error": f"Comment cannot exceed {MAX_COMMENT_LENGTH} characters"}), 400
    
    # Update the rating
    result = update_user_rating(rater_id, recipient_id, stars, comment)
    
    if not result["success"]:
        return jsonify({"error": result["error"]}), 400
    
    return jsonify({"success": True})

@transfers_bp.route('/api/ratings/user/<recipient_id>', methods=['GET'])
@token_required
def get_user_rating(recipient_id, user_id=None, **kwargs):
    """Get the ratings for a specific user"""
    # If user_id is None, fall back to session-based auth
    if user_id is None:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({"error": "Not authenticated"}), 401
    
    # Use user_id as current_user_id
    current_user_id = user_id
    
    # Get the user's ratings
    user_rating_data = get_user_ratings(recipient_id)
    
    # Check if the current user has rated this user
    current_user_rating = ratings_collection.find_one({
        "rater_id": current_user_id,
        "recipient_id": recipient_id
    })
    
    # If the current user has rated, convert ObjectId to string
    if current_user_rating and "_id" in current_user_rating:
        current_user_rating["_id"] = str(current_user_rating["_id"])
    
    # Return the rating data
    return jsonify({
        "user_id": recipient_id,
        "total_ratings": user_rating_data.get("total_ratings", 0),
        "average_rating": user_rating_data.get("average_rating", 0),
        "rating_counts": user_rating_data.get("rating_counts", {
            "1": 0, "2": 0, "3": 0, "4": 0, "5": 0
        }),
        "current_user_rating": current_user_rating,
        "ratings": user_rating_data.get("ratings", [])
    })

# Add a new endpoint to toggle wallet lock status
@transfers_bp.route('/api/wallet/toggle-limit', methods=['POST'])
@token_required
def toggle_wallet_limit(user_id=None, **kwargs):
    """Toggle the wallet limit status for the authenticated user"""
    # If user_id is None, fall back to session-based auth
    if user_id is None:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({"error": "Not authenticated"}), 401
    
    # Get the user
    user = users_collection.find_one({"user_id": user_id})
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    # Toggle wallet_lock status
    current_status = user.get("wallet_lock", False)
    new_status = not current_status
    
    # Update the user record
    result = users_collection.update_one(
        {"user_id": user_id},
        {"$set": {"wallet_lock": new_status}}
    )
    
    if result.modified_count == 0:
        return jsonify({"error": "Failed to update limit status"}), 500
    
    # Get the updated limit info
    updated_limit_info = get_user_limit_info(user_id)
    
    return jsonify({
        "success": True,
        "limit_status": new_status,
        "limit_info": updated_limit_info
    })

# Add a new endpoint to check wallet frozen status
@transfers_bp.route('/api/wallet/frozen-status', methods=['GET'])
@token_required
def get_frozen_status(user_id=None, **kwargs):
    """Get the wallet frozen status for the authenticated user"""
    # If user_id is None, fall back to session-based auth
    if user_id is None:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({"error": "Not authenticated"}), 401
    
    # Get the user with only frozen status field
    user = users_collection.find_one(
        {"user_id": user_id},
        {"frozen": 1, "_id": 0}
    )
    
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    # Return frozen status
    is_frozen = user.get("frozen", False)
    return jsonify({
        "is_frozen": is_frozen
    })

# Add a new endpoint to toggle wallet frozen status
@transfers_bp.route('/api/wallet/toggle-frozen', methods=['POST'])
@token_required
def toggle_wallet_frozen(user_id=None, **kwargs):
    """Toggle the wallet frozen status for the authenticated user"""
    # If user_id is None, fall back to session-based auth
    if user_id is None:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({"error": "Not authenticated"}), 401
    
    # Get the user
    user = users_collection.find_one({"user_id": user_id})
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    # Toggle frozen status
    current_status = user.get("frozen", False)
    new_status = not current_status
    
    # Update the user record
    result = users_collection.update_one(
        {"user_id": user_id},
        {"$set": {"frozen": new_status}}
    )
    
    if result.modified_count == 0:
        return jsonify({"error": "Failed to update frozen status"}), 500
    
    return jsonify({
        "success": True,
        "is_frozen": new_status
    })

# Initialize MongoDB indexes
def create_indexes():
    """Create indexes to optimize database queries"""
    print("Creating MongoDB indexes for both storage approaches...")
    
    try:
        # First check existing indexes to avoid conflicts
        # Users collection indexes
        existing_users_indexes = list(users_collection.list_indexes())
        existing_users_index_names = [idx.get('name') for idx in existing_users_indexes]
        
        # Check if indexes already exist with any name before creating new ones
        has_user_id_index = any('user_id' in idx_name for idx_name in existing_users_index_names)
        has_private_address_index = any('private_address' in idx_name for idx_name in existing_users_index_names)
        has_public_address_index = any('public_address' in idx_name for idx_name in existing_users_index_names)
        
        # Create indexes with specific names only if they don't already exist
        if not has_user_id_index:
            users_collection.create_index("user_id", unique=True, name="transfers_user_id_idx", background=True)
            print("Created user_id index in users collection")
        else:
            print("User ID index already exists in users collection, skipping creation")
            
        if not has_private_address_index:
            users_collection.create_index("private_address", unique=True, name="transfers_private_address_idx", background=True)
            print("Created private_address index in users collection")
        else:
            print("Private address index already exists in users collection, skipping creation")
            
        if not has_public_address_index:
            users_collection.create_index("public_address", unique=True, name="transfers_public_address_idx", background=True)
            print("Created public_address index in users collection")
        else:
            print("Public address index already exists in users collection, skipping creation")
            
        # User transactions collection indexes (for both array and document-based)
        existing_txn_indexes = list(user_transactions_collection.list_indexes())
        existing_txn_index_names = [idx.get('name') for idx in existing_txn_indexes]
        
        # Indexes for array-based approach
        has_array_user_id_index = any('user_id' in idx_name for idx_name in existing_txn_index_names)
        has_array_tx_id_index = any('transactions.tx_id' in idx_name for idx_name in existing_txn_index_names)
        
        # Indexes for document-based approach
        has_doc_tx_id_index = any('tx_id' in idx_name and not 'transactions.tx_id' in idx_name for idx_name in existing_txn_index_names)
        has_doc_user_id_index = any('user_id' in idx_name for idx_name in existing_txn_index_names)
        has_doc_type_index = any('document_type' in idx_name for idx_name in existing_txn_index_names)
        has_timestamp_index = any('timestamp' in idx_name and not 'transactions.timestamp' in idx_name for idx_name in existing_txn_index_names)
        
        # Create indexes for array-based approach
        if not has_array_user_id_index:
            user_transactions_collection.create_index("user_id", name="txn_user_id_idx", background=True)
            print("Created user_id index in user_transactions collection")
        else:
            print("User ID index already exists in user_transactions collection, skipping creation")
            
        if not has_array_tx_id_index:
            user_transactions_collection.create_index("transactions.tx_id", name="txn_array_id_idx", background=True)
            print("Created transactions.tx_id index in user_transactions collection")
        else:
            print("Transaction ID index already exists in user_transactions collection, skipping creation")
            
        # Create indexes for document-based approach
        if not has_doc_tx_id_index:
            user_transactions_collection.create_index("tx_id", name="txn_doc_id_idx", background=True)
            print("Created tx_id index in user_transactions collection (for document transactions)")
        
        if not has_doc_user_id_index:
            user_transactions_collection.create_index([("user_id", 1), ("document_type", 1)], 
                                                  name="txn_doc_user_id_idx", background=True)
            print("Created compound user_id+document_type index in user_transactions collection")
            
        if not has_doc_type_index:
            user_transactions_collection.create_index("document_type", name="txn_doc_type_idx", background=True)
            print("Created document_type index in user_transactions collection")
            
        # Compound indexes for efficient querying
        user_transactions_collection.create_index([("user_id", 1), ("timestamp", -1), ("document_type", 1)], 
                                              name="txn_user_time_type_idx", background=True)
        print("Created user_id + timestamp + document_type index in user_transactions collection")
        
        user_transactions_collection.create_index([("tx_id", 1), ("user_id", 1), ("document_type", 1)], 
                                              name="txn_tx_user_type_idx", background=True)
        print("Created tx_id + user_id + document_type index in user_transactions collection")
            
        if not has_timestamp_index:
            user_transactions_collection.create_index("timestamp", name="txn_doc_timestamp_idx", background=True)
            print("Created timestamp index in user_transactions collection (for document transactions)")
        
        # Add index for type
        user_transactions_collection.create_index([("user_id", 1), ("type", 1), ("document_type", 1)], 
                                              name="txn_user_type_doc_idx", background=True)
        print("Created user_id + type + document_type index in user_transactions collection")
            
        # Ratings collection indexes
        existing_rating_indexes = list(ratings_collection.list_indexes())
        existing_rating_index_names = [idx.get('name') for idx in existing_rating_indexes]
        
        has_rating_user_id_index = any('user_id' in idx_name for idx_name in existing_rating_index_names)
        
        if not has_rating_user_id_index:
            ratings_collection.create_index("user_id", name="transfers_rating_user_id_idx", background=True)
            print("Created user_id index in ratings collection")
        else:
            print("User ID index already exists in ratings collection, skipping creation")
            
        # Rate limits collection indexes
        existing_rate_indexes = list(rate_limits_collection.list_indexes())
        existing_rate_index_names = [idx.get('name') for idx in existing_rate_indexes]
        
        has_rate_user_id_index = any('user_id' in idx_name for idx_name in existing_rate_index_names)
        has_rate_compound_index = any('user_id' in idx_name and 'rate_limits.limit_type' in idx_name for idx_name in existing_rate_index_names)
        
        if not has_rate_user_id_index:
            rate_limits_collection.create_index("user_id", name="transfers_rate_user_id_idx", background=True)
            print("Created user_id index in rate_limits collection")
        else:
            print("User ID index already exists in rate_limits collection, skipping creation")
            
        if not has_rate_compound_index:
            rate_limits_collection.create_index([("user_id", 1), ("rate_limits.limit_type", 1)], 
                                            name="transfers_rate_compound_idx", 
                                            background=True)
            print("Created compound index in rate_limits collection")
        else:
            print("Compound index already exists in rate_limits collection, skipping creation")
        
        print("MongoDB indexes created successfully")
            
        # Create indexes for ratings collections
        # Rating Stats collection indexes
        ratings_stats_indexes = list(user_rating_stats_collection.list_indexes())
        ratings_stats_index_names = [idx.get('name') for idx in ratings_stats_indexes]
        
        has_rating_stats_user_id_index = any('user_id' in idx_name for idx_name in ratings_stats_index_names)
        
        if not has_rating_stats_user_id_index:
            user_rating_stats_collection.create_index("user_id", unique=True, name="rating_stats_user_id_idx", background=True)
            print("Created user_id index in user_rating_stats collection")
            
        # Individual Ratings collection indexes
        ratings_indexes = list(ratings_collection.list_indexes())
        ratings_index_names = [idx.get('name') for idx in ratings_indexes]
        
        has_rating_recipient_id_index = any('recipient_id' in idx_name for idx_name in ratings_index_names)
        has_rating_rater_id_index = any('rater_id' in idx_name for idx_name in ratings_index_names)
        has_rating_compound_index = any('rater_id' in idx_name and 'recipient_id' in idx_name for idx_name in ratings_index_names)
        
        if not has_rating_recipient_id_index:
            ratings_collection.create_index("recipient_id", name="ratings_recipient_id_idx", background=True)
            print("Created recipient_id index in ratings collection")
            
        if not has_rating_rater_id_index:
            ratings_collection.create_index("rater_id", name="ratings_rater_id_idx", background=True)
            print("Created rater_id index in ratings collection")
            
        if not has_rating_compound_index:
            ratings_collection.create_index([("rater_id", 1), ("recipient_id", 1)], 
                                          name="ratings_rater_recipient_idx", 
                                          unique=True,
                                          background=True)
            print("Created compound rater_id+recipient_id index in ratings collection")
            
        # Add timestamp index for sorting
        ratings_collection.create_index([("recipient_id", 1), ("timestamp", -1)], 
                                      name="ratings_recipient_timestamp_idx", 
                                      background=True)
        print("Created recipient_id+timestamp index in ratings collection")
        
        # Rate limits collection indexes
        existing_rate_indexes = list(rate_limits_collection.list_indexes())
        existing_rate_index_names = [idx.get('name') for idx in existing_rate_indexes]
        
        has_rate_user_id_index = any('user_id' in idx_name for idx_name in existing_rate_index_names)
        has_rate_compound_index = any('user_id' in idx_name and 'rate_limits.limit_type' in idx_name for idx_name in existing_rate_index_names)
        
        if not has_rate_user_id_index:
            rate_limits_collection.create_index("user_id", name="transfers_rate_user_id_idx", background=True)
            print("Created user_id index in rate_limits collection")
        else:
            print("User ID index already exists in rate_limits collection, skipping creation")
            
        if not has_rate_compound_index:
            rate_limits_collection.create_index([("user_id", 1), ("rate_limits.limit_type", 1)], 
                                            name="transfers_rate_compound_idx", 
                                            background=True)
            print("Created compound index in rate_limits collection")
        else:
            print("Compound index already exists in rate_limits collection, skipping creation")
        
        print("MongoDB indexes created successfully")
            
        # Add specific indexes for transfer frequency protection
        rate_limits_collection.create_index([("user_id", 1), ("rate_limits.limit_type", 1), ("rate_limits.last_attempt", 1)], 
                                        name="transfers_frequency_idx", 
                                        background=True)
        print("Created transfer frequency index in rate_limits collection")
        
        # Add index for daily transfers to recipient
        rate_limits_collection.create_index([("user_id", 1), ("rate_limits.limit_type", 1), ("rate_limits.count", 1)], 
                                        name="transfers_daily_recipient_idx", 
                                        background=True)
        print("Created daily transfers to recipient index in rate_limits collection")
        
        print("MongoDB indexes created successfully")
            
    except Exception as e:
        print(f"Warning: Error checking/creating MongoDB indexes: {e}")
        print(f"Details: {str(e)}")
        # Continue even if index creation fails - they might already exist

# Initialize Blueprint
def init_app(app):
    """Initialize the transfers blueprint and create indexes"""
    app.register_blueprint(transfers_bp)
    
    # Create MongoDB indexes
    create_indexes()
    
    return app

# Add function to get paginated transactions from document-based approach
def get_user_sharded_transactions(user_id, page=1, limit=20):
    """
    Fetch user transactions with pagination from the document-based approach
    Returns transactions for the given user_id
    """
    # Calculate skip value for pagination
    skip = (page - 1) * limit
    
    # Query transactions for this user using the document_type approach
    transactions = list(user_transactions_collection.find(
        {
            "user_id": user_id,
            "document_type": "transaction"
        }
    ).sort("timestamp", -1).skip(skip).limit(limit))
    
    # Count total documents for pagination info
    total_count = user_transactions_collection.count_documents(
        {
            "user_id": user_id,
            "document_type": "transaction"
        }
    )
    
    # Calculate if there are more pages
    has_next = (skip + limit) < total_count
    has_prev = page > 1
    
    # Add transaction type based on user perspective
    for tx in transactions:
        if tx.get("sender_id") == user_id:
            tx["type"] = "sent"
        else:
            tx["type"] = "received"
        
        # Convert ObjectId to string if present
        if "_id" in tx and isinstance(tx["_id"], ObjectId):
            tx["_id"] = str(tx["_id"])
    
    return {
        "transactions": transactions,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total_count,
            "has_next": has_next,
            "has_prev": has_prev
        }
    }

# For standalone testing
if __name__ == '__main__':
    from flask import Flask
    app = Flask(__name__)
    app.secret_key = os.urandom(24)
    init_app(app)
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True) 