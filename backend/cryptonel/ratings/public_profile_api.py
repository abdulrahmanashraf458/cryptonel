import os
import json
import logging
from datetime import datetime
from flask import Blueprint, jsonify, request
from pymongo import MongoClient
from bson import ObjectId
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.exceptions import TooManyRequests

# Import Redis from cache_utils
from backend.utils.cache_utils import get_redis

# Setup logger - Use central logging configuration
logger = logging.getLogger("public_profile_api")

# Create Blueprint for public profile API
public_profile_api_bp = Blueprint('public_profile_api', __name__)

# Initialize Limiter
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=os.environ.get('REDIS_URI', 'memory://'),
    strategy="fixed-window"
)

# Database connection
MONGODB_URI = os.getenv("DATABASE_URL")
client = MongoClient(MONGODB_URI)
db = client["cryptonel_wallet"]
users_collection = db["users"]
discord_users_collection = db["discord_users"]
rating_settings_collection = db["rating_settings"]
ratings_collection = db["ratings"]
rating_stats_collection = db["user_rating_stats"]

# Redis client for caching
redis_client = get_redis()
CACHE_EXPIRATION = 300  # 5 minutes

# Helper function to format timestamps
def _serialize_timestamp(timestamp):
    """Convert datetime to ISO format string"""
    if isinstance(timestamp, datetime):
        return timestamp.isoformat()
    return timestamp

@public_profile_api_bp.route("/api/public-profile/<username>", methods=["GET"])
@limiter.limit("20/minute")
def get_public_profile(username):
    """Get public profile data for ratings section - accessible without authentication"""
    
    # --- Pagination ---
    try:
        page = int(request.args.get('page', 1))
        if page < 1: page = 1
    except ValueError:
        page = 1
    limit = 100
    skip = (page - 1) * limit

    cache_key = f"public_profile:{username}:page:{page}"
    
    try:
        if redis_client:
            cached_data = redis_client.get(cache_key)
            if cached_data:
                logger.info(f"Cache hit for public profile: {username} page: {page}")
                return jsonify(json.loads(cached_data))
    except Exception as e:
        logger.error(f"Redis cache GET error: {e}", exc_info=True)

    logger.info(f"Cache miss for public profile: {username} page: {page}")
    
    try:
        # Get user information, including staff status and title
        user = users_collection.find_one(
            {"username": username},
            {"user_id": 1, "username": 1, "avatar": 1, "premium": 1, "verified": 1, "vip": 1, "staff": 1, "title": 1, "_id": 0}
        )
        
        if not user:
            logger.error(f"User not found for username: {username}")
            return jsonify({"success": False, "error": "User not found"}), 404
        
        user_id = user.get("user_id")
        
        # Add premium/verified status if available
        user_extended = users_collection.find_one(
            {"user_id": user_id},
            {"premium": 1, "verified": 1, "vip": 1, "account_type": 1, "_id": 0}
        )
        
        if user_extended:
            user.update(user_extended)
        
        # Get rating settings for this user
        settings = rating_settings_collection.find_one({"user_id": user_id})
        
        # Default profile data
        profile_data = {
            "title": "",
            "bio": ""
        }
        
        # Default appearance settings (simplified version)
        appearance_data = {
            "theme": "default",
            "ratingStyle": "stars",
            "cardStyle": "modern",
            "fontStyle": "default",
            "customThemeColors": {
                "primary": "#4338ca",
                "secondary": "#6366f1",
                "text": "#ffffff",
                "background": "#111827"
            },
            "showAnimation": True,
            "highlightTopRatings": True
        }
        
        # If settings exist, update profile and appearance data
        if settings:
            if "profile" in settings:
                profile_data.update(settings["profile"])
                
            if "appearance" in settings:
                appearance_data.update(settings["appearance"])
                
            # Add appearance data to user object
            user["appearance"] = appearance_data
            
            # Add profile data to user object
            user["bio"] = profile_data.get("bio", "")
            user["title"] = profile_data.get("title", "")
            
            # Get advanced settings
            if "settings" in settings:
                user["settings"] = settings["settings"]
        
        # Get rating statistics
        stats = rating_stats_collection.find_one({"user_id": user_id})
        
        # Default ratings data
        ratings_data = {
            "total_ratings": 0,
            "average_rating": 0,
            "ratings": []
        }
        
        # Apply settings to determine if and how ratings are shown
        show_ratings = True
        show_comments = True
        show_rating_count = True
        show_usernames_only = False
        sort_by_newest = True
        
        if settings and "settings" in settings:
            adv_settings = settings["settings"]
            show_comments = adv_settings.get("showComments", True)
            show_rating_count = adv_settings.get("showRatingCount", True)
            show_usernames_only = adv_settings.get("showUsernameOnly", False)
            sort_by_newest = adv_settings.get("sortByNewest", True)
        
        # If stats exist, update ratings data
        if stats:
            ratings_data["total_ratings"] = stats.get("total_ratings", 0)
            ratings_data["average_rating"] = stats.get("average_rating", 0)
            
            # Add distribution data
            if "distribution_percentage" in stats:
                ratings_data["distribution"] = stats["distribution_percentage"]
            
            # Add featured quote if available
            if "featured_quote" in stats:
                ratings_data["featured_quote"] = stats["featured_quote"]
                
        # Get total rating count for pagination
        total_ratings_count = ratings_collection.count_documents({"recipient_id": user_id})
        total_pages = (total_ratings_count + limit - 1) // limit if total_ratings_count > 0 else 1

        # Get actual ratings with pagination
        sort_direction = -1 if sort_by_newest else 1
        ratings_cursor = ratings_collection.find(
            {"recipient_id": user_id}
        ).sort("timestamp", sort_direction).skip(skip).limit(limit)
        
        ratings_list = list(ratings_cursor)
        
        # Format ratings based on user settings
        for rating in ratings_list:
            # Convert ObjectId to string
            if "_id" in rating:
                rating["_id"] = str(rating["_id"])
                
            # Format timestamp
            if "timestamp" in rating:
                rating["timestamp"] = _serialize_timestamp(rating["timestamp"])
                
            # Remove comments if not showing comments
            if not show_comments:
                rating.pop("comment", None)
                
            # Show username only if set
            if show_usernames_only:
                rating.pop("rater_id", None)
        
        ratings_data["ratings"] = ratings_list
        ratings_data["total_pages"] = total_pages
        ratings_data["current_page"] = page
        
        # Prepare response
        response_data = {
            "success": True,
            "user": user,
            "ratings": ratings_data
        }
        
        # Cache the response
        try:
            if redis_client:
                redis_client.set(cache_key, json.dumps(response_data), ex=CACHE_EXPIRATION)
                logger.info(f"Cached public profile for: {username} page: {page}")
        except Exception as e:
            logger.error(f"Redis cache SET error: {e}", exc_info=True)
            
        return jsonify(response_data)
    
    except Exception as e:
        logger.error(f"Error getting public profile data: {e}", exc_info=True)
        return jsonify({"success": False, "error": "Internal server error"}), 500

@public_profile_api_bp.route("/api/discord-users", methods=["GET"])
@limiter.limit("20/minute")
def get_discord_users():
    """Get rich user data for multiple users, including avatars and badges."""
    user_ids_str = request.args.get("ids", "")
    user_ids = sorted(list(set(user_ids_str.split(",")))) if user_ids_str else []
    
    if not user_ids:
        return jsonify({"success": False, "error": "No user IDs provided"}), 400
    
    cache_key = f"rich_users_info:{','.join(user_ids)}"
    
    try:
        if redis_client:
            cached_data = redis_client.get(cache_key)
            if cached_data:
                logger.info(f"Cache hit for discord_users: {','.join(user_ids)}")
                return jsonify(json.loads(cached_data))
    except Exception as e:
        logger.error(f"Redis cache GET error: {e}", exc_info=True)

    logger.info(f"Cache miss for rich_users_info: {','.join(user_ids)}")
    
    try:
        # Use an aggregation pipeline to securely fetch data from both collections
        pipeline = [
            {"$match": {"user_id": {"$in": user_ids}}},
            {
                "$lookup": {
                    "from": "users",
                    "localField": "user_id",
                    "foreignField": "user_id",
                    "as": "main_user_data"
                }
            },
            {
                "$unwind": {
                    "path": "$main_user_data",
                    "preserveNullAndEmptyArrays": True
                }
            },
            {
                "$project": {
                    "_id": 0,
                    "user_id": 1,
                    "username": 1,
                    "avatar": 1,
                    "verified": {"$ifNull": ["$main_user_data.verified", False]},
                    "premium": {"$ifNull": ["$main_user_data.premium", False]},
                    "vip": {"$ifNull": ["$main_user_data.vip", False]},
                    "staff": {"$ifNull": ["$main_user_data.staff", False]},
                }
            }
        ]
        users = list(discord_users_collection.aggregate(pipeline))
        
        if not users:
            return jsonify({"success": False, "error": "No users found"}), 404
            
        response_data = {"success": True, "users": users}
        
        # Cache the response
        try:
            if redis_client:
                redis_client.set(cache_key, json.dumps(response_data), ex=CACHE_EXPIRATION)
                logger.info(f"Cached discord_users for: {','.join(user_ids)}")
        except Exception as e:
            logger.error(f"Redis cache SET error: {e}", exc_info=True)
            
        return jsonify(response_data)
    
    except Exception as e:
        logger.error(f"Error getting rich user data: {e}", exc_info=True)
        return jsonify({"success": False, "error": "Internal server error"}), 500

# Helper function to recalculate user stats
def _recalculate_stats(user_id):
    """Recalculate and update rating stats for a user."""
    ratings = list(ratings_collection.find({"recipient_id": user_id}))
    if not ratings:
        rating_stats_collection.update_one(
            {"user_id": user_id},
            {"$set": {"total_ratings": 0, "average_rating": 0, "distribution": [], "distribution_percentage": []}},
            upsert=True
        )
        return

    total_ratings = len(ratings)
    average_rating = sum(r['stars'] for r in ratings) / total_ratings
    
    distribution = {i: 0 for i in range(1, 6)}
    for r in ratings:
        distribution[r['stars']] += 1
        
    dist_list = [{"stars": s, "count": c} for s, c in distribution.items()]
    dist_percent_list = [{"stars": s, "percentage": round((c / total_ratings) * 100)} for s, c in distribution.items()]

    rating_stats_collection.update_one(
        {"user_id": user_id},
        {"$set": {
            "total_ratings": total_ratings,
            "average_rating": round(average_rating, 2),
            "distribution": dist_list,
            "distribution_percentage": dist_percent_list
        }},
        upsert=True
    )
    logger.info(f"Recalculated stats for user_id: {user_id}")


@public_profile_api_bp.route("/api/public-profile/<username>/rate", methods=["POST"])
@limiter.limit("10/minute") # Keep a reasonable limit
def add_public_rating(username):
    """Add a new rating to a user's public profile."""
    data = request.json
    stars = data.get("stars")
    comment = data.get("comment", "").strip()

    # --- 1. reCAPTCHA Verification REMOVED ---

    # --- 2. Check User Settings ---
    user_settings = rating_settings_collection.find_one({"username": username})
    if not user_settings or not user_settings.get("advanced_settings", {}).get("allowAnonymousRatings", False):
        return jsonify({"success": False, "error": "This user does not accept ratings from the public."}), 403

    # --- 3. Validate Input ---
    if not isinstance(stars, int) or not 1 <= stars <= 5:
        return jsonify({"success": False, "error": "Invalid star rating. Must be between 1 and 5."}), 400

    if len(comment) > 1000: # Limit comment length
        return jsonify({"success": False, "error": "Comment cannot exceed 1000 characters."}), 400

    # --- 4. Submit Rating ---
    try:
        user = users_collection.find_one({"username": username}, {"user_id": 1})
        if not user:
            return jsonify({"success": False, "error": "User not found"}), 404
        
        recipient_id = user["user_id"]
        
        new_rating = {
            "recipient_id": recipient_id,
            "rater_id": "0",  # '0' for anonymous
            "rater_username": "Anonymous",
            "stars": stars,
            "comment": comment,
            "timestamp": datetime.utcnow()
        }
        
        ratings_collection.insert_one(new_rating)
        
        # --- 5. Recalculate Stats & Clear Cache ---
        _recalculate_stats(recipient_id)
        if redis_client:
            # Clear all pages of this user's profile cache
            keys_to_delete = redis_client.keys(f"public_profile:{username}:page:*")
            if keys_to_delete:
                redis_client.delete(*keys_to_delete)
        
        return jsonify({"success": True, "message": "Rating submitted successfully"})

    except Exception as e:
        logger.error(f"Error submitting rating: {e}", exc_info=True)
        return jsonify({"success": False, "error": "Internal server error"}), 500

def init_app(app):
    """Initialize public profile API"""
    limiter.init_app(app)
    app.register_blueprint(public_profile_api_bp)
    logger.info("Public profile API initialized with caching and rate limiting") 