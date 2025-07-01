from flask import Flask, request, jsonify, session, g
from datetime import datetime, timedelta
import re
import logging
import pymongo
import os

# Set up logging
logger = logging.getLogger(__name__)

# Get MongoDB connection string from environment
DATABASE_URL = os.environ.get('DATABASE_URL')

# Connect to MongoDB
try:
    client = pymongo.MongoClient(DATABASE_URL)
    db = client.cryptonel_wallet
    users_collection = db.users
    custom_address_collection = db.custom_addresses
    logger.info("Connected to MongoDB successfully")
except Exception as e:
    logger.error(f"Error connecting to MongoDB: {e}")
    client = None
    db = None
    users_collection = None
    custom_address_collection = None

def register_routes(app: Flask):
    """Register all routes for the Custom Address module"""
    
    @app.route('/api/custom-address/info', methods=['GET'])
    def get_custom_address_info():
        """Get information about the user's current private address and ability to change it"""
        try:
            # Check if user is authenticated
            if 'user_id' not in session:
                return jsonify({
                    "success": False,
                    "message": "Authentication required"
                }), 401
                
            user_id = session['user_id']
            
            # Check if MongoDB connection is available
            if users_collection is None or custom_address_collection is None:
                return jsonify({
                    "success": False,
                    "message": "Database connection error"
                }), 500
                
            # Get user data from users collection
            user = users_collection.find_one({"user_id": user_id})
            if not user:
                return jsonify({
                    "success": False,
                    "message": "User not found"
                }), 404
                
            # Check if user is premium
            if not user.get('premium', False):
                return jsonify({
                    "success": False, 
                    "message": "This feature is only available for premium users"
                }), 403
                
            # Get current private address
            current_address = user.get('private_address', '')
            
            # Check if user has already changed their address before
            address_change_record = custom_address_collection.find_one({"user_id": user_id})
            
            # If no record exists, user can change their address
            if not address_change_record:
                return jsonify({
                    "success": True,
                    "current_address": current_address,
                    "can_change": True,
                    "cooldown_days": 0
                })
                
            # Check if there's a cooldown period
            if address_change_record.get('cooldown_until'):
                cooldown_until = address_change_record['cooldown_until']
                now = datetime.utcnow()
                
                if cooldown_until > now:
                    # Calculate days left in cooldown
                    days_left = (cooldown_until - now).days + 1
                    return jsonify({
                        "success": True,
                        "current_address": current_address,
                        "can_change": False,
                        "cooldown_days": days_left
                    })
            
            # If no cooldown or past cooldown, check if permanently locked
            if address_change_record.get('permanent_lock', False):
                return jsonify({
                    "success": True,
                    "current_address": current_address,
                    "can_change": False,
                    "cooldown_days": 0
                })
                
            # Otherwise user can change
            return jsonify({
                "success": True,
                "current_address": current_address,
                "can_change": True,
                "cooldown_days": 0
            })
            
        except Exception as e:
            logger.error(f"Error getting custom address info: {e}")
            return jsonify({
                "success": False,
                "message": "Server error, please try again later"
            }), 500
    
    # Exempt this route from CSRF protection
    @app.route('/api/custom-address/update', methods=['POST'])
    def update_custom_address():
        """Update the user's private address to a custom one"""
        try:
            # Check if user is authenticated
            if 'user_id' not in session:
                return jsonify({
                    "success": False,
                    "message": "Authentication required"
                }), 401
                
            user_id = session['user_id']
            
            # Check if MongoDB connection is available
            if users_collection is None or custom_address_collection is None:
                return jsonify({
                    "success": False,
                    "message": "Database connection error"
                }), 500
                
            # Get user data
            user = users_collection.find_one({"user_id": user_id})
            if not user:
                return jsonify({
                    "success": False,
                    "message": "User not found"
                }), 404
                
            # Check if user is premium
            if not user.get('premium', False):
                return jsonify({
                    "success": False, 
                    "message": "This feature is only available for premium users"
                }), 403
            
            # Get the new address from request
            data = request.get_json()
            if not data or 'new_address' not in data:
                return jsonify({
                    "success": False,
                    "message": "New address is required"
                }), 400
                
            new_address = data['new_address'].strip()
            
            # Validate new address format - only lowercase English letters allowed
            if not re.match(r'^[a-z]{3,32}$', new_address):
                return jsonify({
                    "success": False,
                    "message": "Address must be 3-32 characters and contain only lowercase English letters (no spaces or special characters)"
                }), 400
                
            # Get current address
            current_address = user.get('private_address', '')
            
            # Check if trying to set the same address
            if current_address == new_address:
                return jsonify({
                    "success": False,
                    "message": "New address cannot be the same as current address"
                }), 400
                
            # Check if address is already in use by another user
            existing_user = users_collection.find_one({"private_address": new_address})
            if existing_user and existing_user['user_id'] != user_id:
                return jsonify({
                    "success": False,
                    "message": "This address is already in use by another user"
                }), 400
                
            # Check if user is allowed to change address
            address_change_record = custom_address_collection.find_one({"user_id": user_id})
            
            if address_change_record:
                # Check for cooldown period
                if address_change_record.get('cooldown_until'):
                    cooldown_until = address_change_record['cooldown_until']
                    now = datetime.utcnow()
                    
                    if cooldown_until > now:
                        days_left = (cooldown_until - now).days + 1
                        return jsonify({
                            "success": False,
                            "message": f"You can change your address in {days_left} days"
                        }), 403
                        
                # Check for permanent lock
                if address_change_record.get('permanent_lock', False):
                    return jsonify({
                        "success": False,
                        "message": "Your address has been permanently locked and cannot be changed"
                    }), 403
            
            # All checks passed, update the private address
            now = datetime.utcnow()
            
            try:
                # Update user record with new address
                users_collection.update_one(
                    {"user_id": user_id},
                    {"$set": {"private_address": new_address}}
                )
            except pymongo.errors.DuplicateKeyError:
                # This handles the race condition if another user claims the address at the same time
                logger.warning(f"Race condition detected: User {user_id} tried to claim address '{new_address}' which was just taken.")
                return jsonify({
                    "success": False,
                    "message": "This address was just claimed by another user. Please choose a different one."
                }), 409 # 409 Conflict is an appropriate status code

            # Create or update address change record
            if address_change_record:
                # Update existing record to set permanent lock
                custom_address_collection.update_one(
                    {"user_id": user_id},
                    {
                        "$set": {
                            "permanent_lock": True,
                            "previous_address": current_address,
                            "new_address": new_address,
                            "updated_at": now
                        }
                    }
                )
            else:
                # Create new record with permanent lock
                custom_address_collection.insert_one({
                    "user_id": user_id,
                    "username": user.get('username', ''),
                    "previous_address": current_address,
                    "new_address": new_address,
                    "created_at": now,
                    "updated_at": now,
                    "permanent_lock": True
                })
                
            # Add audit log
            try:
                db.audit_logs.insert_one({
                    "user_id": user_id,
                    "action": "private_address_changed",
                    "details": {
                        "previous_address": current_address,
                        "new_address": new_address
                    },
                    "timestamp": now,
                    "ip_address": request.remote_addr
                })
            except Exception as e:
                logger.error(f"Error creating audit log: {e}")
            
            return jsonify({
                "success": True,
                "message": "Private address updated successfully"
            })
            
        except Exception as e:
            logger.error(f"Error updating custom address: {e}")
            return jsonify({
                "success": False,
                "message": "Server error, please try again later"
            }), 500 