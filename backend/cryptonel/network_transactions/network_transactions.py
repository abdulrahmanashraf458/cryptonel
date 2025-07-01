"""
Network Transactions Handler
---------------------------
Handles fetching and streaming of public network transactions
"""

import os
import json
import logging
import asyncio
import time
import datetime
from bson import ObjectId
from flask import Blueprint, jsonify, request, current_app
from flask_socketio import SocketIO, emit
from pymongo import MongoClient, DESCENDING
from pymongo.errors import PyMongoError
import functools
from threading import Lock

# Setup logging
logger = logging.getLogger(__name__)

# Create Blueprint
network_transactions_bp = Blueprint('network_transactions', __name__)

# Cache settings
CACHE_DURATION = 30  # seconds
cache_lock = Lock()
transactions_cache = {
    'data': None,
    'last_updated': 0,
    'total_count': 0
}

# Helper functions for anonymization
def anonymize_username(username):
    """Fully anonymizes the username to '********' as per user request."""
    return "********"

def anonymize_address(address):
    """Fully anonymizes the public address to '****************' as per user request."""
    return "****************"

# MongoDB connection and collection access
def get_db_connection():
    try:
        # Get MongoDB connection string from environment
        mongo_uri = os.environ.get('DATABASE_URL')
        if not mongo_uri:
            logger.error("DATABASE_URL environment variable not set")
            return None
            
        # Create client and connect to specific database
        client = MongoClient(mongo_uri)
        db = client['cryptonel_wallet']
        return db
    except Exception as e:
        logger.error(f"Database connection error: {str(e)}")
        return None

def get_transactions_collection():
    db = get_db_connection()
    if db is not None:
        return db['user_transactions']
    return None

# Helper function to format transaction for public display
def format_transaction_for_public(transaction):
    # Determine the sender and receiver info
    # Check if it's from the new document-based format or old array-based format
    if 'document_type' in transaction:
        # New document-based format
        sender_public_address = transaction.get('sender_public_address', 'Unknown')
        sender_username = transaction.get('sender_username', 'Unknown')
        recipient_public_address = transaction.get('recipient_public_address', 'Unknown')
        recipient_username = transaction.get('recipient_username', 'Unknown')
        amount = transaction.get('amount', 0)
        status = transaction.get('status', 'completed')
    else:
        # Old array-based format
        transaction_type = transaction.get('type')
        
        if transaction_type == 'sent':
            sender_public_address = transaction.get('counterparty_public_address', 'Unknown')
            sender_username = transaction.get('counterparty_username', 'Unknown')
            recipient_public_address = transaction.get('sender_id', 'Unknown')
            recipient_username = transaction.get('sender_username', 'Unknown')
        else:  # received
            sender_public_address = transaction.get('counterparty_public_address', 'Unknown')
            sender_username = transaction.get('counterparty_username', 'Unknown')
            recipient_public_address = transaction.get('recipient_id', 'Unknown')
            recipient_username = transaction.get('recipient_username', 'Unknown')
        
        amount = transaction.get('amount', 0)
        status = transaction.get('status', 'completed')
    
    # Format timestamp
    timestamp = transaction.get('timestamp')
    if isinstance(timestamp, datetime.datetime):
        formatted_time = timestamp.strftime('%Y-%m-%d %H:%M:%S')
    else:
        formatted_time = str(timestamp)
    
    # Return formatted ANONYMIZED transaction
    return {
        'tx_id': transaction.get('tx_id', 'Unknown'),
        'amount': float(amount),
        'timestamp': formatted_time,
        'sender': {
            'public_address': anonymize_address(sender_public_address),
            'username': anonymize_username(sender_username)
        },
        'receiver': {
            'public_address': anonymize_address(recipient_public_address),
            'username': anonymize_username(recipient_username)
        },
        'status': status
    }

# Custom JSON encoder to handle ObjectId
class MongoJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        return json.JSONEncoder.default(self, obj)

# Helper function to get all transactions (used by both API and cache)
def get_all_transactions():
    try:
        # Get collection
        transactions_collection = get_transactions_collection()
        if transactions_collection is None:
            logger.error("Could not connect to transactions collection")
            return [], 0
        
        # Fetch all transactions using both formats
        all_transactions = []
        transaction_ids_seen = set()  # Track seen transaction IDs to prevent duplicates
        
        # 1. First query for document-based transactions (new format)
        try:
            # Query document-based transactions
            document_transactions = list(transactions_collection.find(
                {"document_type": "transaction", "status": "completed"},
                {"tx_id": 1, "amount": 1, "timestamp": 1, "sender_username": 1, 
                 "sender_public_address": 1, "recipient_username": 1, 
                 "recipient_public_address": 1, "status": 1, "document_type": 1}
            ).sort("timestamp", -1).limit(1000))
            
            # Add to all transactions
            for tx in document_transactions:
                tx_id = tx.get('tx_id')
                if tx_id and tx_id not in transaction_ids_seen:
                    transaction_ids_seen.add(tx_id)
                    all_transactions.append(tx)
                    
            logger.info(f"Found {len(document_transactions)} document-based transactions")
        except Exception as e:
            logger.error(f"Error fetching document-based transactions: {e}")
        
        # 2. Then query for array-based transactions (old format)
        try:
            # Use projection to limit data retrieved - only get completed transactions
            pipeline = [
                {"$project": {
                    "transactions": {
                        "$filter": {
                            "input": "$transactions", 
                            "as": "tx", 
                            "cond": {"$eq": ["$$tx.status", "completed"]}
                        }
                    }
                }}
            ]
            
            user_docs = list(transactions_collection.aggregate(pipeline))
            
            # Extract all transactions from all users
            for user_doc in user_docs:
                if 'transactions' in user_doc:
                    for tx in user_doc['transactions']:
                        # Add only transactions we haven't seen before
                        tx_id = tx.get('tx_id')
                        if tx_id and tx_id not in transaction_ids_seen:
                            transaction_ids_seen.add(tx_id)
                            all_transactions.append(tx)
                            
            logger.info(f"Found {len(transaction_ids_seen) - len(document_transactions)} array-based transactions")
        except Exception as e:
            logger.error(f"Error fetching array-based transactions: {e}")
        
        # Sort transactions by timestamp
        all_transactions.sort(key=lambda x: x.get('timestamp', datetime.datetime.min), reverse=True)
        
        return all_transactions, len(all_transactions)
        
    except Exception as e:
        logger.error(f"Error in get_all_transactions: {str(e)}")
        return [], 0

# API endpoint to get recent transactions with caching
@network_transactions_bp.route('/api/network-transactions', methods=['GET'])
def get_network_transactions():
    try:
        # Get pagination parameters
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 100))  # Default to 100 transactions
        
        # Calculate skip value for pagination
        skip = (page - 1) * limit
        
        current_time = time.time()
        
        # Check if we have a valid cache
        with cache_lock:
            cache_valid = (
                transactions_cache['data'] is not None and 
                current_time - transactions_cache['last_updated'] < CACHE_DURATION
            )
            
            if cache_valid:
                # Use cached data
                all_transactions = transactions_cache['data']
                total_count = transactions_cache['total_count']
                logger.debug("Using cached transactions data")
            else:
                # Fetch fresh data
                all_transactions, total_count = get_all_transactions()
                
                # Update cache
                transactions_cache['data'] = all_transactions
                transactions_cache['last_updated'] = current_time
                transactions_cache['total_count'] = total_count
                logger.debug("Updated transactions cache with fresh data")
        
        # Apply pagination
        paginated_transactions = all_transactions[skip:skip+limit]
        
        # Format transactions for public display
        formatted_transactions = [format_transaction_for_public(tx) for tx in paginated_transactions]
        
        # Return response
        return jsonify({
            'transactions': formatted_transactions,
            'meta': {
                'page': page,
                'limit': limit,
                'total': total_count,
                'pages': (total_count + limit - 1) // limit
            }
        })
    
    except Exception as e:
        logger.error(f"Error fetching network transactions: {str(e)}")
        return jsonify({'error': 'An error occurred while fetching network transactions'}), 500

# WebSocket setup for real-time updates
def setup_socketio(socketio):
    # Track connected clients for efficient broadcasting
    connected_clients = set()
    
    @socketio.on('connect', namespace='/network-transactions')
    def handle_connect():
        # Add client to connected set
        connected_clients.add(request.sid)
        logger.info(f"Client connected to network transactions socket: {request.sid} (Total: {len(connected_clients)})")
    
    @socketio.on('disconnect', namespace='/network-transactions')
    def handle_disconnect():
        # Remove client from connected set
        if request.sid in connected_clients:
            connected_clients.remove(request.sid)
        logger.info(f"Client disconnected from network transactions socket: {request.sid} (Total: {len(connected_clients)})")

    # Make connected_clients available to the transaction check task
    return connected_clients

# Background task to check for new transactions and emit updates
async def check_for_new_transactions(socketio, connected_clients):
    try:
        last_check_time = datetime.datetime.now() - datetime.timedelta(minutes=5)
        
        while True:
            try:
                # Skip check if no clients are connected
                if len(connected_clients) == 0:
                    await asyncio.sleep(1)
                    continue
                    
                # Get collection
                transactions_collection = get_transactions_collection()
                
                if transactions_collection is not None:
                    # Fetch new transactions
                    new_transactions = []
                    transaction_ids_seen = set()  # Track seen transaction IDs to prevent duplicates
                    
                    # 1. First check for new document-based transactions
                    try:
                        # Query document-based transactions newer than last check
                        document_transactions = list(transactions_collection.find(
                            {
                                "document_type": "transaction", 
                                "status": "completed",
                                "timestamp": {"$gt": last_check_time}
                            },
                            {
                                "tx_id": 1, "amount": 1, "timestamp": 1, 
                                "sender_username": 1, "sender_public_address": 1, 
                                "recipient_username": 1, "recipient_public_address": 1, 
                                "status": 1, "document_type": 1
                            }
                        ).sort("timestamp", -1))
                        
                        # Add to new transactions
                        for tx in document_transactions:
                            tx_id = tx.get('tx_id')
                            if tx_id and tx_id not in transaction_ids_seen:
                                transaction_ids_seen.add(tx_id)
                                new_transactions.append(tx)
                                
                        logger.info(f"Found {len(document_transactions)} new document-based transactions")
                    except Exception as e:
                        logger.error(f"Error fetching new document-based transactions: {e}")
                    
                    # 2. Then check for new array-based transactions
                    try:
                        # Use more efficient query with projection for array-based format
                        pipeline = [
                            {"$project": {
                                "transactions": {
                                    "$filter": {
                                        "input": "$transactions", 
                                        "as": "tx", 
                                        "cond": {
                                            "$and": [
                                                {"$eq": ["$$tx.status", "completed"]},
                                                {"$gt": ["$$tx.timestamp", last_check_time]}
                                            ]
                                        }
                                    }
                                }
                            }}
                        ]
                        
                        user_docs = list(transactions_collection.aggregate(pipeline))
                        
                        # Extract all transactions from all users that are newer than last check
                        for user_doc in user_docs:
                            if 'transactions' in user_doc and user_doc['transactions']:
                                for tx in user_doc['transactions']:
                                    tx_id = tx.get('tx_id')
                                    if tx_id and tx_id not in transaction_ids_seen:
                                        transaction_ids_seen.add(tx_id)
                                        new_transactions.append(tx)
                                        
                        logger.info(f"Found {len(transaction_ids_seen) - len(document_transactions)} new array-based transactions")
                    except Exception as e:
                        logger.error(f"Error fetching new array-based transactions: {e}")
                    
                    # Update last check time
                    new_check_time = datetime.datetime.now()
                    
                    # If there are new transactions, format and emit them
                    if new_transactions:
                        # Sort by timestamp
                        new_transactions.sort(key=lambda x: x.get('timestamp', datetime.datetime.min), reverse=True)
                        
                        # Format for public display
                        formatted_transactions = [format_transaction_for_public(tx) for tx in new_transactions]
                        
                        # Update the cache with new transactions
                        with cache_lock:
                            if transactions_cache['data'] is not None:
                                # Add new transactions to cache
                                all_cached = [tx for tx in new_transactions]
                                all_cached.extend(transactions_cache['data'])
                                
                                # Deduplicate
                                unique_ids = set()
                                unique_transactions = []
                                
                                for tx in all_cached:
                                    tx_id = tx.get('tx_id')
                                    if tx_id and tx_id not in unique_ids:
                                        unique_ids.add(tx_id)
                                        unique_transactions.append(tx)
                                
                                # Sort again
                                unique_transactions.sort(key=lambda x: x.get('timestamp', datetime.datetime.min), reverse=True)
                                
                                # Update cache
                                transactions_cache['data'] = unique_transactions
                                transactions_cache['total_count'] += len(new_transactions)
                                transactions_cache['last_updated'] = time.time()
                        
                        # Emit to all connected clients
                        socketio.emit('new_transactions', 
                                    {'transactions': formatted_transactions}, 
                                    namespace='/network-transactions')
                        
                        logger.info(f"Emitted {len(formatted_transactions)} new transactions to {len(connected_clients)} clients")
                    
                    # Update check time after processing
                    last_check_time = new_check_time
            
            except Exception as e:
                logger.error(f"Error in transaction check loop: {str(e)}")
            
            # Sleep before next check (3 seconds - reduced from 5 to improve responsiveness)
            await asyncio.sleep(3)
    
    except asyncio.CancelledError:
        logger.info("Transaction check task cancelled")
    except Exception as e:
        logger.error(f"Unexpected error in transaction check loop: {str(e)}")

# Main initialization function
def init_app(app):
    # Register blueprint
    app.register_blueprint(network_transactions_bp)
    
    # Register JSON encoder for MongoDB objects
    app.json_encoder = MongoJSONEncoder
    
    # Setup SocketIO if available on the app
    if hasattr(app, 'socketio'):
        socketio = app.socketio
        connected_clients = setup_socketio(socketio)
        
        # Start background task for checking new transactions
        @app.before_first_request
        def start_transaction_check():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Create and run the task with connected clients tracking
            transaction_check_task = loop.create_task(check_for_new_transactions(socketio, connected_clients))
            
            # Store task in app context to prevent garbage collection
            app.transaction_check_task = transaction_check_task
    
    logger.info("Network transactions module initialized")
    return network_transactions_bp 