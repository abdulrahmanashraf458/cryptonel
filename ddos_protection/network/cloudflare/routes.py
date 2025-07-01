#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Cloudflare Routes for DDoS Protection
-----------------------------------
API routes for managing Cloudflare firewall rules.
These routes are used by the admin dashboard to manage IP blocks.

Routes include:
- GET /api/cloudflare/ips - Get all blocked IPs
- POST /api/cloudflare/block - Block an IP
- POST /api/cloudflare/unblock - Unblock an IP
- GET /api/cloudflare/status - Get Cloudflare integration status
"""

import os
import json
import logging
import asyncio
import time
from functools import wraps
from typing import Dict, Any, Optional

try:
    from flask import Blueprint, request, jsonify, Response, current_app
    from werkzeug.local import LocalProxy
    
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False
    
# Configure logger
logger = logging.getLogger('ddos_protection.cloudflare.routes')

# Reference to Cloudflare client
cf_client = None

# Check if we're in development mode
CF_DEV_MODE = os.environ.get('CF_DEV_MODE', 'false').lower() == 'true'

def register_cloudflare_routes(app):
    """
    Register Cloudflare routes with Flask app.
    
    Args:
        app: Flask application
    """
    if not FLASK_AVAILABLE:
        logger.error("Flask not available, cannot register Cloudflare routes")
        return
    
    # Create blueprint
    cf_blueprint = Blueprint('cloudflare', __name__)
    
    # Get Cloudflare client
    global cf_client
    cf_client = app.cf_client if hasattr(app, 'cf_client') else None
    
    # Solo mostrar advertencia si no estamos en modo de desarrollo
    if not cf_client and not CF_DEV_MODE:
        logger.warning("Cloudflare client not available, routes will not function correctly")
    elif CF_DEV_MODE:
        logger.info("Cloudflare routes registered in DEVELOPMENT mode (simulated responses)")
        
        # En modo desarrollo, crear un cliente simulado si no existe
        from ddos_protection.network.cloudflare.api import CloudflareAPIClient
        cf_client = CloudflareAPIClient()
    
    # Define routes
    @cf_blueprint.route('/api/cloudflare/ips', methods=['GET', 'OPTIONS'])
    @cf_blueprint.route('/api/ddos/cloudflare/ips', methods=['GET', 'OPTIONS'])
    def get_blocked_ips():
        """Get all blocked IPs from Cloudflare."""
        # Handle OPTIONS request for CORS
        if request.method == 'OPTIONS':
            return _handle_cors_preflight()
            
        if not cf_client:
            return jsonify({"success": False, "error": "Cloudflare integration not configured"}), 503
        
        try:
            # Run async function in a sync context
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                blocked_ips = loop.run_until_complete(cf_client.get_blocked_ips())
            finally:
                loop.close()
                
            return jsonify({
                "success": True,
                "blocked_ips": blocked_ips
            })
        except Exception as e:
            logger.error(f"Error getting blocked IPs: {e}")
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500
    
    @cf_blueprint.route('/api/cloudflare/block', methods=['POST', 'OPTIONS'])
    @cf_blueprint.route('/api/ddos/cloudflare/block', methods=['POST', 'OPTIONS'])
    def block_ip():
        """Block an IP address in Cloudflare."""
        # Handle OPTIONS request for CORS
        if request.method == 'OPTIONS':
            return _handle_cors_preflight()
            
        if not cf_client:
            return jsonify({"success": False, "error": "Cloudflare integration not configured"}), 503
        
        try:
            data = request.get_json()
            ip = data.get('ip')
            reason = data.get('reason', 'Blocked via API')
            duration = data.get('duration', 86400)  # Default: 24 hours
            
            if not ip:
                return jsonify({"success": False, "error": "IP address required"}), 400
                
            # Run async function in a sync context
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                success, result = loop.run_until_complete(cf_client.block_ip(ip, reason, duration))
            finally:
                loop.close()
                
            if success:
                return jsonify({
                    "success": True,
                    "message": f"IP {ip} blocked successfully"
                })
            else:
                return jsonify({
                    "success": False,
                    "error": f"Failed to block IP: {result.get('message', 'Unknown error')}"
                }), 500
        except Exception as e:
            logger.error(f"Error blocking IP: {e}")
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500
    
    @cf_blueprint.route('/api/cloudflare/unblock', methods=['POST', 'OPTIONS'])
    @cf_blueprint.route('/api/ddos/cloudflare/unblock', methods=['POST', 'OPTIONS'])
    def unblock_ip():
        """Unblock an IP address in Cloudflare."""
        # Handle OPTIONS request for CORS
        if request.method == 'OPTIONS':
            return _handle_cors_preflight()
            
        if not cf_client:
            return jsonify({"success": False, "error": "Cloudflare integration not configured"}), 503
        
        try:
            data = request.get_json()
            ip = data.get('ip')
            
            if not ip:
                return jsonify({"success": False, "error": "IP address required"}), 400
                
            # Run async function in a sync context
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                success, result = loop.run_until_complete(cf_client.unblock_ip(ip))
            finally:
                loop.close()
                
            if success:
                return jsonify({
                    "success": True,
                    "message": f"IP {ip} unblocked successfully"
                })
            else:
                return jsonify({
                    "success": False,
                    "error": f"Failed to unblock IP: {result.get('message', 'Unknown error')}"
                }), 500
        except Exception as e:
            logger.error(f"Error unblocking IP: {e}")
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500
    
    @cf_blueprint.route('/api/cloudflare/status', methods=['GET', 'OPTIONS'])
    @cf_blueprint.route('/api/ddos/cloudflare/status', methods=['GET', 'OPTIONS'])
    def get_status():
        """Get Cloudflare integration status."""
        # Handle OPTIONS request for CORS
        if request.method == 'OPTIONS':
            return _handle_cors_preflight()
            
        # Check if Cloudflare API credentials are configured
        cf_api_email = os.environ.get('CF_API_EMAIL', '')
        cf_api_key = os.environ.get('CF_API_KEY', '')
        cf_zone_id = os.environ.get('CF_ZONE_ID', '')
        
        is_configured = all([cf_api_email, cf_api_key, cf_zone_id])
        is_client_available = cf_client is not None
        using_exclusively = os.environ.get('USE_CLOUDFLARE_EXCLUSIVELY', 'false').lower() == 'true'
        
        return jsonify({
            "success": True,
            "status": {
                "configured": is_configured,
                "client_available": is_client_available,
                "using_exclusively": using_exclusively,
                "api_email_set": bool(cf_api_email),
                "api_key_set": bool(cf_api_key),
                "zone_id_set": bool(cf_zone_id)
            }
        })
    
    @cf_blueprint.route('/api/cloudflare/sync', methods=['POST', 'OPTIONS'])
    @cf_blueprint.route('/api/ddos/cloudflare/sync', methods=['POST', 'OPTIONS'])
    def sync_from_cloudflare():
        """Sync blocked IPs from Cloudflare to local system."""
        # Handle OPTIONS request for CORS
        if request.method == 'OPTIONS':
            return _handle_cors_preflight()
            
        if not cf_client:
            return jsonify({"success": False, "error": "Cloudflare integration not configured"}), 503
            
        try:
            # Run async function in a sync context
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                # Import sync_from_cloudflare function
                from ddos_protection.network.cloudflare import sync_from_cloudflare as do_sync
                success = loop.run_until_complete(do_sync())
            finally:
                loop.close()
                
            if success:
                return jsonify({
                    "success": True,
                    "message": "Successfully synced blocked IPs from Cloudflare"
                })
            else:
                return jsonify({
                    "success": False,
                    "error": "Failed to sync blocked IPs from Cloudflare"
                }), 500
        except Exception as e:
            logger.error(f"Error syncing from Cloudflare: {e}")
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500
            
    def _handle_cors_preflight():
        """Handle CORS preflight OPTIONS request."""
        response = Response()
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE,OPTIONS')
        return response
    
    # Register blueprint with app
    app.register_blueprint(cf_blueprint)
    logger.info("Cloudflare routes registered with Flask app") 