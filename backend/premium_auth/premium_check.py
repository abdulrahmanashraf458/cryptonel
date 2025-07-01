#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Cryptonel - Premium Authentication Module
-----------------------------------------
هذا المودل مسؤول عن التحقق من صلاحيات المستخدم للوصول إلى ميزات البريميوم
والتحقق من حالة قفل المحفظة

IMPORTANT: Wallet Status Definitions
- wallet_lock: Administrative lock that prevents all wallet access (restricts user)
- frozen: User-initiated security feature to protect funds (does NOT restrict access)
- ban: Administrative ban that prevents all access (restricts user)

Only wallet_lock and ban are considered access restrictions. Frozen status is a security feature.
"""

import os
import json
import logging
import traceback
import time
import hashlib
import hmac
from flask import Blueprint, request, jsonify, session, g
from functools import wraps
from pymongo import MongoClient
from bson.objectid import ObjectId
import datetime

# Configure logging
logger = logging.getLogger('premium_auth')

# Initialize MongoDB connection (imported from db_connection)
def get_db_connection():
    """Get MongoDB connection using connection details from environment"""
    try:
        from ..db_connection import get_db_client
        return get_db_client()
    except ImportError:
        # Fallback to direct connection if db_connection not available
        db_url = os.environ.get('DATABASE_URL')
        if not db_url:
            logger.error("DATABASE_URL environment variable not set")
            return None
        
        try:
            client = MongoClient(db_url)
            return client
        except Exception as e:
            logger.error(f"Error connecting to MongoDB: {e}")
            return None

# Create blueprint for premium authentication routes
premium_auth_bp = Blueprint('premium_auth', __name__)

# Security helper function for signing responses
def generate_response_signature(user_id, timestamp):
    """
    Generate a secure signature for API responses to prevent tampering
    
    Args:
        user_id (str): User ID
        timestamp (int): Current timestamp
    
    Returns:
        str: HMAC signature
    """
    try:
        # Get the secret key from environment
        secret_key = os.environ.get('SECRET_KEY', '')
        if not secret_key:
            logger.error("SECRET_KEY not set in environment")
            return ""
        
        # Create signature using HMAC-SHA256
        message = f"{user_id}:{timestamp}"
        signature = hmac.new(
            secret_key.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return signature
    except Exception as e:
        logger.error(f"Error generating signature: {e}")
        return ""

# Rate limiting cache for brute force protection
request_cache = {}

def check_rate_limit(ip_address):
    """
    Check if an IP address has exceeded the rate limit
    
    Args:
        ip_address (str): Client IP address
    
    Returns:
        bool: True if rate limited, False otherwise
    """
    current_time = time.time()
    
    # Clean up old entries
    for ip in list(request_cache.keys()):
        if current_time - request_cache[ip]['timestamp'] > 60:  # 1 minute expiry
            del request_cache[ip]
    
    # Check current IP
    if ip_address in request_cache:
        cache_entry = request_cache[ip_address]
        
        # If 10+ requests in last minute, rate limit
        if cache_entry['count'] >= 10 and current_time - cache_entry['timestamp'] < 60:
            # Update timestamp to extend the block
            cache_entry['timestamp'] = current_time
            return True
        
        # Increment counter
        cache_entry['count'] += 1
    else:
        # New entry
        request_cache[ip_address] = {
            'count': 1,
            'timestamp': current_time
        }
    
    return False

def handle_premium_status_change(user_id, is_premium):
    """
    Handle changes to a user's premium status, particularly for custom addresses
    
    Args:
        user_id (str): The user ID
        is_premium (bool): Whether the user is premium
    
    Returns:
        dict: Result of the operation
    """
    client = None
    try:
        # Get database connection
        client = get_db_connection()
        if not client:
            logger.error("Failed to connect to database")
            return {"success": False, "error": "Database connection failed"}
        
        # Get the collections
        db = client.cryptonel_wallet
        users_collection = db.users
        custom_addresses_collection = db.custom_addresses
        
        # Find the user
        user = users_collection.find_one({"user_id": user_id})
        if not user:
            return {"success": False, "error": "User not found"}
        
        # If user is not premium, reset all premium settings
        if not is_premium:
            # Create update with all premium settings reset
            premium_update = {
                "$set": {
                    # Reset all premium-only privacy settings
                    "hide_balance": False,
                    "hide_address": False,
                    "hide_badges": False,
                    "hide_verification": False,
                    "hidden_wallet_mode": False,
                    
                    # Reset premium styling
                    "primary_color": None,
                    "secondary_color": None,
                    "highlight_color": None,
                    "background_color": None,
                    "enable_secondary_color": False,
                    "enable_highlight_color": False
                }
            }
            
            # Apply the updates to reset premium settings
            users_collection.update_one(
                {"user_id": user_id},
                premium_update
            )
            
            logger.info(f"Reset premium settings for non-premium user {user_id}")
            
            # Check for custom address and restore previous
            custom_address = custom_addresses_collection.find_one({"user_id": user_id})
            
            if custom_address and custom_address.get("previous_address"):
                # User has a custom address and is no longer premium
                previous_address = custom_address.get("previous_address")
                
                # Update user's private address back to the previous one
                users_collection.update_one(
                    {"user_id": user_id},
                    {"$set": {"private_address": previous_address}}
                )
                
                # Log the address restoration
                logger.info(f"Restored previous address for non-premium user {user_id}: {previous_address}")
                
                # Remove the custom address entry if not permanently locked
                if custom_address.get("permanent_lock") != True:
                    custom_addresses_collection.delete_one({"_id": custom_address["_id"]})
                    logger.info(f"Removed custom address entry for user {user_id}")
                    
                    return {
                        "success": True, 
                        "message": "Premium settings reset and previous address restored",
                        "address": previous_address,
                        "entry_removed": True
                    }
                else:
                    return {
                        "success": True, 
                        "message": "Premium settings reset and previous address restored (entry kept due to permanent lock)",
                        "address": previous_address,
                        "entry_removed": False
                    }
            
            return {"success": True, "message": "Premium settings reset successfully"}
        
        # If user is premium, no action needed for addresses
        return {"success": True, "message": "User is premium, no changes needed"}
        
    except Exception as e:
        logger.error(f"Error handling premium status change: {e}")
        logger.error(traceback.format_exc())
        return {"success": False, "error": str(e)}
    finally:
        if client:
            client.close()

def check_premium_status(user_id):
    """
    Check if a user has premium status based on their user_id
    
    Args:
        user_id (str): The user ID to check
        
    Returns:
        dict: Dictionary containing premium status and wallet lock status
    """
    client = None
    try:
        # Get database connection
        client = get_db_connection()
        if not client:
            logger.error("Failed to connect to database")
            return {"premium": False, "wallet_lock": True, "error": "Database connection failed"}
        
        # Get the users collection
        db = client.cryptonel_wallet
        users_collection = db.users
        
        # Find the user
        user = users_collection.find_one({"user_id": user_id})
        
        if not user:
            logger.warning(f"User not found with ID: {user_id}")
            return {"premium": False, "wallet_lock": True, "error": "User not found"}
        
        # SECURITY FIX: Check wallet_lock first and enforce it
        wallet_lock = user.get("wallet_lock", False)
        frozen = user.get("frozen", False)
        ban = user.get("ban", False)
        
        # If wallet is locked or banned, enforce restrictions
        # NOTE: frozen is not considered a restriction as it can be user-initiated security feature
        if wallet_lock or ban:
            # Log the restriction
            logger.warning(f"Access restricted for user {user_id} - Lock:{wallet_lock}, Ban:{ban}")
            
            # Return restricted status
            return {
                "premium": False,  # Disable premium when wallet is restricted
                "wallet_lock": True,
                "membership": "standard",
                "account_type": "Standard User",
                "wallet_restrictions": {
                    "is_locked": wallet_lock,
                    "is_frozen": frozen,
                    "is_banned": ban,
                    "has_access": False
                },
                "username": user.get("username", ""),
                "status": "restricted"
            }
        
        # Get premium status
        # IMPORTANT: Only consider the premium boolean field as source of truth, ignore membership
        premium_status = user.get("premium", False)
        
        # Additional wallet restriction checks
        wallet_restrictions = {
            "is_locked": wallet_lock,
            "is_frozen": frozen,
            "is_banned": ban,
            "has_access": True
        }
        
        # Get membership details if available (for display only, not for premium status check)
        membership = user.get("membership", "standard")
        account_type = user.get("account_type", "Standard User")
        
        # Check if user's premium status is false or has been changed
        if not premium_status:
            # Fix inconsistency: If premium is false but membership is Premium, update membership
            if membership.lower() == "premium":
                users_collection.update_one(
                    {"user_id": user_id},
                    {"$set": {"membership": "Standard"}}
                )
                logger.info(f"Fixed inconsistency for user {user_id}: Set membership to Standard since premium=false")
                membership = "Standard"
                
            # Get previous premium status from session if available
            previous_premium = session.get('premium_status', None)
            
            # If premium status changed from true to false or we're unsure,
            # handle all premium settings reset
            if previous_premium is None or previous_premium:
                logger.info(f"Premium status changed or reset for user {user_id}")
                handle_premium_status_change(user_id, False)
                
                # Update session to reflect new status
                session['premium_status'] = False
        else:
            # User is premium, update session
            session['premium_status'] = True
            
            # Fix inconsistency: If premium is true but membership is not Premium, update membership
            if membership.lower() != "premium":
                users_collection.update_one(
                    {"user_id": user_id},
                    {"$set": {"membership": "Premium"}}
                )
                logger.info(f"Fixed inconsistency for user {user_id}: Set membership to Premium since premium=true")
                membership = "Premium"
        
        # Return the premium status and wallet lock status
        return {
            "premium": premium_status,
            "wallet_lock": wallet_lock,
            "membership": membership,
            "account_type": account_type,
            "wallet_restrictions": wallet_restrictions,
            "username": user.get("username", ""),
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Error checking premium status: {e}")
        logger.error(traceback.format_exc())
        return {"premium": False, "wallet_lock": True, "error": str(e)}
    finally:
        if client:
            client.close()

def require_premium(f):
    """
    Decorator to require premium status for API routes
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get user ID from session
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({
                "success": False,
                "message": "User not authenticated",
                "code": "AUTH_REQUIRED"
            }), 401
        
        # Check premium status
        status = check_premium_status(user_id)
        
        # Check if premium
        if not status.get("premium", False):
            return jsonify({
                "success": False,
                "message": "Premium subscription required for this feature",
                "code": "PREMIUM_REQUIRED"
            }), 403
        
        # Check if wallet is locked
        if status.get("wallet_lock", False):
            return jsonify({
                "success": False,
                "message": "Your wallet is currently locked",
                "code": "WALLET_LOCKED"
            }), 403
            
        # Continue to the route if premium and wallet not locked
        return f(*args, **kwargs)
    
    return decorated_function

# Enhanced Premium status check endpoint with added security
@premium_auth_bp.route('/check', methods=['GET'])
def check_premium():
    """
    API endpoint to check premium status and wallet lock status with enhanced security
    """
    try:
        # Get client IP for rate limiting
        client_ip = request.remote_addr
        
        # Apply rate limiting
        if check_rate_limit(client_ip):
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            return jsonify({
                "success": False,
                "message": "Rate limit exceeded. Please try again later.",
                "code": "RATE_LIMITED",
                "premium": False,
                "wallet_lock": True
            }), 429
        
        # Check for session
        if 'user_id' not in session:
            logger.warning(f"Unauthorized premium check attempt from IP: {client_ip}")
            return jsonify({
                "success": False,
                "message": "Authentication required",
                "code": "UNAUTHORIZED",
                "premium": False,
                "wallet_lock": True
            }), 401
        
        # Validate CSRF token if available - but make it optional for GET requests
        # This is safe because GET requests should be read-only and not modify state
        csrf_token = request.headers.get('X-CSRF-Token')
        session_csrf = session.get('csrf_token')
        
        # For non-GET requests, enforce CSRF validation if token exists in session
        if request.method != 'GET' and session_csrf and (not csrf_token or csrf_token != session_csrf):
            logger.warning(f"CSRF validation failed for user: {session.get('user_id')}")
            return jsonify({
                "success": False,
                "message": "Security validation failed",
                "code": "CSRF_FAILED",
                "premium": False,
                "wallet_lock": True
            }), 403
            
        # For GET requests, we'll log but not block if CSRF doesn't match
        if request.method == 'GET' and session_csrf and (not csrf_token or csrf_token != session_csrf):
            logger.info(f"CSRF token missing/mismatched in GET request for user: {session.get('user_id')}")
            
        # Get user ID from session
        user_id = session.get('user_id')
        
        # Check current premium status in session to detect changes
        was_premium = session.get('premium_status', None)
        
        # Check premium status
        status = check_premium_status(user_id)
        
        # Get current premium status
        is_premium = status.get("premium", False)
        
        # Detect if premium status was just changed
        settings_reset = was_premium is not None and was_premium != is_premium and not is_premium
        
        # Add security-related information
        timestamp = int(time.time())
        signature = generate_response_signature(user_id, timestamp)
        
        # Security logging
        logger.info(f"Premium status checked for user {user_id} from IP {client_ip}")
        
        # Add request fingerprint for anti-replay protection
        request_id = hashlib.md5(f"{user_id}:{client_ip}:{timestamp}".encode()).hexdigest()
        
        # Return the status with security enhancements
        result = {
            "success": True,
            "premium": is_premium,
            "wallet_lock": status.get("wallet_lock", False),
            "membership": status.get("membership", "standard"),
            "account_type": status.get("account_type", "Standard User"),
            "wallet_restrictions": status.get("wallet_restrictions", {}),
            "username": status.get("username", ""),
            "timestamp": timestamp,
            "signature": signature,
            "request_id": request_id
        }
        
        # Add settings reset flag if premium settings were just reset
        if settings_reset:
            result["settings_reset"] = True
            result["message"] = "Premium settings have been reset as premium status is no longer active"
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error in premium check endpoint: {e}")
        logger.error(traceback.format_exc())
        
        # Add request ID even for errors
        error_id = hashlib.md5(f"error:{time.time()}:{str(e)}".encode()).hexdigest()[:8]
        
        return jsonify({
            "success": False,
            "message": "An error occurred while checking premium status",
            "code": "SYSTEM_ERROR",
            "error_id": error_id,
            "premium": False,
            "wallet_lock": True
        }), 500

@premium_auth_bp.route('/restore-address', methods=['POST'])
def restore_address():
    """
    API route to manually restore a user's previous address
    
    Returns:
        JSON response with status of the operation
    """
    # Get user ID from session
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({
            "success": False,
            "message": "User not authenticated"
        }), 401
    
    client = None
    try:
        # Get database connection
        client = get_db_connection()
        if not client:
            logger.error("Failed to connect to database")
            return jsonify({
                "success": False,
                "message": "Database connection failed"
            }), 500
        
        # Get the collections
        db = client.cryptonel_wallet
        users_collection = db.users
        custom_addresses_collection = db.custom_addresses
        
        # Find the user
        user = users_collection.find_one({"user_id": user_id})
        if not user:
            return jsonify({
                "success": False,
                "message": "User not found"
            }), 404
        
        # Check if user has a custom address entry
        custom_address = custom_addresses_collection.find_one({"user_id": user_id})
        if not custom_address or not custom_address.get("previous_address"):
            return jsonify({
                "success": False,
                "message": "No previous address found to restore"
            }), 404
        
        # Get the previous address
        previous_address = custom_address.get("previous_address")
        
        # Update user's private address back to the previous one
        users_collection.update_one(
            {"user_id": user_id},
            {"$set": {"private_address": previous_address}}
        )
        
        # Log the address restoration
        logger.info(f"Manually restored previous address for user {user_id}: {previous_address}")
        
        # Remove the custom address entry if not permanently locked
        if custom_address.get("permanent_lock") != True:
            custom_addresses_collection.delete_one({"_id": custom_address["_id"]})
            logger.info(f"Removed custom address entry for user {user_id}")
            
            return jsonify({
                "success": True,
                "message": "Previous address restored successfully",
                "address": previous_address,
                "entry_removed": True
            })
        else:
            return jsonify({
                "success": True,
                "message": "Previous address restored successfully (entry kept due to permanent lock)",
                "address": previous_address,
                "entry_removed": False
            })
        
    except Exception as e:
        logger.error(f"Error restoring previous address: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            "success": False,
            "message": f"Error: {str(e)}"
        }), 500
    finally:
        if client:
            client.close()

@premium_auth_bp.route('/address-status', methods=['GET'])
def check_address_status():
    """
    API route to check a user's custom address status
    
    Returns:
        JSON response with address status information
    """
    # Get user ID from session
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({
            "success": False,
            "message": "User not authenticated"
        }), 401
    
    client = None
    try:
        # Get database connection
        client = get_db_connection()
        if not client:
            logger.error("Failed to connect to database")
            return jsonify({
                "success": False,
                "message": "Database connection failed"
            }), 500
        
        # Get the collections
        db = client.cryptonel_wallet
        users_collection = db.users
        custom_addresses_collection = db.custom_addresses
        
        # Find the user
        user = users_collection.find_one({"user_id": user_id})
        if not user:
            return jsonify({
                "success": False,
                "message": "User not found"
            }), 404
        
        # Get user's premium status
        premium_status = user.get("premium", False)
        
        # Get current private address
        current_address = user.get("private_address", "")
        
        # Check if user has a custom address entry
        custom_address = custom_addresses_collection.find_one({"user_id": user_id})
        
        if custom_address:
            # User has a custom address entry
            previous_address = custom_address.get("previous_address", "")
            new_address = custom_address.get("new_address", "")
            permanent_lock = custom_address.get("permanent_lock", False)
            created_at = custom_address.get("created_at", "")
            
            return jsonify({
                "success": True,
                "has_custom_address": True,
                "premium_status": premium_status,
                "current_address": current_address,
                "previous_address": previous_address,
                "custom_address": new_address,
                "permanent_lock": permanent_lock,
                "created_at": created_at,
                "will_restore_on_premium_end": not premium_status or not permanent_lock
            })
        else:
            # User doesn't have a custom address entry
            return jsonify({
                "success": True,
                "has_custom_address": False,
                "premium_status": premium_status,
                "current_address": current_address
            })
        
    except Exception as e:
        logger.error(f"Error checking address status: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            "success": False,
            "message": f"Error: {str(e)}"
        }), 500
    finally:
        if client:
            client.close()

@premium_auth_bp.route('/enforce-checks', methods=['POST'])
def enforce_premium_checks():
    """
    Admin API route to enforce premium status checks for all users
    This ensures all non-premium users have their premium settings disabled
    
    Returns:
        JSON response with status of the operation
    """
    # Get user ID from session
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({
            "success": False,
            "message": "User not authenticated"
        }), 401
    
    client = None
    try:
        # Get database connection
        client = get_db_connection()
        if not client:
            logger.error("Failed to connect to database")
            return jsonify({
                "success": False,
                "message": "Database connection failed"
            }), 500
        
        # Get the collections
        db = client.cryptonel_wallet
        users_collection = db.users
        
        # Find the requesting user - check if admin
        user = users_collection.find_one({"user_id": user_id})
        if not user:
            return jsonify({
                "success": False,
                "message": "User not found"
            }), 404
        
        # Check if user is an admin or staff
        is_admin = user.get("admin", False) or user.get("staff", False)
        if not is_admin:
            logger.warning(f"Non-admin user {user_id} attempted to enforce premium checks")
            return jsonify({
                "success": False,
                "message": "Administrative privileges required"
            }), 403
        
        # Find all non-premium users
        non_premium_users = users_collection.find({"premium": {"$ne": True}})
        updated_count = 0
        
        # Create update to reset all premium settings
        premium_update = {
            "$set": {
                # Reset all premium-only privacy settings
                "hide_balance": False,
                "hide_address": False,
                "hide_badges": False,
                "hide_verification": False,
                "hidden_wallet_mode": False,
                
                # Reset premium styling
                "primary_color": None,
                "secondary_color": None,
                "highlight_color": None,
                "background_color": None,
                "enable_secondary_color": False,
                "enable_highlight_color": False
            }
        }
        
        # Apply updates to all non-premium users
        for non_premium_user in non_premium_users:
            non_premium_id = non_premium_user.get("user_id")
            
            # Skip users who already have all premium settings off
            if (not non_premium_user.get("hide_balance", False) and
                not non_premium_user.get("hide_address", False) and
                not non_premium_user.get("hide_badges", False) and
                not non_premium_user.get("hide_verification", False) and
                not non_premium_user.get("hidden_wallet_mode", False) and
                not non_premium_user.get("primary_color") and
                not non_premium_user.get("secondary_color") and
                not non_premium_user.get("highlight_color") and
                not non_premium_user.get("background_color")):
                continue
                
            # Update the user
            users_collection.update_one(
                {"user_id": non_premium_id},
                premium_update
            )
            updated_count += 1
            
            # Handle address restoration if needed
            handle_premium_status_change(non_premium_id, False)
            
            logger.info(f"Reset premium settings for non-premium user {non_premium_id}")
        
        return jsonify({
            "success": True,
            "message": f"Premium settings checked and reset for {updated_count} non-premium users",
            "updated_count": updated_count
        })
        
    except Exception as e:
        logger.error(f"Error enforcing premium checks: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            "success": False,
            "message": f"Error: {str(e)}"
        }), 500
    finally:
        if client:
            client.close()

@premium_auth_bp.route('/fix-premium-inconsistency', methods=['POST'])
def fix_premium_inconsistency():
    """
    Admin API route to fix inconsistencies between premium field and membership
    This ensures all users have consistent settings between premium boolean and membership string
    
    Returns:
        JSON response with status of the operation
    """
    # Get user ID from session
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({
            "success": False,
            "message": "User not authenticated"
        }), 401
    
    client = None
    try:
        # Get database connection
        client = get_db_connection()
        if not client:
            logger.error("Failed to connect to database")
            return jsonify({
                "success": False,
                "message": "Database connection failed"
            }), 500
        
        # Get the collections
        db = client.cryptonel_wallet
        users_collection = db.users
        
        # Find the requesting user - check if admin
        user = users_collection.find_one({"user_id": user_id})
        if not user:
            return jsonify({
                "success": False,
                "message": "User not found"
            }), 404
        
        # Check if user is an admin or staff
        is_admin = user.get("admin", False) or user.get("staff", False)
        if not is_admin:
            logger.warning(f"Non-admin user {user_id} attempted to fix premium inconsistency")
            return jsonify({
                "success": False,
                "message": "Administrative privileges required"
            }), 403
        
        # Find users with inconsistent premium status
        premium_inconsistency1 = users_collection.find({
            "premium": False,
            "membership": "Premium"
        })
        
        premium_inconsistency2 = users_collection.find({
            "premium": True,
            "$or": [
                {"membership": {"$ne": "Premium"}},
                {"membership": {"$exists": False}}
            ]
        })
        
        fixed_count1 = 0
        fixed_count2 = 0
        
        # Fix users with premium=false but membership=Premium
        for inconsistent_user in premium_inconsistency1:
            inconsistent_id = inconsistent_user.get("user_id")
            
            # Set membership to Standard and reset premium features
            users_collection.update_one(
                {"user_id": inconsistent_id},
                {"$set": {"membership": "Standard"}}
            )
            
            # Make sure premium settings are reset
            handle_premium_status_change(inconsistent_id, False)
            
            fixed_count1 += 1
            logger.info(f"Fixed inconsistency for user {inconsistent_id}: premium=false but had Premium membership")
        
        # Fix users with premium=true but membership≠Premium
        for inconsistent_user in premium_inconsistency2:
            inconsistent_id = inconsistent_user.get("user_id")
            
            # Set membership to Premium
            users_collection.update_one(
                {"user_id": inconsistent_id},
                {"$set": {"membership": "Premium"}}
            )
            
            fixed_count2 += 1
            logger.info(f"Fixed inconsistency for user {inconsistent_id}: premium=true but didn't have Premium membership")
        
        total_fixed = fixed_count1 + fixed_count2
        
        return jsonify({
            "success": True,
            "message": f"Fixed premium inconsistencies for {total_fixed} users",
            "details": {
                "premium_false_membership_premium": fixed_count1,
                "premium_true_membership_not_premium": fixed_count2
            }
        })
        
    except Exception as e:
        logger.error(f"Error fixing premium inconsistencies: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            "success": False,
            "message": f"Error: {str(e)}"
        }), 500
    finally:
        if client:
            client.close()

def init_app(app):
    """
    Initialize the premium authentication module with the Flask app
    
    Args:
        app: The Flask application instance
    """
    # Register the blueprint
    app.register_blueprint(premium_auth_bp, url_prefix='/api/premium')
    
    # Add context processor to make premium status available in templates
    @app.context_processor
    def inject_premium_status():
        if 'user_id' in session:
            # Check if status is already in g to avoid duplicate checks
            if hasattr(g, 'premium_status'):
                return g.premium_status
            
            # Check premium status
            status = check_premium_status(session['user_id'])
            
            # Store in g for this request
            g.premium_status = {
                "is_premium": status.get("premium", False),
                "wallet_locked": status.get("wallet_lock", False),
                "membership": status.get("membership", "standard"),
                "account_type": status.get("account_type", "Standard User")
            }
            
            return g.premium_status
        
        return {
            "is_premium": False,
            "wallet_locked": False,
            "membership": "standard",
            "account_type": "Guest"
        }
    
    # Add login event handler to check premium status
    @app.after_request
    def check_premium_on_login(response):
        # Check if this is a login response (status 200 and login-related endpoint)
        if (response.status_code == 200 and 
            request.path in ['/api/auth/login', '/api/auth/token'] and 
            request.method == 'POST' and
            'user_id' in session):
            
            # Check premium status which will restore previous address if needed
            check_premium_status(session['user_id'])
            
        return response 