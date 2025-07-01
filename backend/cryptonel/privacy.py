import os
import json
from flask import Blueprint, request, jsonify, session
from pymongo import MongoClient
from dotenv import load_dotenv
from bson.objectid import ObjectId

# Load environment variables
load_dotenv()

# Get MongoDB connection URI
MONGODB_URI = os.getenv('DATABASE_URL')

# Connect to MongoDB
client = MongoClient(MONGODB_URI)
db = client['cryptonel_wallet']
users_collection = db['users']

privacy_bp = Blueprint('privacy', __name__)

def init_app(app):
    """Initialize privacy routes with the Flask app."""
    app.register_blueprint(privacy_bp, url_prefix='/api/privacy')
    
@privacy_bp.route('/profile-visibility', methods=['GET'])
def get_profile_visibility():
    """Get the current profile visibility status for a user."""
    # Get the user ID from the session
    user_id = session.get('user_id')
    
    if not user_id:
        return jsonify({'error': 'Not authenticated'}), 401
    
    # Find the user in the database
    user = users_collection.find_one({'user_id': user_id})
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
        
    # Return the current profile_hidden status
    return jsonify({
        'success': True,
        'profile_hidden': user.get('profile_hidden', False)
    })

@privacy_bp.route('/toggle-profile-visibility', methods=['POST'])
def toggle_profile_visibility():
    """Toggle the profile_hidden field for a user."""
    # Get the user ID from the session
    user_id = session.get('user_id')
    
    if not user_id:
        return jsonify({'error': 'Not authenticated'}), 401
    
    # Get the desired visibility state from the request
    data = request.get_json()
    is_hidden = data.get('is_hidden')
    
    if is_hidden is None:
        return jsonify({'error': 'Missing required field: is_hidden'}), 400
    
    # Update the user's profile_hidden field in the database
    result = users_collection.update_one(
        {'user_id': user_id},
        {'$set': {'profile_hidden': is_hidden}}
    )
    
    if result.matched_count == 0:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify({
        'success': True,
        'profile_hidden': is_hidden
    })

@privacy_bp.route('/premium-settings', methods=['GET'])
def get_premium_settings():
    """Get the current premium privacy settings for a user."""
    user_id = session.get('user_id')
    
    if not user_id:
        return jsonify({'error': 'Not authenticated'}), 401
    
    # Find the user in the database
    user = users_collection.find_one({'user_id': user_id})
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Check if user is premium instead of setting it
    is_premium = user.get('premium', False)
    
    # Only return premium settings if the user is actually premium
    if not is_premium:
        return jsonify({
            'success': False,
            'error': 'Premium subscription required',
            'is_premium': False
        }), 403
    
    # طباعة إعدادات الألوان للتأكد منها
    print(f"Current user color settings - primary_color: {user.get('primary_color')}, secondary_color: {user.get('secondary_color')}, highlight_color: {user.get('highlight_color')}")
    
    # Return the current premium privacy settings
    settings = {
        'success': True,
        'is_premium': True,
        'profile_hidden': user.get('profile_hidden', False),
        'hide_balance': user.get('hide_balance', False),
        'hide_address': user.get('hide_address', False),
        'hide_verification': user.get('hide_verification', False),
        'hidden_wallet_mode': user.get('hidden_wallet_mode', False),
        'primary_color': user.get('primary_color', '#FFD700'),  # Default is gold
        'secondary_color': user.get('secondary_color', '#B9A64B'),  # Default gold
        'highlight_color': user.get('highlight_color', '#DAA520'),  # Default goldenrod
        'background_color': user.get('background_color', '#000000'),  # Default black
        'enable_secondary_color': user.get('enable_secondary_color', True),
        'enable_highlight_color': user.get('enable_highlight_color', True)
    }
    
    return jsonify(settings)

@privacy_bp.route('/premium-settings', methods=['POST'])
def update_premium_settings():
    """Update premium privacy settings for a user."""
    user_id = session.get('user_id')
    
    if not user_id:
        return jsonify({'error': 'Not authenticated'}), 401
    
    # Find the user in the database
    user = users_collection.find_one({'user_id': user_id})
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Check if user is premium instead of setting it
    is_premium = user.get('premium', False)
    
    # Reject if user is not premium
    if not is_premium:
        return jsonify({
            'success': False,
            'error': 'Premium subscription required'
        }), 403
    
    # Get the settings from the request
    data = request.get_json()
    print(f"Received premium settings for user {user_id}: {data}")  # للتصحيح
    
    # Extract fields to update
    update_fields = {}
    
    # Privacy toggles
    if 'hide_balance' in data:
        update_fields['hide_balance'] = data['hide_balance']
    
    if 'hide_address' in data:
        update_fields['hide_address'] = data['hide_address']
    
    if 'hide_verification' in data:
        update_fields['hide_verification'] = data['hide_verification']
        
    if 'hidden_wallet_mode' in data:
        update_fields['hidden_wallet_mode'] = data['hidden_wallet_mode']
    
    # Color settings
    if 'primary_color' in data:
        update_fields['primary_color'] = data['primary_color']
    
    if 'secondary_color' in data:
        update_fields['secondary_color'] = data['secondary_color']
    
    if 'highlight_color' in data:
        update_fields['highlight_color'] = data['highlight_color']
    
    if 'background_color' in data:
        update_fields['background_color'] = data['background_color']
    
    # Toggle settings for color features
    if 'enable_secondary_color' in data:
        update_fields['enable_secondary_color'] = data['enable_secondary_color']
    
    if 'enable_highlight_color' in data:
        update_fields['enable_highlight_color'] = data['enable_highlight_color']
    
    print(f"Updating user {user_id} with fields: {update_fields}")  # للتصحيح
    
    # Update the user's settings in the database
    result = users_collection.update_one(
        {'user_id': user_id},
        {'$set': update_fields}
    )
    
    if result.matched_count == 0:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify({
        'success': True,
        'message': 'Premium settings updated successfully'
    })

@privacy_bp.route('/update-profile', methods=['POST'])
def update_profile():
    """Update the user's profile information."""
    # Get the user ID from the session
    user_id = session.get('user_id')
    
    if not user_id:
        return jsonify({'error': 'Not authenticated'}), 401
    
    # Get profile data from the request
    data = request.get_json()
    
    # Extract the profile fields to update
    update_fields = {}
    
    if 'displayName' in data:
        update_fields['display_name'] = data['displayName']
    
    if 'bio' in data:
        update_fields['bio'] = data['bio']
    
    if 'showEmailPublicly' in data:
        update_fields['show_email_publicly'] = data['showEmailPublicly']
    
    if 'showTransactions' in data:
        update_fields['show_transactions'] = data['showTransactions']
    
    # Update the user's profile information in the database
    result = users_collection.update_one(
        {'user_id': user_id},
        {'$set': update_fields}
    )
    
    if result.matched_count == 0:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify({
        'success': True,
        'message': 'Profile updated successfully'
    })

@privacy_bp.route('/privacy-settings', methods=['GET'])
def get_privacy_settings():
    """Get privacy settings for all users (not just premium)."""
    user_id = session.get('user_id')
    
    if not user_id:
        return jsonify({'error': 'Not authenticated'}), 401
    
    # Find the user in the database
    user = users_collection.find_one({'user_id': user_id})
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Check if user is premium instead of setting it
    is_premium = user.get('premium', False)
    
    # طباعة إعدادات الألوان للتأكد منها
    print(f"Current user color settings - primary_color: {user.get('primary_color')}, secondary_color: {user.get('secondary_color')}, highlight_color: {user.get('highlight_color')}")
    
    # Return privacy settings for all users
    settings = {
        'success': True,
        'is_premium': is_premium,
        'profile_hidden': user.get('profile_hidden', False),  # Only hides username and avatar
        'hide_balance': user.get('hide_balance', False),      # Hides balance independently
        'hide_address': user.get('hide_address', False),      # Hides wallet address independently
        'hide_verification': user.get('hide_badges', False),  # Renamed to hide_badges in database but keep API consistent
        'hide_badges': user.get('hide_badges', False),        # New field to hide all badges
        'hidden_wallet_mode': user.get('hidden_wallet_mode', False)  # To be removed later
    }
    
    # Include appearance settings for premium users
    if is_premium:
        settings.update({
            'primary_color': user.get('primary_color', '#FFD700'),  # Default is gold
            'secondary_color': user.get('secondary_color', '#B9A64B'),  # Default gold
            'highlight_color': user.get('highlight_color', '#DAA520'),  # Default goldenrod
            'background_color': user.get('background_color', '#000000'),  # Default black
            'enable_secondary_color': user.get('enable_secondary_color', True),
            'enable_highlight_color': user.get('enable_highlight_color', True)
        })
    
    return jsonify(settings)

@privacy_bp.route('/privacy-settings', methods=['POST'])
def update_privacy_settings():
    """Update privacy settings for all users (not premium specific)."""
    user_id = session.get('user_id')
    
    if not user_id:
        return jsonify({'error': 'Not authenticated'}), 401
    
    # Find the user in the database
    user = users_collection.find_one({'user_id': user_id})
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Check if user is premium
    is_premium = user.get('premium', False)
    
    # Get the settings from the request
    data = request.get_json()
    print(f"Received privacy settings update: {data}")  # اطبع البيانات التي استلمتها
    
    # Extract fields to update
    update_fields = {}
    
    # Profile hidden only affects username and avatar visibility - available to all users
    if 'profile_hidden' in data:
        update_fields['profile_hidden'] = data['profile_hidden']
    
    # These features are premium only
    premium_features = ['hide_balance', 'hide_address', 'hide_badges', 'hide_verification', 'hidden_wallet_mode']
    premium_requested = False
    
    # Check if any premium features are being requested
    for feature in premium_features:
        if feature in data:
            premium_requested = True
            if is_premium:
                # Only add to update if user is premium
                if feature == 'hide_verification':  # For backward compatibility
                    update_fields['hide_badges'] = data[feature]
                else:
                    update_fields[feature] = data[feature]
    
    # If premium features were requested but user is not premium, return error
    if premium_requested and not is_premium:
        return jsonify({
            'success': False,
            'error': 'Premium subscription required for some requested features'
        }), 403
    
    print(f"Updating user {user_id} with privacy settings: {update_fields}")
    
    # Update user document
    if update_fields:
        result = users_collection.update_one(
            {'user_id': user_id},
            {'$set': update_fields}
        )
        
        if result.matched_count == 0:
            return jsonify({'error': 'User not found or no changes made'}), 404
    
    return jsonify({
        'success': True,
        'message': 'Privacy settings updated successfully'
    })

@privacy_bp.route('/appearance-settings', methods=['POST'])
def update_appearance_settings():
    """Update appearance settings for premium users only."""
    user_id = session.get('user_id')
    
    if not user_id:
        return jsonify({'error': 'Not authenticated'}), 401
    
    # Find the user in the database
    user = users_collection.find_one({'user_id': user_id})
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Check if user is premium instead of setting it
    is_premium = user.get('premium', False)
    
    # Reject if user is not premium
    if not is_premium:
        return jsonify({
            'success': False,
            'error': 'Premium subscription required'
        }), 403
    
    # Get the settings from the request
    data = request.get_json()
    
    # قم بطباعة البيانات المستلمة للتأكد من استلامها بشكل صحيح
    print(f"Received appearance settings for user {user_id}: {data}")
    
    # Extract appearance fields to update (premium only)
    update_fields = {}
    
    # Color settings
    if 'primary_color' in data:
        update_fields['primary_color'] = data['primary_color']
    
    if 'secondary_color' in data:
        update_fields['secondary_color'] = data['secondary_color']
    
    if 'highlight_color' in data:
        update_fields['highlight_color'] = data['highlight_color']
    
    if 'background_color' in data:
        update_fields['background_color'] = data['background_color']
        
    # Toggle settings for color features
    if 'enable_secondary_color' in data:
        update_fields['enable_secondary_color'] = data['enable_secondary_color']
    
    if 'enable_highlight_color' in data:
        update_fields['enable_highlight_color'] = data['enable_highlight_color']
    
    # قم بطباعة التحديثات التي ستتم
    print(f"Updating user {user_id} appearance with fields: {update_fields}")
    
    # Update user document
    if update_fields:
        result = users_collection.update_one(
            {'user_id': user_id},
            {'$set': update_fields}
        )
        
        if result.matched_count == 0:
            return jsonify({'error': 'User not found or no changes made'}), 404
    
    # الحصول على البيانات المحدثة من قاعدة البيانات للتأكد من الحفظ
    updated_user = users_collection.find_one({'user_id': user_id})
    print(f"User after update - colors: primary={updated_user.get('primary_color')}, secondary={updated_user.get('secondary_color')}, highlight={updated_user.get('highlight_color')}")
    
    return jsonify({
        'success': True,
        'message': 'Appearance settings updated successfully'
    }) 