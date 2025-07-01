import os
import json
import logging
from datetime import datetime
from flask import Blueprint, jsonify, request, session
from pymongo import MongoClient
from bson import ObjectId
from backend.jwt_utils import token_required

# Setup logger
logger = logging.getLogger("profile_api")
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# Create Blueprint for profile API
profile_api_bp = Blueprint('profile_api', __name__)

# Database connection
MONGODB_URI = os.getenv("DATABASE_URL")
client = MongoClient(MONGODB_URI)
db = client["cryptonel_wallet"]
users_collection = db["users"]
rating_settings_collection = db["rating_settings"]  # Collection for rating settings

# Helper function to sanitize/validate profile data
def validate_profile_data(field, value):
    """Validate profile data fields"""
    if field == "title":
        # Limit title to 5 words
        words = value.strip().split()
        if len(words) > 5:
            return False, "Title must be 5 words or less"
        return True, value.strip()
    
    elif field == "bio":
        # Limit bio to 300 characters
        if len(value) > 300:
            return False, "Bio must be 300 characters or less"
        return True, value.strip()
    
    return False, "Invalid field"

@profile_api_bp.route("/api/ratings/profile", methods=["GET"])
@token_required
def get_profile(user_id=None, **kwargs):
    """Get user profile data for ratings section"""
    try:
        # If user_id is None, use the user_id from the session
        if user_id is None:
            user_id = session.get('user_id')
            if not user_id:
                logger.error("No user_id found in request")
                return jsonify({"error": "Not authorized"}), 401
        
        logger.info(f"Fetching profile data for user_id: {user_id}")
        
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
        
        # Default profile data
        profile_data = {
            "title": "",
            "bio": ""
        }
        
        # If settings exist, update profile data
        if settings and "profile" in settings:
            profile_data.update(settings["profile"])
        
        # Prepare response
        response = {
            "user_id": user_id,
            "username": user.get("username"),
            "profile": profile_data
        }
        
        return jsonify(response)
    
    except Exception as e:
        logger.error(f"Error getting profile data: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

@profile_api_bp.route("/api/ratings/profile/update", methods=["POST"])
@token_required
def update_profile(user_id=None, **kwargs):
    """Update user profile data for ratings section"""
    try:
        # If user_id is None, use the user_id from the session
        if user_id is None:
            user_id = session.get('user_id')
            if not user_id:
                logger.error("No user_id found in request")
                return jsonify({"error": "Not authorized"}), 401
        
        # Get update data
        data = request.json
        field = data.get("field")
        value = data.get("value", "")
        
        if not field:
            return jsonify({"error": "Field is required"}), 400
        
        # Validate field and value
        is_valid, processed_value = validate_profile_data(field, value)
        
        if not is_valid:
            return jsonify({"error": processed_value}), 400
        
        logger.info(f"Updating {field} for user_id: {user_id}")
        
        # Update or create rating settings document
        now = datetime.now()
        rating_settings_collection.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    f"profile.{field}": processed_value,
                    "last_updated": now
                }
            },
            upsert=True
        )
        
        return jsonify({"success": True, "field": field, "value": processed_value})
    
    except Exception as e:
        logger.error(f"Error updating profile data: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

def init_app(app):
    """Register Blueprint with main Flask app"""
    logger.info("Registering profile_api blueprint")
    app.register_blueprint(profile_api_bp)
    
    # Create indexes
    try:
        # Index for rating settings collection
        rating_settings_collection.create_index([("user_id", 1)], 
                                         unique=True, 
                                         name="rating_settings_user_id_unique_idx", 
                                         background=True)
        
        logger.info("Rating settings indexes created successfully")
    except Exception as e:
        logger.warning(f"Warning: Error creating rating settings indexes: {e}")
    
    return app 