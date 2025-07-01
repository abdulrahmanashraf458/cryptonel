"""
Database Utilities - Optimized MongoDB database operations

This module provides optimized database access with query caching,
performance monitoring, and proper indexing for MongoDB.
"""

import os
import time
import logging
import traceback
import functools
from typing import Any, Dict, List, Optional, Union, Callable, Tuple

# Configure logging
logger = logging.getLogger('cryptonel.db')

# Try to import MongoDB
try:
    import pymongo
    from pymongo import MongoClient, IndexModel
    from pymongo.errors import ConnectionFailure, OperationFailure
    from pymongo.collection import Collection
    from pymongo.cursor import Cursor
    HAS_MONGODB = True
except ImportError:
    HAS_MONGODB = False
    logger.warning("MongoDB not installed. Database operations will fail.")

# Import our caching utilities
from backend.utils.cache_utils import cached

# MongoDB client
_mongo_client = None
_db = None

def configure_mongodb(mongo_uri: Optional[str] = None, db_name: Optional[str] = None) -> bool:
    """
    Configure MongoDB connection from environment or explicit URI
    
    Args:
        mongo_uri: MongoDB connection URI (optional, falls back to env var)
        db_name: Database name (optional, falls back to env var or 'cryptonel')
        
    Returns:
        bool: Whether MongoDB is available and configured
    """
    global _mongo_client, _db
    
    if not HAS_MONGODB:
        return False
    
    # Get URI from param or environment variable
    uri = mongo_uri or os.environ.get('DATABASE_URL')
    database = db_name or os.environ.get('MONGO_DB', 'cryptonel')
    
    if not uri:
        logger.warning("No MongoDB URI provided. Database operations will fail.")
        return False
    
    try:
        _mongo_client = MongoClient(uri)
        # Test connection
        _mongo_client.admin.command('ping')
        
        # Get database
        _db = _mongo_client[database]
        logger.info(f"MongoDB connected to database '{database}'")
        
        # Initialize indexes
        _initialize_indexes()
        
        return True
    except (ConnectionFailure, OperationFailure) as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        return False


def get_db():
    """
    Get the MongoDB database instance
    
    Returns:
        pymongo.database.Database: MongoDB database or None if not available
    """
    return _db


def get_collection(collection_name: str) -> Optional[Collection]:
    """
    Get a MongoDB collection
    
    Args:
        collection_name: Name of the collection
        
    Returns:
        Optional[Collection]: Collection or None if database not configured
    """
    if not _db:
        logger.error(f"Attempted to access collection '{collection_name}' but MongoDB is not configured")
        return None
    
    return _db[collection_name]


def _initialize_indexes():
    """Initialize all indexes for collections"""
    if not _db:
        return
    
    try:
        # Check all existing indexes first
        users_indexes = [idx.get('name') for idx in list(_db.users.list_indexes())]
        transactions_indexes = [idx.get('name') for idx in list(_db.transactions.list_indexes())]
        sessions_indexes = [idx.get('name') for idx in list(_db.sessions.list_indexes())]
        login_attempts_indexes = [idx.get('name') for idx in list(_db.login_attempts.list_indexes())]
        rate_limits_indexes = [idx.get('name') for idx in list(_db.rate_limits.list_indexes())]
        
        # Users collection indexes - only create if they don't exist
        users = _db.users
        if not any('email' in idx for idx in users_indexes):
            users.create_index([("email", pymongo.ASCENDING)], unique=True, name="db_utils_email_idx")
            logger.info("Created users email index")
            
        if not any('username' in idx for idx in users_indexes):
            users.create_index([("username", pymongo.ASCENDING)], unique=True, name="db_utils_username_idx")
            logger.info("Created users username index")
            
        if not any('last_login' in idx for idx in users_indexes):
            users.create_index([("last_login", pymongo.DESCENDING)], name="db_utils_last_login_idx")
            logger.info("Created users last_login index")
        
        # Transactions collection indexes
        transactions = _db.transactions
        if not any('user_id_timestamp' in idx for idx in transactions_indexes):
            transactions.create_index([("user_id", pymongo.ASCENDING), ("timestamp", pymongo.DESCENDING)], 
                                     name="db_utils_user_txn_time_idx")
            logger.info("Created transactions user_id+timestamp index")
            
        if not any('status' in idx for idx in transactions_indexes):
            transactions.create_index([("status", pymongo.ASCENDING)], name="db_utils_txn_status_idx")
            logger.info("Created transactions status index")
            
        if not any('timestamp' in idx for idx in transactions_indexes):
            transactions.create_index([("timestamp", pymongo.DESCENDING)], name="db_utils_txn_time_idx")
            logger.info("Created transactions timestamp index")
            
        if not any('amount' in idx for idx in transactions_indexes):
            transactions.create_index([("amount", pymongo.DESCENDING)], name="db_utils_txn_amount_idx")
            logger.info("Created transactions amount index")
        
        # Sessions collection indexes
        sessions = _db.sessions
        if not any('user_id' in idx for idx in sessions_indexes):
            sessions.create_index([("user_id", pymongo.ASCENDING)], name="db_utils_session_user_idx")
            logger.info("Created sessions user_id index")
            
        if not any('created_at' in idx for idx in sessions_indexes):
            sessions.create_index([("created_at", pymongo.DESCENDING)], name="db_utils_session_created_idx")
            logger.info("Created sessions created_at index")
            
        if not any('expires_at' in idx for idx in sessions_indexes):
            sessions.create_index([("expires_at", pymongo.ASCENDING)], name="db_utils_session_expiry_idx")
            logger.info("Created sessions expires_at index")
        
        # LoginAttempts collection indexes
        login_attempts = _db.login_attempts
        if not any('ip_address_timestamp' in idx for idx in login_attempts_indexes):
            login_attempts.create_index([("ip_address", pymongo.ASCENDING), ("timestamp", pymongo.DESCENDING)],
                                      name="db_utils_login_ip_time_idx")
            logger.info("Created login_attempts ip+timestamp index")
            
        if not any('email_timestamp' in idx for idx in login_attempts_indexes):
            login_attempts.create_index([("email", pymongo.ASCENDING), ("timestamp", pymongo.DESCENDING)],
                                      name="db_utils_login_email_time_idx")
            logger.info("Created login_attempts email+timestamp index")
            
        if not any('success' in idx for idx in login_attempts_indexes):
            login_attempts.create_index([("success", pymongo.ASCENDING)], name="db_utils_login_success_idx")
            logger.info("Created login_attempts success index")
        
        # RateLimits collection indexes (if using MongoDB for rate limiting)
        rate_limits = _db.rate_limits
        if not any('key' in idx for idx in rate_limits_indexes):
            rate_limits.create_index([("key", pymongo.ASCENDING)], unique=True, name="db_utils_ratelimit_key_idx")
            logger.info("Created rate_limits key index")
            
        if not any('expires_at' in idx for idx in rate_limits_indexes):
            rate_limits.create_index([("expires_at", pymongo.ASCENDING)], expireAfterSeconds=0, 
                                    name="db_utils_ratelimit_expiry_idx")
            logger.info("Created rate_limits expiry index")
        
        logger.info("MongoDB indexes initialized")
    except Exception as e:
        logger.error(f"Failed to initialize indexes: {e}")


def timed_query(func):
    """
    Decorator to time and log slow queries
    
    Args:
        func: Function to decorate
    
    Returns:
        Wrapped function with timing
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            end_time = time.time()
            duration = end_time - start_time
            
            # Log slow queries (>100ms)
            if duration > 0.1:
                logger.warning(f"Slow query in {func.__name__}: {duration:.2f}s")
                
                # If first argument is a collection, include it in the log
                collection_name = str(args[0]) if args and isinstance(args[0], Collection) else "unknown"
                
                # Try to get query details
                query = kwargs.get('filter', kwargs.get('query', {}))
                logger.warning(f"Slow query details: collection={collection_name}, query={query}")
            
            return result
        except Exception as e:
            logger.error(f"Query error in {func.__name__}: {e}")
            logger.debug(traceback.format_exc())
            raise
    
    return wrapper


@timed_query
def find_one(collection: Collection, filter: Dict, *args, **kwargs) -> Optional[Dict]:
    """
    Find a single document with timing and logging
    
    Args:
        collection: MongoDB collection
        filter: Query filter
        *args, **kwargs: Additional arguments for find_one
        
    Returns:
        Optional[Dict]: Found document or None
    """
    return collection.find_one(filter, *args, **kwargs)


@timed_query
def find(collection: Collection, filter: Dict, *args, **kwargs) -> Cursor:
    """
    Find documents with timing and logging
    
    Args:
        collection: MongoDB collection
        filter: Query filter
        *args, **kwargs: Additional arguments for find
        
    Returns:
        Cursor: MongoDB cursor for results
    """
    return collection.find(filter, *args, **kwargs)


@timed_query
def insert_one(collection: Collection, document: Dict, *args, **kwargs) -> pymongo.results.InsertOneResult:
    """
    Insert a document with timing and logging
    
    Args:
        collection: MongoDB collection
        document: Document to insert
        *args, **kwargs: Additional arguments for insert_one
        
    Returns:
        pymongo.results.InsertOneResult: Insert result
    """
    return collection.insert_one(document, *args, **kwargs)


@timed_query
def update_one(collection: Collection, filter: Dict, update: Dict, *args, **kwargs) -> pymongo.results.UpdateResult:
    """
    Update a document with timing and logging
    
    Args:
        collection: MongoDB collection
        filter: Query filter
        update: Update operations
        *args, **kwargs: Additional arguments for update_one
        
    Returns:
        pymongo.results.UpdateResult: Update result
    """
    return collection.update_one(filter, update, *args, **kwargs)


@timed_query
def delete_one(collection: Collection, filter: Dict, *args, **kwargs) -> pymongo.results.DeleteResult:
    """
    Delete a document with timing and logging
    
    Args:
        collection: MongoDB collection
        filter: Query filter
        *args, **kwargs: Additional arguments for delete_one
        
    Returns:
        pymongo.results.DeleteResult: Delete result
    """
    return collection.delete_one(filter, *args, **kwargs)


@timed_query
def count_documents(collection: Collection, filter: Dict, *args, **kwargs) -> int:
    """
    Count documents with timing and logging
    
    Args:
        collection: MongoDB collection
        filter: Query filter
        *args, **kwargs: Additional arguments for count_documents
        
    Returns:
        int: Document count
    """
    return collection.count_documents(filter, *args, **kwargs)


@timed_query
def aggregate(collection: Collection, pipeline: List[Dict], *args, **kwargs) -> Cursor:
    """
    Run an aggregation pipeline with timing and logging
    
    Args:
        collection: MongoDB collection
        pipeline: Aggregation pipeline
        *args, **kwargs: Additional arguments for aggregate
        
    Returns:
        Cursor: MongoDB cursor for results
    """
    return collection.aggregate(pipeline, *args, **kwargs)


def explain_query(collection: Collection, filter: Dict, *args, **kwargs) -> Dict:
    """
    Get query explanation for performance analysis
    
    Args:
        collection: MongoDB collection
        filter: Query filter
        *args, **kwargs: Additional arguments for find
        
    Returns:
        Dict: Query explanation
    """
    cursor = collection.find(filter, *args, **kwargs)
    return cursor.explain()


def cached_find(collection: Collection, filter: Dict, cache_ttl: int = 300, *args, **kwargs) -> List[Dict]:
    """
    Cached version of find that stores results
    
    Args:
        collection: MongoDB collection
        filter: Query filter
        cache_ttl: Cache time-to-live in seconds
        *args, **kwargs: Additional arguments for find
        
    Returns:
        List[Dict]: Query results as a list
    """
    cache_key = f"db:{collection.name}:{str(filter)}"
    
    @cached(ttl=cache_ttl, prefix=cache_key)
    def _cached_query():
        return list(find(collection, filter, *args, **kwargs))
    
    return _cached_query()


def cached_find_one(collection: Collection, filter: Dict, cache_ttl: int = 300, *args, **kwargs) -> Optional[Dict]:
    """
    Cached version of find_one that stores results
    
    Args:
        collection: MongoDB collection
        filter: Query filter
        cache_ttl: Cache time-to-live in seconds
        *args, **kwargs: Additional arguments for find_one
        
    Returns:
        Optional[Dict]: Query result or None
    """
    cache_key = f"db:{collection.name}:{str(filter)}"
    
    @cached(ttl=cache_ttl, prefix=cache_key)
    def _cached_query():
        return find_one(collection, filter, *args, **kwargs)
    
    return _cached_query()


def cached_count(collection: Collection, filter: Dict, cache_ttl: int = 300, *args, **kwargs) -> int:
    """
    Cached version of count_documents that stores results
    
    Args:
        collection: MongoDB collection
        filter: Query filter
        cache_ttl: Cache time-to-live in seconds
        *args, **kwargs: Additional arguments for count_documents
        
    Returns:
        int: Document count
    """
    cache_key = f"db:count:{collection.name}:{str(filter)}"
    
    @cached(ttl=cache_ttl, prefix=cache_key)
    def _cached_query():
        return count_documents(collection, filter, *args, **kwargs)
    
    return _cached_query()


def cached_aggregate(collection: Collection, pipeline: List[Dict], cache_ttl: int = 300, *args, **kwargs) -> List[Dict]:
    """
    Cached version of aggregate that stores results
    
    Args:
        collection: MongoDB collection
        pipeline: Aggregation pipeline
        cache_ttl: Cache time-to-live in seconds
        *args, **kwargs: Additional arguments for aggregate
        
    Returns:
        List[Dict]: Aggregation results as a list
    """
    cache_key = f"db:agg:{collection.name}:{str(pipeline)}"
    
    @cached(ttl=cache_ttl, prefix=cache_key)
    def _cached_query():
        return list(aggregate(collection, pipeline, *args, **kwargs))
    
    return _cached_query()


def get_slow_queries(threshold_ms: int = 100, limit: int = 20) -> List[Dict]:
    """
    Get slow queries from the database for analysis
    
    Args:
        threshold_ms: Minimum query time in milliseconds to consider slow
        limit: Maximum number of slow queries to return
        
    Returns:
        List[Dict]: Slow query information
    """
    if not _db:
        return []
    
    try:
        # Get slow queries from system.profile collection
        # Requires profiling to be enabled on the database
        profile = _db.system.profile
        
        return list(profile.find(
            {"millis": {"$gt": threshold_ms}},
            sort=[("millis", pymongo.DESCENDING)],
            limit=limit
        ))
    except Exception as e:
        logger.error(f"Error retrieving slow queries: {e}")
        return []


def enable_profiling(level: int = 1, slow_ms: int = 100):
    """
    Enable database profiling for query analysis
    
    Args:
        level: Profiling level (0=off, 1=slow queries, 2=all queries)
        slow_ms: Threshold in milliseconds for slow queries
    
    Returns:
        bool: Whether operation succeeded
    """
    if not _db:
        return False
    
    try:
        _db.command({"profile": level, "slowms": slow_ms})
        return True
    except Exception as e:
        logger.error(f"Failed to enable profiling: {e}")
        return False


# Initialize MongoDB on module import if possible
mongo_uri = os.environ.get('DATABASE_URL')
if mongo_uri:
    configure_mongodb(mongo_uri) 