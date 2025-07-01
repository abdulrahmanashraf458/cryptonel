"""
Server Trading Module
-------------------
This module handles fetching and managing Discord servers that trade with the currency.

Endpoints:
- GET /api/partner-servers/ - Get all trading servers with pagination
- GET /api/partner-servers/partners - Get partner servers with pagination
- GET /api/partner-servers/services - Get service servers with pagination
- GET /api/partner-servers/shops - Get shop servers with pagination
- GET /api/partner-servers/<server_id> - Get a specific server by ID
- GET /api/partner-servers/search - Search for servers by name
- GET /api/partner-servers/stats - Get network statistics
"""

from flask import Blueprint, jsonify, request
from backend.db_connection import client
from backend.server_trade_crn.routes import init_routes
import logging

# Setup logging
logger = logging.getLogger(__name__)

# Create Blueprint for partner server API endpoints
partner_servers_bp = Blueprint('partner_servers', __name__, url_prefix='/api/partner-servers')

def init_app(app):
    """Initialize the partner servers module with the Flask app"""
    try:
        # Initialize the routes
        init_routes(partner_servers_bp)
        
        # Register the blueprint with the app
        app.register_blueprint(partner_servers_bp)
        
        logger.info("Server Trade CRN module initialized successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize Server Trade CRN module: {str(e)}", exc_info=True)
        return False

# Add health check endpoint to verify module is running
@partner_servers_bp.route('/health', methods=['GET'])
def health_check():
    """Simple health check endpoint to verify the module is running"""
    try:
        # Check database connection
        client.admin.command('ping')
        return jsonify({
            "status": "healthy",
            "message": "Server Trade CRN module is running and database connection is working"
        })
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}", exc_info=True)
        return jsonify({
            "status": "unhealthy",
            "message": "Database connection failed"
        }), 500 