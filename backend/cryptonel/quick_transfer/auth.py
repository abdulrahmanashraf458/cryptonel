import functools
from flask import request, jsonify, current_app, session
import jwt
import logging

# إعداد التسجيل
logger = logging.getLogger(__name__)

def token_required(f):
    """
    Decorator for routes that require a valid JWT token or session authentication
    """
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        # أولاً: تحقق من وجود مصادقة في الجلسة
        if session.get('user_id'):
            # إذا كان المستخدم مصادق عبر الجلسة، استخدم معرف المستخدم من الجلسة
            kwargs['user_id'] = session.get('user_id')
            kwargs['username'] = session.get('username')
            logger.info(f"User authenticated via session: {kwargs['user_id']}")
            return f(*args, **kwargs)
        
        # ثانياً: إذا لم تكن هناك مصادقة في الجلسة، تحقق من وجود رمز JWT
        token = None
        
        # Get token from Authorization header
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            
            # Check for Bearer token format
            parts = auth_header.split()
            if len(parts) == 2 and parts[0].lower() == 'bearer':
                token = parts[1]
        
        # If no token provided
        if not token:
            logger.warning("No authentication token found in request")
            return jsonify({
                'success': False,
                'error': 'Authentication token is required'
            }), 401
        
        try:
            # Decode token
            secret_key = current_app.config.get('SECRET_KEY', 'default-secret-key')
            data = jwt.decode(token, secret_key, algorithms=["HS256"])
            
            # Add user_id to kwargs so the route function can use it
            # JWT token stores user ID in the 'sub' field
            user_id = data.get('sub')
            if not user_id:
                logger.warning("JWT token does not contain 'sub' field")
                return jsonify({
                    'success': False,
                    'error': 'Invalid token format'
                }), 401
                
            kwargs['user_id'] = user_id
            kwargs['username'] = data.get('username')
            
            logger.info(f"User authenticated via JWT: {kwargs['user_id']}")
            
            # Call original function with added user info
            return f(*args, **kwargs)
            
        except jwt.ExpiredSignatureError:
            logger.warning("Expired JWT token")
            return jsonify({
                'success': False,
                'error': 'Token has expired'
            }), 401
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT token: {str(e)}")
            return jsonify({
                'success': False,
                'error': 'Invalid token'
            }), 401
            
    return decorated 