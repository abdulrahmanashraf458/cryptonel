import os
import json
import time
import hashlib
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request, current_app, session
from pymongo import MongoClient, DESCENDING, IndexModel
from pymongo.errors import OperationFailure
from bson.decimal128 import Decimal128
import functools
from flask import make_response

# Create blueprint
leaderboard_bp = Blueprint('leaderboard', __name__)

# MongoDB connection
MONGODB_URI = os.environ.get('DATABASE_URL')
client = MongoClient(MONGODB_URI)
db = client['cryptonel_wallet']

# Simple in-memory cache implementation to replace werkzeug.contrib.cache
class SimpleCache:
    def __init__(self, threshold=500, default_timeout=300):
        self.cache = {}
        self.threshold = threshold
        self.default_timeout = default_timeout
        self.last_prune_time = time.time()
    
    def get(self, key):
        now = time.time()
        
        # Periodically prune to avoid memory leaks
        if now - self.last_prune_time > 60:  # Once a minute
            self._prune()
            self.last_prune_time = now
            
        if key in self.cache:
            value, expiry = self.cache[key]
            if expiry > now:
                return value
            else:
                # Delete expired item
                del self.cache[key]
        return None
    
    def set(self, key, value, timeout=None):
        if len(self.cache) >= self.threshold:
            self._prune()
            
        timeout = timeout if timeout is not None else self.default_timeout
        self.cache[key] = (value, time.time() + timeout)
        return True

    def delete(self, key):
        if key in self.cache:
            del self.cache[key]
            return True
        return False

    def clear(self):
        self.cache.clear()
        return True
    
    def _prune(self):
        # Remove expired items
        now = time.time()
        for k, (_, expiry) in list(self.cache.items()):
            if expiry <= now:
                del self.cache[k]
                
        # If still too many items, remove oldest
        if len(self.cache) >= self.threshold:
            sorted_items = sorted(self.cache.items(), key=lambda x: x[1][1])
            # Remove oldest 10% of items
            for k, _ in sorted_items[:max(1, int(len(sorted_items) * 0.1))]:
                del self.cache[k]

# Create a cache with a 2-minute timeout for better performance
cache = SimpleCache(threshold=500, default_timeout=120)

# Rate limiting implementation
class RateLimiter:
    def __init__(self, limit=10, window=60):
        self.limit = limit  # Max requests per window
        self.window = window  # Time window in seconds
        self.clients = {}
        self.last_cleanup = time.time()
    
    def is_rate_limited(self, client_id):
        now = time.time()
        
        # Clean up old entries to prevent memory leaks
        if now - self.last_cleanup > 300:  # Every 5 minutes
            self._cleanup()
            self.last_cleanup = now
        
        # Get or create client record
        if client_id not in self.clients:
            self.clients[client_id] = []
        
        # Remove timestamps outside current window
        client_timestamps = self.clients[client_id]
        current_window = [ts for ts in client_timestamps if ts > now - self.window]
        self.clients[client_id] = current_window
        
        # Check if client has exceeded rate limit
        if len(current_window) >= self.limit:
            return True
        
        # Add new timestamp
        current_window.append(now)
        return False
    
    def _cleanup(self):
        """Remove expired client records"""
        now = time.time()
        cutoff = now - self.window
        
        for client_id in list(self.clients.keys()):
            # Remove timestamps outside window
            self.clients[client_id] = [ts for ts in self.clients[client_id] if ts > cutoff]
            
            # Remove empty client records
            if not self.clients[client_id]:
                del self.clients[client_id]

# Create rate limiter - 10 requests per 2 seconds per IP
rate_limiter = RateLimiter(limit=10, window=2)

# Helper function to clear the leaderboard cache
def clear_leaderboard_cache():
    """Clear the leaderboard cache to force fresh data"""
    cache_keys = [k for k in cache.cache.keys() if k.startswith('leaderboard_')]
    for key in cache_keys:
        cache.delete(key)
    print(f"Cleared {len(cache_keys)} leaderboard cache entries")

# Helper function to generate avatar URL
def get_discord_avatar_url(user_id, avatar_hash):
    """Generate Discord avatar URL from user ID and avatar hash"""
    if not avatar_hash:
        return f"https://cdn.discordapp.com/embed/avatars/{int(user_id) % 5}.png"
    
    # Determine if avatar is animated (gif)
    extension = "gif" if avatar_hash.startswith("a_") else "png"
    return f"https://cdn.discordapp.com/avatars/{user_id}/{avatar_hash}.{extension}"

# Get client identifier for rate limiting
def get_client_id():
    ip = request.remote_addr
    user_agent = request.headers.get('User-Agent', '')
    # Use a hash to anonymize IP but still identify unique clients
    return hashlib.md5(f"{ip}:{user_agent}".encode()).hexdigest()

# Helper function to format public address
def format_partial_address(address):
    """Formats a public address to show only the start and end, for display."""
    if not isinstance(address, str) or len(address) < 12:
        return ""  # Return empty if invalid
    return f"{address[:6]}..{address[-4:]}"

# Cache decorator for leaderboard with improved cache invalidation strategy
def cache_leaderboard(timeout=120):  # Increased timeout to 2 minutes (120 seconds)
    def decorator(f):
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            # Always skip cache for authenticated users looking at their own changes 
            # or when explicitly requested with refresh parameter
            user_id = session.get('user_id')
            force_refresh = '_t' in request.args or 'refresh' in request.args
            
            # Generate cache key based on request path
            cache_key = f"leaderboard_{request.path}"
            
            # Skip cache for refresh requests or authenticated users
            if force_refresh:
                result = f(*args, **kwargs)
                # Still save to cache so other requests can benefit
                if hasattr(result, 'json') and callable(result.json):
                    cache.set(cache_key, result.json, timeout=timeout)
                elif isinstance(result, tuple) and len(result) == 2:
                    # Handle tuple return (data, status_code)
                    cache.set(cache_key, result[0], timeout=timeout)
                return result
                
            # Try to get from cache
            cached_data = cache.get(cache_key)
            
            if cached_data:
                # Special handling for authenticated users
                if user_id:
                    # Check if this is their own data so they see changes immediately
                    try:
                        # This is a simple check - in a real app you'd have more sophisticated logic
                        if any(entry.get('user_id') == user_id for entry in cached_data.get('data', [])):
                            # User's own data might have changed, bypass cache
                            result = f(*args, **kwargs)
                            # Update cache with new data
                            if hasattr(result, 'json') and callable(result.json):
                                cache.set(cache_key, result.json, timeout=timeout)
                            return result
                    except:
                        # If any error occurs, just use cache
                        pass
                
                # Modify cached data to indicate it came from cache
                if isinstance(cached_data, dict):
                    if 'meta' in cached_data:
                        cached_data['meta']['cache_status'] = 'hit'
                        cached_data['meta']['cached_at'] = datetime.utcnow().isoformat()
                    return jsonify(cached_data)
                return cached_data
                
            # Generate fresh response
            response = f(*args, **kwargs)
            
            # Store just the JSON data in cache, not the response object
            if hasattr(response, 'get_json') and callable(response.get_json):
                cache.set(cache_key, response.get_json(), timeout=timeout)
            elif isinstance(response, tuple) and len(response) == 2:
                if hasattr(response[0], 'get_json') and callable(response[0].get_json):
                    cache.set(cache_key, response[0].get_json(), timeout=timeout)
            return response
        return decorated_function
    return decorator

# Ensure we have indexes for performance
def ensure_indexes():
    """Safely create indexes without failing if they already exist"""
    try:
        # Check if indexes already exist to avoid conflicts
        existing_user_indexes = db.users.list_indexes()
        existing_discord_indexes = db.discord_users.list_indexes()
        
        # تحويلها إلى قائمة للاستخدام المتكرر
        existing_user_index_names = [idx.get('name') for idx in existing_user_indexes]
        existing_discord_index_names = [idx.get('name') for idx in existing_discord_indexes]
        
        print(f"Found existing indexes: {existing_user_index_names}")
        
        # تجنب إنشاء فهارس موجودة بالفعل
        if "ban_frozen_index" not in existing_user_index_names and "leaderboard_active_index" not in existing_user_index_names:
            try:
                # Create index on ban and frozen fields
                db['users'].create_index([("ban", 1), ("frozen", 1)], 
                                        background=True, 
                                        name="ban_frozen_index")
                print("Created ban/frozen index")
            except OperationFailure as e:
                print(f"Note: Could not create ban/frozen index: {str(e)}")
        else:
            print("Ban/frozen index already exists, skipping creation")
        
        # فهرس للتصنيف
        if "balance_numeric_index" not in existing_user_index_names and "leaderboard_balance_index" not in existing_user_index_names:
            try:
                # Create proper index for numeric balance sorting
                db['users'].create_index([("balance_numeric", -1)], 
                                        background=True,
                                        name="balance_numeric_index")
                print("Created balance index")
            except OperationFailure as e:
                print(f"Note: Could not create balance index: {str(e)}")
        else:
            print("Balance index already exists, skipping creation")
        
        # التحقق من وجود فهارس user_id
        user_id_indexes = [idx for idx in existing_user_index_names 
                          if "user_id" in idx]
        
        # Comprobar específicamente si existe el índice user_id_index_overview
        if "user_id_index_overview" in existing_user_index_names:
            print(f"User ID index 'user_id_index_overview' already exists, skipping creation")
        elif user_id_indexes:
            print(f"User ID indexes already exist: {user_id_indexes}, skipping creation")
        else:
            # لا توجد فهارس user_id، يمكننا إنشاء واحدة
            try:
                db['users'].create_index([("user_id", 1)], 
                                        background=True,
                                        name="user_id_leaderboard")
                print("Created users user_id index")
            except OperationFailure as e:
                print(f"Note: User ID index may already exist: {str(e)}")
        
        # التحقق من فهارس discord_users
        discord_user_id_indexes = [idx for idx in existing_discord_index_names 
                                  if "user_id" in idx]
        
        if not discord_user_id_indexes:
            try:
                db['discord_users'].create_index([("user_id", 1)], 
                                               background=True,
                                               name="discord_user_id_leaderboard")
                print("Created discord_users user_id index")
            except OperationFailure as e:
                print(f"Note: Discord user ID index may already exist: {str(e)}")
        else:
            print(f"Discord user ID indexes already exist: {discord_user_id_indexes}, skipping creation")
    
    except Exception as e:
        print(f"Warning: Error checking MongoDB indexes: {str(e)}")
    
    print("Leaderboard indexes verified")

@leaderboard_bp.route('/leaderboard', methods=['GET'])
@cache_leaderboard(timeout=120)  # Increased timeout to 2 minutes (120 seconds)
def get_leaderboard():
    """Get top 100 users ordered by balance - optimized version with rate limiting"""
    try:
        # Apply rate limiting
        client_id = get_client_id()
        if rate_limiter.is_rate_limited(client_id):
            print(f"Rate limited client: {client_id}")
            response = make_response(jsonify({
                'success': False,
                'error': 'Too many requests. Please wait before trying again.',
                'retry_after': 2  # Seconds before client should retry
            }))
            response.status_code = 429
            response.headers['Retry-After'] = '2'
            response.headers['X-RateLimit-Limit'] = str(rate_limiter.limit)
            response.headers['X-RateLimit-Window'] = str(rate_limiter.window)
            return response
            
        start_time = datetime.now()
        
        # Get collections
        users_collection = db['users']
        discord_users_collection = db['discord_users']
        
        # Create projection to only fetch needed fields for better performance
        user_projection = {
            "_id": 0,
            "user_id": 1,
            "username": 1,
            "balance": 1, 
            "membership": 1, 
            "verified": 1, 
            "profile_hidden": 1, 
            "public_address": 1, 
            "premium": 1, 
            "vip": 1,
            "staff": 1,
            "hide_avatar": 1,
            "hide_balance": 1, 
            "hide_address": 1, 
            "hide_badges": 1,
            "hide_verification": 1,
            "hidden_wallet_mode": 1,
            "primary_color": 1, 
            "secondary_color": 1, 
            "highlight_color": 1,
            "background_color": 1,
            "bio": 1,
            "last_active": 1
        }
        
        # Find all active users - directly sort and limit in MongoDB for better efficiency
        pipeline = [
            # Remove the filter for banned accounts
            # {"$match": {"ban": False}},  # إزالة شرط frozen: False للسماح بظهور الحسابات المجمدة
            {"$project": user_projection},
            {"$addFields": {
                "numeric_balance": {
                    "$convert": {
                        "input": "$balance",
                        "to": "double",
                        "onError": 0.0,
                        "onNull": 0.0
                    }
                }
            }},
            {"$sort": {"numeric_balance": -1}},
            {"$limit": 100}
        ]
        
        # Execute the aggregation with a hint to use the balance index
        try:
            top_users = list(users_collection.aggregate(pipeline).hint("balance_numeric_index"))
        except Exception as e:
            # Fallback if hint fails (index might not exist)
            print(f"Hint failed, using default index: {str(e)}")
            top_users = list(users_collection.aggregate(pipeline))
        
        # Get user_ids to fetch avatar data in a single batch query
        user_ids = [user['user_id'] for user in top_users]
        
        # Create a lookup dictionary for avatar data - use a single query
        avatar_data = {}
        discord_users = discord_users_collection.find(
            {"user_id": {"$in": user_ids}},
            {"user_id": 1, "avatar": 1, "username": 1}
        )
        
        for discord_user in discord_users:
            avatar_data[discord_user['user_id']] = {
                'avatar': discord_user.get('avatar'),
                'discord_username': discord_user.get('username')
            }
        
        # Check if the current user is authenticated
        current_user_id = session.get('user_id')
        
        # Process user data and create leaderboard entries
        leaderboard = []
        for idx, user in enumerate(top_users):
            user_id = user['user_id']
            avatar_info = avatar_data.get(user_id, {'avatar': None, 'discord_username': None})
            
            is_current_user = current_user_id and current_user_id == user_id

            # Determine all privacy settings from the database first
            is_premium = user.get('premium') is True
            profile_hidden = user.get('profile_hidden', False)
            hide_address = is_premium and user.get('hide_address', False)
            hide_balance = is_premium and user.get('hide_balance', False)
            hide_badges = is_premium and (user.get('hide_badges', False) or user.get('hide_verification', False))
            hidden_wallet_mode = is_premium and user.get('hidden_wallet_mode', False)

            # --- Build the response entry field by field, respecting each independent privacy setting ---

            # 1. Handle identity fields (username, avatar, user_id) based ONLY on 'profile_hidden'
            if profile_hidden and not is_current_user:
                display_username = "Hidden Profile"
                display_avatar = None
                display_avatar_url = ""
                display_user_id = f"hidden_user_{idx + 1}"
            else:
                display_username = user.get('username', avatar_info.get('discord_username', 'Unknown'))
                display_avatar = avatar_info.get('avatar')
                display_avatar_url = get_discord_avatar_url(user_id, display_avatar)
                display_user_id = user_id

            # 2. Handle public address based ONLY on 'hide_address' (premium only)
            if hide_address and not is_current_user:
                display_public_address = "hidden"
            else:
                # Format the address on the backend before sending to the client
                full_address = user.get('public_address', '')
                display_public_address = format_partial_address(full_address)

            # 3. Handle balance based ONLY on 'hide_balance' and 'hidden_wallet_mode' (premium only)
            if hide_balance and not is_current_user:
                display_balance = "Hidden"
                formatted_balance = "Hidden"
            elif hidden_wallet_mode and not is_current_user:
                display_balance = "0"
                formatted_balance = "0.00 (Hidden)"
            else:
                display_balance = user.get('balance', '0')
                numeric_balance = user.get('numeric_balance', 0.0)
                formatted_balance = f"{numeric_balance:.2f}"
            
            # 4. Handle badges/verification based ONLY on 'hide_badges' (premium only)
            show_verification_badge = not (hide_badges and not is_current_user)

            # 5. Assemble the final entry
            entry = {
                'rank': idx + 1,
                'user_id': display_user_id,
                'username': display_username,
                'avatar': display_avatar,
                'avatar_url': display_avatar_url,
                'balance': display_balance,
                'formatted_balance': formatted_balance,
                'public_address': display_public_address,

                'verified': user.get('verified', False) and show_verification_badge,
                'is_premium': is_premium, # Send real premium status for UI logic
                'is_vip': user.get('vip', False),
                'is_staff': user.get('staff', False),

                # Send the actual privacy settings for the frontend to use
                'profile_hidden': profile_hidden,
                'hide_address': hide_address,
                'hide_balance': hide_balance,
                'hide_badges': hide_badges,
                'hidden_wallet_mode': hidden_wallet_mode,
                
                'is_current_user': is_current_user,
                'is_frozen': user.get('frozen', False),
                'membership': user.get('membership', 'Standard'),
            }
            leaderboard.append(entry)
        
        # Calculate execution time
        execution_time = (datetime.now() - start_time).total_seconds()
        
        # Create response data dictionary
        response_data = {
            'success': True,
            'data': leaderboard,
            'timestamp': datetime.utcnow().isoformat(),
            'meta': {
                'execution_time_ms': round(execution_time * 1000, 2),
                'cache_status': 'miss',
                'count': len(leaderboard),
                'generated_at': datetime.utcnow().isoformat()
            }
        }
        
        # Add cache and compression headers to improve performance
        response = jsonify(response_data)
        
        # Add cache-control headers - prevent browser caching to ensure fresh data
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        response.headers['Vary'] = 'Accept-Encoding'
        
        return response
        
    except Exception as e:
        # Log error with more details for debugging
        print(f"Error in leaderboard: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve leaderboard data'
        }), 500

# Add API route to force-refresh the leaderboard cache
@leaderboard_bp.route('/leaderboard/refresh', methods=['GET', 'POST'])
def refresh_leaderboard_cache():
    """API route to force-refresh the leaderboard cache"""
    try:
        # Clear all leaderboard cache entries
        clear_leaderboard_cache()
        
        return jsonify({
            'success': True,
            'message': 'Leaderboard cache refreshed successfully'
        })
    except Exception as e:
        print(f"Error refreshing leaderboard cache: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to refresh leaderboard cache'
        }), 500

def init_app(app):
    """Initialize the leaderboard module with the Flask app"""
    app.register_blueprint(leaderboard_bp, url_prefix='/api')
    
    # Create MongoDB indexes on first initialization
    try:
        with app.app_context():
            ensure_indexes()
    except Exception as e:
        print(f"Warning: Could not create MongoDB indexes: {str(e)}")
    
    print("Leaderboard module initialized") 