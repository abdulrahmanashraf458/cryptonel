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
logger = logging.getLogger("appearance_api")
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# Create Blueprint for appearance API
appearance_api_bp = Blueprint('appearance_api', __name__)

# Database connection
MONGODB_URI = os.getenv("DATABASE_URL")
client = MongoClient(MONGODB_URI)
db = client["cryptonel_wallet"]
users_collection = db["users"]
rating_settings_collection = db["rating_settings"]  # Collection for rating settings

# Default appearance settings
DEFAULT_APPEARANCE_SETTINGS = {
    "theme": "default",
    "customThemeColors": {
        "primary": "#3B82F6",
        "secondary": "#6B7280",
        "text": "#1F2937",
        "background": "#FFFFFF"
    },
    "ratingStyle": "stars",
    "cardStyle": "modern",
    "fontStyle": "default",
    "showAnimation": True,
    "highlightTopRatings": True
}

# Valid theme options
VALID_THEMES = [
    'default', 'dark', 'gradient', 'luxury', 'elegant', 'neon', 
    'forest', 'cosmic', 'minimalist', 'tech', 'pastel', 'monochrome', 'custom'
]

# Valid rating styles
VALID_RATING_STYLES = ['stars', 'numbers', 'bars', 'emoji', 'percent']

# Valid card styles
VALID_CARD_STYLES = ['modern', 'compact', 'detailed']

# Valid font styles
VALID_FONT_STYLES = ['default', 'modern', 'classic']

# Helper function to validate appearance settings
def validate_appearance_settings(setting, value):
    """Validate appearance setting name and value"""
    
    if setting == "theme":
        if value not in VALID_THEMES:
            return False, f"Invalid theme: {value}. Must be one of {VALID_THEMES}"
        return True, value
    
    elif setting == "customThemeColors":
        if not isinstance(value, dict):
            return False, "customThemeColors must be an object"
        
        required_colors = ["primary", "secondary", "text", "background"]
        for color in required_colors:
            if color not in value:
                return False, f"Missing required color: {color}"
            if not isinstance(value[color], str) or not value[color].startswith('#'):
                return False, f"Invalid color format for {color}. Must be hex color (e.g., #FF0000)"
        
        return True, value
    
    elif setting == "ratingStyle":
        if value not in VALID_RATING_STYLES:
            return False, f"Invalid rating style: {value}. Must be one of {VALID_RATING_STYLES}"
        return True, value
    
    elif setting == "cardStyle":
        if value not in VALID_CARD_STYLES:
            return False, f"Invalid card style: {value}. Must be one of {VALID_CARD_STYLES}"
        return True, value
    
    elif setting == "fontStyle":
        if value not in VALID_FONT_STYLES:
            return False, f"Invalid font style: {value}. Must be one of {VALID_FONT_STYLES}"
        return True, value
    
    elif setting in ["showAnimation", "highlightTopRatings"]:
        if not isinstance(value, bool):
            return False, f"{setting} must be a boolean value"
        return True, value
    
    else:
        return False, f"Invalid setting: {setting}"

@appearance_api_bp.route("/api/ratings/appearance", methods=["GET"])
@token_required
def get_appearance_settings(user_id=None, **kwargs):
    """Get user appearance settings - premium required"""
    try:
        # If user_id is None, use the user_id from the session
        if user_id is None:
            user_id = session.get('user_id')
            if not user_id:
                logger.error("No user_id found in request")
                return jsonify({"error": "Not authorized"}), 401
        
        logger.info(f"Fetching appearance settings for user_id: {user_id}")
        
        # Check premium status
        premium_status = premium_check.check_premium_status(user_id)
        if not premium_status.get("premium", False):
            logger.warning(f"Non-premium user {user_id} attempted to access premium appearance settings")
            return jsonify({
                "error": "Premium subscription required", 
                "code": "PREMIUM_REQUIRED"
            }), 403
            
        # Check if wallet is locked
        if premium_status.get("wallet_lock", True):
            logger.warning(f"User {user_id} with locked wallet attempted to access appearance settings")
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
        
        # If no settings or no appearance settings, create default appearance settings
        if not settings or "appearance" not in settings:
            username = user.get("username", "")
            
            # Use default appearance settings
            appearance_data = DEFAULT_APPEARANCE_SETTINGS
            
            # Save default appearance settings to database
            now = datetime.now()
            rating_settings_collection.update_one(
                {"user_id": user_id},
                {
                    "$set": {
                        "user_id": user_id,
                        "username": username,
                        "appearance": appearance_data,
                        "created_at": now,
                        "last_updated": now
                    }
                },
                upsert=True
            )
            
            logger.info(f"Created default appearance settings for user {user_id}")
        else:
            appearance_data = settings.get("appearance", DEFAULT_APPEARANCE_SETTINGS)
        
        # Prepare response
        response = {
            "user_id": user_id,
            "username": user.get("username"),
            "appearance": appearance_data,
            "is_premium": premium_status.get("premium", False),
            "last_updated": settings.get("last_updated", datetime.now()).isoformat() if settings else datetime.now().isoformat()
        }
        
        return jsonify(response)
    
    except Exception as e:
        logger.error(f"Error getting appearance settings: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

@appearance_api_bp.route("/api/ratings/appearance/update", methods=["POST"])
@token_required
def update_appearance_setting(user_id=None, **kwargs):
    """Update specific appearance setting - premium required"""
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
            logger.warning(f"Non-premium user {user_id} attempted to update premium appearance settings")
            return jsonify({
                "error": "Premium subscription required", 
                "code": "PREMIUM_REQUIRED"
            }), 403
            
        # Check if wallet is locked
        if premium_status.get("wallet_lock", True):
            logger.warning(f"User {user_id} with locked wallet attempted to update appearance settings")
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
        is_valid, processed_value = validate_appearance_settings(setting, value)
        
        if not is_valid:
            return jsonify({"error": processed_value}), 400
        
        logger.info(f"Updating appearance setting {setting} for user_id: {user_id}")
        
        # Get current settings
        settings_doc = rating_settings_collection.find_one({"user_id": user_id})
        
        # Initialize appearance settings if none exist
        current_appearance = DEFAULT_APPEARANCE_SETTINGS
        if settings_doc and "appearance" in settings_doc:
            current_appearance = settings_doc.get("appearance")
        
        # Update specific setting
        current_appearance[setting] = processed_value
        
        # Get user info
        user = users_collection.find_one(
            {"user_id": user_id},
            {"username": 1, "_id": 0}
        )
        
        if not user:
            logger.error(f"User not found for user_id: {user_id}")
            return jsonify({"error": "User not found"}), 404
            
        username = user.get("username", "")
        
        # Save updated appearance settings
        now = datetime.now()
        rating_settings_collection.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "user_id": user_id,
                    "username": username,
                    "appearance": current_appearance,
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
        logger.error(f"Error updating appearance setting: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

@appearance_api_bp.route("/api/ratings/appearance/update-all", methods=["POST"])
@token_required
def update_all_appearance_settings(user_id=None, **kwargs):
    """Update all appearance settings at once - premium required"""
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
            logger.warning(f"Non-premium user {user_id} attempted to update premium appearance settings")
            return jsonify({
                "error": "Premium subscription required", 
                "code": "PREMIUM_REQUIRED"
            }), 403
            
        # Check if wallet is locked
        if premium_status.get("wallet_lock", True):
            logger.warning(f"User {user_id} with locked wallet attempted to update appearance settings")
            return jsonify({
                "error": "Wallet is locked", 
                "code": "WALLET_LOCKED"
            }), 403
        
        # Get update data
        data = request.json
        appearance_settings = data.get("appearance")
        
        if not appearance_settings or not isinstance(appearance_settings, dict):
            return jsonify({"error": "Appearance settings object is required"}), 400
        
        # Validate each setting
        valid_appearance = {}
        for setting, value in appearance_settings.items():
            is_valid, processed_value = validate_appearance_settings(setting, value)
            if is_valid:
                valid_appearance[setting] = processed_value
            else:
                logger.warning(f"Invalid appearance setting {setting}: {processed_value}")
        
        logger.info(f"Updating all appearance settings for user_id: {user_id}")
        
        # Get user info
        user = users_collection.find_one(
            {"user_id": user_id},
            {"username": 1, "_id": 0}
        )
        
        if not user:
            logger.error(f"User not found for user_id: {user_id}")
            return jsonify({"error": "User not found"}), 404
            
        username = user.get("username", "")
        
        # Save updated appearance settings
        now = datetime.now()
        rating_settings_collection.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "user_id": user_id,
                    "username": username,
                    "appearance": valid_appearance,
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
        logger.error(f"Error updating all appearance settings: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

@appearance_api_bp.route("/api/ratings/appearance/reset", methods=["POST"])
@token_required
def reset_appearance_settings(user_id=None, **kwargs):
    """Reset appearance settings to default - premium required"""
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
            logger.warning(f"Non-premium user {user_id} attempted to reset premium appearance settings")
            return jsonify({
                "error": "Premium subscription required", 
                "code": "PREMIUM_REQUIRED"
            }), 403
            
        # Check if wallet is locked
        if premium_status.get("wallet_lock", True):
            logger.warning(f"User {user_id} with locked wallet attempted to reset appearance settings")
            return jsonify({
                "error": "Wallet is locked", 
                "code": "WALLET_LOCKED"
            }), 403
        
        logger.info(f"Resetting appearance settings for user_id: {user_id}")
        
        # Get user info
        user = users_collection.find_one(
            {"user_id": user_id},
            {"username": 1, "_id": 0}
        )
        
        if not user:
            logger.error(f"User not found for user_id: {user_id}")
            return jsonify({"error": "User not found"}), 404
            
        username = user.get("username", "")
        
        # Reset to default appearance settings
        now = datetime.now()
        rating_settings_collection.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "user_id": user_id,
                    "username": username,
                    "appearance": DEFAULT_APPEARANCE_SETTINGS,
                    "last_updated": now
                }
            },
            upsert=True
        )
        
        return jsonify({
            "success": True,
            "appearance": DEFAULT_APPEARANCE_SETTINGS,
            "updated_at": now.isoformat()
        })
    
    except Exception as e:
        logger.error(f"Error resetting appearance settings: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

@appearance_api_bp.route("/api/ratings/appearance/share-code", methods=["POST"])
@token_required
def generate_share_code(user_id=None, **kwargs):
    """Generate share code for appearance settings - premium required"""
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
            logger.warning(f"Non-premium user {user_id} attempted to generate share code")
            return jsonify({
                "error": "Premium subscription required", 
                "code": "PREMIUM_REQUIRED"
            }), 403
            
        # Check if wallet is locked
        if premium_status.get("wallet_lock", True):
            logger.warning(f"User {user_id} with locked wallet attempted to generate share code")
            return jsonify({
                "error": "Wallet is locked", 
                "code": "WALLET_LOCKED"
            }), 403
        
        # Get current appearance settings
        settings = rating_settings_collection.find_one({"user_id": user_id})
        appearance_data = settings.get("appearance", DEFAULT_APPEARANCE_SETTINGS) if settings else DEFAULT_APPEARANCE_SETTINGS
        
        # Generate share code (simple base64 encoding for now)
        import base64
        share_data = {
            "appearance": appearance_data,
            "generated_at": datetime.now().isoformat(),
            "user_id": user_id
        }
        
        share_json = json.dumps(share_data, separators=(',', ':'))
        share_code = base64.b64encode(share_json.encode('utf-8')).decode('utf-8')
        
        return jsonify({
            "success": True,
            "share_code": share_code,
            "generated_at": share_data["generated_at"]
        })
    
    except Exception as e:
        logger.error(f"Error generating share code: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

@appearance_api_bp.route("/api/ratings/appearance/import", methods=["POST"])
@token_required
def import_appearance_settings(user_id=None, **kwargs):
    """Import appearance settings from share code - premium required"""
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
            logger.warning(f"Non-premium user {user_id} attempted to import appearance settings")
            return jsonify({
                "error": "Premium subscription required", 
                "code": "PREMIUM_REQUIRED"
            }), 403
            
        # Check if wallet is locked
        if premium_status.get("wallet_lock", True):
            logger.warning(f"User {user_id} with locked wallet attempted to import appearance settings")
            return jsonify({
                "error": "Wallet is locked", 
                "code": "WALLET_LOCKED"
            }), 403
        
        # Get share code from request
        data = request.json
        share_code = data.get("share_code")
        
        if not share_code:
            return jsonify({"error": "Share code is required"}), 400
        
        # Decode share code
        try:
            import base64
            share_json = base64.b64decode(share_code.encode('utf-8')).decode('utf-8')
            share_data = json.loads(share_json)
        except Exception as e:
            logger.error(f"Error decoding share code: {e}")
            return jsonify({"error": "Invalid share code format"}), 400
        
        # Validate imported data
        if "appearance" not in share_data:
            return jsonify({"error": "Invalid share code: missing appearance data"}), 400
        
        imported_appearance = share_data["appearance"]
        
        # Validate each setting in imported data
        valid_appearance = {}
        for setting, value in imported_appearance.items():
            is_valid, processed_value = validate_appearance_settings(setting, value)
            if is_valid:
                valid_appearance[setting] = processed_value
            else:
                logger.warning(f"Invalid imported setting {setting}: {processed_value}")
        
        # Get user info
        user = users_collection.find_one(
            {"user_id": user_id},
            {"username": 1, "_id": 0}
        )
        
        if not user:
            logger.error(f"User not found for user_id: {user_id}")
            return jsonify({"error": "User not found"}), 404
            
        username = user.get("username", "")
        
        # Save imported appearance settings
        now = datetime.now()
        rating_settings_collection.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "user_id": user_id,
                    "username": username,
                    "appearance": valid_appearance,
                    "last_updated": now
                }
            },
            upsert=True
        )
        
        return jsonify({
            "success": True,
            "appearance": valid_appearance,
            "imported_at": now.isoformat()
        })
    
    except Exception as e:
        logger.error(f"Error importing appearance settings: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

def init_app(app):
    """Register Blueprint with main Flask app"""
    logger.info("Registering appearance_api blueprint")
    app.register_blueprint(appearance_api_bp)
    
    # Create indexes
    try:
        # Index for rating settings collection (if not already created)
        if not any(idx.get('name') == 'rating_settings_user_id_unique_idx' 
                  for idx in rating_settings_collection.list_indexes()):
            rating_settings_collection.create_index([("user_id", 1)], 
                                             unique=True, 
                                             name="rating_settings_user_id_unique_idx", 
                                             background=True)
            
            logger.info("Appearance settings indexes created")
    except Exception as e:
        logger.warning(f"Warning: Error creating appearance settings indexes: {e}")
    
    return app 