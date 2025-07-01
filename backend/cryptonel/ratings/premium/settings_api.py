import os
import json
import logging
from datetime import datetime
from flask import Blueprint, jsonify, request, session
from pymongo import MongoClient
from bson import ObjectId
from backend.premium_auth import premium_check
from backend.jwt_utils import token_required

# Setup logger
logger = logging.getLogger("settings_api")
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# Create Blueprint for settings API
settings_api_bp = Blueprint('settings_api', __name__)

# Database connection
MONGODB_URI = os.getenv("DATABASE_URL")
client = MongoClient(MONGODB_URI)
db = client["cryptonel_wallet"]
users_collection = db["users"]
rating_settings_collection = db["rating_settings"]  # Collection for rating settings

# Default settings
DEFAULT_SETTINGS = {
    "showRatingCount": True,
    "showComments": True,
    "sortByNewest": True,
    "showUsernameOnly": False,
    "allowAnonymousRatings": False
}

# Helper function to validate settings
def validate_settings(setting, value):
    """Validate setting name and value"""
    valid_settings = list(DEFAULT_SETTINGS.keys())
    
    if setting not in valid_settings:
        return False, f"Invalid setting: {setting}"
    
    if not isinstance(value, bool):
        return False, "Setting value must be a boolean"
    
    return True, value

@settings_api_bp.route("/api/ratings/settings", methods=["GET"])
@token_required
def get_settings(user_id=None, **kwargs):
    """Get user rating settings - premium required"""
    try:
        # If user_id is None, use the user_id from the session
        if user_id is None:
            user_id = session.get('user_id')
            if not user_id:
                logger.error("No user_id found in request")
                return jsonify({"error": "Not authorized"}), 401
        
        logger.info(f"Fetching rating settings for user_id: {user_id}")
        
        # Check premium status
        premium_status = premium_check.check_premium_status(user_id)
        if not premium_status.get("premium", False):
            logger.warning(f"Non-premium user {user_id} attempted to access premium settings")
            return jsonify({
                "error": "Premium subscription required", 
                "code": "PREMIUM_REQUIRED"
            }), 403
            
        # Check if wallet is locked
        if premium_status.get("wallet_lock", True):
            logger.warning(f"User {user_id} with locked wallet attempted to access settings")
            return jsonify({
                "error": "Wallet is locked", 
                "code": "WALLET_LOCKED"
            }), 403
        
        # Get user information
        user = users_collection.find_one(
            {"user_id": user_id},
            {"username": 1, "_id": 0}
        )
        
        if not user:
            logger.error(f"User not found for user_id: {user_id}")
            return jsonify({"error": "User not found"}), 404
        
        # Get rating settings for this user
        settings = rating_settings_collection.find_one({"user_id": user_id})
        
        # If no settings, create default settings
        if not settings or "settings" not in settings:
            username = user.get("username", "")
            
            # Use default settings
            settings_data = DEFAULT_SETTINGS
            
            # Save default settings to database
            now = datetime.now()
            rating_settings_collection.update_one(
                {"user_id": user_id},
                {
                    "$set": {
                        "user_id": user_id,
                        "username": username,
                        "settings": settings_data,
                        "created_at": now,
                        "last_updated": now
                    }
                },
                upsert=True
            )
            
            logger.info(f"Created default settings for user {user_id}")
        else:
            settings_data = settings.get("settings", DEFAULT_SETTINGS)
        
        # Prepare response
        response = {
            "user_id": user_id,
            "username": user.get("username"),
            "settings": settings_data,
            "is_premium": premium_status.get("premium", False),
            "last_updated": settings.get("last_updated", datetime.now()).isoformat() if settings else datetime.now().isoformat()
        }
        
        return jsonify(response)
    
    except Exception as e:
        logger.error(f"Error getting rating settings: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

@settings_api_bp.route("/api/ratings/settings/update", methods=["POST"])
@token_required
def update_settings(user_id=None, **kwargs):
    """Update user rating settings - premium required"""
    try:
        # If user_id is None, use the user_id from the session
        if user_id is None:
            user_id = session.get('user_id')
            if not user_id:
                logger.error("No user_id found in request")
                return jsonify({"error": "Not authorized"}), 401
        
        # Check premium status
        premium_status = premium_check.check_premium_status(user_id)
        if not premium_status.get("premium", False):
            logger.warning(f"Non-premium user {user_id} attempted to update premium settings")
            return jsonify({
                "error": "Premium subscription required", 
                "code": "PREMIUM_REQUIRED"
            }), 403
            
        # Check if wallet is locked
        if premium_status.get("wallet_lock", True):
            logger.warning(f"User {user_id} with locked wallet attempted to update settings")
            return jsonify({
                "error": "Wallet is locked", 
                "code": "WALLET_LOCKED"
            }), 403
        
        # Get update data
        data = request.json
        setting = data.get("setting")
        value = data.get("value")
        
        if not setting:
            return jsonify({"error": "Setting name is required"}), 400
        
        # Validate setting name and value
        is_valid, processed_value = validate_settings(setting, value)
        
        if not is_valid:
            return jsonify({"error": processed_value}), 400
        
        logger.info(f"Updating setting {setting} for user_id: {user_id}")
        
        # Get current settings
        settings_doc = rating_settings_collection.find_one({"user_id": user_id})
        
        # Initialize settings if none exist
        current_settings = DEFAULT_SETTINGS
        if settings_doc and "settings" in settings_doc:
            current_settings = settings_doc.get("settings")
        
        # Update specific setting
        current_settings[setting] = processed_value
        
        # Get user info
        user = users_collection.find_one(
            {"user_id": user_id},
            {"username": 1, "_id": 0}
        )
        
        if not user:
            logger.error(f"User not found for user_id: {user_id}")
            return jsonify({"error": "User not found"}), 404
            
        username = user.get("username", "")
        
        # Save updated settings
        now = datetime.now()
        rating_settings_collection.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "user_id": user_id,
                    "username": username,
                    "settings": current_settings,
                    "last_updated": now
                }
            },
            upsert=True
        )
        
        return jsonify({
            "success": True, 
            "setting": setting, 
            "value": processed_value,
            "updated_at": now.isoformat()
        })
    
    except Exception as e:
        logger.error(f"Error updating rating settings: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

@settings_api_bp.route("/api/ratings/settings/update-all", methods=["POST"])
@token_required
def update_all_settings(user_id=None, **kwargs):
    """Update all user rating settings at once - premium required"""
    try:
        # If user_id is None, use the user_id from the session
        if user_id is None:
            user_id = session.get('user_id')
            if not user_id:
                logger.error("No user_id found in request")
                return jsonify({"error": "Not authorized"}), 401
        
        # Check premium status
        premium_status = premium_check.check_premium_status(user_id)
        if not premium_status.get("premium", False):
            logger.warning(f"Non-premium user {user_id} attempted to update premium settings")
            return jsonify({
                "error": "Premium subscription required", 
                "code": "PREMIUM_REQUIRED"
            }), 403
            
        # Check if wallet is locked
        if premium_status.get("wallet_lock", True):
            logger.warning(f"User {user_id} with locked wallet attempted to update settings")
            return jsonify({
                "error": "Wallet is locked", 
                "code": "WALLET_LOCKED"
            }), 403
        
        # Get update data
        data = request.json
        settings = data.get("settings")
        
        if not settings or not isinstance(settings, dict):
            return jsonify({"error": "Settings object is required"}), 400
        
        # Validate each setting
        valid_settings = {}
        for setting, value in settings.items():
            is_valid, processed_value = validate_settings(setting, value)
            if is_valid:
                valid_settings[setting] = processed_value
        
        logger.info(f"Updating all settings for user_id: {user_id}")
        
        # Get user info
        user = users_collection.find_one(
            {"user_id": user_id},
            {"username": 1, "_id": 0}
        )
        
        if not user:
            logger.error(f"User not found for user_id: {user_id}")
            return jsonify({"error": "User not found"}), 404
            
        username = user.get("username", "")
        
        # Save updated settings
        now = datetime.now()
        rating_settings_collection.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "user_id": user_id,
                    "username": username,
                    "settings": valid_settings,
                    "last_updated": now
                }
            },
            upsert=True
        )
        
        return jsonify({
            "success": True,
            "updated_at": now.isoformat()
        })
    
    except Exception as e:
        logger.error(f"Error updating all settings: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

def init_app(app):
    """Register Blueprint with main Flask app"""
    logger.info("Registering settings_api blueprint")
    app.register_blueprint(settings_api_bp)
    
    # Create indexes
    try:
        # Index for rating settings collection (if not already created)
        if not any(idx.get('name') == 'rating_settings_user_id_unique_idx' 
                  for idx in rating_settings_collection.list_indexes()):
            rating_settings_collection.create_index([("user_id", 1)], 
                                             unique=True, 
                                             name="rating_settings_user_id_unique_idx", 
                                             background=True)
            
            logger.info("Rating settings indexes created")
    except Exception as e:
        logger.warning(f"Warning: Error creating rating settings indexes: {e}")
    
    return app 