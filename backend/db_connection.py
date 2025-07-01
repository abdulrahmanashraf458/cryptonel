"""
Centralized MongoDB Connection Module
------------------------------------
This module provides a centralized MongoDB connection that all parts of the application
can import to ensure consistent database connectivity.
"""

import os
import logging
from pymongo import MongoClient
from dotenv import load_dotenv

# Set up logging
logger = logging.getLogger("mongodb_connection")

# Default MongoDB Atlas connection string to use as fallback - NEVER LOG CREDENTIALS
DEFAULT_MONGODB_URI = "mongodb://localhost:27017" # Default to local MongoDB for development only

# Load environment variables directly
try:
    # Try to load from secure_config
    secure_env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'secure_config', 'clyne.env')
    if os.path.exists(secure_env_path):
        load_dotenv(secure_env_path, override=True)
        logger.info(f"Loaded environment from: {secure_env_path}")
except Exception as e:
    logger.error(f"Error loading environment: {e}")

# Get MongoDB connection string with fallback
MONGODB_URI = os.environ.get("DATABASE_URL", DEFAULT_MONGODB_URI)

# Log connection information (securely without credentials)
connection_info = MONGODB_URI.split('@')[-1] if '@' in MONGODB_URI else "<connection-url-masked>"
logger.info(f"Using MongoDB connection: {connection_info}")

# Create MongoDB client and databases
try:
    client = MongoClient(MONGODB_URI)
    
    # Test connection
    client.admin.command('ping')
    logger.info("Successfully connected to MongoDB")
    
    # Set up database references
    db = client["cryptonel_wallet"]
    mining_db = client["cryptonel_mining"]
    security_db = client["cryptonel_security"]
    
    # Common collections
    users_collection = db["users"]
    discord_users_collection = db["discord_users"]
    transactions_collection = db["transactions"]
    csrf_tokens_collection = db["csrf_tokens"]
    rate_limits_collection = db["rate_limits"]
    blacklist_tokens_collection = db["blacklist_tokens"]
    suspicious_activity_collection = db["suspicious_activity"]
    user_login_history_collection = db["user_login_history"]
    settings_collection = db["settings"]
    
except Exception as e:
    logger.error(f"Failed to connect to MongoDB: {e}")
    # Re-raise to let the application handle the error
    raise

# Helper functions
def get_connection_status():
    """Check if the MongoDB connection is healthy
    
    Returns:
        tuple: (bool, str) - (is_connected, status_message)
    """
    try:
        # Test the connection with a ping
        client.admin.command('ping')
        return True, "Connected to MongoDB successfully"
    except Exception as e:
        return False, f"MongoDB connection error: {str(e)}"

def get_connection_info():
    """Get information about the current MongoDB connection
    
    Returns:
        dict: Connection information
    """
    # Only include non-sensitive parts of the connection string
    connection_info = MONGODB_URI.split('@')[-1] if '@' in MONGODB_URI else "<connection-url-masked>"
    
    return {
        "connection_url": connection_info,
        "database_name": db.name,
        "is_connected": get_connection_status()[0],
        "collections": db.list_collection_names()
    }

def switch_connection(new_uri):
    """Switch to a different MongoDB connection
    
    Args:
        new_uri: New MongoDB connection URI
    
    Returns:
        bool: Success status
    """
    global client, db, mining_db, security_db
    global users_collection, discord_users_collection, transactions_collection
    global csrf_tokens_collection, rate_limits_collection, blacklist_tokens_collection
    global suspicious_activity_collection, user_login_history_collection, settings_collection
    
    try:
        # Create new client
        new_client = MongoClient(new_uri)
        
        # Test connection
        new_client.admin.command('ping')
        
        # Replace old client and update references
        client = new_client
        db = client["cryptonel_wallet"]
        mining_db = client["cryptonel_mining"]
        security_db = client["cryptonel_security"]
        
        # Update collection references
        users_collection = db["users"]
        discord_users_collection = db["discord_users"]
        transactions_collection = db["transactions"]
        csrf_tokens_collection = db["csrf_tokens"]
        rate_limits_collection = db["rate_limits"]
        blacklist_tokens_collection = db["blacklist_tokens"]
        suspicious_activity_collection = db["suspicious_activity"]
        user_login_history_collection = db["user_login_history"]
        settings_collection = db["settings"]
        
        logger.info(f"Successfully switched to new MongoDB connection")
        return True
    except Exception as e:
        logger.error(f"Failed to switch MongoDB connection: {e}")
        return False 