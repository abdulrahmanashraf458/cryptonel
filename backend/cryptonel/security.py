import os
import json
import random
import string
import pyotp
import qrcode
import io
import base64
import time
import re
import requests
from flask import Blueprint, jsonify, request, session
from pymongo import MongoClient
from dotenv import load_dotenv
import datetime
from bson.objectid import ObjectId
import traceback
import logging

# Import session devices functions 
try:
    from backend.cryptonel.session_devices import get_user_devices
except ImportError:
    # Fallback if module is not available yet
    get_user_devices = None

# Load environment variables
load_dotenv()

# Create Blueprint for Security endpoints
security_bp = Blueprint('security', __name__)

# MongoDB connection
MONGODB_URI = os.getenv("DATABASE_URL")
client = MongoClient(MONGODB_URI)
db = client["cryptonel_wallet"]
users_collection = db["users"]
security_logs_collection = db["security_logs"]
device_sessions_collection = db["device_sessions"]

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Helper functions
def get_user_data(user_id):
    """Fetch user data from MongoDB by user_id"""
    user = users_collection.find_one({"user_id": user_id})
    return user

def update_user_security(user_id, update_data):
    """Update user security settings in MongoDB"""
    result = users_collection.update_one(
        {"user_id": user_id},
        {"$set": update_data}
    )
    # Consider both modified and matched count for success
    # This handles cases where data hasn't actually changed
    return result.modified_count > 0 or result.matched_count > 0

def update_security_timestamp(user_id, update_type):
    """Update the user's security settings timestamp and type."""
    timestamp = datetime.datetime.utcnow().isoformat() + "Z"
    
    users_collection.update_one(
        {"user_id": user_id},
        {"$set": {
            "security.lastUpdate": timestamp,
            "security.updateType": update_type
        }}
    )
    
    # Also log this security activity
    security_logs_collection.insert_one({
        "user_id": user_id,
        "timestamp": timestamp,
        "update_type": update_type,
        "ip_address": request.remote_addr
    })
    
    return timestamp, update_type

def generate_unique_secret():
    """Generate a unique 2FA secret key"""
    while True:
        # Generate a random base32 secret compatible with TOTP standards
        secret = pyotp.random_base32()
        
        # Check if this secret already exists in the database
        existing_user = users_collection.find_one({"2fa_secret": secret})
        if not existing_user:
            return secret

def generate_backup_codes():
    """Generate 8 unique backup codes"""
    codes = []
    for _ in range(8):
        # Generate a random 12-character string for each backup code
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))
        # Format as XXXX-XXXX-XXXX
        formatted_code = f"{code[:4]}-{code[4:8]}-{code[8:]}"
        codes.append(formatted_code)
    return codes

def generate_qr_code(secret, username):
    """Generate QR code for 2FA setup"""
    # Format secret for proper TOTP use
    secret = secret.replace(" ", "").upper()
    
    # Create the provisioning URI manually to ensure correct format
    provisioning_uri = f"otpauth://totp/Cryptonel:{username}?secret={secret}&issuer=Cryptonel"
    
    # Generate QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=20,
        border=4,
    )
    qr.add_data(provisioning_uri)
    qr.make(fit=True)
    
    # Create an in-memory bytes stream
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer)
    
    # Convert to base64 for embedding in HTML
    qr_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    return f"data:image/png;base64,{qr_base64}"

def verify_2fa_code(secret, code):
    """Verify a 2FA code against the secret"""
    # Ensure secret is formatted correctly
    secret = secret.replace(" ", "").upper()
    
    # Create TOTP object and verify
    totp = pyotp.TOTP(secret)
    
    # Get current time
    current_time = int(time.time())
    
    # First try with a tight window for maximum security
    if totp.verify(code, valid_window=2):
        return True
        
    # If failed, check if it's a clock skew issue by checking previous and next codes
    expected_totp = totp.at(current_time)
    prev_totp = totp.at(current_time - 30)
    next_totp = totp.at(current_time + 30)
    
    # Log the debug info (can be disabled in production)
    print(f"DEBUG: User provided: {code}, Expected: {expected_totp}, Previous: {prev_totp}, Next: {next_totp}, Timestamp: {current_time}")
    
    # For slightly out-of-sync clocks, try with a slightly larger window as fallback
    # valid_window=4 allows for 2 minutes each way (4 periods of 30 seconds)
    # This balances security with usability for users with clock sync issues
    return totp.verify(code, valid_window=4)

def calculate_security_score(user_data):
    """Calculate the security score for a user based on their security settings"""
    base_score = 40  # Lower base security score to allow for more granular points
    
    # Check security features and add points - 2FA highest priority
    if user_data.get('2fa_activated', False):
        base_score += 25  # +25 for having 2FA enabled (increased from 20)
    
    # Transfer Password is second highest priority
    if user_data.get('transfer_password') is not None:
        base_score += 15  # +15 for having transfer password enabled (increased from 10)
    
    # Daily limit is lower priority
    if user_data.get('wallet_limit') is not None:
        base_score += 7  # +7 for having daily limit enabled (increased from 5)
    
    # Wallet frozen is lowest priority but still valuable
    if user_data.get('frozen', False):
        base_score += 5  # +5 for having wallet frozen
    
    # Check transfer authentication method (most secure to least secure)
    transfer_auth = user_data.get('transfer_auth', {"password": False, "2fa": False, "secret_word": True})
    
    if transfer_auth.get('2fa', False):
        base_score += 20  # +20 for using 2FA as transfer auth method (increased from 15)
    elif transfer_auth.get('password', False):
        base_score += 12  # +12 for using transfer password as auth method (increased from 8)
    # No additional points for secret word (least secure)

    # Check login authentication method (most secure to least secure)
    login_auth = user_data.get('login_auth', {"none": True, "2fa": False, "secret_word": False})
    
    if login_auth.get('2fa', False):
        base_score += 20  # +20 for using 2FA as login auth method (increased from 15)
    elif login_auth.get('secret_word', False):
        base_score += 12  # +12 for using secret word as login auth method (increased from 8)
    # No additional points for none (least secure)
    
    # New security features
    # Time-based access
    if user_data.get('time_based_access', {}).get('enabled', False):
        base_score += 8  # +8 for having time-based access enabled
    
    # Geo-lock
    if user_data.get('geo_lock', {}).get('enabled', False):
        base_score += 10  # +10 for having geo-lock enabled
    
    # IP whitelist
    if user_data.get('ip_whitelist', {}).get('enabled', False):
        ip_count = len(user_data.get('ip_whitelist', {}).get('ips', []))
        if ip_count == 1:
            base_score += 12  # +12 for having a single whitelisted IP (very secure)
        elif ip_count > 1:
            base_score += 8  # +8 for having multiple whitelisted IPs (less secure but still good)
    
    # Cap score at 100
    return min(base_score, 100)

# Routes
@security_bp.route('/api/security/settings', methods=['GET'])
def get_security_settings():
    """Get security settings and information for the user"""
    # Check if user is authenticated
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Not authenticated"}), 401
    
    # Get user data
    user_data = users_collection.find_one({"user_id": user_id})
    if not user_data:
        return jsonify({"error": "User not found"}), 404
    
    # Check if user is premium and disable premium features if not
    is_premium = user_data.get('premium', False)
    settings_reset = False
    
    if not is_premium:
        # Check if any premium features are enabled
        premium_features_enabled = (
            user_data.get('time_based_access', {}).get('enabled', False) or
            user_data.get('geo_lock', {}).get('enabled', False) or
            user_data.get('ip_whitelist', {}).get('enabled', False)
        )
        
        # If any premium features are enabled, disable them
        if premium_features_enabled:
            update_data = {
                "time_based_access": {
                    "enabled": False,
                    "start_time": "07:00",
                    "end_time": "19:00",
                    "timezone": "UTC"
                },
                "geo_lock": {
                    "enabled": False,
                    "countries": [],
                    "country_details": []
                },
                "ip_whitelist": {
                    "enabled": False,
                    "ips": [],
                    "ip_details": []
                }
            }
            
            # Update user data to disable premium features
            update_user_security(user_id, update_data)
            update_security_timestamp(user_id, "Premium Features Disabled - Not Premium")
            settings_reset = True
            
            # Refresh user data
            user_data = users_collection.find_one({"user_id": user_id})
    
    # Get the number of active sessions from device_sessions collection
    active_sessions_count = get_active_sessions_count(user_id)
    
    # Calculate security alerts based on enabled premium features
    security_alerts = 0
    security_features = []
    
    # Only show alerts for premium users with inactive features
    if user_data.get('premium', False):
        # Check each premium security feature
        if not user_data.get('time_based_access', {}).get('enabled', False):
            security_alerts += 1
            security_features.append("Time-Based Access")
            
        if not user_data.get('geo_lock', {}).get('enabled', False):
            security_alerts += 1
            security_features.append("Geo-Lock")
            
        if not user_data.get('ip_whitelist', {}).get('enabled', False):
            security_alerts += 1
            security_features.append("IP Whitelist")
    
    # Get most recent security update from security logs
    last_update = security_logs_collection.find_one(
        {"user_id": user_id},
        sort=[("timestamp", -1)]
    )
    
    # Create response with all security information
    security_settings = {
        "twoFAEnabled": user_data.get('2fa_activated', False),
        "twoFASecret": user_data.get('2fa_secret', "") if user_data.get('2fa_activated', False) else "",
        "transferPasswordEnabled": bool(user_data.get('transfer_password')),
        "secretWordEnabled": user_data.get('transfer_auth', {}).get('secret_word', False),
        "dailyLimitEnabled": user_data.get('wallet_limit') is not None,
        "dailyLimit": user_data.get('wallet_limit', 100),
        "walletFrozen": user_data.get('frozen', False),
        "loginSecretWordEnabled": user_data.get('login_auth', {}).get('secret_word', False),
        "login2FAEnabled": user_data.get('login_auth', {}).get('2fa', False),
        
        # Time-based access
        "timeBasedAccessEnabled": user_data.get('time_based_access', {}).get('enabled', False),
        "timeBasedAccessStart": user_data.get('time_based_access', {}).get('start_time', "09:00"),
        "timeBasedAccessEnd": user_data.get('time_based_access', {}).get('end_time', "17:00"),
        "timeBasedAccessTimezone": user_data.get('time_based_access', {}).get('timezone', "UTC"),
        
        # Auto sign-in settings
        "autoSignInEnabled": user_data.get('auto_signin', {}).get('enabled', False),
        "autoSignInDuration": user_data.get('auto_signin', {}).get('duration', 20),
        
        # Geo-lock settings
        "geoLockEnabled": user_data.get('geo_lock', {}).get('enabled', False),
        "geoLockCountry": user_data.get('geo_lock', {}).get('country', ""),
        "geoLockCountries": user_data.get('geo_lock', {}).get('countries', []),
        "geoLockCountryDetails": user_data.get('geo_lock', {}).get('country_details', []),
        
        # IP whitelist settings
        "ipWhitelistEnabled": user_data.get('ip_whitelist', {}).get('enabled', False),
        "ipWhitelist": user_data.get('ip_whitelist', {}).get('ips', []),
        
        # Security update information
        "lastUpdate": user_data.get('security', {}).get('lastUpdate', "") or (last_update.get('timestamp') if last_update else ""),
        "updateType": user_data.get('security', {}).get('updateType', "") or (last_update.get('update_type') if last_update else ""), 
        
        # Login information
        "lastLogin": user_data.get('last_login', ""),
        "lastLoginIp": user_data.get('last_login_ip', ""),
        "lastLoginLocation": user_data.get('last_login_location', ""),
        "deviceInfo": user_data.get('last_device_info', ""),
        
        # Status information
        "activeSessions": active_sessions_count,
        "alerts": security_alerts,
        "premium": user_data.get('premium', False),
        "settings_reset": settings_reset,
    }
    
    # Add auth method objects in format expected by frontend
    # Create transfer_auth_method object for frontend
    transfer_auth_method = {
        "password": user_data.get('transfer_auth', {}).get('password', True),
        "2fa": user_data.get('transfer_auth', {}).get('2fa', False),
        "secret_word": user_data.get('transfer_auth', {}).get('secret_word', False)
    }
    security_settings["transferAuthMethod"] = transfer_auth_method
    
    # Create login_auth_method object for frontend
    login_auth_method = {
        "none": user_data.get('login_auth', {}).get('none', True),
        "2fa": user_data.get('login_auth', {}).get('2fa', False),
        "secret_word": user_data.get('login_auth', {}).get('secret_word', False)
    }
    security_settings["loginAuthMethod"] = login_auth_method
    
    # Create the response with cache control headers
    response = jsonify(security_settings)
    
    # Add cache control headers to prevent caching
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    
    return response

@security_bp.route('/api/security/2fa/setup', methods=['GET'])
def setup_2fa():
    """Initialize 2FA setup by generating a secret and QR code"""
    # Check if user is authenticated
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Not authenticated"}), 401
    
    # Get user data from MongoDB
    user_data = get_user_data(user_id)
    if not user_data:
        return jsonify({"error": "User not found"}), 404
    
    # Generate a new secret
    secret = generate_unique_secret()
    
    # Update user data with the new secret (but don't activate 2FA yet)
    update_success = update_user_security(user_id, {"2fa_secret": secret})
    if not update_success:
        return jsonify({"error": "Failed to update user data"}), 500
    
    # Generate QR code
    qr_code = generate_qr_code(secret, user_data.get("username", "User"))
    
    # Return data for setup
    return jsonify({
        "secret": secret,
        "qrCode": qr_code
    })

@security_bp.route('/api/security/2fa/verify', methods=['POST'])
def verify_and_enable_2fa():
    """Verify 2FA setup and enable it"""
    # Check if user is authenticated
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Not authenticated"}), 401
    
    # Get user data from MongoDB
    user_data = get_user_data(user_id)
    if not user_data:
        return jsonify({"error": "User not found"}), 404
    
    # Get the verification code from request
    data = request.json
    if not data or 'code' not in data:
        return jsonify({"error": "Verification code is required"}), 400
    
    code = data.get('code')
    secret = user_data.get('2fa_secret')
    
    if not secret:
        return jsonify({"error": "2FA setup has not been initiated"}), 400
    
    # Get additional security parameters
    timestamp = data.get('timestamp')
    client_code_hash = data.get('codeHash')
    challenge = data.get('challenge')
    
    # Verify timestamp is recent (within last 5 minutes) if provided
    if timestamp:
        current_time = int(time.time() * 1000)  # Convert to milliseconds
        if abs(current_time - timestamp) > 300000:  # 5 minutes
            return jsonify({"error": "Verification request expired"}), 401
    
    # Verify the code - use strict verification with no return of is_valid flag
    is_valid = verify_2fa_code(secret, code)
    
    # Verify challenge if provided (should be base64 encoded reversed code)
    if is_valid and challenge:
        try:
            expected_challenge = base64.b64encode(code[::-1].encode()).decode()
            if challenge != expected_challenge:
                is_valid = False
                print(f"Challenge verification failed. Expected: {expected_challenge}, Got: {challenge}")
        except Exception as e:
            print(f"Error verifying challenge: {str(e)}")
    
    # Verify code hash if provided
    if is_valid and code and timestamp and client_code_hash:
        try:
            import hashlib
            
            # Recreate the hash on server side
            server_hash_input = f"{code}-{timestamp}"
            server_hash = hashlib.sha256(server_hash_input.encode()).hexdigest()
            
            # Compare with client hash
            if server_hash != client_code_hash:
                is_valid = False
                print(f"Hash verification failed. Expected: {server_hash}, Got: {client_code_hash}")
        except Exception as e:
            print(f"Error verifying hash: {str(e)}")
    
    if not is_valid:
        # For failed verification, respond with 401 Unauthorized
        return jsonify({"error": "Invalid verification code"}), 401
    
    # Generate backup codes
    backup_codes = generate_backup_codes()
    
    # Enable 2FA and store backup codes
    update_success = update_user_security(user_id, {
        "2fa_activated": True,
        "backup_codes": backup_codes
    })
    
    if not update_success:
        return jsonify({"error": "Failed to enable 2FA"}), 500
    
    # Update last security timestamp
    update_security_timestamp(user_id, "2FA Enabled")
    
    # Store 2FA verification success in session
    session["2fa_verified"] = True
    session["2fa_verified_timestamp"] = time.time()
    
    # Generate a verification token for future operations
    verification_token = base64.b64encode(os.urandom(32)).decode()
    
    # Return success with backup codes
    return jsonify({
        "message": "Two-factor authentication enabled successfully",
        "backupCodes": backup_codes,
        "verification_token": verification_token
    }), 200

@security_bp.route('/api/security/2fa/backup-codes', methods=['POST'])
def get_backup_codes():
    """Get 2FA backup codes with security verification"""
    # Check if user is authenticated
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Not authenticated"}), 401
    
    # Get user data from MongoDB
    user_data = get_user_data(user_id)
    if not user_data:
        return jsonify({"error": "User not found"}), 404
    
    # Check if 2FA is enabled
    if not user_data.get('2fa_activated', False):
        return jsonify({"error": "Two-factor authentication is not enabled"}), 400
    
    # Get the secret word from request
    data = request.json
    if not data or 'secretWord' not in data:
        return jsonify({"error": "Secret word is required"}), 400
    
    # Verify secret word
    secret_word = data.get('secretWord')
    stored_secret_word = user_data.get('secret_word')
    
    if secret_word != stored_secret_word:
        return jsonify({"error": "Invalid secret word"}), 401
    
    # Return backup codes
    backup_codes = user_data.get('backup_codes', [])
    return jsonify({"backupCodes": backup_codes})

@security_bp.route('/api/security/2fa/disable', methods=['POST'])
def disable_2fa():
    """Disable 2FA with verification"""
    # Check if user is authenticated
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Not authenticated"}), 401
    
    # Get user data from MongoDB
    user_data = get_user_data(user_id)
    if not user_data:
        return jsonify({"error": "User not found"}), 404
    
    # Check if 2FA is enabled
    if not user_data.get('2fa_activated', False):
        return jsonify({"error": "Two-factor authentication is not enabled"}), 400
    
    # Get verification data from request
    data = request.json
    if not data or ('code' not in data and 'backupCode' not in data):
        return jsonify({"error": "Verification code or backup code is required"}), 400
    
    # Get additional security parameters
    timestamp = data.get('timestamp')
    client_code_hash = data.get('codeHash')
    challenge = data.get('challenge')
    
    # Verify timestamp is recent (within last 5 minutes)
    if timestamp:
        current_time = int(time.time() * 1000)  # Convert to milliseconds
        if abs(current_time - timestamp) > 300000:  # 5 minutes
            return jsonify({"error": "Verification request expired"}), 401
    
    is_valid = False
    verification_code = None
    
    # Check if using app code
    if 'code' in data:
        verification_code = data.get('code')
        secret = user_data.get('2fa_secret')
        is_valid = verify_2fa_code(secret, verification_code)
        
        # Verify challenge if provided (should be base64 encoded reversed code)
        if is_valid and challenge:
            expected_challenge = base64.b64encode(verification_code[::-1].encode()).decode()
            if challenge != expected_challenge:
                is_valid = False
                print(f"Challenge verification failed. Expected: {expected_challenge}, Got: {challenge}")
    
    # Check if using backup code
    elif 'backupCode' in data:
        verification_code = data.get('backupCode')
        backup_codes = user_data.get('backup_codes', [])
        is_valid = verification_code in backup_codes
        
        # Verify challenge if provided (should be base64 encoded reversed code)
        if is_valid and challenge:
            expected_challenge = base64.b64encode(verification_code[::-1].encode()).decode()
            if challenge != expected_challenge:
                is_valid = False
                print(f"Challenge verification failed. Expected: {expected_challenge}, Got: {challenge}")
    
    # Verify code hash if provided
    if is_valid and verification_code and timestamp and client_code_hash:
        import hashlib
        
        # Recreate the hash on server side
        server_hash_input = f"{verification_code}-{timestamp}"
        server_hash = hashlib.sha256(server_hash_input.encode()).hexdigest()
        
        # Compare with client hash
        if server_hash != client_code_hash:
            is_valid = False
            print(f"Hash verification failed. Expected: {server_hash}, Got: {client_code_hash}")
    
    # Use proper HTTP status codes instead of is_valid flag
    if not is_valid:
        return jsonify({"error": "Invalid verification code or backup code"}), 401
    
    # Check if the user is using 2FA as transfer authentication method
    transfer_auth = user_data.get('transfer_auth', {"password": False, "2fa": False, "secret_word": True})
    
    update_data = {
        "2fa_activated": False,
        "backup_codes": []
    }
    
    # If user was using 2FA for transfers, switch to another method
    if transfer_auth.get('2fa', False):
        # Check if transfer password is enabled
        has_transfer_password = user_data.get('transfer_password') is not None
        
        if has_transfer_password:
            # Switch to transfer password
            update_data["transfer_auth"] = {
                "password": True,
                "2fa": False,
                "secret_word": False
            }
        else:
            # Switch to security password
            update_data["transfer_auth"] = {
                "password": False,
                "2fa": False,
                "secret_word": True
            }
    
    # Disable 2FA
    update_success = update_user_security(user_id, update_data)
    
    if not update_success:
        return jsonify({"error": "Failed to disable 2FA"}), 500
    
    # Update last security timestamp
    update_security_timestamp(user_id, "2FA Disabled")
    
    # Clear any 2FA session variables
    if "2fa_verified" in session:
        session.pop("2fa_verified")
    if "2fa_verified_timestamp" in session:
        session.pop("2fa_verified_timestamp")
    
    # Generate a verification token for future operations
    verification_token = base64.b64encode(os.urandom(32)).decode()
    
    return jsonify({
        "message": "Two-factor authentication disabled successfully",
        "transfer_auth_updated": transfer_auth.get('2fa', False),
        "verification_token": verification_token
    }), 200

@security_bp.route('/api/security/transfer-password', methods=['POST'])
def set_transfer_password():
    """Set or update transfer password"""
    # Check if user is authenticated
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Not authenticated"}), 401
    
    # Get user data from MongoDB
    user_data = get_user_data(user_id)
    if not user_data:
        return jsonify({"error": "User not found"}), 404
    
    # Get request data
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    # Check if enabling or disabling
    is_disabling = data.get('isDisabling', False)
    
    if is_disabling:
        # Verify wallet password for disabling
        wallet_password = data.get('walletPassword')
        if not wallet_password:
            return jsonify({"error": "Wallet password is required"}), 400
        
        # Check if password matches
        stored_password = user_data.get('password', '')
        if wallet_password != stored_password:
            return jsonify({"error": "Invalid wallet password"}), 401
        
        # Check if the user is using Transfer Password as authentication method
        transfer_auth = user_data.get('transfer_auth', {"password": False, "2fa": False, "secret_word": True})
        
        update_data = {
            "transfer_password": None
        }
        
        # If user was using Transfer Password for transfers, switch to another method
        if transfer_auth.get('password', False):
            # Check if 2FA is enabled
            has_2fa = user_data.get('2fa_activated', False)
            
            if has_2fa:
                # Switch to 2FA
                update_data["transfer_auth"] = {
                    "password": False,
                    "2fa": True,
                    "secret_word": False
                }
            else:
                # Switch to security password
                update_data["transfer_auth"] = {
                    "password": False,
                    "2fa": False,
                    "secret_word": True
                }
        
        # Disable transfer password
        update_success = update_user_security(user_id, update_data)
        if not update_success:
            return jsonify({"error": "Failed to update security settings"}), 500
        
        # Update last security timestamp
        update_security_timestamp(user_id, "Transfer Password Disabled")
        
        return jsonify({
            "message": "Transfer password disabled successfully", 
            "enabled": False,
            "transfer_auth_updated": transfer_auth.get('password', False)
        })
    else:
        # Enabling transfer password
        new_password = data.get('transferPassword')
        if not new_password:
            return jsonify({"error": "New transfer password is required"}), 400
            
        # Check if this is the string "null" - this is different from actual null
        if new_password == "null":
            return jsonify({"error": "Invalid transfer password format"}), 400
        
        # Validate the transfer password with strict requirements
        if len(new_password) < 8:
            return jsonify({"error": "Password must be at least 8 characters (16+ recommended for better security)"}), 400
        
        # Check for required character types
        has_uppercase = any(c.isupper() for c in new_password)
        has_lowercase = any(c.islower() for c in new_password)
        has_digit = any(c.isdigit() for c in new_password)
        has_special = any(c in "!@#$%^&*()_-+=<>?/[]{}" for c in new_password)
        
        # Create a specific error message based on what's missing
        missing = []
        if not has_uppercase:
            missing.append("uppercase letter")
        if not has_lowercase:
            missing.append("lowercase letter")
        if not has_digit:
            missing.append("number")
        if not has_special:
            missing.append("special character (!@#$%^&*()_-+=<>?/[]{})")
        
        if missing:
            error_message = "Password must include at least one " + ", one ".join(missing)
            return jsonify({"error": error_message}), 400
        
        # Create update data - set transfer password and also enable it as auth method
        update_data = {
        # Store password directly (no hashing)
            "transfer_password": new_password,
            # Automatically enable transfer password as the auth method
            "transfer_auth": {
                "password": True,  # Enable transfer password auth
                "2fa": False,
                "secret_word": False
            }
        }
        
        # Store password and update auth method
        update_success = update_user_security(user_id, update_data)
        if not update_success:
            return jsonify({"error": "Failed to update security settings"}), 500
        
        # Update last security timestamp
        update_security_timestamp(user_id, "Transfer Password Enabled")
        
        return jsonify({
            "message": "Transfer password set successfully", 
            "enabled": True,
            "transfer_auth_method": "password"
        })

@security_bp.route('/api/security/daily-limit', methods=['POST'])
def set_daily_limit():
    """Set or remove daily transfer limit"""
    # Check if user is authenticated
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Not authenticated"}), 401
    
    # Get user data from MongoDB
    user_data = get_user_data(user_id)
    if not user_data:
        return jsonify({"error": "User not found"}), 404
    
    # Get request data
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    # Check if enabling or disabling
    is_disabling = data.get('isDisabling', False)
    
    if is_disabling:
        # Verify wallet password for disabling
        wallet_password = data.get('walletPassword')
        if not wallet_password:
            return jsonify({"error": "Wallet password is required"}), 400
        
        # Check if password matches
        stored_password = user_data.get('password', '')
        if wallet_password != stored_password:
            return jsonify({"error": "Invalid wallet password"}), 401
        
        # Remove daily limit
        update_success = update_user_security(user_id, {"wallet_limit": None})
        if not update_success:
            return jsonify({"error": "Failed to update security settings"}), 500
        
        # Update last security timestamp
        update_security_timestamp(user_id, "Daily Limit Removed")
        
        return jsonify({"message": "Daily limit removed successfully", "enabled": False})
    else:
        # Enabling daily limit
        daily_limit = data.get('dailyLimit')
        if daily_limit is None or daily_limit <= 0:
            return jsonify({"error": "Valid daily limit is required"}), 400
        
        # Update user data
        update_success = update_user_security(user_id, {"wallet_limit": daily_limit})
        if not update_success:
            return jsonify({"error": "Failed to update security settings"}), 500
        
        # Update last security timestamp
        update_security_timestamp(user_id, "Daily Limit Set")
        
        return jsonify({"message": "Daily limit set successfully", "enabled": True, "limit": daily_limit})

@security_bp.route('/api/security/freeze-wallet', methods=['POST'])
def toggle_wallet_freeze():
    """Freeze or unfreeze wallet"""
    # Check if user is authenticated
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Not authenticated"}), 401
    
    # Get user data from MongoDB
    user_data = get_user_data(user_id)
    if not user_data:
        return jsonify({"error": "User not found"}), 404
    
    # Get request data
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    # Check current freeze status
    current_frozen = user_data.get('frozen', False)
    action = data.get('action')
    
    if action == 'unfreeze' and current_frozen:
        # Verify wallet password for unfreezing
        wallet_password = data.get('walletPassword')
        if not wallet_password:
            return jsonify({"error": "Wallet password is required"}), 400
        
        # Check if password matches
        stored_password = user_data.get('password', '')
        if wallet_password != stored_password:
            return jsonify({"error": "Invalid wallet password"}), 401
        
        # Unfreeze wallet
        update_success = update_user_security(user_id, {"frozen": False})
        if not update_success:
            return jsonify({"error": "Failed to update security settings"}), 500
        
        # Update last security timestamp
        update_security_timestamp(user_id, "Wallet Unfrozen")
        
        return jsonify({"message": "Wallet unfrozen successfully", "frozen": False})
    elif action == 'freeze' and not current_frozen:
        # Freeze wallet (no password verification needed)
        update_success = update_user_security(user_id, {"frozen": True})
        if not update_success:
            return jsonify({"error": "Failed to update security settings"}), 500
        
        # Update last security timestamp
        update_security_timestamp(user_id, "Wallet Frozen")
        
        return jsonify({"message": "Wallet frozen successfully", "frozen": True})
    else:
        return jsonify({"error": "Invalid action or wallet already in requested state"}), 400

@security_bp.route('/api/security/transfer-auth-method', methods=['POST'])
def set_transfer_auth_method():
    """Set the authentication method used for transfers"""
    # Check if user is authenticated
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Not authenticated"}), 401
    
    # Get user data from MongoDB
    user_data = get_user_data(user_id)
    if not user_data:
        return jsonify({"error": "User not found"}), 404
    
    # Get request data
    data = request.json
    if not data or 'method' not in data:
        return jsonify({"error": "Method is required"}), 400
    
    # Get the selected method
    method = data.get('method')
    
    # Validate the method
    valid_methods = ['password', '2fa', 'secret_word']
    if method not in valid_methods:
        return jsonify({"error": "Invalid method"}), 400
    
    # Check if 2FA is enabled when selecting that method
    if method == '2fa' and not user_data.get('2fa_activated', False):
        return jsonify({"error": "2FA must be enabled to use this method"}), 400
    
    # Check if Transfer Password is enabled when selecting that method
    if method == 'password' and not user_data.get('transfer_password'):
        return jsonify({"error": "Transfer Password must be enabled to use this method"}), 400
    
    # Get current transfer auth method
    current_transfer_auth = user_data.get('transfer_auth', {"password": False, "2fa": False, "secret_word": True})
    
    # Check if the requested method is already active
    is_already_selected = (
        (method == 'password' and current_transfer_auth.get('password', False)) or
        (method == '2fa' and current_transfer_auth.get('2fa', False)) or
        (method == 'secret_word' and current_transfer_auth.get('secret_word', False))
    )
    
    if is_already_selected:
        # Return success without making DB changes
        # Calculate security score with current settings
        security_score = calculate_security_score(user_data)
        return jsonify({
            "method": method,
            "transferAuthMethod": current_transfer_auth,
            "securityScore": security_score,
            "message": "No changes made - selected method is already active"
        })
    
    # Create transfer_auth object with all methods, and only the selected method set to true
    transfer_auth = {
        "password": method == "password",
        "2fa": method == "2fa",
        "secret_word": method == "secret_word"
    }
    
    # Update user data
    update_success = update_user_security(user_id, {"transfer_auth": transfer_auth})
    if not update_success:
        return jsonify({"error": "Failed to update transfer authentication method"}), 500
    
    # Update last security timestamp
    update_security_timestamp(user_id, f"Transfer Auth Changed to {method}")
    
    # Calculate new security score with updated method
    user_data['transfer_auth'] = transfer_auth
    security_score = calculate_security_score(user_data)
    
    # Calculate security points change
    old_score = calculate_security_score({**user_data, 'transfer_auth': current_transfer_auth})
    score_change = security_score - old_score
    
    # Get score impact message
    impact_message = ""
    if method == '2fa':
        impact_message = "Maximum security! Using 2FA for transfers adds 20 points to your security score."
    elif method == 'password':
        impact_message = "Good choice! Using Transfer Password adds 12 points to your security score."
    else:  # secret_word
        impact_message = "Basic security. Consider using 2FA or Transfer Password for better protection."
    
    return jsonify({
        "method": method,
        "transferAuthMethod": transfer_auth,
        "securityScore": security_score,
        "scoreChange": score_change,
        "impactMessage": impact_message,
        "message": f"Transfer authentication method set to {method} successfully"
    })

@security_bp.route('/api/security/login-auth-method', methods=['POST'])
def set_login_auth_method():
    """Set the authentication method used for login"""
    # Check if user is authenticated
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Not authenticated"}), 401
    
    # Get user data from MongoDB
    user_data = get_user_data(user_id)
    if not user_data:
        return jsonify({"error": "User not found"}), 404
    
    # Get request data
    data = request.json
    if not data or 'method' not in data:
        return jsonify({"error": "Method is required"}), 400
    
    # Get the selected method
    method = data.get('method')
    
    # Validate the method
    valid_methods = ['none', '2fa', 'secret_word']
    if method not in valid_methods:
        return jsonify({"error": "Invalid method"}), 400
    
    # Check if 2FA is enabled when selecting that method
    if method == '2fa' and not user_data.get('2fa_activated', False):
        return jsonify({"error": "2FA must be enabled to use this method"}), 400
    
    # Get current login auth method
    current_login_auth = user_data.get('login_auth', {"none": True, "2fa": False, "secret_word": False})
    
    # Check if the requested method is already active
    is_already_selected = (
        (method == 'none' and current_login_auth.get('none', True)) or
        (method == '2fa' and current_login_auth.get('2fa', False)) or
        (method == 'secret_word' and current_login_auth.get('secret_word', False))
    )
    
    if is_already_selected:
        # Return success without making DB changes
        # Calculate security score with current settings
        security_score = calculate_security_score(user_data)
        return jsonify({
            "method": method,
            "loginAuthMethod": current_login_auth,
            "securityScore": security_score,
            "message": "No changes made - selected method is already active"
        })
    
    # Create login_auth object with all methods, and only the selected method set to true
    login_auth = {
        "none": method == "none",
        "2fa": method == "2fa",
        "secret_word": method == "secret_word"
    }
    
    # Update user data
    update_success = update_user_security(user_id, {"login_auth": login_auth})
    if not update_success:
        return jsonify({"error": "Failed to update login authentication method"}), 500
    
    # Update last security timestamp
    update_security_timestamp(user_id, f"Login Auth Changed to {method}")
    
    # Calculate new security score with updated method
    user_data['login_auth'] = login_auth
    security_score = calculate_security_score(user_data)
    
    # Calculate security points change
    old_score = calculate_security_score({**user_data, 'login_auth': current_login_auth})
    score_change = security_score - old_score
    
    # Get score impact message
    impact_message = ""
    if method == '2fa':
        impact_message = "Maximum security! Using 2FA for login adds 20 points to your security score."
    elif method == 'secret_word':
        impact_message = "Good choice! Using Secret Word adds 12 points to your security score."
    else:  # none
        impact_message = "Basic security. Consider using 2FA or Secret Word for better protection."
    
    return jsonify({
        "method": method,
        "loginAuthMethod": login_auth,
        "securityScore": security_score,
        "scoreChange": score_change,
        "impactMessage": impact_message,
        "message": f"Login authentication method set to {method} successfully"
    })

@security_bp.route('/api/security/change-password', methods=['POST'])
def change_wallet_password():
    """Change the wallet password for the authenticated user"""
    # Check if user is authenticated
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Not authenticated"}), 401
    
    # Get user data from MongoDB
    user_data = get_user_data(user_id)
    if not user_data:
        return jsonify({"error": "User not found"}), 404
    
    # Get data from request
    data = request.json
    if not data or 'currentPassword' not in data or 'newPassword' not in data:
        return jsonify({"error": "Current password and new password are required"}), 400
    
    current_password = data.get('currentPassword')
    new_password = data.get('newPassword')
    
    # Verify current password
    if user_data.get('password') != current_password:
        return jsonify({"error": "Current password is incorrect"}), 401
    
    # Validate the new password with strict requirements
    if not new_password:
        return jsonify({"error": "Password cannot be empty"}), 400
        
    # Check minimum length
    if len(new_password) < 8:
        return jsonify({"error": "Password must be at least 8 characters (16+ recommended for better security)"}), 400
    
    # Check for required character types
    has_uppercase = any(c.isupper() for c in new_password)
    has_lowercase = any(c.islower() for c in new_password)
    has_digit = any(c.isdigit() for c in new_password)
    has_special = any(c in "!@#$%^&*()_-+=<>?/[]{}" for c in new_password)
    
    # Create a specific error message based on what's missing
    missing = []
    if not has_uppercase:
        missing.append("uppercase letter")
    if not has_lowercase:
        missing.append("lowercase letter")
    if not has_digit:
        missing.append("number")
    if not has_special:
        missing.append("special character (!@#$%^&*()_-+=<>?/[]{})")
    
    if missing:
        error_message = "Password must include at least one " + ", one ".join(missing)
        return jsonify({"error": error_message}), 400
    
    # Update the password in the database
    update_success = update_user_security(user_id, {"password": new_password})
    if not update_success:
        return jsonify({"error": "Failed to update password"}), 500
    
    # Update last security timestamp
    update_security_timestamp(user_id, "Password Changed")
    
    return jsonify({"message": "Password changed successfully"})

@security_bp.route('/api/security/delete-account', methods=['POST'])
def delete_account():
    """Delete user account and all associated data"""
    # Check if user is authenticated
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Not authenticated"}), 401
    
    # Get user data from MongoDB
    user_data = get_user_data(user_id)
    if not user_data:
        return jsonify({"error": "User not found"}), 404
    
    # Get data from request
    data = request.json
    if not data or 'mnemonic_phrase' not in data:
        return jsonify({"error": "Mnemonic phrase is required"}), 400
    
    submitted_mnemonic = data.get('mnemonic_phrase')
    stored_mnemonic = user_data.get('mnemonic_phrase')
    
    # Check if this is verify-only mode
    verify_only = data.get('verify_only', False)
    
    # Verify mnemonic phrase
    if submitted_mnemonic != stored_mnemonic:
        return jsonify({"error": "Invalid mnemonic phrase"}), 401
    
    # If verify_only is True, just return success without deleting
    if verify_only:
        return jsonify({"message": "Mnemonic phrase verified successfully"})
    
    try:
        # Delete user data from all collections
        users_collection.delete_one({"user_id": user_id})
        
        # Delete from user_ratings collection
        db["user_ratings"].delete_many({"user_id": user_id})
        
        # Delete from user_transactions collection
        db["user_transactions"].delete_many({"user_id": user_id})
        
        # Clear session
        session.clear()
        
        return jsonify({"message": "Account deleted successfully"})
    
    except Exception as e:
        print(f"Error deleting account: {e}")
        return jsonify({"error": "Failed to delete account"}), 500

@security_bp.route('/api/security/time-based-access', methods=['POST'])
def set_time_based_access():
    """Set time-based access restrictions for the wallet"""
    # Check if user is authenticated
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Not authenticated"}), 401
    
    # Get user data
    user_data = get_user_data(user_id)
    if not user_data:
        return jsonify({"error": "User not found"}), 404
        
    # Check if user is premium
    if not user_data.get('premium', False):
        # Force disable this premium feature for non-premium users
        update_data = {
            "time_based_access": {
                "enabled": False,
                "start_time": "07:00",
                "end_time": "19:00",
                "timezone": "UTC"
            }
        }
        update_user_security(user_id, update_data)
        update_security_timestamp(user_id, "Premium Feature Disabled - Not Premium")
        return jsonify({"error": "This feature is only available for premium users", "disabled": True}), 403
    
    # Get data from request
    data = request.json
    if not data:
        return jsonify({"error": "Invalid request"}), 400
    
    enabled = data.get('enabled', False)
    
    # If disabling, completely update the time_based_access object
    if not enabled:
        update_data = {
            "time_based_access": {
                "enabled": False,
                "start_time": "07:00",
                "end_time": "19:00",
                "timezone": "UTC"
            }
        }
    else:
        # Validate time range
        start_time = data.get('start_time')
        end_time = data.get('end_time')
        timezone = data.get('timezone', 'UTC')  # Get user's timezone, default to UTC
        
        if not start_time or not end_time:
            return jsonify({"error": "Start time and end time are required"}), 400
        
        # Validate time format (HH:MM) - 24-hour format
        time_format = re.compile(r"^([0-1][0-9]|2[0-3]):([0-5][0-9])$")
        if not time_format.match(start_time) or not time_format.match(end_time):
            return jsonify({"error": "Invalid time format. Use HH:MM (24-hour format)"}), 400
            
        update_data = {
            "time_based_access": {
                "enabled": True,
                "start_time": start_time,
                "end_time": end_time,
                "timezone": timezone
            }
        }
    
    # Update user data
    update_success = update_user_security(user_id, update_data)
    if not update_success:
        return jsonify({"error": "Failed to update time-based access settings"}), 500
    
    # Update security timestamp with appropriate message
    if enabled:
        update_security_timestamp(user_id, "Time-based Access Enabled")
    else:
        update_security_timestamp(user_id, "Time-based Access Disabled")
    
    return jsonify({"message": "Time-based access settings updated successfully"})

@security_bp.route('/api/security/geo-lock', methods=['POST'])
def set_geo_lock():
    """Set geo-based restrictions for the wallet"""
    # Check if user is authenticated
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Not authenticated"}), 401
    
    # Get user data
    user_data = get_user_data(user_id)
    if not user_data:
        return jsonify({"error": "User not found"}), 404
        
    # Check if user is premium
    if not user_data.get('premium', False):
        # Force disable this premium feature for non-premium users
        update_data = {
            "geo_lock": {
                "enabled": False,
                "countries": [],
                "country_details": []
            }
        }
        update_user_security(user_id, update_data)
        update_security_timestamp(user_id, "Premium Feature Disabled - Not Premium")
        return jsonify({"error": "This feature is only available for premium users", "disabled": True}), 403
    
    # Get data from request
    data = request.json
    if not data:
        return jsonify({"error": "Invalid request"}), 400
    
    enabled = data.get('enabled', False)
    
    # If disabling, completely update the geo_lock object
    if not enabled:
        update_data = {
            "geo_lock": {
                "enabled": False,
                "countries": [],
                "country_details": []
            }
        }
    else:
        # Get countries and details
        if 'country' in data:  # Old single-country format for backward compatibility
            country = data.get('country')
            coordinates = data.get('coordinates', {"lat": 0, "lng": 0})
            
            if not country:
                return jsonify({"error": "Country is required"}), 400
                
            # Convert to new multi-country format
            countries = [country]
            country_details = [{
                "country_code": country,
                "country_name": data.get('country_name', ''),
                "coordinates": coordinates
            }]
        else:  # New multi-country format
            countries = data.get('countries', [])
            country_details = data.get('country_details', [])
            
            if not countries or not isinstance(countries, list) or len(countries) == 0:
                return jsonify({"error": "At least one country is required"}), 400
            
            # Make sure we have details for all countries
            country_details_map = {detail.get('country_code'): detail for detail in country_details if isinstance(detail, dict)}
            for code in countries:
                if code not in country_details_map:
                    # Create basic details for countries that don't have them
                    country_details.append({
                        "country_code": code,
                        "country_name": code,
                        "coordinates": {"lat": 0, "lng": 0}
                    })
        
        update_data = {
            "geo_lock": {
                "enabled": True,
                "countries": countries,
                "country_details": country_details
            }
        }
    
    # Update user data
    update_success = update_user_security(user_id, update_data)
    if not update_success:
        return jsonify({"error": "Failed to update geo-lock settings"}), 500
    
    # Update security timestamp with appropriate message
    if enabled:
        update_security_timestamp(user_id, "Geo-lock Enabled")
    else:
        update_security_timestamp(user_id, "Geo-lock Disabled")
    
    return jsonify({"message": "Geo-lock settings updated successfully"})

# API endpoint to add a country to geo-lock
@security_bp.route('/api/security/geo-lock/add-country', methods=['POST'])
def add_country_to_geolock():
    """Add a country to geo-lock allowed countries"""
    # Check if user is authenticated
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Not authenticated"}), 401
    
    # Get user data
    user_data = get_user_data(user_id)
    if not user_data:
        return jsonify({"error": "User not found"}), 404
        
    # Check if user is premium
    if not user_data.get('premium', False):
        return jsonify({"error": "This feature is only available for premium users"}), 403
    
    # Get data from request
    data = request.json
    if not data:
        return jsonify({"error": "Invalid request"}), 400
    
    country_code = data.get('country_code')
    country_name = data.get('country_name', '')
    coordinates = data.get('coordinates', {"lat": 0, "lng": 0})
    
    if not country_code:
        return jsonify({"error": "Country code is required"}), 400
    
    # Get current geo_lock settings
    current_geo_lock = user_data.get('geo_lock', {
        "enabled": False,
        "countries": [],
        "country_details": []
    })
    
    # Check if we need to migrate from old format
    if 'country' in current_geo_lock and current_geo_lock.get('country'):
        # Migrate from old format to new format
        old_country = current_geo_lock.get('country')
        old_coordinates = current_geo_lock.get('coordinates', {"lat": 0, "lng": 0})
        
        current_geo_lock = {
            "enabled": current_geo_lock.get('enabled', False),
            "countries": [old_country],
            "country_details": [{
                "country_code": old_country,
                "country_name": old_country,
                "coordinates": old_coordinates
            }]
        }
    
    # Initialize if not present
    if 'countries' not in current_geo_lock:
        current_geo_lock['countries'] = []
    if 'country_details' not in current_geo_lock:
        current_geo_lock['country_details'] = []
    
    # Check if country already exists
    if country_code in current_geo_lock.get('countries', []):
        # Update the details if it exists
        for i, detail in enumerate(current_geo_lock.get('country_details', [])):
            if detail.get('country_code') == country_code:
                current_geo_lock['country_details'][i] = {
                    "country_code": country_code,
                    "country_name": country_name,
                    "coordinates": coordinates
                }
                break
    else:
        # Add the new country
        current_geo_lock['countries'].append(country_code)
        current_geo_lock['country_details'].append({
            "country_code": country_code,
            "country_name": country_name,
            "coordinates": coordinates
        })
    
    # Ensure it's enabled
    current_geo_lock['enabled'] = True
    
    # Update user data
    update_success = update_user_security(user_id, {"geo_lock": current_geo_lock})
    if not update_success:
        return jsonify({"error": "Failed to add country to geo-lock"}), 500
    
    return jsonify({
        "message": f"Country {country_name or country_code} added to geo-lock successfully",
        "geo_lock": current_geo_lock
    })

# API endpoint to remove a country from geo-lock
@security_bp.route('/api/security/geo-lock/remove-country', methods=['POST'])
def remove_country_from_geolock():
    """Remove a country from geo-lock allowed countries"""
    # Check if user is authenticated
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Not authenticated"}), 401
    
    # Get user data
    user_data = get_user_data(user_id)
    if not user_data:
        return jsonify({"error": "User not found"}), 404
        
    # Check if user is premium
    if not user_data.get('premium', False):
        return jsonify({"error": "This feature is only available for premium users"}), 403
    
    # Get data from request
    data = request.json
    if not data:
        return jsonify({"error": "Invalid request"}), 400
    
    country_code = data.get('country_code')
    
    if not country_code:
        return jsonify({"error": "Country code is required"}), 400
    
    # Get current geo_lock settings
    current_geo_lock = user_data.get('geo_lock', {
        "enabled": False,
        "countries": [],
        "country_details": []
    })
    
    # Check if we need to migrate from old format
    if 'country' in current_geo_lock and current_geo_lock.get('country'):
        # Migrate from old format to new format
        old_country = current_geo_lock.get('country')
        old_coordinates = current_geo_lock.get('coordinates', {"lat": 0, "lng": 0})
        
        current_geo_lock = {
            "enabled": current_geo_lock.get('enabled', False),
            "countries": [old_country],
            "country_details": [{
                "country_code": old_country,
                "country_name": old_country,
                "coordinates": old_coordinates
            }]
        }
    
    # Initialize if not present
    if 'countries' not in current_geo_lock:
        current_geo_lock['countries'] = []
    if 'country_details' not in current_geo_lock:
        current_geo_lock['country_details'] = []
    
    # Remove the country if it exists
    if country_code in current_geo_lock.get('countries', []):
        current_geo_lock['countries'].remove(country_code)
        
        # Remove from country_details
        current_geo_lock['country_details'] = [
            detail for detail in current_geo_lock.get('country_details', [])
            if detail.get('country_code') != country_code
        ]
    
    # If no countries left, disable geo-lock
    if len(current_geo_lock.get('countries', [])) == 0:
        current_geo_lock['enabled'] = False
    
    # Update user data
    update_success = update_user_security(user_id, {"geo_lock": current_geo_lock})
    if not update_success:
        return jsonify({"error": "Failed to remove country from geo-lock"}), 500
    
    return jsonify({
        "message": f"Country {country_code} removed from geo-lock successfully",
        "geo_lock": current_geo_lock
    })

@security_bp.route('/api/security/ip-whitelist', methods=['POST'])
def set_ip_whitelist():
    """Set IP whitelist for wallet access"""
    # Check if user is authenticated
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Not authenticated"}), 401
    
    # Get user data
    user_data = get_user_data(user_id)
    if not user_data:
        return jsonify({"error": "User not found"}), 404
        
    # Check if user is premium
    if not user_data.get('premium', False):
        # Force disable this premium feature for non-premium users
        update_data = {
            "ip_whitelist": {
                "enabled": False,
                "ips": [],
                "ip_details": []
            }
        }
        update_user_security(user_id, update_data)
        update_security_timestamp(user_id, "Premium Feature Disabled - Not Premium")
        return jsonify({"error": "This feature is only available for premium users", "disabled": True}), 403
    
    # Get data from request
    data = request.json
    if not data:
        return jsonify({"error": "Invalid request"}), 400
    
    enabled = data.get('enabled', False)
    
    # If disabling, completely update the ip_whitelist object
    if not enabled:
        update_data = {
            "ip_whitelist": {
                "enabled": False,
                "ips": [],
                "ip_details": []
            }
        }
    else:
        # Get IP addresses
        ip_addresses = data.get('ips', [])
        ip_details = data.get('ip_details', [])
        
        if not ip_addresses or not isinstance(ip_addresses, list):
            return jsonify({"error": "At least one IP address is required"}), 400
            
        # Validate IP addresses
        ip_regex = re.compile(r"^(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$")
        for ip in ip_addresses:
            if not ip_regex.match(ip):
                return jsonify({"error": f"Invalid IP address format: {ip}"}), 400
        
        # Create any missing IP details for addresses that don't have details yet
        if not ip_details:
            ip_details = []
            
        # Make sure we have details for all IPs
        ip_details_map = {detail.get('ip_address'): detail for detail in ip_details if isinstance(detail, dict)}
        for ip in ip_addresses:
            if ip not in ip_details_map:
                # Create basic details for IPs that don't have them
                ip_details.append({
                    "ip_address": ip,
                    "country": "",
                    "region": "",
                    "city": "",
                    "location": "",
                    "timezone": "",
                    "provider": ""
                })
                
        update_data = {
            "ip_whitelist": {
                "enabled": True,
                "ips": ip_addresses,
                "ip_details": ip_details
            }
        }
    
    # Update user data
    update_success = update_user_security(user_id, update_data)
    if not update_success:
        return jsonify({"error": "Failed to update IP whitelist settings"}), 500
    
    # Update security timestamp with appropriate message
    if enabled:
        update_security_timestamp(user_id, "IP Whitelist Enabled")
    else:
        update_security_timestamp(user_id, "IP Whitelist Disabled")
    
    return jsonify({"message": "IP whitelist settings updated successfully"})

# API endpoint to detect country for geo-lock feature
@security_bp.route('/api/security/detect-country', methods=['GET'])
def detect_country():
    """Detect user's country for geo-lock feature"""
    # Check if user is authenticated
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Not authenticated"}), 401
    
    # Get user data
    user_data = get_user_data(user_id)
    if not user_data:
        return jsonify({"error": "User not found"}), 404
        
    # Check if user is premium
    if not user_data.get('premium', False):
        return jsonify({"error": "This feature is only available for premium users"}), 403
    
    try:
        # Get the real external IP address using multiple services
        print("Getting real external IP address for country detection...")
        # Start with headers/local IP as initial value
        client_ip = request.remote_addr
        if request.headers.get('X-Forwarded-For'):
            client_ip = request.headers.get('X-Forwarded-For').split(',')[0].strip()
            
        # If the IP is localhost or internal, try to get the real external IP
        if client_ip in ['127.0.0.1', 'localhost'] or client_ip.startswith('192.168.') or client_ip.startswith('10.'):
            print(f"Detected internal IP: {client_ip}, attempting to find external IP")
            
            # Try multiple services in sequence until we get a valid external IP
            external_ip_services = [
                ('https://api.ipify.org?format=json', 'json', 'ip'),
                ('https://api64.ipify.org?format=json', 'json', 'ip'),
                ('https://ifconfig.me/ip', 'text', None),
                ('https://icanhazip.com', 'text', None),
                ('https://wtfismyip.com/text', 'text', None)
            ]
            
            for service_url, response_type, json_key in external_ip_services:
                try:
                    print(f"Trying external IP service: {service_url}")
                    ip_response = requests.get(service_url, timeout=3)
                    
                    if ip_response.status_code == 200:
                        if response_type == 'json':
                            detected_ip = ip_response.json().get(json_key)
                        else:  # text
                            detected_ip = ip_response.text.strip()
                            
                        # Basic validation that it looks like an IP
                        if detected_ip and re.match(r'^(\d{1,3}\.){3}\d{1,3}$', detected_ip):
                            client_ip = detected_ip
                            print(f"External IP successfully detected: {client_ip}")
                            break
                except Exception as e:
                    print(f"Error with {service_url}: {str(e)}")
                    continue
        
        print(f"Final IP address for country detection: {client_ip}")
        
        # Get API tokens from environment variables
        api_tokens = [
            os.environ.get('IPINFO_API_TOKEN_1', '5f9adf4c632001'),
            os.environ.get('IPINFO_API_TOKEN_2', 'ec2560bf0ec1b2'),
            os.environ.get('IPINFO_API_TOKEN_3', 'b5ea70b8b192d3')
        ]
        
        # Choose a random valid token
        token = random.choice([t for t in api_tokens if t])
        print(f"Using token: {token}")
        
        # Call the API
        api_url = f"https://ipinfo.io/{client_ip}/json?token={token}"
        print(f"Making API request to: {api_url}")
        
        response = requests.get(api_url, timeout=5)
        print(f"API response status: {response.status_code}")
        
        if response.status_code != 200:
            error_msg = f"Failed to retrieve country information (Status: {response.status_code})"
            if response.text:
                error_msg += f", Response: {response.text[:100]}"
            print(error_msg)
            return jsonify({"error": error_msg}), 500
        
        ip_data = response.json()
        print(f"Received IP data for country detection: {ip_data}")
        
        # Format the response
        country_details = {
            "ip_address": ip_data.get("ip", client_ip),
            "country": ip_data.get("country", ""),
            "country_name": ip_data.get("country_name", ""),
            "region": ip_data.get("region", ""),
            "city": ip_data.get("city", ""),
            "location": ip_data.get("loc", ""),
            "coordinates": {
                "lat": float(ip_data.get("loc", "0,0").split(",")[0]) if "," in ip_data.get("loc", "0,0") else 0,
                "lng": float(ip_data.get("loc", "0,0").split(",")[1]) if "," in ip_data.get("loc", "0,0") else 0
            },
            "timezone": ip_data.get("timezone", "")
        }
        
        print(f"Formatted country response: {country_details}")
        return jsonify(country_details)
    
    except requests.exceptions.Timeout:
        print("IPinfo API request timed out for country detection")
        return jsonify({"error": "API request timed out. Please try again."}), 500
    except requests.exceptions.RequestException as e:
        print(f"Request error during country detection: {str(e)}")
        return jsonify({"error": f"Network error: {str(e)}"}), 500
    except Exception as e:
        print(f"Error detecting country: {type(e).__name__}: {str(e)}")
        return jsonify({"error": f"Failed to detect country: {str(e)}"}), 500

@security_bp.route('/api/security/ip-whitelist/scan', methods=['GET'])
def scan_current_ip():
    """Scan current IP and get its details"""
    # Check if user is authenticated
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Not authenticated"}), 401
    
    # Get user data
    user_data = get_user_data(user_id)
    if not user_data:
        return jsonify({"error": "User not found"}), 404
        
    # Check if user is premium
    if not user_data.get('premium', False):
        return jsonify({"error": "This feature is only available for premium users"}), 403
    
    try:
        # Get the real external IP address using multiple services
        print("Getting real external IP address...")
        # Start with headers/local IP as initial value
        client_ip = request.remote_addr
        if request.headers.get('X-Forwarded-For'):
            client_ip = request.headers.get('X-Forwarded-For').split(',')[0].strip()
            
        # If the IP is localhost or internal, try to get the real external IP
        if client_ip in ['127.0.0.1', 'localhost'] or client_ip.startswith('192.168.') or client_ip.startswith('10.'):
            print(f"Detected internal IP: {client_ip}, attempting to find external IP")
            
            # Try multiple services in sequence until we get a valid external IP
            external_ip_services = [
                ('https://api.ipify.org?format=json', 'json', 'ip'),
                ('https://api64.ipify.org?format=json', 'json', 'ip'),
                ('https://ifconfig.me/ip', 'text', None),
                ('https://icanhazip.com', 'text', None),
                ('https://wtfismyip.com/text', 'text', None)
            ]
            
            for service_url, response_type, json_key in external_ip_services:
                try:
                    print(f"Trying external IP service: {service_url}")
                    ip_response = requests.get(service_url, timeout=3)
                    
                    if ip_response.status_code == 200:
                        if response_type == 'json':
                            detected_ip = ip_response.json().get(json_key)
                        else:  # text
                            detected_ip = ip_response.text.strip()
                            
                        # Basic validation that it looks like an IP
                        if detected_ip and re.match(r'^(\d{1,3}\.){3}\d{1,3}$', detected_ip):
                            client_ip = detected_ip
                            print(f"External IP successfully detected: {client_ip}")
                            break
                except Exception as e:
                    print(f"Error with {service_url}: {str(e)}")
                    continue
        
        print(f"Final IP address for scanning: {client_ip}")
        
        print(f"Starting IP scan for IP: {client_ip}")
        
        # Get API tokens from environment variables
        api_tokens = [
            os.environ.get('IPINFO_API_TOKEN_1', '5f9adf4c632001'),
            os.environ.get('IPINFO_API_TOKEN_2', 'ec2560bf0ec1b2'),
            os.environ.get('IPINFO_API_TOKEN_3', 'b5ea70b8b192d3')
        ]
        
        # Choose a random valid token
        token = random.choice([t for t in api_tokens if t])
        print(f"Using token: {token}")
        
        # Call the API
        api_url = f"https://ipinfo.io/{client_ip}/json?token={token}"
        print(f"Making API request to: {api_url}")
        
        response = requests.get(api_url, timeout=5)
        print(f"API response status: {response.status_code}")
        
        if response.status_code != 200:
            error_msg = f"Failed to retrieve IP information (Status: {response.status_code})"
            if response.text:
                error_msg += f", Response: {response.text[:100]}"
            print(error_msg)
            return jsonify({"error": error_msg}), 500
        
        ip_data = response.json()
        print(f"Received IP data: {ip_data}")
        
        # Format the response
        ip_details = {
            "ip_address": ip_data.get("ip", client_ip),
            "country": ip_data.get("country", ""),
            "region": ip_data.get("region", ""),
            "city": ip_data.get("city", ""),
            "location": ip_data.get("loc", ""),
            "postal": ip_data.get("postal", None),
            "timezone": ip_data.get("timezone", ""),
            "provider": ip_data.get("org", "")
        }
        
        print(f"Formatted response: {ip_details}")
        return jsonify(ip_details)
    
    except requests.exceptions.Timeout:
        print("IPinfo API request timed out")
        return jsonify({"error": "IPinfo API request timed out. Please try again."}), 500
    except requests.exceptions.RequestException as e:
        print(f"Request error: {str(e)}")
        return jsonify({"error": f"Network error: {str(e)}"}), 500
    except Exception as e:
        print(f"Error scanning IP: {type(e).__name__}: {str(e)}")
        return jsonify({"error": f"Failed to scan IP address: {str(e)}"}), 500

@security_bp.route('/api/security/auto-signin', methods=['POST'])
def set_auto_signin():
    """Set auto sign-in settings for wallet access"""
    # Check if user is authenticated
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Not authenticated"}), 401
    
    # Get user data
    user_data = get_user_data(user_id)
    if not user_data:
        return jsonify({"error": "User not found"}), 404
    
    # Get data from request
    data = request.json
    if not data:
        return jsonify({"error": "Invalid request"}), 400
    
    # Add debug logging to help diagnose the issue
    logger.info(f"Auto Sign-In request received: {data}")
    
    # Get the enabled flag explicitly, defaulting to False for safety
    enabled = data.get('enabled')
    if enabled is None:
        enabled = False
        logger.warning(f"No enabled flag provided, defaulting to False")
    else:
        enabled = bool(enabled)  # Explicitly convert to boolean
    
    # Get duration but only use if enabled is True
    duration = data.get('duration', 20)  # Default to 20 days to match frontend
    
    logger.info(f"Processing Auto Sign-In update: enabled={enabled}, duration={duration}")
    
    # Update auto sign-in settings with correct naming
    if enabled:
        update_data = {
            "auto_signin": {
                "enabled": True,
                "duration": duration
            }
        }
    else:
        # When disabling, completely remove the auto_signin settings
        logger.info(f"Disabling Auto Sign-In for user: {user_id}")
        update_data = {
            "auto_signin": {
                "enabled": False,
                "duration": 0  # Clear the duration
            }
        }
    
    # Update user data
    update_success = update_user_security(user_id, update_data)
    if not update_success:
        logger.error(f"Failed to update Auto Sign-In settings for user: {user_id}")
        return jsonify({"error": "Failed to update auto sign-in settings"}), 500
    
    # Update security timestamp with appropriate message
    if enabled:
        update_security_timestamp(user_id, "Auto Sign-In Enabled")
    else:
        update_security_timestamp(user_id, "Auto Sign-In Disabled")
    
    # Re-fetch user data to confirm update
    updated_user = get_user_data(user_id)
    updated_auto_signin = updated_user.get('auto_signin', {})
    logger.info(f"Auto Sign-In settings after update: {updated_auto_signin}")
    
    return jsonify({
        "message": "Auto sign-in settings updated successfully",
        "enabled": enabled,
        "duration": duration if enabled else 0
    })

# Get active sessions count for a user
def get_active_sessions_count(user_id):
    """Get the number of active devices for a user"""
    if get_user_devices:
        # Use the function from session_devices.py if available
        user_devices = get_user_devices(user_id)
        return len(user_devices.get("devices", []))
    else:
        # Fallback if the function is not available
        devices = device_sessions_collection.find_one({"user_id": user_id})
        if devices:
            return len(devices.get("devices", []))
        return 1  # Default is at least 1 device (current device)

# Initialize Blueprint
def init_app(app):
    app.register_blueprint(security_bp)
    return app 