import os
import json
import logging
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request, session
from pymongo import MongoClient, DESCENDING
from bson import ObjectId
from backend.jwt_utils import token_required

# Setup logger
logger = logging.getLogger("ratings_api")
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# Create Blueprint for ratings
ratings_api_bp = Blueprint('ratings_api', __name__)

# Database connection
MONGODB_URI = os.getenv("DATABASE_URL")
client = MongoClient(MONGODB_URI)
db = client["cryptonel_wallet"]
users_collection = db["users"]
ratings_collection = db["ratings"]  # Collection for individual ratings
rating_stats_collection = db["user_rating_stats"]  # Collection for rating statistics

# Helper functions
def _serialize_timestamp(ts):
    """Convert various timestamp formats to ISO strings"""
    if isinstance(ts, datetime):
        return ts.isoformat()
    if isinstance(ts, dict) and "$date" in ts:
        return ts["$date"]
    if isinstance(ts, str):
        return ts
    return None

def calculate_average_rating(ratings):
    """Calculate average rating from ratings"""
    if not ratings or len(ratings) == 0:
        return 0
    
    total = sum(rating["stars"] for rating in ratings)
    return round(total / len(ratings), 1)  # Round to 1 decimal place

def update_rating_stats(user_id, username):
    """Update rating statistics for a user"""
    try:
        # Get all ratings for this user
        ratings_cursor = ratings_collection.find({"recipient_id": user_id})
        ratings = list(ratings_cursor)
        
        logger.info(f"Updating stats for user {user_id}, found {len(ratings)} ratings")
        
        if not ratings:
            # If no ratings, create default stats
            default_stats = {
                "user_id": user_id,
                "username": username,
                "total_ratings": 0,
                "average_rating": 0,
                "distribution": {
                    "1": 0,
                    "2": 0,
                    "3": 0,
                    "4": 0,
                    "5": 0
                },
                "distribution_percentage": [
                    {"stars": 5, "percentage": 0},
                    {"stars": 4, "percentage": 0},
                    {"stars": 3, "percentage": 0},
                    {"stars": 2, "percentage": 0},
                    {"stars": 1, "percentage": 0}
                ],
                "featured_quote": None,
                "last_updated": datetime.now()
            }
            
            # Update or create stats document
            rating_stats_collection.update_one(
                {"user_id": user_id},
                {"$set": default_stats},
                upsert=True
            )
            
            logger.info(f"Created default stats for user {user_id} (no ratings)")
            return default_stats
        
        # Calculate statistics
        total_ratings = len(ratings)
        average_rating = calculate_average_rating(ratings)
        
        # Calculate rating distribution
        distribution = {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0}
        for rating in ratings:
            stars = str(rating["stars"])
            if stars in distribution:
                distribution[stars] += 1
        
        logger.info(f"Raw distribution counts: {distribution}")
        
        # Calculate percentage distribution
        distribution_percentage = []
        for stars in range(5, 0, -1):  # 5 down to 1
            stars_str = str(stars)
            count = distribution[stars_str]
            percentage = round((count / total_ratings * 100) if total_ratings > 0 else 0)
            distribution_percentage.append({
                "stars": stars,
                "percentage": percentage
            })
        
        logger.info(f"Calculated distribution percentages: {distribution_percentage}")
        
        # Find featured quote (newest rating with comment)
        featured_quote = None
        # First try to find a 4+ star rating with comment
        for rating in sorted(ratings, key=lambda r: r.get("timestamp", datetime.min), reverse=True):
            if rating.get("stars", 0) >= 4 and rating.get("comment"):
                featured_quote = {
                    "text": rating["comment"],
                    "author": rating.get("rater_username", "User"),
                    "stars": rating["stars"]
                }
                logger.info(f"Found 4+ star featured quote: {featured_quote}")
                break
        
        # If no 4+ star rating with comment, use the newest rating with any comment
        if not featured_quote:
            for rating in sorted(ratings, key=lambda r: r.get("timestamp", datetime.min), reverse=True):
                if rating.get("comment"):
                    featured_quote = {
                        "text": rating["comment"],
                        "author": rating.get("rater_username", "User"),
                        "stars": rating["stars"]
                    }
                    logger.info(f"Found fallback featured quote: {featured_quote}")
                    break
        
        # Create stats document
        stats = {
            "user_id": user_id,
            "username": username,
            "total_ratings": total_ratings,
            "average_rating": average_rating,
            "distribution": distribution,
            "distribution_percentage": distribution_percentage,
            "featured_quote": featured_quote,
            "last_updated": datetime.now()
        }
        
        # Update or create stats document
        rating_stats_collection.update_one(
            {"user_id": user_id},
            {"$set": stats},
            upsert=True
        )
        
        logger.info(f"Successfully updated stats for user {user_id}: total={total_ratings}, avg={average_rating}")
        return stats
    
    except Exception as e:
        logger.error(f"Error updating rating statistics: {e}", exc_info=True)
        return None

# API Endpoints

@ratings_api_bp.route("/api/ratings/user/current", methods=["GET"])
@token_required
def get_user_ratings(user_id=None, **kwargs):
    """Get ratings for the current user"""
    try:
        # If user_id is None, use the user_id from the session
        if user_id is None:
            user_id = session.get('user_id')
            if not user_id:
                logger.error("No user_id found in request")
                return jsonify({"error": "Not authorized"}), 401
        
        logger.info(f"Fetching ratings for user_id: {user_id}")
        
        # Get user information
        user = users_collection.find_one(
            {"user_id": user_id},
            {"username": 1, "_id": 0}
        )
        
        if not user:
            logger.error(f"User not found for user_id: {user_id}")
            return jsonify({"error": "User not found"}), 404
        
        username = user.get("username")
        logger.info(f"Found user: {username}")
        
        # Get rating statistics
        stats = rating_stats_collection.find_one({"user_id": user_id})
        
        # If no stats, update them
        if not stats:
            logger.info(f"No rating stats found for user {user_id}, generating default stats")
            stats = update_rating_stats(user_id, username)
        else:
            logger.info(f"Found rating stats for user {user_id}: total_ratings={stats.get('total_ratings', 0)}, avg={stats.get('average_rating', 0)}")
            
            # Check if stats need to be updated (if they're older than 1 hour)
            if "last_updated" in stats:
                last_updated = stats["last_updated"]
                if isinstance(last_updated, datetime) and (datetime.now() - last_updated).total_seconds() > 3600:
                    logger.info(f"Stats are older than 1 hour, updating them")
                    stats = update_rating_stats(user_id, username)
        
        # Get ratings
        ratings_data = list(ratings_collection.find(
            {"recipient_id": user_id}
        ).sort("timestamp", -1).limit(50))
        
        logger.info(f"Found {len(ratings_data)} ratings for user {user_id}")
        
        # Format timestamps
        for rating in ratings_data:
            if "timestamp" in rating:
                rating["timestamp"] = _serialize_timestamp(rating["timestamp"])
            # Convert ObjectId to string
            if "_id" in rating:
                rating["_id"] = str(rating["_id"])
        
        # Prepare rating distribution
        distribution = []
        if stats and "distribution_percentage" in stats:
            distribution = stats["distribution_percentage"]
            logger.info(f"Using distribution from stats: {distribution}")
        else:
            # Create default distribution
            distribution = [
                {"stars": 5, "percentage": 0},
                {"stars": 4, "percentage": 0},
                {"stars": 3, "percentage": 0},
                {"stars": 2, "percentage": 0},
                {"stars": 1, "percentage": 0}
            ]
            logger.info("Using default distribution (all zeros)")
        
        # Prepare featured quote
        featured_quote = stats.get("featured_quote") if stats else None
        
        # If no featured quote in stats but we have ratings with comments, use the latest one
        if not featured_quote and ratings_data:
            for rating in ratings_data:
                if rating.get("comment"):
                    featured_quote = {
                        "text": rating["comment"],
                        "author": rating.get("rater_username", "Anonymous"),
                        "stars": rating.get("stars", 0)
                    }
                    logger.info(f"Created featured quote from latest rating: {featured_quote}")
                    break
        
        # If still no featured quote, use default
        if not featured_quote:
            featured_quote = {
                "text": "No ratings yet",
                "author": "",
                "stars": 0
            }
            logger.info("Using default featured quote (No ratings yet)")
        
        # Prepare response
        response = {
            "user_id": user_id,
            "username": username,
            "total_ratings": stats.get("total_ratings", 0) if stats else 0,
            "average_rating": stats.get("average_rating", 0) if stats else 0,
            "distribution": distribution,
            "featured_quote": featured_quote,
            "ratings": ratings_data,
            "last_updated": _serialize_timestamp(stats.get("last_updated", datetime.now())) if stats else _serialize_timestamp(datetime.now())
        }
        
        # Log final response data for debugging
        logger.info(f"Sending ratings response: user_id={response['user_id']}, total_ratings={response['total_ratings']}, avg={response['average_rating']}")
        logger.info(f"Response includes {len(response['ratings'])} individual ratings")
        
        return jsonify(response)
    
    except Exception as e:
        logger.error(f"Error getting user ratings: {e}", exc_info=True)
        return jsonify({
            "error": "Internal server error",
            "user_id": user_id if 'user_id' in locals() else None,
            "debug_info": str(e)
        }), 500

@ratings_api_bp.route("/api/ratings/user/<recipient_id>", methods=["GET"])
@token_required
def get_user_rating_by_id(recipient_id, user_id=None, **kwargs):
    """Get ratings for a specific user"""
    try:
        # If user_id is None, use the user_id from the session
        if user_id is None:
            user_id = session.get('user_id')
            if not user_id:
                return jsonify({"error": "Not authorized"}), 401
        
        # Get recipient user information
        recipient = users_collection.find_one(
            {"user_id": recipient_id},
            {"username": 1, "_id": 0}
        )
        
        if not recipient:
            return jsonify({"error": "User not found"}), 404
        
        recipient_username = recipient.get("username")
        
        # Get rating statistics
        stats = rating_stats_collection.find_one({"user_id": recipient_id})
        
        # If no stats, update them
        if not stats:
            stats = update_rating_stats(recipient_id, recipient_username)
        
        # Get ratings
        ratings_data = list(ratings_collection.find(
            {"recipient_id": recipient_id}
        ).sort("timestamp", -1).limit(50))
        
        # Format timestamps
        for rating in ratings_data:
            if "timestamp" in rating:
                rating["timestamp"] = _serialize_timestamp(rating["timestamp"])
            # Convert ObjectId to string
            if "_id" in rating:
                rating["_id"] = str(rating["_id"])
        
        # Check if current user has rated this user
        current_user_rating = ratings_collection.find_one({
            "rater_id": user_id,
            "recipient_id": recipient_id
        })
        
        if current_user_rating and "_id" in current_user_rating:
            current_user_rating["_id"] = str(current_user_rating["_id"])
            if "timestamp" in current_user_rating:
                current_user_rating["timestamp"] = _serialize_timestamp(current_user_rating["timestamp"])
        
        # Prepare rating distribution
        distribution = []
        if stats and "distribution_percentage" in stats:
            distribution = stats["distribution_percentage"]
        else:
            # Create default distribution
            distribution = [
                {"stars": 5, "percentage": 0},
                {"stars": 4, "percentage": 0},
                {"stars": 3, "percentage": 0},
                {"stars": 2, "percentage": 0},
                {"stars": 1, "percentage": 0}
            ]
        
        # Prepare response
        response = {
            "user_id": recipient_id,
            "username": recipient_username,
            "total_ratings": stats.get("total_ratings", 0) if stats else 0,
            "average_rating": stats.get("average_rating", 0) if stats else 0,
            "distribution": distribution,
            "current_user_rating": current_user_rating,
            "ratings": ratings_data
        }
        
        return jsonify(response)
    
    except Exception as e:
        logger.error(f"Error getting user ratings: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

@ratings_api_bp.route("/api/ratings/submit", methods=["POST"])
@token_required
def submit_rating(user_id=None, **kwargs):
    """Submit a rating for a user"""
    try:
        # If user_id is None, use the user_id from the session
        if user_id is None:
            user_id = session.get('user_id')
            if not user_id:
                return jsonify({"error": "Not authorized"}), 401
        
        # Get rating data
        data = request.json
        recipient_id = data.get("recipient_id")
        stars = data.get("stars")
        comment = data.get("comment", "")
        
        # Validate data
        if not recipient_id:
            return jsonify({"error": "Recipient ID is required"}), 400
        
        if not stars or not isinstance(stars, int) or stars < 1 or stars > 5:
            return jsonify({"error": "Rating must be between 1 and 5 stars"}), 400
        
        # Don't allow rating yourself
        if recipient_id == user_id:
            return jsonify({"error": "You cannot rate yourself"}), 400
        
        # Check comment length - maximum 300 characters
        MAX_COMMENT_LENGTH = 300
        if comment and len(comment) > MAX_COMMENT_LENGTH:
            return jsonify({"error": f"Comment cannot exceed {MAX_COMMENT_LENGTH} characters"}), 400
        
        # Get rater information
        rater = users_collection.find_one(
            {"user_id": user_id},
            {"username": 1, "_id": 0}
        )
        
        if not rater:
            return jsonify({"error": "Rater not found"}), 404
        
        rater_username = rater.get("username")
        
        # Get recipient information
        recipient = users_collection.find_one(
            {"user_id": recipient_id},
            {"username": 1, "_id": 0}
        )
        
        if not recipient:
            return jsonify({"error": "Recipient not found"}), 404
        
        recipient_username = recipient.get("username")
        
        # Create rating document
        now = datetime.now()
        rating_document = {
            "rater_id": user_id,
            "rater_username": rater_username,
            "recipient_id": recipient_id,
            "recipient_username": recipient_username,
            "stars": stars,
            "comment": comment,
            "timestamp": now,
            "updated_at": now
        }
        
        # Check if user has already rated this user
        existing_rating = ratings_collection.find_one({
            "rater_id": user_id,
            "recipient_id": recipient_id
        })
        
        if existing_rating:
            # Update existing rating
            ratings_collection.update_one(
                {"_id": existing_rating["_id"]},
                {"$set": {
                    "stars": stars,
                    "comment": comment,
                    "updated_at": now
                }}
            )
        else:
            # Add new rating
            ratings_collection.insert_one(rating_document)
        
        # Update rating statistics
        update_rating_stats(recipient_id, recipient_username)
        
        return jsonify({"success": True})
    
    except Exception as e:
        logger.error(f"Error submitting rating: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

@ratings_api_bp.route("/api/ratings/user/given", methods=["GET"])
@token_required
def get_ratings_given(user_id=None, **kwargs):
    """Get ratings given by the user"""
    try:
        # If user_id is None, use the user_id from the session
        if user_id is None:
            user_id = session.get('user_id')
            if not user_id:
                return jsonify({"error": "Not authorized"}), 401
        
        # Find all ratings given by the user
        ratings_given = list(ratings_collection.find(
            {"rater_id": user_id}
        ).sort("timestamp", -1).limit(50))
        
        # Format timestamps and convert ObjectIds
        for rating in ratings_given:
            if "timestamp" in rating:
                rating["timestamp"] = _serialize_timestamp(rating["timestamp"])
            if "_id" in rating:
                rating["_id"] = str(rating["_id"])
        
        return jsonify({"success": True, "ratings": ratings_given})
    
    except Exception as e:
        logger.error(f"Error getting ratings given: {e}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

def init_app(app):
    """Register Blueprint with main Flask app"""
    logger.info("Registering ratings_api blueprint")
    app.register_blueprint(ratings_api_bp)
    
    # Create indexes
    try:
        # Indexes for ratings collection
        ratings_collection.create_index([("recipient_id", 1)], background=True)
        ratings_collection.create_index([("rater_id", 1)], background=True)
        ratings_collection.create_index([("rater_id", 1), ("recipient_id", 1)], 
                                      unique=True, background=True)
        ratings_collection.create_index([("timestamp", -1)], background=True)
        
        # Indexes for rating stats collection
        rating_stats_collection.create_index([("user_id", 1)], 
                                           unique=True, 
                                           name="ratings_user_id_unique_idx", 
                                           background=True)
        rating_stats_collection.create_index([("average_rating", -1)], background=True)
        
        logger.info("Rating indexes created successfully")
    except Exception as e:
        logger.warning(f"Warning: Error creating rating indexes: {e}")
    
    return app 