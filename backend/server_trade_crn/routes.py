"""
Server Trading Routes
-------------------
API routes for fetching and managing Discord servers that trade with the currency.
"""

from flask import jsonify, request, current_app
from backend.db_connection import client
import logging
import re
from functools import wraps
from bson.objectid import ObjectId
import time
import hashlib
from pymongo.errors import OperationFailure

# Setup logging
logger = logging.getLogger(__name__)

# Initialize staff database connection
staff_db = client["staff"]
server_trade_collection = staff_db["server_trade_crn"]

# Constants
DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 100
RATE_LIMIT_WINDOW = 60  # seconds
MAX_REQUESTS = 30  # requests per minute

# Cache for rate limiting
request_cache = {}

def sanitize_input(input_str):
    """Sanitize input to prevent NoSQL injection"""
    if not input_str or not isinstance(input_str, str):
        return ""
    # Remove MongoDB operators and special characters
    return re.sub(r'[${}()[\].]', '', input_str)

def rate_limit(f):
    """Rate limiting decorator for API endpoints"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get client IP
        client_ip = request.remote_addr
        
        # Generate a unique key for this endpoint + IP
        endpoint = request.path
        key = f"{client_ip}:{endpoint}"
        
        # Get current timestamp
        current_time = time.time()
        
        # Initialize or clean up old entries
        if key not in request_cache:
            request_cache[key] = []
        request_cache[key] = [t for t in request_cache[key] if current_time - t < RATE_LIMIT_WINDOW]
        
        # Check if rate limit exceeded
        if len(request_cache[key]) >= MAX_REQUESTS:
            logger.warning(f"Rate limit exceeded for {key}")
            return jsonify({
                "success": False,
                "error": "Rate limit exceeded. Please try again later."
            }), 429
        
        # Add current request timestamp
        request_cache[key].append(current_time)
        
        # Call the original function
        return f(*args, **kwargs)
    return decorated_function

def format_server_doc(server):
    """Format server document for JSON response"""
    if not server:
        return None
        
    # Create a copy to avoid modifying the original
    formatted = dict(server)
    
    # Convert ObjectId to string
    if '_id' in formatted:
        formatted['_id'] = str(formatted['_id'])
    
    # Convert NumberLong to int
    if 'server_id' in formatted and isinstance(formatted['server_id'], dict) and '$numberLong' in formatted['server_id']:
        formatted['server_id'] = int(formatted['server_id']['$numberLong'])
    
    # Ensure server_type exists
    if 'server_type' not in formatted:
        formatted['server_type'] = 'other'
        
    return formatted

def get_pagination_params():
    """Extract and validate pagination parameters"""
    try:
        page = max(1, int(request.args.get('page', 1)))
        limit = min(MAX_PAGE_SIZE, max(1, int(request.args.get('limit', DEFAULT_PAGE_SIZE))))
        skip = (page - 1) * limit
        return page, limit, skip
    except (ValueError, TypeError):
        return 1, DEFAULT_PAGE_SIZE, 0

def init_routes(blueprint):
    """Initialize routes for the partner servers blueprint"""
    
    @blueprint.route('/', methods=['GET'])
    @rate_limit
    def get_all_servers():
        """Get all trading servers with pagination"""
        try:
            # Get pagination parameters
            page, limit, skip = get_pagination_params()
            
            # Get query filters
            server_type = request.args.get('type')
            
            # Build query
            query = {}
            if server_type:
                sanitized_type = sanitize_input(server_type)
                if sanitized_type:
                    query["server_type"] = sanitized_type
            
            # Execute query with pagination
            cursor = server_trade_collection.find(query).skip(skip).limit(limit)
            servers = list(cursor)
            
            # Get total count for pagination
            total_count = server_trade_collection.count_documents(query)
            
            # Format response
            formatted_servers = [format_server_doc(server) for server in servers]
            
            return jsonify({
                "success": True,
                "servers": formatted_servers,
                "count": len(formatted_servers),
                "total": total_count,
                "page": page,
                "pages": (total_count // limit) + (1 if total_count % limit > 0 else 0)
            })
        except Exception as e:
            logger.error(f"Error fetching servers: {str(e)}", exc_info=True)
            return jsonify({
                "success": False,
                "error": "Failed to fetch servers"
            }), 500
    
    @blueprint.route('/partners', methods=['GET'])
    @rate_limit
    def get_partner_servers():
        """Get partner servers with pagination"""
        try:
            # Get pagination parameters
            page, limit, skip = get_pagination_params()
            
            # Query for servers with type 'partner' or partner flag
            query = {"$or": [
                {"server_type": "partner"},
                {"partner": True}
            ]}
            
            # Execute query with pagination
            cursor = server_trade_collection.find(query).skip(skip).limit(limit)
            servers = list(cursor)
            
            # Get total count for pagination
            total_count = server_trade_collection.count_documents(query)
            
            # Format response
            formatted_servers = [format_server_doc(server) for server in servers]
            
            return jsonify({
                "success": True,
                "servers": formatted_servers,
                "count": len(formatted_servers),
                "total": total_count,
                "page": page,
                "pages": (total_count // limit) + (1 if total_count % limit > 0 else 0)
            })
        except Exception as e:
            logger.error(f"Error fetching partner servers: {str(e)}", exc_info=True)
            return jsonify({
                "success": False,
                "error": "Failed to fetch partner servers"
            }), 500
    
    @blueprint.route('/services', methods=['GET'])
    @rate_limit
    def get_service_servers():
        """Get service servers with pagination"""
        try:
            # Get pagination parameters
            page, limit, skip = get_pagination_params()
            
            # Query for servers with service flag
            query = {"$or": [
                {"server_type": "service"},
                {"service": True}
            ]}
            
            # Execute query with pagination
            cursor = server_trade_collection.find(query).skip(skip).limit(limit)
            servers = list(cursor)
            
            # Get total count for pagination
            total_count = server_trade_collection.count_documents(query)
            
            # Format response
            formatted_servers = [format_server_doc(server) for server in servers]
            
            return jsonify({
                "success": True,
                "servers": formatted_servers,
                "count": len(formatted_servers),
                "total": total_count,
                "page": page,
                "pages": (total_count // limit) + (1 if total_count % limit > 0 else 0)
            })
        except Exception as e:
            logger.error(f"Error fetching service servers: {str(e)}", exc_info=True)
            return jsonify({
                "success": False,
                "error": "Failed to fetch service servers"
            }), 500
    
    @blueprint.route('/shops', methods=['GET'])
    @rate_limit
    def get_shop_servers():
        """Get shop servers with pagination"""
        try:
            # Get pagination parameters
            page, limit, skip = get_pagination_params()
            
            # Query for servers with shop flag
            query = {"$or": [
                {"server_type": "shop"},
                {"server_shop": True}
            ]}
            
            # Execute query with pagination
            cursor = server_trade_collection.find(query).skip(skip).limit(limit)
            servers = list(cursor)
            
            # Get total count for pagination
            total_count = server_trade_collection.count_documents(query)
            
            # Format response
            formatted_servers = [format_server_doc(server) for server in servers]
            
            return jsonify({
                "success": True,
                "servers": formatted_servers,
                "count": len(formatted_servers),
                "total": total_count,
                "page": page,
                "pages": (total_count // limit) + (1 if total_count % limit > 0 else 0)
            })
        except Exception as e:
            logger.error(f"Error fetching shop servers: {str(e)}", exc_info=True)
            return jsonify({
                "success": False,
                "error": "Failed to fetch shop servers"
            }), 500
    
    @blueprint.route('/<server_id>', methods=['GET'])
    @rate_limit
    def get_server_by_id(server_id):
        """Get a specific server by ID"""
        try:
            # Validate server_id
            try:
                server_id_int = int(server_id)
                # Try to find server by ID
                server = server_trade_collection.find_one({"server_id": {"$numberLong": str(server_id_int)}})
            except ValueError:
                # If not an integer, try as ObjectId if in correct format
                if ObjectId.is_valid(server_id):
                    server = server_trade_collection.find_one({"_id": ObjectId(server_id)})
                else:
                    return jsonify({
                        "success": False,
                        "error": "Invalid server ID format"
                    }), 400
            
            if not server:
                return jsonify({
                    "success": False,
                    "error": "Server not found"
                }), 404
            
            # Format response
            formatted_server = format_server_doc(server)
            
            return jsonify({
                "success": True,
                "server": formatted_server
            })
        except Exception as e:
            logger.error(f"Error fetching server {server_id}: {str(e)}", exc_info=True)
            return jsonify({
                "success": False,
                "error": "Failed to fetch server"
            }), 500
            
    @blueprint.route('/search', methods=['GET'])
    @rate_limit
    def search_servers():
        """Search for servers by name or description with protection against injection"""
        try:
            # Get pagination parameters
            page, limit, skip = get_pagination_params()
            
            # Get and sanitize search term
            search_term = request.args.get('q', '').strip()
            
            # Limit search term length for security
            if len(search_term) > 100:
                search_term = search_term[:100]
                
            # If search term is empty, return all servers
            if not search_term:
                return get_all_servers()
                
            # Sanitize input to prevent NoSQL injection
            sanitized_term = sanitize_input(search_term)
            
            # Get filter type if specified
            filter_type = request.args.get('type')
            
            # Create secure search query (case insensitive)
            search_query = {
                "$or": [
                    {"server_name": {"$regex": sanitized_term, "$options": "i"}},
                    {"server_description": {"$regex": sanitized_term, "$options": "i"}}
                ]
            }
            
            # Add type filter if specified
            if filter_type:
                sanitized_type = sanitize_input(filter_type)
                if sanitized_type:
                    if sanitized_type == "partner":
                        search_query["$and"] = [{"$or": [{"server_type": "partner"}, {"partner": True}]}]
                    elif sanitized_type == "service":
                        search_query["$and"] = [{"$or": [{"server_type": "service"}, {"service": True}]}]
                    elif sanitized_type == "shop":
                        search_query["$and"] = [{"$or": [{"server_type": "shop"}, {"server_shop": True}]}]
                    else:
                        search_query["server_type"] = sanitized_type
            
            # Get total count
            total_count = server_trade_collection.count_documents(search_query)
            
            # Execute query with pagination
            servers = list(server_trade_collection.find(search_query).skip(skip).limit(limit))
            
            # Process results for JSON serialization
            formatted_servers = [format_server_doc(server) for server in servers]
            
            # Return results with metadata
            return jsonify({
                "success": True,
                "servers": formatted_servers,
                "count": len(formatted_servers),
                "total": total_count,
                "page": page,
                "pages": (total_count // limit) + (1 if total_count % limit > 0 else 0),
                "search_term": sanitized_term
            })
        except Exception as e:
            logger.error(f"Error during server search: {str(e)}", exc_info=True)
            return jsonify({
                "success": False,
                "error": "Failed to search servers"
            }), 500

    # Add a stats endpoint for getting network statistics
    @blueprint.route('/stats', methods=['GET'])
    @rate_limit
    def get_network_stats():
        """Get network statistics"""
        try:
            # Create aggregation pipeline to calculate statistics
            pipeline = [
                {
                    "$facet": {
                        "total": [
                            {"$count": "count"},
                            {"$addFields": {"members": {"$sum": "$member_count"}}}
                        ],
                        "partners": [
                            {"$match": {"$or": [{"server_type": "partner"}, {"partner": True}]}},
                            {"$count": "count"},
                            {"$addFields": {"members": {"$sum": "$member_count"}}}
                        ],
                        "services": [
                            {"$match": {"$or": [{"server_type": "service"}, {"service": True}]}},
                            {"$count": "count"},
                            {"$addFields": {"members": {"$sum": "$member_count"}}}
                        ],
                        "shops": [
                            {"$match": {"$or": [{"server_type": "shop"}, {"server_shop": True}]}},
                            {"$count": "count"},
                            {"$addFields": {"members": {"$sum": "$member_count"}}}
                        ]
                    }
                }
            ]
            
            # Alternative approach with multiple queries if aggregation pipeline doesn't work
            total_servers = server_trade_collection.count_documents({})
            total_members = sum(server.get('member_count', 0) for server in server_trade_collection.find({}, {"member_count": 1}))
            
            partner_query = {"$or": [{"server_type": "partner"}, {"partner": True}]}
            partner_servers = server_trade_collection.count_documents(partner_query)
            partner_members = sum(server.get('member_count', 0) for server in server_trade_collection.find(partner_query, {"member_count": 1}))
            
            service_query = {"$or": [{"server_type": "service"}, {"service": True}]}
            service_servers = server_trade_collection.count_documents(service_query)
            service_members = sum(server.get('member_count', 0) for server in server_trade_collection.find(service_query, {"member_count": 1}))
            
            shop_query = {"$or": [{"server_type": "shop"}, {"server_shop": True}]}
            shop_servers = server_trade_collection.count_documents(shop_query)
            shop_members = sum(server.get('member_count', 0) for server in server_trade_collection.find(shop_query, {"member_count": 1}))
            
            stats = {
                "totalServers": total_servers,
                "totalMembers": total_members,
                "partners": {
                    "count": partner_servers,
                    "members": partner_members
                },
                "services": {
                    "count": service_servers,
                    "members": service_members
                },
                "shops": {
                    "count": shop_servers,
                    "members": shop_members
                }
            }
            
            return jsonify({
                "success": True,
                "stats": stats
            })
        except Exception as e:
            logger.error(f"Error fetching network stats: {str(e)}", exc_info=True)
            return jsonify({
                "success": False,
                "error": "Failed to fetch network statistics"
            }), 500 