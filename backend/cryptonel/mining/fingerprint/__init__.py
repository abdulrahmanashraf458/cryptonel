"""
Advanced Fingerprinting System for Cryptonel Mining

This package provides advanced device fingerprinting capabilities
for enhanced security and fraud prevention.
"""

import logging
import os
import hashlib
import hmac
import time
import json
import secrets
from flask import Blueprint

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
)
logger = logging.getLogger("advanced_fingerprinting")

# Import routes
from .routes import init_fingerprint_routes

# Import key functions for direct access
from .advanced_fingerprinting import get_advanced_device_fingerprint, calculate_fingerprint_similarity, find_matching_devices
from .anti_spoofing import detect_spoofing
from .fingerprint_storage import store_fingerprint, get_stored_fingerprints, get_fingerprint_history, remove_fingerprint, check_device_limit, mark_fingerprint_trusted

__all__ = [
    'init_fingerprint_routes',
    'get_advanced_device_fingerprint',
    'calculate_fingerprint_similarity',
    'find_matching_devices',
    'detect_spoofing',
    'store_fingerprint',
    'get_stored_fingerprints',
    'get_fingerprint_history',
    'remove_fingerprint',
    'check_device_limit',
    'mark_fingerprint_trusted'
]

# Create a secret key for HMAC verification
# This will be regenerated each time the server starts for added security
FINGERPRINT_SECRET = os.getenv("FINGERPRINT_SECRET") or secrets.token_hex(32)

# Store the last time we rotated the secret
SECRET_CREATED_AT = int(time.time())

# Configure how often to rotate the secret (default: 24 hours)
SECRET_ROTATION_SECONDS = int(os.getenv("FINGERPRINT_SECRET_ROTATION", "86400"))

fingerprint_bp = Blueprint('fingerprint', __name__)

def get_fingerprint_secret():
    """
    Get the current fingerprint secret, rotating if necessary
    """
    global FINGERPRINT_SECRET, SECRET_CREATED_AT
    
    # Check if we need to rotate the secret
    current_time = int(time.time())
    if current_time - SECRET_CREATED_AT > SECRET_ROTATION_SECONDS:
        # Rotate the secret
        old_secret = FINGERPRINT_SECRET
        FINGERPRINT_SECRET = secrets.token_hex(32)
        SECRET_CREATED_AT = current_time
        logger.info("Rotated fingerprint secret key")
        
        # Return both old and new secrets during transition period
        return {"current": FINGERPRINT_SECRET, "previous": old_secret}
    
    return {"current": FINGERPRINT_SECRET}

def create_fingerprint_hmac(data):
    """
    Create an HMAC signature for fingerprint data
    
    Args:
        data: Dict or string to sign
        
    Returns:
        str: HMAC signature
    """
    try:
        # Convert to string if it's a dict
        if isinstance(data, dict):
            data_str = json.dumps(data, sort_keys=True)
        else:
            data_str = str(data)
        
        # Get current secret
        secret = get_fingerprint_secret()["current"]
        
        # Create HMAC using SHA-256
        signature = hmac.new(
            secret.encode(), 
            data_str.encode(), 
            hashlib.sha256
        ).hexdigest()
        
        return signature
    except Exception as e:
        logger.error(f"Error creating fingerprint HMAC: {e}")
        return ""

def verify_fingerprint_hmac(data, signature):
    """
    Verify an HMAC signature for fingerprint data
    
    Args:
        data: Dict or string that was signed
        signature: HMAC signature to verify
        
    Returns:
        bool: True if signature is valid
    """
    try:
        # Convert to string if it's a dict
        if isinstance(data, dict):
            data_str = json.dumps(data, sort_keys=True)
        else:
            data_str = str(data)
        
        # Get current and previous secrets
        secrets_dict = get_fingerprint_secret()
        
        # Try with current secret first
        current_signature = hmac.new(
            secrets_dict["current"].encode(), 
            data_str.encode(), 
            hashlib.sha256
        ).hexdigest()
        
        if hmac.compare_digest(current_signature, signature):
            return True
        
        # If that fails and we have a previous secret, try that
        if "previous" in secrets_dict:
            previous_signature = hmac.new(
                secrets_dict["previous"].encode(), 
                data_str.encode(), 
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(previous_signature, signature)
        
        # Signature doesn't match either secret
        return False
    except Exception as e:
        logger.error(f"Error verifying fingerprint HMAC: {e}")
        return False

def init_fingerprint(app=None, parent_blueprint=None):
    """
    Initialize fingerprint system
    
    Args:
        app: Flask application instance
        parent_blueprint: Parent blueprint to register routes under
    """
    logger.info("Initializing advanced fingerprinting system")
    
    try:
        # Import routes module (lazy import to avoid circular imports)
        from .routes import init_fingerprint_routes, fingerprint_routes
        
        # Export storage functions for use in other modules
        from .fingerprint_storage import store_fingerprint, get_stored_fingerprints, get_fingerprint_history, remove_fingerprint, check_device_limit, mark_fingerprint_trusted
        
        # Create blueprint if none provided
        if not parent_blueprint:
            fingerprint_bp = Blueprint('fingerprint_bp', __name__, url_prefix='/api/fingerprint')
            init_fingerprint_routes(fingerprint_bp)
            
            # Register blueprint with app if provided
            if app:
                app.register_blueprint(fingerprint_bp)
                logger.info("Registered fingerprint blueprint with app")
        else:
            # Initialize routes under parent blueprint
            init_fingerprint_routes(parent_blueprint)
            logger.info(f"Registered fingerprint routes under parent blueprint")
            
        # Create database indexes
        try:
            # Create indexes for fingerprint collections
            from .fingerprint_storage import create_indexes
            create_indexes()
            logger.info("Created fingerprint database indexes")
        except Exception as e:
            logger.error(f"Error creating fingerprint database indexes: {e}")
            
        return True
    except Exception as e:
        logger.error(f"Error initializing fingerprint system: {e}")
        return False 