import os
import json
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request, session
from pymongo import MongoClient, ASCENDING
from dotenv import load_dotenv
from bson import ObjectId, json_util
import random
import math
from bson.json_util import dumps
from functools import lru_cache
import logging

# Configure logger
logger = logging.getLogger('cryptonel.overview')

# Load environment variables
load_dotenv()

# Create Blueprint for Overview endpoints
overview_bp = Blueprint('overview', __name__)

# MongoDB connection
MONGODB_URI = os.getenv("DATABASE_URL")
client = MongoClient(MONGODB_URI)
db = client["cryptonel_wallet"]
users_collection = db["users"]
discord_users_collection = db["discord_users"]  # Add Discord users collection
transactions_collection = db["user_transactions"]
ratings_collection = db["ratings"]  # Add ratings collection
rating_stats_collection = db["user_rating_stats"]  # Collection for user rating statistics

# New collections for improved growth tracking system
growth_wallets_collection = db["growth_wallets"]  # Current wallet state (snapshots)
growth_wallet_history_collection = db["growth_wallet_history"]  # All changes over time
growth_wallet_snapshots_collection = db["growth_wallet_snapshots"]  # Daily fixed reports (optional)

# Legacy collection - kept for backward compatibility
wallet_growth_collection = db["wallet_growth"]

# Create necessary indexes for performance - with specific names and only if they don't exist
try:
    # Check existing indexes to avoid conflicts
    existing_indexes_dict = {}
    for collection in [users_collection, discord_users_collection, transactions_collection, 
                      ratings_collection, wallet_growth_collection, growth_wallets_collection,
                      growth_wallet_history_collection, growth_wallet_snapshots_collection]:
        existing_indexes_dict[collection.name] = []
        for idx in collection.list_indexes():
            existing_indexes_dict[collection.name].append(idx.get('name'))
    
    # Now create indexes with unique names if they don't exist yet
    if "user_id_index_overview" not in existing_indexes_dict[users_collection.name] and "user_id_overview_idx" not in existing_indexes_dict[users_collection.name]:
        # Verificación adicional para comprobar si ya existe algún índice en user_id
        # Obtener detalles de todos los índices existentes para verificar campos
        all_indexes = list(users_collection.list_indexes())
        user_id_index_exists = False
        
        # Comprobar si ya existe algún índice que use el campo user_id
        for idx in all_indexes:
            idx_keys = idx.get('key', {})
            if len(idx_keys) == 1 and "user_id" in idx_keys:
                print(f"Found existing user_id index with name: {idx.get('name')}")
                user_id_index_exists = True
                break
        
        if not user_id_index_exists:
            try:
                users_collection.create_index([("user_id", ASCENDING)], name="user_id_index_overview", background=True)
                print(f"Created user_id_index_overview")
            except Exception as e:
                print(f"Could not create user_id_index_overview: {str(e)}")
        else:
            print("Skipping creation of user_id_index_overview as index on field already exists")
        
    if "discord_user_id_idx" not in existing_indexes_dict[discord_users_collection.name]:
        discord_users_collection.create_index([("user_id", ASCENDING)], name="discord_user_id_idx", background=True)
        
    if "txn_user_id_idx" not in existing_indexes_dict[transactions_collection.name]:
        transactions_collection.create_index([("user_id", ASCENDING)], name="txn_user_id_idx", background=True)
        
    if "rating_user_id_idx" not in existing_indexes_dict[ratings_collection.name]:
        ratings_collection.create_index([("user_id", ASCENDING)], name="rating_user_id_idx", background=True)
        
    if "wallet_growth_id_idx" not in existing_indexes_dict[wallet_growth_collection.name]:
        wallet_growth_collection.create_index([("user_id", ASCENDING)], name="wallet_growth_id_idx", background=True)
    
    # Create indexes for new growth tracking collections
    if "growth_wallets_id_idx" not in existing_indexes_dict.get(growth_wallets_collection.name, []):
        growth_wallets_collection.create_index([("user_id", ASCENDING)], name="growth_wallets_id_idx", background=True, unique=True)
        
    if "growth_history_id_idx" not in existing_indexes_dict.get(growth_wallet_history_collection.name, []):
        growth_wallet_history_collection.create_index([("user_id", ASCENDING)], name="growth_history_id_idx", background=True)
        
    if "growth_history_date_idx" not in existing_indexes_dict.get(growth_wallet_history_collection.name, []):
        growth_wallet_history_collection.create_index([("timestamp", ASCENDING)], name="growth_history_date_idx", background=True)
        
    if "growth_history_compound_idx" not in existing_indexes_dict.get(growth_wallet_history_collection.name, []):
        growth_wallet_history_collection.create_index([("user_id", ASCENDING), ("timestamp", ASCENDING)], 
                                                    name="growth_history_compound_idx", background=True)
    
    if "growth_snapshots_id_idx" not in existing_indexes_dict.get(growth_wallet_snapshots_collection.name, []):
        growth_wallet_snapshots_collection.create_index([("user_id", ASCENDING)], name="growth_snapshots_id_idx", background=True)
        
    if "growth_snapshots_date_idx" not in existing_indexes_dict.get(growth_wallet_snapshots_collection.name, []):
        growth_wallet_snapshots_collection.create_index([("date", ASCENDING)], name="growth_snapshots_date_idx", background=True)
        
    print("MongoDB indexes created or already exist.")
except Exception as e:
    print(f"Warning: Could not create MongoDB indexes: {e}")

# Custom JSON encoder for MongoDB ObjectId
class MongoJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return json.JSONEncoder.default(self, obj)

# Cache storage with real-time validation
class TimedCache:
    def __init__(self, max_size=100):
        self.cache = {}
        self.expiry = {}
        self.max_size = max_size
        
    def get(self, key, collection=None, user_id=None, always_check_db=False):
        """
        Get a value from cache with DB validation
        
        Parameters:
        - key: The cache key
        - collection: MongoDB collection to check (optional)
        - user_id: User ID to check for (optional)
        - always_check_db: If True, always check DB for latest data
        
        For financial/critical data, set always_check_db=True to bypass cache
        """
        # For financial data or when requested, always get fresh data
        if always_check_db:
            return None
            
        if key in self.cache:
            # First check expiration
            if self.expiry[key] <= datetime.now():
                # Expired
                self._remove_key(key)
                return None
                
            # Check with DB if requested
            if collection and user_id:
                # Query the collection for _id to check if document exists and get modified time
                doc = collection.find_one(
                    {"user_id": user_id}, 
                    {"_id": 1, "last_modified": 1}
                )
                
                # If document exists in DB, check timestamp if available
                if doc:
                    last_modified = doc.get("last_modified")
                    # If the document was modified or doesn't have timestamp, invalidate cache
                    if not last_modified or "cache_timestamp" not in self.cache[key]:
                        self._remove_key(key)
                        return None
                    
                    # Compare timestamps if both exist
                    if last_modified > self.cache[key]["cache_timestamp"]:
                        self._remove_key(key)
                        return None
                else:
                    # Document doesn't exist anymore
                    self._remove_key(key)
                    return None
                    
            # Return the actual data, not the metadata wrapper
            return self.cache[key]["data"]
        return None
    
    def _remove_key(self, key):
        """Helper to remove a key from all dictionaries"""
        if key in self.cache:
            del self.cache[key]
        if key in self.expiry:
            del self.expiry[key]
        
    def set(self, key, value, ttl_seconds):
        """Set a value in cache with TTL in seconds"""
        # Clear old entries if cache is too large
        if len(self.cache) >= self.max_size:
            # Remove oldest items
            oldest = sorted(self.expiry.items(), key=lambda x: x[1])[0][0]
            self._remove_key(oldest)
            
        now = datetime.now()
        # Store the value with timestamp metadata
        self.cache[key] = {
            "data": value,
            "cache_timestamp": now
        }
        self.expiry[key] = now + timedelta(seconds=ttl_seconds)
        
    def invalidate_by_pattern(self, pattern):
        """Invalidate all cache keys matching a pattern"""
        keys_to_remove = []
        for key in list(self.cache.keys()):  # Create a copy of keys to avoid modification during iteration
            if pattern in key:
                keys_to_remove.append(key)
                
        for key in keys_to_remove:
            self._remove_key(key)
    
    def invalidate_for_user(self, user_id):
        """Invalidate all cache entries for a specific user"""
        self.invalidate_by_pattern(f"{user_id}")
        
    def clear(self):
        """Clear the entire cache"""
        self.cache.clear()
        self.expiry.clear()

# Create cache instances with appropriate settings
user_data_cache = TimedCache(max_size=128)
user_ratings_cache = TimedCache(max_size=64)
users_ranking_cache = TimedCache(max_size=1)

# Do not cache financial data - just use a placeholder
growth_data_cache = TimedCache(max_size=1)  # Not really used, just for API compatibility

# Function to update last_modified timestamp on MongoDB documents
def update_last_modified(collection, user_id):
    """Update the last_modified timestamp on a document"""
    collection.update_one(
        {"user_id": user_id},
        {"$set": {"last_modified": datetime.now()}},
        upsert=False
    )
    
    # Invalidate all caches for this user
    user_data_cache.invalidate_for_user(user_id)
    user_ratings_cache.invalidate_for_user(user_id)
    users_ranking_cache.clear()  # Global rankings depend on all users
    
# Helper functions
def get_user_data(user_id):
    """Fetch user data from MongoDB by user_id with smart caching"""
    # Check cache first with DB validation
    cached_data = user_data_cache.get(user_id, users_collection, user_id)
    if cached_data:
        return cached_data
        
    # Use projection to only fetch needed fields
    user = users_collection.find_one(
        {"user_id": user_id},
        {
            "_id": 1,
            "user_id": 1,
            "username": 1,
            "balance": 1, 
            "account_type": 1,
            "wallet_id": 1,
            "created_at": 1,
            "verified": 1,
            "staff": 1,
            "premium": 1,
            "membership": 1,
            "profile_hidden": 1,
            "ban": 1,
            "wallet_lock": 1,
            "vip": 1,
            "public_address": 1,
            "private_address": 1,
            "2fa_activated": 1,
            "email": 1,
            "frozen": 1,
            "last_login": 1,
            "wallet_limit": 1,
            "daily_limit_used": 1,
            "transfer_auth": 1,
            "login_auth": 1,
            "hidden_wallet_mode": 1,
            "last_growth_access": 1,
            "last_modified": 1
        }
    )
    
    if not user:
        return None
    
    # Convert ObjectId to string
    if '_id' in user:
        user['_id'] = str(user['_id'])
    
    # Only fetch Discord data if user exists
    discord_user = discord_users_collection.find_one(
        {"user_id": user_id},
        {"avatar": 1, "username": 1, "email": 1, "_id": 0}
    )
    
    if discord_user:
        # Update user data with Discord information
        if 'avatar' in discord_user:
            user['avatar'] = discord_user['avatar']
        
        if 'username' in discord_user:
            user['discord_username'] = discord_user['username']
        
        # Optional: Update email if available
        if 'email' in discord_user and discord_user['email']:
            user['email'] = discord_user['email']
    
    # Cache basic user data for a short time - but not financial data
    # Financial data will be fetched directly from the DB each time
    user_data_cache.set(user_id, user, 60)  # Cache for 1 minute only
    
    return user

def get_user_transactions(user_id):
    """Fetch transaction data for a user from MongoDB with optimized query"""
    try:
        # Normalize user_id to handle different formats
        user_id_options = [user_id, str(user_id)]
        
        # Initialize combined transactions list
        all_transactions = []
        
        # 1. First get transactions from array-based format
        user_txns = None
        for uid in user_id_options:
            if uid is None:
                continue
                
            query = {"user_id": uid}
            user_txns = transactions_collection.find_one(query)
            if user_txns:
                break
        
        if user_txns and user_txns.get("transactions"):
            # Get transactions array from old format
            all_transactions.extend(user_txns.get("transactions", []))
        
        # 2. Now get transactions from document-based format (same collection)
        try:
            # Build query for document-based transactions
            query = {
                "document_type": "transaction",
                "user_id": {"$in": [uid for uid in user_id_options if uid is not None]}
            }
            
            # Execute query to get document-based transactions
            document_transactions = list(transactions_collection.find(query))
            
            # Add document-based transactions to the combined list
            all_transactions.extend(document_transactions)
            
        except Exception as e:
            print(f"Error fetching document-based transactions: {e}")
        
        # If no transactions found in either format
        if not all_transactions:
            return []
        
        # Convert timestamps to datetime objects for reliable sorting
        processed_transactions = []
        for tx in all_transactions:
            try:
                timestamp = tx.get("timestamp")
                date_obj = None
                
                if isinstance(timestamp, dict) and "$date" in timestamp:
                    date_str = timestamp["$date"]
                    try:
                        date_obj = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                    except (ValueError, TypeError):
                        try:
                            from dateutil import parser
                            date_obj = parser.parse(date_str)
                        except:
                            date_obj = datetime.min
                elif isinstance(timestamp, datetime):
                    date_obj = timestamp
                elif isinstance(timestamp, str):
                    try:
                        from dateutil import parser
                        date_obj = parser.parse(timestamp)
                    except:
                        date_obj = datetime.min
                else:
                    date_obj = datetime.min
                
                tx['_parsed_date'] = date_obj
                processed_transactions.append(tx)
            except Exception as e:
                print(f"Error processing transaction timestamp: {e}")
                tx['_parsed_date'] = datetime.min
                processed_transactions.append(tx)
        
        # Sort by the parsed date (newest first)
        processed_transactions.sort(key=lambda x: x['_parsed_date'], reverse=True)
        
        # Take only the 5 most recent transactions
        recent_transactions = processed_transactions[:5]
        
        # Format the transactions for the frontend
        formatted_txns = []
        for txn in recent_transactions:
            # Format the timestamp to a readable date
            timestamp = txn.get("timestamp")
            date_str = "Unknown date"
            
            # Handle MongoDB date format - IMPROVED FORMATTING with time
            if isinstance(timestamp, dict) and "$date" in timestamp:
                try:
                    date_obj = datetime.fromisoformat(timestamp["$date"].replace("Z", "+00:00"))
                    date_str = date_obj.strftime("%Y-%m-%d %H:%M")
                except (ValueError, TypeError):
                    # Try alternative parsing methods if ISO parsing fails
                    try:
                        from dateutil import parser
                        date_obj = parser.parse(timestamp["$date"])
                        date_str = date_obj.strftime("%Y-%m-%d %H:%M")
                    except:
                        date_str = "Unknown date"
            elif isinstance(timestamp, datetime):
                date_str = timestamp.strftime("%Y-%m-%d %H:%M")
            elif isinstance(timestamp, str):
                # Try to parse direct string timestamp
                try:
                    from dateutil import parser
                    date_obj = parser.parse(timestamp)
                    date_str = date_obj.strftime("%Y-%m-%d %H:%M")
                except:
                    date_str = "Unknown date"
            
            # Get username instead of just displaying address
            transaction_type = txn.get("type", "unknown")
            
            # Format counterparty public address (truncate to first 4 and last 2 characters)
            # This matches the logic used in transaction_history.py
            public_address = txn.get("counterparty_public_address", "")
            if public_address and len(public_address) > 6:
                display_name = f"{public_address[:4]}..{public_address[-2:]}"
            else:
                display_name = public_address or "Unknown"
            
            formatted_txns.append({
                "type": transaction_type,
                "amount": float(txn.get("amount", 0)),
                "address": display_name,  # Use abbreviated public address
                "date": date_str,
                "tx_id": txn.get("tx_id", ""),
                "counterparty_id": txn.get("counterparty_id", ""),
                "counterparty_username": txn.get("counterparty_username", "")
            })
        
        # No need to reverse - we want newest transactions first
        # formatted_txns are already sorted newest first from processed_transactions
        
        return formatted_txns
    except Exception as e:
        print(f"Error fetching user transactions: {e}")
        return []

def get_user_ratings(user_id):
    """Fetch ratings data for a user from MongoDB with caching"""
    # Check cache first
    cached_data = user_ratings_cache.get(user_id)
    if cached_data:
        return cached_data
        
    # Find the user's ratings document with projection
    user_ratings = rating_stats_collection.find_one(
        {"user_id": user_id},
        {"distribution_percentage": 1, "average_rating": 1, "total_ratings": 1, "featured_quote": 1, "_id": 0}
    )
    
    # If no stats document exists, try to get data from the ratings collection directly
    if not user_ratings:
        # Try to get ratings directly from ratings collection
        ratings = list(ratings_collection.find(
            {"recipient_id": user_id}
        ).sort("timestamp", -1).limit(50))
        
        # If we have ratings, format them
        if ratings:
            total = len(ratings)
            # Calculate average rating
            stars_sum = sum(rating.get("stars", 0) for rating in ratings)
            average_rating = stars_sum / total if total > 0 else 0
            
            # Count by star rating
            stars_count = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
            for rating in ratings:
                star = rating.get("stars", 0)
                if 1 <= star <= 5:
                    stars_count[star] += 1
            
            # Calculate distribution
            distribution = []
            for star in range(5, 0, -1):  # 5 down to 1
                percentage = (stars_count[star] / total * 100) if total > 0 else 0
                distribution.append({
                    "stars": star,
                    "percentage": round(percentage)
                })
            
            # Find a rating with a comment for the featured quote
            featured_quote = {
                "text": "No ratings with comments yet.",
                "author": "",
                "stars": 0
            }
            
            # Look for a rating with a comment
            for rating in ratings:
                if rating.get("comment") and rating.get("comment").strip():
                    featured_quote = {
                        "text": rating.get("comment", ""),
                        "author": rating.get("rater_username", "Anonymous"),
                        "stars": rating.get("stars", 5)
                    }
                    break
                    
            result = {
                "average_rating": round(average_rating, 1),
                "total_ratings": total,
                "distribution": distribution,
                "featured_quote": featured_quote
            }
            
            # Cache the result
            user_ratings_cache.set(user_id, result, 300)
            
            return result
    
    # Default values if no ratings found
    if not user_ratings:
        default_ratings = {
            "average_rating": 0,
            "total_ratings": 0,
            "distribution": [
                {"stars": 5, "percentage": 0},
                {"stars": 4, "percentage": 0},
                {"stars": 3, "percentage": 0},
                {"stars": 2, "percentage": 0},
                {"stars": 1, "percentage": 0}
            ],
            "featured_quote": {
                "text": "No ratings yet.",
                "author": "",
                "stars": 0
            }
        }
        # Cache the default result
        user_ratings_cache.set(user_id, default_ratings, 300)
        return default_ratings
    
    # Extract distribution from the stats document
    distribution = user_ratings.get("distribution_percentage", [])
    if not distribution:
        # If distribution_percentage is missing, calculate it from distribution
        raw_distribution = user_ratings.get("distribution", {})
        total = user_ratings.get("total_ratings", 0)
        
        # Create distribution array from distribution object
        distribution = []
        for star in range(5, 0, -1):  # 5 down to 1
            star_str = str(star)
            count = raw_distribution.get(star_str, 0)
            percentage = (count / total * 100) if total > 0 else 0
            distribution.append({
                "stars": star,
                "percentage": round(percentage)
            })
    
    # Get featured quote
    featured_quote = user_ratings.get("featured_quote", {})
    if not featured_quote:
        # If no featured quote in stats, try to find one from ratings
        recent_ratings = list(ratings_collection.find(
            {"recipient_id": user_id, "comment": {"$exists": True, "$ne": ""}}
        ).sort("timestamp", -1).limit(1))
        
        if recent_ratings:
            recent_rating = recent_ratings[0]
            featured_quote = {
                "text": recent_rating.get("comment", ""),
                "author": recent_rating.get("rater_username", "Anonymous"),
                "stars": recent_rating.get("stars", 5)
            }
        else:
            featured_quote = {
                "text": "No ratings with comments yet.",
                "author": "",
                "stars": 0
            }
    
    result = {
        "average_rating": user_ratings.get("average_rating", 0),
        "total_ratings": user_ratings.get("total_ratings", 0),
        "distribution": distribution,
        "featured_quote": featured_quote
    }
    
    # Cache the result
    user_ratings_cache.set(user_id, result, 300)
    
    return result

def calculate_transaction_stats(user_id):
    """Calculate transaction statistics using the same approach as transaction_history.py"""
    try:
        # Normalize user_id to handle different formats (like in transaction_history)
        user_id_options = [user_id, str(user_id)]
        
        # Initialize combined transactions list
        all_transactions = []
        
        # 1. First get transactions from array-based format
        user_txns = None
        for uid in user_id_options:
            if uid is None:
                continue
                
            query = {"user_id": uid}
            user_txns = transactions_collection.find_one(query)
            if user_txns:
                break
        
        if user_txns and user_txns.get("transactions"):
            # Get transactions array from old format
            all_transactions.extend(user_txns.get("transactions", []))
        
        # 2. Now get transactions from document-based format (same collection)
        try:
            # Build query for document-based transactions
            query = {
                "document_type": "transaction",
                "user_id": {"$in": [uid for uid in user_id_options if uid is not None]}
            }
            
            # Execute query to get document-based transactions
            document_transactions = list(transactions_collection.find(query))
            
            # Add document-based transactions to the combined list
            all_transactions.extend(document_transactions)
            
        except Exception as e:
            print(f"Error fetching document-based transactions for stats: {e}")
        
        # If no transactions found in either format
        if not all_transactions:
            # No transactions found
            return {
                "totalValue": "$0.00",
                "highest": {"amount": 0, "change": "+0%"},
                "lowest": {"amount": 0, "change": "+0%"},
                "total": {"count": 0, "sent": 0, "received": 0}
            }
        
        # Calculate statistics exactly like in transaction_history.py
        sent_count = 0
        received_count = 0
        total_value = 0
        highest_amount = 0
        lowest_amount = float('inf')  # Start with infinity for finding minimum
        
        for tx in all_transactions:
            # Parse amount to float
            try:
                amount = float(tx.get("amount", 0))
            except (ValueError, TypeError):
                amount = 0
            
            # Update highest/lowest
            if amount > highest_amount:
                highest_amount = amount
            if amount > 0 and amount < lowest_amount:
                lowest_amount = amount
            
            # Calculate sent/received counts
            tx_type = tx.get("type", "")
            if tx_type == "sent":
                sent_count += 1
                total_value += amount
            elif tx_type == "received":
                received_count += 1
                total_value += amount
        
        # Fix lowest amount if no transactions found
        if lowest_amount == float('inf'):
            lowest_amount = 0
            
        # Total count is sum of sent and received
        total_count = sent_count + received_count
        
        # Sample growth percentages (normally would be based on historical data)
        highest_change = "+15%"
        lowest_change = "-8%"
        
        return {
            "totalValue": f"${total_value:.2f}",
            "highest": {
                "amount": highest_amount,
                "change": highest_change
            },
            "lowest": {
                "amount": lowest_amount,
                "change": lowest_change
            },
            "total": {
                "count": total_count,
                "sent": sent_count,
                "received": received_count
            }
        }
    except Exception as e:
        print(f"Error calculating transaction stats: {e}")
        # Return default values on error
        return {
            "totalValue": "$0.00",
            "highest": {"amount": 0, "change": "+0%"},
            "lowest": {"amount": 0, "change": "+0%"},
            "total": {"count": 0, "sent": 0, "received": 0}
        }

def get_all_users_for_ranking():
    """Get all users for ranking with efficient projection - cached for 5 minutes"""
    # Check cache first
    cached_data = users_ranking_cache.get("all_users")
    if cached_data:
        return cached_data
        
    users = list(users_collection.find(
        {},  # No filters - include all accounts regardless of status
        {"user_id": 1, "balance": 1, "_id": 0}
    ))
    
    # Convert string balances to float for proper sorting
    for user in users:
        try:
            user['numeric_balance'] = float(user.get('balance', '0'))
        except (ValueError, TypeError):
            user['numeric_balance'] = 0.0
    
    # Sort by numeric balance (descending)
    users.sort(key=lambda x: x['numeric_balance'], reverse=True)
    
    # Cache the result
    users_ranking_cache.set("all_users", users, 300)
    
    return users

def get_user_leaderboard_rank(user_id, user_balance):
    """Calculate user's rank in the leaderboard using cached user list"""
    # Convert user_balance to float
    if isinstance(user_balance, str):
        user_balance = float(user_balance)
    
    # Get pre-sorted list of all users (cached)
    all_users = get_all_users_for_ranking()
    
    # Get total number of users
    total_users = len(all_users)
    
    # Find user's rank
    user_rank = 0
    
    # Special handling for zero balances
    if user_balance == 0:
        # Find all users with zero balance
        zero_balance_users = [u for u in all_users if u.get('numeric_balance') == 0]
        
        # Sort by user_id as secondary ordering
        zero_balance_users.sort(key=lambda x: x.get('user_id', ''))
        
        # Find user's rank among zero balance users
        zero_balance_rank = 0
        for idx, user in enumerate(zero_balance_users):
            if user.get("user_id") == user_id:
                zero_balance_rank = idx + 1
                break
                
        if zero_balance_rank > 0:
            # Calculate total rank: users with non-zero balances + rank among zero balances
            non_zero_users = total_users - len(zero_balance_users)
            user_rank = non_zero_users + zero_balance_rank
    else:
        # Normal path for non-zero balances
        for idx, user in enumerate(all_users):
            if user.get("user_id") == user_id:
                user_rank = idx + 1  # +1 because index starts at 0
                break
    
    # If user not found, give last rank
    if user_rank == 0 and total_users > 0:
        user_rank = total_users
    
    # Calculate percentile
    top_percent = round((user_rank / total_users) * 100, 1) if total_users > 0 and user_rank > 0 else 0
    
    # Determine trend (simple approach: if rank is in top 50%, trend is up)
    is_improving = user_rank <= (total_users / 2) if total_users > 0 else True
    
    return {
        "rank": user_rank,
        "total_users": total_users,
        "percentile": top_percent,
        "trend": "up" if is_improving else "down"
    }

def record_balance_snapshot(user_id, balance):
    """
    Record a snapshot of the user's wallet balance using the new growth tracking system
    This function updates both current state and history collections
    """
    # Get current timestamp
    current_time = datetime.now()
    
    try:
        # Convert balance to float
        balance_float = float(balance)
        
        # 1. Update current wallet state in growth_wallets collection
        growth_wallets_collection.update_one(
        {"user_id": user_id},
        {
            "$set": {
                    "balance": balance_float,
                "last_updated": current_time,
                    "last_modified": current_time
            },
            "$setOnInsert": {"created_at": current_time}
        },
            upsert=True
        )
        
        # 2. Add history entry to growth_wallet_history collection
        history_entry = {
            "user_id": user_id,
            "balance": balance_float,
            "timestamp": current_time,
            "type": "snapshot"  # Can be extended with other types like "deposit", "withdrawal", etc.
        }
        
        growth_wallet_history_collection.insert_one(history_entry)
        
        # 3. Clean up old history entries (keep only last 30 days)
        thirty_days_ago = current_time - timedelta(days=30)
        growth_wallet_history_collection.delete_many({
            "user_id": user_id,
            "timestamp": {"$lt": thirty_days_ago}
        })
        
        # 4. Create hourly snapshot if needed (once per hour)
        # Get the most recent snapshot for this user
        latest_snapshot = growth_wallet_snapshots_collection.find_one(
            {"user_id": user_id},
            sort=[("timestamp", -1)]
        )
        
        # If no snapshot exists or the last one is more than an hour old
        if not latest_snapshot or (current_time - latest_snapshot.get("timestamp", datetime.min)).total_seconds() > 3600:
            snapshot_entry = {
                "user_id": user_id,
                "balance": balance_float,
                "timestamp": current_time,
                "date": current_time.strftime("%Y-%m-%d"),
                "hour": current_time.hour
            }
            growth_wallet_snapshots_collection.insert_one(snapshot_entry)
            
            # Clean up old snapshots (keep only last 30 days)
            growth_wallet_snapshots_collection.delete_many({
                "user_id": user_id,
                "timestamp": {"$lt": thirty_days_ago}
            })
        
        # 5. For backward compatibility, also update the old collection
        # This can be removed in the future when all clients are updated
        wallet_growth_collection.update_one(
            {"user_id": user_id},
            {
                "$push": {"snapshots": {
                    "balance": balance_float,
                    "timestamp": current_time
                }},
                "$set": {
                    "last_updated": current_time,
                    "last_modified": current_time
                },
                "$setOnInsert": {"created_at": current_time}
            },
            upsert=True
        )
    
        # Update last_modified in users collection to invalidate related caches
        update_last_modified(users_collection, user_id)
    
        return True
        
    except Exception as e:
        print(f"Error recording balance snapshot: {e}")
        return False

# Wallet growth data - NEVER use cache for financial data
def get_wallet_growth_data(user_id, period="daily"):
    """Fetch wallet growth data using the new growth tracking system - NO CACHING for financial data"""
    # Always get fresh data from the database
    now = datetime.now()
    
    # Determine the time range based on the period
    if period == "daily":
        since = now - timedelta(days=1)
        interval_hours = 1  # Hourly data points for daily view
    elif period == "weekly":
        since = now - timedelta(days=7)
        interval_hours = 4  # Every 4 hours for weekly view
    elif period == "monthly":
        since = now - timedelta(days=30)
        interval_hours = 24  # Daily data points for monthly view
    else:
        # Default to daily
        since = now - timedelta(days=1)
        interval_hours = 1
    
    try:
        # First try to get data from the new growth tracking system
        
        # For daily and weekly views, use the detailed history collection
        if period in ["daily", "weekly"]:
            # Query the history collection with appropriate time filter
            history_entries = list(growth_wallet_history_collection.find(
                {
                    "user_id": user_id,
                    "timestamp": {"$gte": since}
                },
                {
                    "balance": 1,
                    "timestamp": 1,
                    "_id": 0
                }
            ).sort("timestamp", 1))  # Sort by timestamp ascending
            
            # If we have enough data points, process them
            if history_entries:
                # Group data points by interval for cleaner charts
                grouped_data = {}
                
                for entry in history_entries:
                    timestamp = entry.get("timestamp")
                    balance = entry.get("balance", 0)
                    
                    # Create interval key based on period
                    if period == "daily":
                        # For daily, group by hour
                        interval_key = timestamp.replace(minute=0, second=0, microsecond=0)
                    else:  # weekly
                        # For weekly, group by 4-hour blocks
                        hour = (timestamp.hour // interval_hours) * interval_hours
                        interval_key = timestamp.replace(hour=hour, minute=0, second=0, microsecond=0)
                    
                    # Use the latest balance for each interval
                    grouped_data[interval_key] = balance
                
                # Convert grouped data to chart format
                result = []
                for timestamp, balance in sorted(grouped_data.items()):
                    # Format timestamp based on period
                    if period == "daily":
                        time_str = timestamp.strftime("%H:%M")
                    else:  # weekly
                        time_str = f"{timestamp.strftime('%a')} {timestamp.strftime('%H:%M')}"
                    
                    result.append({
                        "name": time_str,
                        "value": balance
                    })
                
                # Calculate summary
                if result:
                    # For daily/weekly, use the average balance
                    total_sum = sum(item["value"] for item in result)
                    summary = total_sum / len(result)
                    
                    # Store last access time
                    users_collection.update_one(
                        {"user_id": user_id},
                        {"$set": {"last_growth_access": now, "last_modified": now}},
                        upsert=False
                    )
                    
                    return (result, round(summary, 2))
        
        # For monthly view or if daily/weekly had insufficient data, use snapshots
        if period == "monthly" or not locals().get('result'):
            # Query the snapshots collection with appropriate time filter
            snapshots = list(growth_wallet_snapshots_collection.find(
                {
                    "user_id": user_id,
                    "timestamp": {"$gte": since}
                },
                {
                    "balance": 1,
                    "timestamp": 1,
                    "date": 1,
                    "hour": 1,
                    "_id": 0
                }
            ).sort("timestamp", 1))  # Sort by timestamp ascending
            
            # If we have snapshot data, process it
            if snapshots:
                # Group data by day for monthly view
                grouped_data = {}
                
                for snapshot in snapshots:
                    timestamp = snapshot.get("timestamp")
                    balance = snapshot.get("balance", 0)
                    
                    # Create interval key based on period
                    if period == "monthly":
                        # For monthly, group by day
                        interval_key = timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
                    elif period == "weekly":
                        # For weekly, group by 4-hour blocks
                        hour = (timestamp.hour // interval_hours) * interval_hours
                        interval_key = timestamp.replace(hour=hour, minute=0, second=0, microsecond=0)
                    else:  # daily
                        # For daily, group by hour
                        interval_key = timestamp.replace(minute=0, second=0, microsecond=0)
                    
                    # Use the latest balance for each interval
                    grouped_data[interval_key] = balance
                
                # Convert grouped data to chart format
                result = []
                for timestamp, balance in sorted(grouped_data.items()):
                    # Format timestamp based on period
                    if period == "daily":
                        time_str = timestamp.strftime("%H:%M")
                    elif period == "weekly":
                        time_str = f"{timestamp.strftime('%a')} {timestamp.strftime('%H:%M')}"
                    else:  # monthly
                        time_str = timestamp.strftime("%m-%d")
                    
                    result.append({
                        "name": time_str,
                        "value": balance
                    })
                
                # Calculate summary
                if result:
                    if period == "monthly":
                        # For monthly, use the total (sum of daily balances)
                        total_sum = sum(item["value"] for item in result)
                        summary = total_sum
                    else:
                        # For daily/weekly, use the average
                        total_sum = sum(item["value"] for item in result)
                        summary = total_sum / len(result)
                    
                    # Store last access time
                    users_collection.update_one(
                        {"user_id": user_id},
                        {"$set": {"last_growth_access": now, "last_modified": now}},
                        upsert=False
                    )
                    
                    return (result, round(summary, 2))
        
        # If we still don't have data, try the legacy collection as fallback
        user_growth = wallet_growth_collection.find_one(
            {"user_id": user_id},
            {"snapshots": 1, "_id": 0}
        )
        
        # Process legacy snapshots if found
        if user_growth and "snapshots" in user_growth:
            snapshots = user_growth.get("snapshots", [])
            
            # Filter snapshots for the specified period
            filtered_snapshots = [
                snapshot for snapshot in snapshots 
                if "timestamp" in snapshot and snapshot["timestamp"] >= since
            ]
            
            # If no snapshots found in the period, check for the last snapshot before the period
            if not filtered_snapshots and snapshots:
                # Sort snapshots by timestamp
                sorted_snapshots = sorted(snapshots, key=lambda x: x.get("timestamp", datetime.min))
                
                # Find the most recent snapshot before the period
                last_before_period = None
                for snapshot in sorted_snapshots:
                    if snapshot.get("timestamp") < since:
                        last_before_period = snapshot
                    else:
                        break
                
                if last_before_period:
                    filtered_snapshots.append(last_before_period)
                    
                # If we have legacy data, process it
                if filtered_snapshots:
                    # Process snapshots to create data points
                    result = []
                    
                    # Sort snapshots for processing
                    filtered_snapshots.sort(key=lambda x: x.get("timestamp", datetime.min))
                    
                    for snapshot in filtered_snapshots:
                        timestamp = snapshot.get("timestamp")
                        balance = snapshot.get("balance", 0)
                        
                        # Format timestamp based on period
                        if period == "daily":
                            time_str = timestamp.strftime("%H:%M")
                        elif period == "weekly":
                            time_str = timestamp.strftime("%a %H:%M")
                        else:
                            time_str = timestamp.strftime("%m-%d")
                            
                        result.append({
                            "name": time_str,
                            "value": balance
                        })
                    
                    # Calculate summary
                    if result:
                        total_sum = sum(item["value"] for item in result)
                        
                        # For daily/weekly, use average; for monthly, use total
                        if period == "daily" or period == "weekly":
                            summary = total_sum / len(result)
                        else:
                            summary = total_sum
                        
                        # Store last access time
                        users_collection.update_one(
                            {"user_id": user_id},
                            {"$set": {"last_growth_access": now, "last_modified": now}},
                            upsert=False
                        )
                        
                        return (result, round(summary, 2))
    
    except Exception as e:
        print(f"Error fetching growth data: {e}")
        # Continue to fallback option
    
    # If we reach here, we couldn't get data from any source
    # Get current balance and generate sample data
    user_data = users_collection.find_one(
        {"user_id": user_id},
        {"balance": 1, "_id": 0}
    )
    current_balance = float(user_data.get("balance", 0)) if user_data else 0
    
    # Record this balance to start building history
    record_balance_snapshot(user_id, current_balance)
    
    # Generate sample data as fallback
    return generate_sample_growth_data(period, current_balance)

def generate_sample_growth_data(period="daily", current_balance=0):
    """Generate sample growth data for demo purposes based on user's actual balance"""
    now = datetime.now()
    result = []
    
    # Use actual balance as a base to make samples more realistic
    # If no balance provided, use a default
    base_balance = current_balance if current_balance > 0 else 200
    
    if period == "daily":
        # Generate hourly data for the past day
        hours = 24
        for i in range(hours):
            timestamp = now - timedelta(hours=hours-i-1)
            time_str = timestamp.strftime("%H:%M")
            # Generate data with some realistic patterns
            # Morning rise, midday dip, evening peak
            variation = 0.05 + (0.03 * math.sin((i - 6) * math.pi / 12))
            time_factor = 1.0 + variation
            # Progressive growth throughout the day
            growth_factor = 1.0 + (i / hours * 0.1)
            value = base_balance * time_factor * growth_factor
            
            result.append({
                "name": time_str,
                "value": round(value, 2)
            })
        
        # Calculate daily average for summary
        total_sum = sum(item["value"] for item in result)
        daily_average = total_sum / len(result) if result else base_balance
        return result, round(daily_average, 2)
        
    elif period == "weekly":
        # Generate daily data for the past week
        days = 7
        for i in range(days):
            timestamp = now - timedelta(days=days-i-1)
            time_str = timestamp.strftime("%a")
            # Generate data with weekend variations
            is_weekend = timestamp.weekday() >= 5
            weekend_factor = 1.15 if is_weekend else 1.0
            # Progressive growth
            growth_factor = 1.0 + (i / days * 0.15)
            value = base_balance * weekend_factor * growth_factor
            
            result.append({
                "name": time_str,
                "value": round(value, 2)
            })
        
        # Calculate sum for the weekly summary
        total_sum = sum(item["value"] for item in result)
        return result, round(total_sum, 2)
        
    else:  # monthly
        # Generate data for past 30 days
        days = 30
        for i in range(days):
            timestamp = now - timedelta(days=days-i-1)
            time_str = timestamp.strftime("%m-%d")
            # Generate data with some monthly patterns
            week_factor = 1.0 + 0.1 * math.sin(i * math.pi / 7)
            growth_factor = 1.0 + (i / days * 0.25)
            value = base_balance * week_factor * growth_factor
            
            result.append({
                "name": time_str,
                "value": round(value, 2)
            })
        
        # Calculate sum for the monthly summary
        total_sum = sum(item["value"] for item in result)
        return result, round(total_sum, 2)

def get_balance_growth(user_id, current_balance):
    """Calculate the balance growth percentage using the new growth tracking system"""
    # Convert current_balance to float if it's a string
    if isinstance(current_balance, str):
        current_balance = float(current_balance)
    
    # Record a snapshot of the current balance for growth tracking
    record_balance_snapshot(user_id, current_balance)
    
    current_time = datetime.now()
    growth_percent = 0.0
    
    try:
        # First try to get data from the new growth tracking system
        # Get the current wallet state
        current_wallet = growth_wallets_collection.find_one({"user_id": user_id})
        
        # Find the previous balance from history (from 24 hours ago if possible)
        yesterday = current_time - timedelta(days=1)
        
        # Look for entries around 24 hours ago
        previous_entry = growth_wallet_history_collection.find_one(
            {
                "user_id": user_id,
                "timestamp": {"$lte": yesterday}
            },
            sort=[("timestamp", -1)]  # Get the most recent entry before yesterday
        )
        
        # If we found a previous entry, calculate growth
        if previous_entry:
            previous_balance = float(previous_entry.get("balance", 0))
            
            # Only calculate growth if previous balance exists and is not zero
            if previous_balance > 0:
                # Calculate growth percentage
                growth_percent = ((current_balance - previous_balance) / previous_balance) * 100
        else:
            # If no previous entry found, try the legacy collection as fallback
            user_growth = wallet_growth_collection.find_one(
                {"user_id": user_id},
                {"snapshots": 1, "_id": 0}
            )
            
            if user_growth and "snapshots" in user_growth:
                snapshots = user_growth.get("snapshots", [])
                
                # Only sort if we have snapshots
                if len(snapshots) > 1:
                    # Sort snapshots by timestamp (oldest to newest)
                    sorted_snapshots = sorted(snapshots, key=lambda x: x.get("timestamp", datetime.min))
                    
                    # Get the second-to-last snapshot
                    previous_snapshot = sorted_snapshots[-2]
                    previous_balance = float(previous_snapshot.get("balance", 0))
                    
                    # Only calculate growth if previous balance exists and is not zero
                    if previous_balance > 0:
                        # Calculate growth percentage
                        growth_percent = ((current_balance - previous_balance) / previous_balance) * 100
    
    except Exception as e:
        print(f"Error calculating balance growth: {e}")
        # Continue with default growth_percent value
    
    # Format the growth percentage
    formatted_growth = None
    if current_balance > 0:  # Only show growth indicator if balance is not zero
        formatted_growth = f"{'+' if growth_percent >= 0 else ''}{growth_percent:.1f}%"
    
    # Format the last updated timestamp
    last_updated = current_time.strftime("%Y-%m-%d %H:%M:%S")
    
    return {
        "growth_percent": formatted_growth,
        "last_updated": last_updated
    }

def format_wallet_data(user_data):
    """Format user data into wallet format with optimized queries"""
    if not user_data:
        return None
        
    # Get user ID for data lookup
    user_id = user_data.get("user_id")
    
    # Fetch all required data in parallel (if using asyncio)
    # For now, we'll just call them in sequence
    transactions = get_user_transactions(user_id)
    stats = calculate_transaction_stats(user_id)
    ratings_data = get_user_ratings(user_id)
    
    # Get verification and staff status directly from user data
    is_verified = user_data.get("verified", False)
    is_staff = user_data.get("staff", False)
    
    # Get leaderboard ranking
    user_balance = user_data.get("balance", "0")
    leaderboard_data = get_user_leaderboard_rank(user_id, user_balance)
    
    # Calculate balance growth
    balance_growth_data = get_balance_growth(user_id, user_balance)
    
    # Get avatar data (either from user_data or discord_users)
    user_avatar = user_data.get("avatar", "")
    discord_username = user_data.get("discord_username", "")
    
    # Check if hidden wallet mode is enabled
    hidden_wallet_mode = user_data.get("hidden_wallet_mode", False)
    
    # Set display balance based on hidden wallet mode
    display_balance = "0.00000000" if hidden_wallet_mode else user_balance
    
    # Always use wallet username (not Discord username)
    username = user_data.get("username", "")
    
    # Construct formatted wallet data
    return {
        "username": username,
        "accountType": user_data.get("account_type", "Cryptonel Client"),
        "balance": display_balance,
        "growth": balance_growth_data["growth_percent"] if not hidden_wallet_mode else None,
        "last_updated": balance_growth_data["last_updated"],
        "walletId": str(user_data.get("wallet_id", "")),
        "createdAt": user_data.get("created_at", "").split(" ")[0] if " " in user_data.get("created_at", "") else user_data.get("created_at", ""),
        "verified": is_verified,
        "adminVerified": is_staff,
        "premium": user_data.get("premium", False),
        "membership": user_data.get("membership", "Standard"),
        "publicVisible": not user_data.get("profile_hidden", False),
        "active": not user_data.get("ban", False),
        "locked": user_data.get("wallet_lock", False),
        "vip": user_data.get("vip", False),
        "user_id": user_id,
        "avatar": user_avatar,
        
        # Add leaderboard data
        "leaderboard": leaderboard_data,
        
        # Wallet addresses
        "address": {
            "public": user_data.get("public_address", "0x0000000000000000000000000000000000000000"),
            "private": user_data.get("private_address", "********************************************")
        },
        
        # Security information
        "security": {
            "twoFA": user_data.get("2fa_activated", False),
            "recoveryEmail": user_data.get("email", ""),
            "recoveryVerified": is_verified,
            "lastLogin": user_data.get("last_login", datetime.now().strftime("%b %d, %Y %H:%M")),
            "walletFrozen": user_data.get("frozen", False),
            "dailyTransferLimit": user_data.get("wallet_limit", 10000),
            "dailyLimitUsed": user_data.get("daily_limit_used", 0),
            "transferAuth": user_data.get("transfer_auth", {"password": False, "2fa": False, "secret_word": True}),
            "loginAuth": user_data.get("login_auth", {"none": True, "2fa": False, "secret_word": False})
        },
        
        # Include transaction data
        "transactions": transactions,
        "stats": stats,
        "ratings": ratings_data
    }

# Optimize routes
@overview_bp.route('/api/overview', methods=['GET'])
def get_overview_data():
    """Get overview data for the authenticated user"""
    # Check if user is authenticated
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Not authenticated"}), 401
    
    # Get user data from MongoDB
    user_data = get_user_data(user_id)
    if not user_data:
        return jsonify({"error": "User not found"}), 404
    
    # Check premium status - IMPORTANT: Only consider the premium boolean field as source of truth
    premium_status = user_data.get("premium", False)
    membership = user_data.get("membership", "Standard")
    
    # Fix inconsistency: If premium is false but membership is Premium, update membership
    try:
        from ..premium_auth.premium_check import get_db_connection
        client = get_db_connection()
        if client and not premium_status and membership.lower() == "premium":
            db = client.cryptonel_wallet
            users_collection = db.users
            users_collection.update_one(
                {"user_id": user_id},
                {"$set": {"membership": "Standard"}}
            )
            user_data["membership"] = "Standard"
            logger.info(f"Fixed premium inconsistency for user {user_id} in overview")
    except ImportError:
        # Continue without DB update if premium_check module is not available
        logger.warning("Could not import get_db_connection, skipping DB update")
    except Exception as e:
        logger.error(f"Error updating membership status: {str(e)}")
    
    # Format user data for the overview page
    wallet_data = format_wallet_data(user_data)
    
    # Set cache headers for better client-side caching
    response = jsonify(wallet_data)
    response.headers['Cache-Control'] = 'private, max-age=30'  # Cache for 30 seconds
    
    return response

@overview_bp.route('/api/wallet/growth', methods=['GET'])
def get_growth_data():
    """Get wallet growth data for specified time period using the new growth tracking system"""
    # Check if user is authenticated
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Not authenticated"}), 401
    
    # Get period from query parameters (default to daily)
    period = request.args.get("period", "daily")
    if period not in ["daily", "weekly", "monthly"]:
        period = "daily"
    
    # Track which data source is used (for debugging)
    data_source = "unknown"
    
    try:
        # Get growth data with accurate summary
        growth_data, summary = get_wallet_growth_data(user_id, period)
        
        # Determine which data source was used (for debugging)
        if len(growth_data) > 0:
            # Check if we have data in the new collections
            history_count = growth_wallet_history_collection.count_documents({"user_id": user_id})
            snapshot_count = growth_wallet_snapshots_collection.count_documents({"user_id": user_id})
            
            if history_count > 0:
                data_source = "history"
            elif snapshot_count > 0:
                data_source = "snapshots"
            else:
                data_source = "legacy"
        else:
            data_source = "sample"
        
        # Check if user has been inactive with a single query
        user_data = users_collection.find_one(
            {"user_id": user_id},
            {"last_growth_access": 1, "_id": 0}
        )
        
        # Calculate time since last access
        time_since_last_access = None
        last_access = user_data.get("last_growth_access") if user_data else None
        
        if last_access:
            now = datetime.now()
            time_diff = now - last_access
            hours_diff = time_diff.total_seconds() / 3600
            if hours_diff > 1:  # If more than 1 hour since last access
                time_since_last_access = round(hours_diff, 1)
        
        # Record this access with a non-blocking update
        users_collection.update_one(
            {"user_id": user_id},
            {"$set": {"last_growth_access": datetime.now()}},
            upsert=True
        )
        
        # Set cache headers for better client-side caching
        response = jsonify({
            "data": growth_data,
            "total": summary,
            "period": period,
            "time_since_last_access": time_since_last_access,
            "data_source": data_source  # Include data source for debugging
        })
        
        # Set shorter cache for frequently changing data
        response.headers['Cache-Control'] = 'private, max-age=60'  # Cache for 1 minute
        
        return response
        
    except Exception as e:
        print(f"Error in growth data API: {e}")
        
        # Generate sample data as fallback
        sample_data, sample_summary = generate_sample_growth_data(period, 0)
        
        # Set cache headers for better client-side caching
        response = jsonify({
            "data": sample_data,
            "total": sample_summary,
            "period": period,
            "time_since_last_access": None,
            "data_source": "error_fallback",
            "error": str(e)
        })
        
        # Set shorter cache for error responses
        response.headers['Cache-Control'] = 'private, max-age=30'  # Cache for 30 seconds
        
        return response

# Initialize Blueprint
def init_app(app):
    # Conditionally register test routes only in development/debug mode
    if app.debug:
        @overview_bp.route('/api/overview/test/<user_id>', methods=['GET'])
        def get_test_overview_data(user_id):
            """Test endpoint to get overview data for a specific user (for development only)"""
            # In production, this would be secured or removed
            
            # Get user data from MongoDB
            user_data = get_user_data(user_id)
            if not user_data:
                return jsonify({"error": "User not found"}), 404
            
            # Format user data for the overview page
            wallet_data = format_wallet_data(user_data)
            
            return jsonify(wallet_data)

        @overview_bp.route('/api/overview/update-user', methods=['POST'])
        def update_user_data():
            """Test endpoint to update user data (for development only)"""
            # Check if user is authenticated
            user_id = session.get('user_id')
            if not user_id:
                return jsonify({"error": "Not authenticated"}), 401
            
            # Get request data
            data = request.json
            if not data:
                return jsonify({"error": "No data provided"}), 400
            
            # Update fields that are allowed to be modified
            update_fields = {}
            allowed_fields = ['premium', 'verified', 'vip', 'staff', 'wallet_lock', 'profile_hidden']
            
            for field in allowed_fields:
                if field in data:
                    update_fields[field] = data[field]
            
            if not update_fields:
                return jsonify({"error": "No valid fields to update"}), 400
            
            # If premium status is being updated, ensure membership is consistent
            if 'premium' in update_fields:
                premium_status = update_fields['premium']
                if premium_status:
                    update_fields['membership'] = "Premium"
                else:
                    update_fields['membership'] = "Standard"
            
            # Update the user in MongoDB
            result = users_collection.update_one(
                {"user_id": user_id},
                {"$set": update_fields}
            )
            
            if result.modified_count == 0:
                return jsonify({"error": "Failed to update user data"}), 500
            
            # If premium was set to false, reset all premium settings
            if 'premium' in update_fields and not update_fields['premium']:
                try:
                    from ..premium_auth.premium_check import handle_premium_status_change
                    handle_premium_status_change(user_id, False)
                except ImportError:
                    # If premium_check module is not available, continue without reset
                    pass
            
            # Get the updated user data
            updated_user = users_collection.find_one({"user_id": user_id})
            if not updated_user:
                return jsonify({"error": "User not found after update"}), 404
            
            # Format and return updated wallet data
            wallet_data = format_wallet_data(updated_user)
            
            return jsonify({
                "success": True,
                "message": "User data updated successfully",
                "wallet_data": wallet_data
            })

        @overview_bp.route('/api/wallet/growth/test/<user_id>', methods=['GET'])
        def get_test_growth_data(user_id):
            """Test endpoint to get growth data for a specific user (for development only)"""
            # In production, this would be secured or removed
            
            # Get period from query parameters (default to daily)
            period = request.args.get("period", "daily")
            if period not in ["daily", "weekly", "monthly"]:
                period = "daily"
            
            # Get growth data with accurate summary
            growth_data, summary = get_wallet_growth_data(user_id, period)
            
            # Check if user has been inactive for a while
            user_data = users_collection.find_one({"user_id": user_id})
            last_access = user_data.get("last_growth_access") if user_data else None
            
            # Calculate time since last access
            time_since_last_access = None
            if last_access:
                now = datetime.now()
                time_diff = now - last_access
                hours_diff = time_diff.total_seconds() / 3600
                if hours_diff > 1:  # If more than 1 hour since last access
                    time_since_last_access = round(hours_diff, 1)
            
            # Record this access
            users_collection.update_one(
                {"user_id": user_id},
                {"$set": {"last_growth_access": datetime.now()}},
                upsert=True
            )
            
            return jsonify({
                "data": growth_data,
                "total": summary,
                "period": period,
                "time_since_last_access": time_since_last_access
            })

    app.register_blueprint(overview_bp)
    app.json_encoder = MongoJSONEncoder
    
    return app

# For standalone testing
if __name__ == '__main__':
    from flask import Flask
    app = Flask(__name__)
    app.secret_key = os.urandom(24)
    init_app(app)
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True) 