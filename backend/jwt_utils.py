# -*- coding: utf-8 -*-

import os
import jwt
import time
import secrets
import hashlib
from datetime import datetime, timedelta
from flask import jsonify, request, current_app
from functools import wraps
import logging

# Configure logger
logger = logging.getLogger(__name__)

# Load JWT secret key from environment variable or use a default one
JWT_SECRET_KEY = os.environ.get('SECRET_KEY', 'my-super-secret-key-deal-with-it')
# Add a secondary key for token signing (layered security)
JWT_SECONDARY_KEY = os.environ.get('JWT_SECONDARY_KEY', secrets.token_hex(32))

def get_secret_key():
    """Return the JWT secret key"""
    return JWT_SECRET_KEY

# Update token expiration times with more secure values
# Token expiration times (in seconds)
ACCESS_TOKEN_EXPIRE = 15 * 60  # 15 minutes
REFRESH_TOKEN_EXPIRE = 12 * 60 * 60  # 12 hours (reduced from 24 hours)

# Persistent token expiration times (when remember_me is True)
PERSISTENT_ACCESS_TOKEN_EXPIRE = 24 * 60 * 60  # 1 day (reduced from 30 days)
PERSISTENT_REFRESH_TOKEN_EXPIRE = 7 * 24 * 60 * 60  # 7 days (reduced from 90 days)

# Token blacklist (memory-based for simplicity, use Redis in production)
TOKEN_BLACKLIST = set()

def generate_token_id():
    """Generate a unique token ID to help with revocation"""
    return secrets.token_hex(8)

def blacklist_token(jti):
    """Add a token ID to the blacklist"""
    TOKEN_BLACKLIST.add(jti)
    # Limit blacklist size to prevent memory issues
    if len(TOKEN_BLACKLIST) > 10000:
        # Remove random items when list gets too big
        for _ in range(1000):
            TOKEN_BLACKLIST.pop()

def is_token_blacklisted(jti):
    """Check if a token ID is blacklisted"""
    return jti in TOKEN_BLACKLIST

def create_tokens(user_id, username=None, premium=False, remember_me=False, fingerprint=None):
    """
    Create JWT access and refresh tokens
    
    Args:
        user_id (str): The user's ID
        username (str): The user's username (optional)
        premium (bool): Whether the user has premium status
        remember_me (bool): Whether to create persistent tokens
        fingerprint (str): Optional device fingerprint for additional security
        
    Returns:
        dict: Dictionary containing access_token, refresh_token, and expiration time
    """
    # Current timestamp
    now = int(time.time())
    
    # Set token expiry times based on remember_me flag
    access_expire = PERSISTENT_ACCESS_TOKEN_EXPIRE if remember_me else ACCESS_TOKEN_EXPIRE
    refresh_expire = PERSISTENT_REFRESH_TOKEN_EXPIRE if remember_me else REFRESH_TOKEN_EXPIRE
    
    # Generate unique token IDs
    access_jti = generate_token_id()
    refresh_jti = generate_token_id()
    
    # Claims common to both tokens
    common_claims = {
        "sub": user_id,  # subject (user_id)
        "iat": now,      # issued at time
    }
    
    # Additional claims for access token
    access_claims = {
        **common_claims,
        "exp": now + access_expire,  # expiration time
        "type": "access",
        "jti": access_jti,           # JWT ID for revocation
        "remember_me": remember_me   # Store remember_me flag in the token
    }
    
    # Add optional claims
    if username:
        access_claims["username"] = username
    if premium:
        access_claims["premium"] = premium
    if fingerprint:
        # Store a hash of the fingerprint, not the raw value
        access_claims["fph"] = hashlib.sha256(fingerprint.encode()).hexdigest()[:16]
    
    # Add a nonce to prevent token reuse
    access_claims["nonce"] = secrets.token_hex(8)
    
    # Create access token with stronger algorithm
    access_token = jwt.encode(
        access_claims,
        JWT_SECRET_KEY,
        algorithm="HS384"  # Upgraded from HS256
    )
    
    # Create refresh token (simpler, longer expiry)
    refresh_claims = {
        **common_claims,
        "exp": now + refresh_expire,
        "type": "refresh",
        "jti": refresh_jti,
        "remember_me": remember_me  # Store remember_me flag in refresh token too
    }
    
    # Add fingerprint hash to refresh token if provided
    if fingerprint:
        refresh_claims["fph"] = hashlib.sha256(fingerprint.encode()).hexdigest()[:16]
    
    refresh_token = jwt.encode(
        refresh_claims,
        JWT_SECRET_KEY,
        algorithm="HS384"  # Upgraded from HS256
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_in": access_expire,
        "token_type": "Bearer",
        "jti": access_jti  # Include token ID for client-side reference
    }

def decode_token(token, verify_type=True, expected_type=None, verify_fingerprint=True):
    """
    Verify and decode JWT token
    
    Args:
        token: JWT token to decode
        verify_type: Whether to verify the token type
        expected_type: Expected token type (access or refresh)
        verify_fingerprint: Whether to verify the fingerprint
        
    Returns:
        dict: Decoded payload or None if invalid
    """
    try:
        # Get secret key from app config
        secret_key = get_secret_key()
        
        # Debug logging
        logger.debug(f"Attempting to decode token starting with {token[:10]}...")
        
        # Decode token
        payload = jwt.decode(
            token,
            secret_key,
            algorithms=["HS384", "HS256"]  # Support both old and new algorithms
        )
        
        # Check if token is blacklisted
        if 'jti' in payload and is_token_blacklisted(payload['jti']):
            logger.warning(f"Token is blacklisted, jti={payload.get('jti')}")
            return None
        
        # Ensure the token type is correct if verification is requested
        if verify_type:
            token_type = payload.get('type')
            if expected_type and token_type != expected_type:
                logger.debug(f"Token type mismatch: expected={expected_type}, got={token_type}")
                return None
            elif not expected_type and token_type not in ['access', 'refresh']:
                logger.debug(f"Token has invalid type: {token_type}")
                return None
        
        # Verify fingerprint if required and present in request
        if verify_fingerprint and 'fph' in payload and request:
            # Get fingerprint from request header
            req_fingerprint = request.headers.get('X-Device-Fingerprint')
            if req_fingerprint:
                # Create hash from request fingerprint
                fp_hash = hashlib.sha256(req_fingerprint.encode()).hexdigest()[:16]
                # Compare with token fingerprint
                if fp_hash != payload.get('fph'):
                    logger.warning("Fingerprint in token doesn't match request fingerprint")
                    return None
        
        # Additional debug logging
        logger.debug(f"Token decoded successfully. User ID: {payload.get('sub')}")
        
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("Token has expired")
        return None
    except (jwt.InvalidTokenError, jwt.DecodeError) as e:
        logger.warning(f"Invalid token: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Error decoding token: {str(e)}")
        return None

def refresh_access_token(refresh_token, fingerprint=None):
    """
    Create a new access token from a valid refresh token
    
    Args:
        refresh_token (str): Refresh token
        fingerprint (str): Device fingerprint for verification
        
    Returns:
        dict: New access token info if refresh token is valid, 
              None if refresh token is invalid
    """
    try:
        # Decode refresh token (verify it's a refresh token)
        decoded = decode_token(refresh_token, verify_type=True, expected_type="refresh", 
                            verify_fingerprint=fingerprint is not None)
        
        if not decoded:
            logger.warning("Refresh token validation failed - invalid or expired token")
            return None
        
        # Extract user info
        user_id = decoded.get("sub")
        username = decoded.get("username")
        premium = decoded.get("premium", False)
        remember_me = decoded.get("remember_me", False)  # Extract remember_me flag
        token_fingerprint = decoded.get("fph")
        
        # Verify fingerprint if provided
        if fingerprint and token_fingerprint:
            fp_hash = hashlib.sha256(fingerprint.encode()).hexdigest()[:16]
            if fp_hash != token_fingerprint:
                logger.warning(f"Fingerprint mismatch during token refresh for user {user_id}")
                return None
        
        # Create new access token only
        now = int(time.time())
        
        # Set token expiry time based on remember_me flag
        access_expire = PERSISTENT_ACCESS_TOKEN_EXPIRE if remember_me else ACCESS_TOKEN_EXPIRE
        
        # Generate a new token ID
        access_jti = generate_token_id()
        
        access_claims = {
            "sub": user_id,
            "iat": now,
            "exp": now + access_expire,
            "type": "access",
            "jti": access_jti,
            "remember_me": remember_me  # Maintain remember_me flag in new token
        }
        
        # Add optional claims
        if username:
            access_claims["username"] = username
        if premium:
            access_claims["premium"] = premium
        if token_fingerprint:
            access_claims["fph"] = token_fingerprint
        
        # Add a nonce to prevent token reuse
        access_claims["nonce"] = secrets.token_hex(8)
        
        # Create access token with stronger algorithm
        access_token = jwt.encode(
            access_claims,
            JWT_SECRET_KEY,
            algorithm="HS384"
        )
        
        logger.info(f"Successfully refreshed access token for user {user_id}")
        
        return {
            "access_token": access_token,
            "expires_in": access_expire,
            "token_type": "Bearer",
            "jti": access_jti
        }
    except Exception as e:
        logger.error(f"Error during token refresh: {str(e)}")
        return None

def invalidate_token(token):
    """
    Invalidate a token by adding it to the blacklist
    
    Args:
        token (str): JWT token to invalidate
        
    Returns:
        bool: True if token was invalidated, False otherwise
    """
    try:
        # Decode token without verifying type
        decoded = decode_token(token, verify_type=False)
        
        if decoded and 'jti' in decoded:
            # Add token ID to blacklist
            blacklist_token(decoded['jti'])
            logger.info(f"Token invalidated: jti={decoded['jti']}")
            return True
        return False
    except Exception as e:
        logger.error(f"Error invalidating token: {e}")
        return False

def token_required(f):
    """
    Decorator for Flask routes that require a valid JWT token
    
    Usage:
        @app.route('/protected')
        @token_required
        def protected_route():
            # This will only execute if a valid token is provided
            return jsonify({"message": "This is a protected route"})
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        auth_header = request.headers.get('Authorization')
        
        # Check if Authorization header exists and has Bearer token
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
        
        # No token provided, continue without user_id (function should check session)
        if not token:
            # We don't return error, we let the function handle session auth
            return f(*args, **kwargs)
        
        # Get fingerprint for additional verification
        fingerprint = request.headers.get('X-Device-Fingerprint')
        
        # Decode and verify token
        decoded = decode_token(token, expected_type="access", 
                              verify_fingerprint=fingerprint is not None)
        
        # Token is invalid or expired
        if not decoded:
            # If token is provided but invalid, return error
            return jsonify({"error": "Token is invalid or expired"}), 401
        
        # Get user ID from token
        user_id = decoded.get("sub")
        
        # Check rate limits
        try:
            from backend.login import rate_limits_collection
            import time
            
            # Find user's rate limits document
            user_limits = rate_limits_collection.find_one({"user_id": user_id})
            
            if user_limits:
                current_time = time.time()
                
                # Check if user is rate limited
                for limit in user_limits.get("rate_limits", []):
                    if limit.get("limit_type") == "login" and limit.get("blocked_until", 0) > current_time:
                        retry_after = int(limit.get("blocked_until") - current_time)
                        return jsonify({
                            "error": "Your account is temporarily locked due to too many login attempts",
                            "retry_after": retry_after
                        }), 429
        except ImportError:
            # Skip this check if rate_limits_collection can't be imported
            pass
        
        # Add user ID to kwargs
        kwargs['user_id'] = user_id
        
        # Add premium status if present
        if "premium" in decoded:
            kwargs['premium'] = decoded.get("premium")
        
        return f(*args, **kwargs)
    
    return decorated 