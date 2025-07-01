import os
import requests
import json
from datetime import datetime, timedelta
from pymongo import MongoClient
from flask import Flask, request, redirect, jsonify, session, make_response
from flask_cors import CORS
from dotenv import load_dotenv

# Import JWT utilities
try:
    from backend.jwt_utils import create_tokens, decode_token, refresh_access_token, token_required
except ImportError:
    # إذا تم تشغيل الملف مباشرة، استخدم مسار مختلف
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from jwt_utils import create_tokens, decode_token, refresh_access_token, token_required
    print("Imported jwt_utils directly when running as standalone script")

# Load environment variables directly
try:
    # Try to load from secure_config
    secure_env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'secure_config', 'clyne.env')
    if os.path.exists(secure_env_path):
        load_dotenv(secure_env_path, override=True)
        print(f"Auth: Loaded environment from: {secure_env_path}")
        
        # قراءة بيانات البوت مباشرة من الملف
        with open(secure_env_path, 'r') as file:
            env_content = file.read()
            # طباعة أقسام الملف للتأكد من قراءتها بشكل صحيح
            print("Reading bot credentials directly from file:")
            if "DISCORD_TOKEN=" in env_content:
                discord_token = env_content.split("DISCORD_TOKEN=")[1].split("\n")[0]
                print(f"Found DISCORD_TOKEN: {discord_token[:10]}...")
                os.environ["DISCORD_TOKEN"] = discord_token
            
            if "APPLICATION_ID=" in env_content:
                app_id = env_content.split("APPLICATION_ID=")[1].split("\n")[0]
                print(f"Found APPLICATION_ID: {app_id}")
                os.environ["APPLICATION_ID"] = app_id
            
            if "CLIENT_SECRET=" in env_content:
                client_secret = env_content.split("CLIENT_SECRET=")[1].split("\n")[0]
                print(f"Found CLIENT_SECRET: {client_secret[:5]}...")
                os.environ["CLIENT_SECRET"] = client_secret
            
            if "CALLBACK_URL=" in env_content:
                callback_url = env_content.split("CALLBACK_URL=")[1].split("\n")[0]
                print(f"Found CALLBACK_URL: {callback_url}")
                os.environ["CALLBACK_URL"] = callback_url
except Exception as e:
    print(f"Auth: Error loading environment: {e}")

# Discord API endpoints
DISCORD_API = "https://discord.com/api/v10"
TOKEN_URL = f"{DISCORD_API}/oauth2/token"
USER_URL = f"{DISCORD_API}/users/@me"

# Discord OAuth2 configuration
CLIENT_ID = os.getenv("APPLICATION_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")

# الرابط المحدد للتطبيق - استخدام رابط إعادة التوجيه من ملف البيئة
# يجب أن يكون متطابقاً مع ما تم تعيينه في لوحة تحكم Discord
REDIRECT_URI = os.getenv("CALLBACK_URL", "CALLBACK_URL=https://cryptonel.online/api/auth/discord/callback")

# Log the callback URL being used
print(f"Using Discord callback URL: {REDIRECT_URI}")
print(f"Using CLIENT_ID: {CLIENT_ID}")
print(f"Using CLIENT_SECRET: {CLIENT_SECRET[:5]}..." if CLIENT_SECRET else "CLIENT_SECRET not found")

# MongoDB connection with fallback to localhost if DATABASE_URL not provided
MONGODB_URI = os.environ.get("DATABASE_URL")
if not MONGODB_URI:
    print("Auth: DATABASE_URL not found in environment, using local fallback")
    MONGODB_URI = "mongodb://localhost:27017" # Default to local MongoDB for development

# Log only non-sensitive part of the connection string
connection_info = "mongodb+srv://<credentials>@" + MONGODB_URI.split('@')[-1] if '@' in MONGODB_URI else "<connection-url-masked>"
print(f"Auth: Using MongoDB host: {connection_info}")

try:
    client = MongoClient(MONGODB_URI)
    db = client["cryptonel_wallet"]
    users_collection = db["discord_users"]
    wallet_users_collection = db["users"]
    print("Auth: Successfully connected to MongoDB Atlas")
except Exception as e:
    print(f"Auth: MongoDB connection error: {e}")
    raise

# OAuth2 scopes
SCOPES = ["identify", "email"]

def create_auth_app():
    """Create and configure the authentication Flask application"""
    app = Flask(__name__)
    app.secret_key = os.urandom(24)
    
    # Set session lifetime to 24 hours (increased from default 31 minutes)
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)
    
    CORS(app)
    
    @app.route('/api/auth/discord')
    def discord_login():
        """Redirect user to Discord OAuth2 authorization page"""
        # التأكد من وجود جميع البيانات اللازمة
        if not CLIENT_ID:
            print("ERROR: APPLICATION_ID/CLIENT_ID is missing!")
            return jsonify({"error": "Discord CLIENT_ID is not configured"}), 500
            
        if not CLIENT_SECRET:
            print("ERROR: CLIENT_SECRET is missing!")
            return jsonify({"error": "Discord CLIENT_SECRET is not configured"}), 500
        
        # إعداد URL التفويض مع الرابط المحدد
        oauth_url = f"{DISCORD_API}/oauth2/authorize?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&response_type=code&scope={'%20'.join(SCOPES)}"
        
        print(f"Redirecting to Discord OAuth URL: {oauth_url}")
        return redirect(oauth_url)

    @app.route('/api/auth/discord/callback')
    def discord_callback():
        """Handle Discord OAuth2 callback"""
        code = request.args.get('code')
        
        if not code:
            return jsonify({"error": "No authorization code provided"}), 400
        
        # Exchange code for token using our fixed callback URL
        token_data = exchange_code(code)
        
        if not token_data:
            return jsonify({"error": "Failed to get access token"}), 500
        
        # Get user info
        user_data = get_user_info(token_data)
        
        if not user_data:
            return jsonify({"error": "Failed to get user info"}), 500
        
        # Save user to database
        user = update_or_create_user(user_data)
        
        # Make session permanent with longer lifetime
        session.permanent = True
        
        # Set session data - keep this for backward compatibility
        session['user_id'] = user['user_id']
        session['is_authenticated'] = True
        
        # Check premium status and reset premium features if not premium
        user_premium = user.get('premium', False)
        if not user_premium:
            # Reset premium features for non-premium users
            try:
                # Reset premium-only features
                wallet_users_collection.update_one(
                    {"user_id": user['user_id']},
                    {"$set": {
                        "timeBasedAccessEnabled": False,
                        "geoLockEnabled": False,
                        "ipWhitelistEnabled": False
                    }}
                )
                print(f"Reset premium features for non-premium user: {user['user_id']}")
            except Exception as e:
                print(f"Error resetting premium features: {e}")
        
        # Create JWT tokens
        tokens = create_tokens(
            user_id=user['user_id'],
            username=user.get('username'),
            premium=user_premium
        )
        
        # Store tokens in session as well (better security than URL fragment)
        session['access_token'] = tokens['access_token']
        session['refresh_token'] = tokens['refresh_token']
        
        # إضافة متغير جديد للsession يشير إلى أن المستخدم قد مر عبر التحقق من ديسكورد فقط
        session['discord_authenticated'] = True
        session['wallet_authenticated'] = False  # يحتاج إلى المرور بصفحة اللوجين
        
        # Redirect to login page instead of dashboard
        return redirect('/login')

    @app.route('/api/user')
    @token_required
    def get_current_user(user_id=None, **kwargs):
        """Get current authenticated user using JWT"""
        # If no user_id from token, try to get from session
        if not user_id:
            user_id = session.get('user_id')
            if not user_id:
                return jsonify({"error": "Not authenticated"}), 401
        
        user = wallet_users_collection.find_one({"user_id": user_id})
        
        if not user:
            return jsonify({"error": "User not found in database"}), 404
        
        # Convert ObjectId to string for JSON serialization
        user['_id'] = str(user['_id'])
        
        # Remove sensitive fields
        user.pop('2fa_secret', None)
        user.pop('secret_word', None)
        
        return jsonify(user)

    @app.route('/api/logout')
    def logout():
        """Log out current user"""
        session.pop('user_id', None)
        session.pop('is_authenticated', None)
        
        response = make_response(jsonify({"message": "Logged out successfully"}))
        
        # Clear client-side cookies if any
        response.set_cookie('access_token', '', expires=0)
        response.set_cookie('refresh_token', '', expires=0)
        
        return response
    
    @app.route('/api/token/refresh', methods=['POST'])
    def token_refresh():
        """Refresh access token using refresh token"""
        # Get refresh token from request
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        refresh_token = data.get('refresh_token')
        if not refresh_token:
            return jsonify({"error": "No refresh token provided"}), 400
        
        # Refresh token
        new_tokens = refresh_access_token(refresh_token)
        if not new_tokens:
            return jsonify({"error": "Invalid or expired refresh token"}), 401
        
        return jsonify(new_tokens)
    
    @app.route('/api/token/validate', methods=['GET'])
    def validate_token():
        """Validate access token"""
        auth_header = request.headers.get('Authorization')
        
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({"valid": False}), 401
        
        token = auth_header.split(' ')[1]
        decoded = decode_token(token)
        
        if not decoded or decoded.get('type') != 'access':
            return jsonify({"valid": False}), 401
        
        return jsonify({"valid": True, "user_id": decoded.get('sub')})
    
    @app.route('/api/auth/check-session')
    def check_session():
        """Check if user is authenticated via session or token"""
        # First check for JWT token in Authorization header
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            decoded = decode_token(token)
            
            if decoded and decoded.get('type') == 'access':
                # Valid token - must have gone through wallet login since tokens are only set there
                user_id = decoded.get('sub')
                
                # Check if user is banned
                wallet_user = wallet_users_collection.find_one({"user_id": user_id})
                is_banned = wallet_user and wallet_user.get('ban', False)
                
                # Check premium status
                is_premium = wallet_user and wallet_user.get('premium', False)
                
                # If user is not premium, ensure premium features are disabled
                if wallet_user and not is_premium:
                    # Check if any premium features are enabled
                    has_premium_features = (
                        wallet_user.get('timeBasedAccessEnabled', False) or
                        wallet_user.get('geoLockEnabled', False) or
                        wallet_user.get('ipWhitelistEnabled', False)
                    )
                    
                    # Reset premium features if any are enabled
                    if has_premium_features:
                        try:
                            wallet_users_collection.update_one(
                                {"user_id": user_id},
                                {"$set": {
                                    "timeBasedAccessEnabled": False,
                                    "geoLockEnabled": False,
                                    "ipWhitelistEnabled": False
                                }}
                            )
                            print(f"Reset premium features for non-premium user: {user_id}")
                        except Exception as e:
                            print(f"Error resetting premium features: {e}")
                
                return jsonify({
                    "authenticated": True,
                    "auth_type": "jwt",
                    "user_id": user_id,
                    "has_wallet": True,  # Must have wallet if using JWT token
                    "banned": is_banned,
                    "premium": is_premium
                })
        
        # Fall back to session-based auth, but check both Discord and wallet auth
        if session.get('is_authenticated') and session.get('user_id'):
            user_id = session.get('user_id')
            
            # Check if user has a wallet in the database
            wallet_user = wallet_users_collection.find_one({"user_id": user_id})
            has_wallet = wallet_user is not None
            is_banned = wallet_user and wallet_user.get('ban', False)
            is_premium = wallet_user and wallet_user.get('premium', False)
            
            # If user is not premium, ensure premium features are disabled
            if wallet_user and not is_premium:
                # Check if any premium features are enabled
                has_premium_features = (
                    wallet_user.get('timeBasedAccessEnabled', False) or
                    wallet_user.get('geoLockEnabled', False) or
                    wallet_user.get('ipWhitelistEnabled', False)
                )
                
                # Reset premium features if any are enabled
                if has_premium_features:
                    try:
                        wallet_users_collection.update_one(
                            {"user_id": user_id},
                            {"$set": {
                                "timeBasedAccessEnabled": False,
                                "geoLockEnabled": False,
                                "ipWhitelistEnabled": False
                            }}
                        )
                        print(f"Reset premium features for non-premium user: {user_id}")
                    except Exception as e:
                        print(f"Error resetting premium features: {e}")
            
            # If user has wallet, add the username to session for validation
            if has_wallet and wallet_user:
                session['wallet_username'] = wallet_user.get('username')
            
            # Check if user completed the wallet login step
            if session.get('wallet_authenticated', False):
                return jsonify({
                    "authenticated": True,
                    "auth_type": "session",
                    "user_id": user_id,
                    "has_wallet": True,  # User must have wallet if wallet authenticated
                    "banned": is_banned,
                    "premium": is_premium
                })
            else:
                # Only Discord authenticated but not wallet
                return jsonify({
                    "authenticated": False,
                    "discord_authenticated": True,
                    "auth_type": "discord_only",
                    "user_id": user_id,
                    "has_wallet": has_wallet,  # Check actual status from DB
                    "wallet_username": session.get('wallet_username') if has_wallet else None,  # Include wallet username if available
                    "banned": is_banned,
                    "premium": is_premium
                })
        
        return jsonify({
            "authenticated": False,
            "auth_type": None,
            "user_id": None,
            "has_wallet": False,
            "banned": False,
            "premium": False
        })
    
    return app

def exchange_code(code):
    """Exchange authorization code for access token"""
    data = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': REDIRECT_URI  # استخدام الرابط الثابت
    }
    
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    
    try:
        response = requests.post(TOKEN_URL, data=data, headers=headers)
        response.raise_for_status()  # Raise exception for 4XX/5XX responses
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error exchanging code for token: {e}")
        print(f"Response: {getattr(e.response, 'text', '')}")
        return None

def get_user_info(token):
    """Get user information from Discord API"""
    headers = {
        'Authorization': f"Bearer {token['access_token']}"
    }
    
    try:
        response = requests.get(USER_URL, headers=headers)
        response.raise_for_status()  # Raise exception for 4XX/5XX responses
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error getting user info: {e}")
        print(f"Response: {getattr(e.response, 'text', '')}")
        return None

def update_or_create_user(user_data):
    """Update or create user in the database"""
    # Extract necessary fields
    user_id = user_data.get('id')
    
    # Check if user exists in discord_users collection
    existing_user = users_collection.find_one({"user_id": user_id})
    
    # Get current timestamp in ISO format with timezone
    timestamp = datetime.utcnow().isoformat() + "+00:00"
    
    # Prepare user document for discord_users collection
    user_doc = {
        "user_id": user_id,
        "username": user_data.get('username'),
        "discriminator": user_data.get('discriminator', '0'),
        "email": user_data.get('email'),
        "avatar": user_data.get('avatar'),
        "last_login": timestamp
    }
    
    if existing_user:
        # Update existing user in discord_users collection
        users_collection.update_one(
            {"user_id": user_id},
            {"$set": user_doc}
        )
        user_doc["_id"] = str(existing_user["_id"])
        print(f"Updated user in discord_users: {user_doc['username']} (ID: {user_id})")
        
        # Check if user exists in wallet users collection
        existing_wallet_user = wallet_users_collection.find_one({"user_id": user_id})
        if existing_wallet_user:
            # Set premium flag from existing wallet user if they have one
            user_doc["premium"] = existing_wallet_user.get("premium", False)
            # Store wallet username for verification
            user_doc["wallet_username"] = existing_wallet_user.get("username")
            
            print(f"Found existing wallet for: {existing_wallet_user.get('username', 'Unknown')} (ID: {user_id})")
        
        return user_doc
    else:
        # Create new user in discord_users collection
        result = users_collection.insert_one(user_doc)
        user_doc["_id"] = str(result.inserted_id)
        print(f"Created new user in discord_users: {user_doc['username']} (ID: {user_id})")
        
        return user_doc

# For standalone testing
if __name__ == '__main__':
    app = create_auth_app()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True) 