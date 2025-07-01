import secrets
import os
import logging
from flask import session, request
from werkzeug.security import safe_str_cmp as constant_time_compare

# Configure logging
logger = logging.getLogger(__name__)

# Functions for CSRF token management
def generate_csrf_token():
    """Generate a new CSRF token and store it in session"""
    import hashlib
    import time
    import base64
    
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
    from flask import current_app
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
    """Validate the CSRF token from the request against the one in session"""
    # تحقق إذا كان تفعيل CSRF متاح في ملف الإعدادات
    csrf_enabled = os.environ.get('CSRF_ENABLED', 'true').lower() in ('true', '1', 't')
    
    # إذا كان CSRF معطل، إرجاع True دائمًا
    if not csrf_enabled:
        return True
        
    # فحص إذا كان التوكن فارغ
    if not token:
        return False
        
    stored_token = session.get('csrf_token')
    if not stored_token:
        return False
    
    # Decrypt the token from client
    try:
        import base64
        
        # Decode base64
        encrypted_bytes = base64.b64decode(token)
        
        # XOR decryption
        from flask import current_app
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
        
    # استخدام المقارنة بثبات الوقت لمنع هجمات التوقيت
    return constant_time_compare(stored_token, client_token) 