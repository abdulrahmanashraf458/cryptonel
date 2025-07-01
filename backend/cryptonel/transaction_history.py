import logging
import os
import math
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request, session, current_app
from pymongo import MongoClient, DESCENDING
from bson.objectid import ObjectId
from pymongo.errors import PyMongoError
from backend.jwt_utils import token_required
import time  # Added for performance tracking

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# MongoDB connection
MONGODB_URI = os.getenv("DATABASE_URL")
client = MongoClient(MONGODB_URI)
db = client["cryptonel_wallet"]
users_collection = db["users"]
# Use the same collection for both old (array-based) and new (document-based) transactions
user_transactions_collection = db["user_transactions"]
tax_collection = db["transaction_taxes"]  # Collection for transaction taxes if exists

# Create blueprint
transaction_history_bp = Blueprint('transaction_history', __name__)

def get_transaction_summary(transactions):
    """Calculate summary statistics from user transactions."""
    summary = {
        "total_transactions": len(transactions),
        "total_sent": 0,
        "total_received": 0,
        "sent_count": 0,
        "received_count": 0,
        "largest_transaction": 0,
        "recent_activity": {
            "week": 0,
            "month": 0,
            "year": 0
        }
    }
    
    if not transactions:
        return summary
    
    # Current time for calculating recent activity
    now = datetime.utcnow()
    one_week_ago = now - timedelta(days=7)
    one_month_ago = now - timedelta(days=30)
    one_year_ago = now - timedelta(days=365)
    
    largest_tx_amount = 0
    
    for tx in transactions:
        # Parse amount to float
        amount = float(tx.get("amount", 0))
        
        # Calculate sent/received totals
        tx_type = tx.get("type", "")
        if tx_type == "sent":
            summary["total_sent"] += amount
            summary["sent_count"] += 1
        elif tx_type == "received":
            summary["total_received"] += amount
            summary["received_count"] += 1
        
        # Track largest transaction
        if amount > largest_tx_amount:
            largest_tx_amount = amount
        
        # Calculate recent activity
        tx_timestamp = tx.get("timestamp")
        if isinstance(tx_timestamp, dict) and "$date" in tx_timestamp:
            try:
                tx_date = datetime.fromisoformat(tx_timestamp["$date"].replace("Z", "+00:00"))
                if tx_date >= one_week_ago:
                    summary["recent_activity"]["week"] += 1
                if tx_date >= one_month_ago:
                    summary["recent_activity"]["month"] += 1
                if tx_date >= one_year_ago:
                    summary["recent_activity"]["year"] += 1
            except (ValueError, TypeError) as e:
                logger.error(f"Error parsing transaction timestamp: {e}")
        elif isinstance(tx_timestamp, datetime):
            # Handle native datetime objects
            if tx_timestamp >= one_week_ago:
                summary["recent_activity"]["week"] += 1
            if tx_timestamp >= one_month_ago:
                summary["recent_activity"]["month"] += 1
            if tx_timestamp >= one_year_ago:
                summary["recent_activity"]["year"] += 1
    
    summary["largest_transaction"] = largest_tx_amount
    
    # Calculate balance
    summary["balance"] = summary["total_received"] - summary["total_sent"]
    
    # Format numeric values for display
    summary["total_sent"] = "{:.8f}".format(summary["total_sent"])
    summary["total_received"] = "{:.8f}".format(summary["total_received"])
    summary["largest_transaction"] = "{:.8f}".format(summary["largest_transaction"])
    summary["balance"] = "{:.8f}".format(summary["balance"])
    
    return summary

def parse_and_format_date(timestamp):
    """Parse MongoDB timestamp and format it for display."""
    try:
        # Direct datetime object (most common case in our database)
        if isinstance(timestamp, datetime):
            return timestamp.strftime("%Y-%m-%d %H:%M")
        # MongoDB format with $date field
        elif isinstance(timestamp, dict) and "$date" in timestamp:
            date_str = timestamp["$date"]
            # Try to parse the ISO format date
            try:
                # Remove 'Z' and replace with UTC offset
                date_obj = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                # Format the date into a readable string: YYYY-MM-DD HH:MM
                return date_obj.strftime("%Y-%m-%d %H:%M")
            except (ValueError, TypeError) as e:
                logger.error(f"Error parsing ISO date: {e} - Date string: {date_str}")
                # Try alternative parsing methods if ISO parsing fails
                try:
                    from dateutil import parser
                    date_obj = parser.parse(date_str)
                    return date_obj.strftime("%Y-%m-%d %H:%M")
                except:
                    logger.error(f"All date parsing methods failed for: {date_str}")
                    return "Unknown date"
        # String timestamp
        elif isinstance(timestamp, str):
            # Try to parse direct string timestamp
            try:
                from dateutil import parser
                date_obj = parser.parse(timestamp)
                return date_obj.strftime("%Y-%m-%d %H:%M")
            except:
                logger.error(f"Failed to parse string timestamp: {timestamp}")
                return "Unknown date"
        else:
            logger.warning(f"Unexpected timestamp format: {type(timestamp)}")
            return "Unknown date"
    except Exception as e:
        logger.error(f"Unexpected error during date parsing: {e}")
        return "Unknown date"

def normalize_user_id(user_id):
    """Attempt to normalize the user_id to match what's in the database"""
    # Try as string
    user_id_str = str(user_id) if not isinstance(user_id, str) else user_id
    
    # Try as integer if it looks like a number
    user_id_int = None
    if user_id_str.isdigit():
        user_id_int = int(user_id_str)
    
    return [user_id, user_id_str, user_id_int]

def get_transaction_tax(tx_id):
    """Get tax information for a transaction if available"""
    try:
        tax_info = tax_collection.find_one({"tx_id": tx_id})
        if tax_info and "amount" in tax_info:
            return "{:.8f}".format(float(tax_info.get("amount", 0)))
    except PyMongoError:
        # If there's an error or the collection doesn't exist
        pass
    return None

def format_transaction(tx):
    """Format a transaction for display in the API response"""
    # Create a copy of the transaction to modify
    formatted_tx = tx.copy()
    
    # Format the date properly
    formatted_tx["formatted_date"] = parse_and_format_date(tx.get("timestamp"))
    
    # Format counterparty public address (truncate to first 4 and last 2 characters)
    public_address = tx.get("counterparty_public_address", "")
    if public_address and len(public_address) > 6:
        formatted_tx["display_address"] = f"{public_address[:4]}..{public_address[-2:]}"
    else:
        formatted_tx["display_address"] = public_address
    
    # Add tax information if available - only if needed, otherwise skip for performance
    # tax_amount = get_transaction_tax(tx.get("tx_id"))
    # if tax_amount:
    #     formatted_tx["tax"] = tax_amount
    
    # Ensure fee is formatted correctly
    if "fee" not in formatted_tx or formatted_tx["fee"] is None:
        formatted_tx["fee"] = "0.00000000"
    else:
        try:
            fee_value = float(formatted_tx["fee"])
            formatted_tx["fee"] = "{:.8f}".format(fee_value)
        except (ValueError, TypeError):
            formatted_tx["fee"] = "0.00000000"
    
    # Additional details formatting
    if "status" not in formatted_tx or not formatted_tx["status"]:
        formatted_tx["status"] = "completed"  # Default status
    
    if "reason" not in formatted_tx:
        formatted_tx["reason"] = ""
    
    return formatted_tx

def enrich_transaction_details(tx):
    """Add additional details to transaction for detailed view"""
    enriched_tx = format_transaction(tx)
    
    # Add tax information only for detailed view
    tax_amount = get_transaction_tax(tx.get("tx_id"))
    if tax_amount:
        enriched_tx["tax"] = tax_amount
    
    # Add more detailed information if available
    try:
        # Get detailed transaction info from another collection if needed
        # Additional detail fields could be added here
        
        # Example: Add blockchain verification status
        enriched_tx["blockchain_verified"] = True
        
        # Example: Add category if available
        category = tx.get("category", "")
        if category:
            enriched_tx["category"] = category
        else:
            # Try to auto-categorize based on keywords in the reason
            reason = tx.get("reason", "").lower()
            if any(word in reason for word in ["salary", "payment", "invoice"]):
                enriched_tx["category"] = "income"
            elif any(word in reason for word in ["food", "restaurant", "coffee"]):
                enriched_tx["category"] = "food"
            elif any(word in reason for word in ["transfer", "send", "gift"]):
                enriched_tx["category"] = "transfer"
            else:
                enriched_tx["category"] = "other"
    
    except Exception as e:
        logger.error(f"Error enriching transaction details: {e}")
    
    return enriched_tx

# Function to get user's transactions from both formats in the same collection
def convert_objectid_to_str(obj):
    """Convert ObjectId to string in a document or list of documents"""
    if isinstance(obj, list):
        return [convert_objectid_to_str(item) for item in obj]
    elif isinstance(obj, dict):
        result = {}
        for key, value in obj.items():
            if isinstance(value, ObjectId):
                result[key] = str(value)
            elif isinstance(value, (dict, list)):
                result[key] = convert_objectid_to_str(value)
            else:
                result[key] = value
        return result
    else:
        return obj

def get_merged_transactions(user_id, tx_type=None, start_date=None, end_date=None):
    """
    Get transactions from both array-based and document-based formats in the user_transactions collection
    """
    start_time = time.time()
    
    # Normalize user_id
    user_id_options = normalize_user_id(user_id)
    
    # 1. Get transactions from array-based format
    array_transactions = []
    for uid in user_id_options:
        if uid is None:
            continue
            
        user_txns = user_transactions_collection.find_one({"user_id": uid})
        if user_txns and "transactions" in user_txns:
            array_transactions = user_txns.get("transactions", [])
            break
    
    # 2. Get transactions from document-based format (same collection)
    document_transactions = []
    try:
        # Build query for document-based transactions
        query = {
            "document_type": "transaction",
            "user_id": {"$in": [uid for uid in user_id_options if uid is not None]}
        }
        
        # Add filters to query
        if tx_type:
            query["type"] = tx_type
            
        date_filter = {}
        if start_date:
            date_filter["$gte"] = start_date
        if end_date:
            date_filter["$lte"] = end_date
            
        if date_filter:
            query["timestamp"] = date_filter
            
        # Execute query
        document_transactions = list(user_transactions_collection.find(query))
        
        # Convert ObjectId to string to make it JSON serializable
        document_transactions = convert_objectid_to_str(document_transactions)
        
        # Log the count
        logger.debug(f"Found {len(document_transactions)} document-based transactions")
        
    except Exception as e:
        logger.error(f"Error fetching document transactions: {e}")
    
    # 3. Process array transactions to avoid duplicates
    processed_array_transactions = []
    
    # Create set of transaction IDs from document-based transactions for faster lookup
    document_tx_ids = {tx.get("tx_id") for tx in document_transactions}
    
    # Only include array transactions that don't exist in document transactions
    for tx in array_transactions:
        if tx.get("tx_id") not in document_tx_ids:
            processed_array_transactions.append(tx)
    
    # 4. Merge both sources
    all_transactions = processed_array_transactions + document_transactions
    
    # Log the result
    logger.debug(f"Merged {len(processed_array_transactions)} array transactions and {len(document_transactions)} document transactions")
    logger.debug(f"Total transactions after merge: {len(all_transactions)}")
    logger.debug(f"Merger completed in {time.time() - start_time:.2f}s")
    
    return all_transactions

@transaction_history_bp.route('/api/transaction-history', methods=['GET'])
@token_required
def get_transaction_history(user_id=None, **kwargs):
    """Fetch transaction history for the authenticated user with pagination."""
    start_time = time.time()
    try:
        # If no user_id from token, try to get from session
        if not user_id:
            user_id = session.get('user_id')
            if not user_id:
                return jsonify({"error": "Not authenticated"}), 401
        
        # Pagination parameters
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 100))
        
        # Type filter (optional)
        tx_type = request.args.get('type')
        
        # Date range filter (optional)
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        
        # Parse dates
        start_date = None
        end_date = None
        
        if start_date_str:
            try:
                start_date = datetime.fromisoformat(start_date_str + "T00:00:00+00:00")
            except ValueError as e:
                logger.error(f"Error parsing start_date: {e}")
        
        if end_date_str:
            try:
                # Add time component to include the entire day
                end_date = datetime.fromisoformat(end_date_str + "T23:59:59+00:00")
            except ValueError as e:
                logger.error(f"Error parsing end_date: {e}")
        
        # Sort order
        sort_order = request.args.get('sort', 'desc').lower()
        
        # Get transactions from both formats in the same collection
        all_transactions = get_merged_transactions(
            user_id,
            tx_type=tx_type,
            start_date=start_date,
            end_date=end_date
        )
        
        if not all_transactions:
            logger.warning(f"No transactions found for user {user_id}")
            return jsonify({
                "transactions": [],
                "summary": get_transaction_summary([]),
                "pagination": {"page": 1, "per_page": per_page, "total_count": 0, "total_pages": 0}
            }), 200
        
        # Apply date filter to array transactions if needed
        if start_date or end_date:
            filtered_transactions = []
            
            for tx in all_transactions:
                tx_timestamp = tx.get("timestamp")
                tx_date = None
                
                if isinstance(tx_timestamp, dict) and "$date" in tx_timestamp:
                    try:
                        tx_date = datetime.fromisoformat(tx_timestamp["$date"].replace("Z", "+00:00"))
                    except (ValueError, TypeError):
                        continue
                elif isinstance(tx_timestamp, datetime):
                    tx_date = tx_timestamp
                else:
                    continue
                
                # Check if transaction is within date range
                include_tx = True
                
                if start_date and tx_date < start_date:
                    include_tx = False
                    
                if end_date and tx_date > end_date:
                    include_tx = False
                    
                if include_tx:
                    filtered_transactions.append(tx)
                    
            all_transactions = filtered_transactions
        
        # Sort transactions by timestamp
        def get_tx_timestamp(tx):
            timestamp = tx.get("timestamp")
            
            if isinstance(timestamp, datetime):
                return timestamp
                
            if isinstance(timestamp, dict) and "$date" in timestamp:
                try:
                    return datetime.fromisoformat(timestamp["$date"].replace("Z", "+00:00"))
                except:
                    return datetime.min
                    
            return datetime.min
        
        all_transactions.sort(
            key=get_tx_timestamp,
            reverse=(sort_order == "desc")
        )
        
        # Get total count for pagination
        total_count = len(all_transactions)
        
        # Calculate total pages
        total_pages = math.ceil(total_count / per_page)
        
        # Paginate transactions
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        
        # Safety check to prevent index out of bounds
        if start_idx >= len(all_transactions):
            paginated_transactions = []
        else:
            paginated_transactions = all_transactions[start_idx:min(end_idx, len(all_transactions))]
        
        # Format transactions for response
        formatted_transactions = [format_transaction(tx) for tx in paginated_transactions]
        
        # Get summary statistics
        summary = get_transaction_summary(all_transactions)
        
        # Format response
        response = {
            "transactions": formatted_transactions,
            "summary": summary,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total_count": total_count,
                "total_pages": total_pages
            }
        }
        
        logger.debug(f"Total API time: {time.time() - start_time:.2f}s")
        
        # Add Cache-Control header for better performance
        resp = jsonify(response)
        resp.headers['Cache-Control'] = 'private, max-age=60'  # Cache for 60 seconds
        
        return resp, 200
    
    except PyMongoError as e:
        logger.error(f"MongoDB error: {e}")
        return jsonify({"error": "Database error occurred", "details": str(e)}), 500
    except ValueError as e:
        logger.error(f"Value error: {e}")
        return jsonify({"error": "Invalid parameter value", "details": str(e)}), 400
    except Exception as e:
        logger.error(f"Error fetching transaction history: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({"error": "An error occurred while fetching transaction history"}), 500

@transaction_history_bp.route('/api/transaction-history/<tx_id>', methods=['GET'])
@token_required
def get_transaction_details(tx_id, user_id=None, **kwargs):
    """Fetch detailed information for a specific transaction."""
    try:
        # If no user_id from token, try to get from session
        if not user_id:
            user_id = session.get('user_id')
            if not user_id:
                return jsonify({"error": "Not authenticated"}), 401
        
        # First look in the document-based format
        transaction = user_transactions_collection.find_one({
            "tx_id": tx_id,
            "user_id": {"$in": normalize_user_id(user_id)},
            "document_type": "transaction"
        })
        
        # Convert ObjectId to string if found
        if transaction:
            transaction = convert_objectid_to_str(transaction)
        
        # If not found, look in the array-based format
        if not transaction:
            # Normalize user_id to handle different formats
            user_id_options = normalize_user_id(user_id)
            
            # Try to find in array-based format
            for uid in user_id_options:
                if uid is None:
                    continue
                
                query = {"user_id": uid}
                user_txns = user_transactions_collection.find_one(query)
                
                if user_txns and "transactions" in user_txns:
                    # Find the specific transaction
                    transactions = user_txns.get("transactions", [])
                    transaction = next((tx for tx in transactions if tx.get("tx_id") == tx_id), None)
                    if transaction:
                        break
        
        if not transaction:
            return jsonify({"error": "Transaction not found"}), 404
        
        # Format the transaction with extended details
        formatted_tx = enrich_transaction_details(transaction)
        
        return jsonify({"transaction": formatted_tx}), 200
    
    except PyMongoError as e:
        logger.error(f"MongoDB error: {e}")
        return jsonify({"error": "Database error occurred", "details": str(e)}), 500
    except Exception as e:
        logger.error(f"Error fetching transaction details: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({"error": "An error occurred while fetching transaction details"}), 500

@transaction_history_bp.route('/api/transactions/stats', methods=['GET'])
@token_required
def get_transaction_stats(user_id=None, **kwargs):
    """Get advanced transaction statistics."""
    try:
        # Validate user ID
        if not user_id:
            user_id = session.get('user_id')
            if not user_id:
                return jsonify({"error": "Not authenticated"}), 401
        
        # Get all transactions from both formats
        all_transactions = get_merged_transactions(user_id)
        
        if not all_transactions:
            return jsonify({"stats": {
                "transaction_counts": [],
                "volume_data": [],
                "averages": {"avg_sent": 0, "avg_received": 0}
            }}), 200
        
        # Get time period from query param (day, week, month, year)
        period = request.args.get('period', 'month')
        
        # Calculate stats based on period
        now = datetime.utcnow()
        date_ranges = []
        
        if period == 'day':
            # Last 24 hours, hourly intervals
            for i in range(24):
                start_time = now - timedelta(hours=24-i)
                end_time = now - timedelta(hours=23-i)
                date_ranges.append(('hour', start_time, end_time, f"{start_time.hour}:00"))
        elif period == 'week':
            # Last 7 days, daily intervals
            for i in range(7):
                start_date = (now - timedelta(days=7-i)).date()
                end_date = (now - timedelta(days=6-i)).date()
                date_ranges.append(('day', datetime.combine(start_date, datetime.min.time()), 
                                    datetime.combine(end_date, datetime.min.time()), 
                                    start_date.strftime("%a")))
        elif period == 'year':
            # Last 12 months, monthly intervals
            for i in range(12):
                curr_month = now.month - i - 1
                curr_year = now.year
                if curr_month <= 0:
                    curr_month += 12
                    curr_year -= 1
                
                month_start = datetime(curr_year, curr_month, 1)
                if curr_month == 12:
                    month_end = datetime(curr_year + 1, 1, 1)
                else:
                    month_end = datetime(curr_year, curr_month + 1, 1)
                
                date_ranges.append(('month', month_start, month_end, month_start.strftime("%b")))
        else:  # default to 'month'
            # Last 30 days, daily intervals
            for i in range(30):
                start_date = (now - timedelta(days=30-i)).date()
                end_date = (now - timedelta(days=29-i)).date()
                date_ranges.append(('day', datetime.combine(start_date, datetime.min.time()), 
                                    datetime.combine(end_date, datetime.min.time()), 
                                    start_date.strftime("%d")))
        
        # Calculate transaction stats
        transaction_counts = []
        volume_data = []
        
        for period_type, start, end, label in date_ranges:
            period_sent_count = 0
            period_received_count = 0
            period_sent_volume = 0
            period_received_volume = 0
            
            for tx in all_transactions:
                tx_timestamp = tx.get("timestamp")
                tx_date = None
                
                if isinstance(tx_timestamp, dict) and "$date" in tx_timestamp:
                    try:
                        tx_date = datetime.fromisoformat(tx_timestamp["$date"].replace("Z", "+00:00"))
                    except (ValueError, TypeError):
                        continue
                elif isinstance(tx_timestamp, datetime):
                    tx_date = tx_timestamp
                else:
                    continue
                
                if start <= tx_date < end:
                    tx_type = tx.get("type")
                    amount = float(tx.get("amount", 0))
                    
                    if tx_type == "sent":
                        period_sent_count += 1
                        period_sent_volume += amount
                    elif tx_type == "received":
                        period_received_count += 1
                        period_received_volume += amount
            
            transaction_counts.append({
                "label": label,
                "sent": period_sent_count,
                "received": period_received_count,
                "total": period_sent_count + period_received_count
            })
            
            volume_data.append({
                "label": label,
                "sent": round(period_sent_volume, 8),
                "received": round(period_received_volume, 8),
                "net": round(period_received_volume - period_sent_volume, 8)
            })
        
        # Calculate averages
        sent_amounts = [float(tx.get("amount", 0)) for tx in all_transactions if tx.get("type") == "sent"]
        received_amounts = [float(tx.get("amount", 0)) for tx in all_transactions if tx.get("type") == "received"]
        
        avg_sent = sum(sent_amounts) / len(sent_amounts) if sent_amounts else 0
        avg_received = sum(received_amounts) / len(received_amounts) if received_amounts else 0
        
        stats = {
            "transaction_counts": transaction_counts,
            "volume_data": volume_data,
            "averages": {
                "avg_sent": round(avg_sent, 8),
                "avg_received": round(avg_received, 8)
            }
        }
        
        return jsonify({"stats": stats}), 200

    except Exception as e:
        logger.error(f"Error fetching transaction stats: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({"error": "An error occurred while calculating transaction statistics"}), 500

def init_app(app):
    """Initialize the transaction history blueprint with the Flask app."""
    app.register_blueprint(transaction_history_bp) 