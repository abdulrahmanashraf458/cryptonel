#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Cryptonel - CSRF Helpers
-----------------------
Helper functions for CSRF token generation and validation
"""

import secrets
import time
import logging
import hashlib
import base64
from flask import Blueprint, jsonify, session, request, current_app

# Configure logging
logger = logging.getLogger('premium_auth')

# Create blueprint for CSRF routes
csrf_bp = Blueprint('csrf', __name__)

def generate_csrf_token():
    """
    Generate a new CSRF token and store it in the session
    
    Returns:
        str: The encrypted CSRF token
    """
    # Combine multiple entropy sources for better security
    # Remove current_time from entropy sources to make tokens more stable
    entropy_sources = [
        secrets.token_hex(32),  # Random bytes
        str(session.get('user_id', 'anonymous')),  # User ID
        request.headers.get('User-Agent', ''),  # User agent
        request.remote_addr     # Client IP
    ]
    
    # Create a hash of all entropy sources
    combined_entropy = ''.join(entropy_sources).encode('utf-8')
    raw_token = hashlib.sha256(combined_entropy).hexdigest()
    
    # Store the original token in session for validation
    session['csrf_token'] = raw_token
    session['csrf_token_created'] = time.time()
    
    # Encrypt the token before sending to client
    # Use a simple XOR encryption with a server-side key
    server_key_raw = current_app.config.get('SECRET_KEY', 'default-secret-key')
    # Handle both string and bytes types for SECRET_KEY
    if isinstance(server_key_raw, bytes):
        server_key = server_key_raw
    else:
        server_key = str(server_key_raw).encode('utf-8')
    token_bytes = raw_token.encode('utf-8')
    
    # XOR encryption
    encrypted_token = bytearray()
    for i, byte in enumerate(token_bytes):
        key_byte = server_key[i % len(server_key)]
        encrypted_token.append(byte ^ key_byte)
    
    # Encode as base64 for safe transmission
    encrypted_token_b64 = base64.b64encode(encrypted_token).decode('utf-8')
    
    return encrypted_token_b64

def validate_csrf_token(token):
    """
    Validate the CSRF token from the request against the one in session
    
    Args:
        token (str): The encrypted token from the request
        
    Returns:
        bool: True if token is valid, False otherwise
    """
    # Check if token is empty
    if not token:
        return False
        
    stored_token = session.get('csrf_token')
    if not stored_token:
        return False
    
    # Decrypt the token from client
    try:
        # Decode base64
        encrypted_bytes = base64.b64decode(token)
        
        # XOR decryption
        server_key_raw = current_app.config.get('SECRET_KEY', 'default-secret-key')
        # Handle both string and bytes types for SECRET_KEY
        if isinstance(server_key_raw, bytes):
            server_key = server_key_raw
        else:
            server_key = str(server_key_raw).encode('utf-8')
        decrypted_token = bytearray()
        for i, byte in enumerate(encrypted_bytes):
            key_byte = server_key[i % len(server_key)]
            decrypted_token.append(byte ^ key_byte)
        
        # Convert back to string
        client_token = decrypted_token.decode('utf-8')
        
    except Exception as e:
        logger.warning(f"Failed to decrypt CSRF token: {e}")
        return False
        
    # Use constant-time comparison to prevent timing attacks
    return secrets.compare_digest(stored_token, client_token)

# CSRF Token endpoint - DISABLED to prevent conflicts with main server endpoint
# @csrf_bp.route('/token', methods=['GET'])
# def get_csrf_token():
#     """
#     Endpoint to get a new CSRF token
#     """
#     try:
#         # Check if user is authenticated
#         if 'user_id' not in session:
#             return jsonify({
#                 "success": False,
#                 "message": "Authentication required"
#             }), 401
#             
#         # Generate a new encrypted token
#         encrypted_token = generate_csrf_token()
#         
#         # Log the token generation
#         logger.info(f"CSRF token generated for user: {session.get('user_id')}")
#         
#         # Return the encrypted token
#         return jsonify({
#             "success": True,
#             "csrf_token": encrypted_token,
#             "expires_in": 24 * 60 * 60  # 24 hours in seconds
#         })
#     except Exception as e:
#         logger.error(f"Error generating CSRF token: {e}")
#         return jsonify({
#             "success": False,
#             "message": "Error generating CSRF token"
#         }), 500

def init_app(app):
    """
    Initialize the CSRF module with the Flask app
    
    Args:
        app: The Flask application instance
    """
    # Register the blueprint
    app.register_blueprint(csrf_bp, url_prefix='/api/csrf')
    
    # DISABLED: Auto-generation of CSRF tokens to prevent conflicts with main server endpoint
    # @app.before_request
    # def ensure_csrf_token():
    #     """Ensure a CSRF token exists in the session"""
    #     if 'user_id' in session and 'csrf_token' not in session:
    #         generate_csrf_token()
    #         logger.debug(f"Auto-generated CSRF token for user: {session.get('user_id')}") 