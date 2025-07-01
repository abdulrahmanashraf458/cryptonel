import json
import uuid
from flask import Blueprint, request, jsonify, Flask, session
from bson.objectid import ObjectId
from pymongo.collection import ReturnDocument
import logging
from functools import wraps
from .auth import token_required
from .db import get_db
from ..transfers import process_transfer, get_user_by_private_address, get_user_balance
import time
from pymongo import MongoClient
import os
from datetime import datetime, timedelta

# Create blueprint for quick transfer with a unique name
quicktransfer_bp = Blueprint('quick_transfer', __name__)

# Logger setup
logger = logging.getLogger(__name__)

# Maximum number of trusted contacts per user
MAX_TRUSTED_CONTACTS = 5

# Rate limiting settings
RATE_LIMIT_MAX_ATTEMPTS = 5
RATE_LIMIT_WINDOW = 60  # seconds

# Dictionary to store rate limiting data
rate_limit_data = {}

# Minimum time (in days) before a contact can be removed
MIN_DAYS_BEFORE_REMOVAL = 14

# Rate limiting decorator
def rate_limit(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        user_id = kwargs.get('user_id')
        if not user_id:
            return jsonify({
                "valid": False,
                "message": "Authentication required"
            }), 401

        current_time = time.time()
        user_rate_data = rate_limit_data.get(user_id, {
            'attempts': 0,
            'reset_time': current_time + RATE_LIMIT_WINDOW
        })

        # Reset rate limit if window has passed
        if current_time > user_rate_data.get('reset_time', 0):
            user_rate_data = {
                'attempts': 0,
                'reset_time': current_time + RATE_LIMIT_WINDOW
            }

        # Check if rate limit exceeded
        if user_rate_data['attempts'] >= RATE_LIMIT_MAX_ATTEMPTS:
            remaining_time = int(user_rate_data['reset_time'] - current_time)
            return jsonify({
                "valid": False,
                "message": f"Rate limit exceeded. Please try again in {remaining_time} seconds.",
                "rate_limited": True,
                "reset_time": user_rate_data['reset_time'],
                "remaining_time": remaining_time
            }), 429

        # لا نزيد العداد مسبقًا، سنزيده فقط إذا فشلت المحاولة
        # user_rate_data['attempts'] += 1
        
        # Execute the function
        response = func(*args, **kwargs)
        
        # Only count failed attempts towards rate limit
        if isinstance(response, tuple) and len(response) >= 2:
            status_code = response[1]
            response_json = response[0].json
            
            # إذا كان الرد يشير إلى فشل التحقق، نزيد العداد
            if status_code >= 400 or (isinstance(response_json, dict) and response_json.get('valid') is False):
                user_rate_data['attempts'] += 1
                logger.info(f"Failed validation attempt for user {user_id}. Attempts: {user_rate_data['attempts']}")
            else:
                logger.info(f"Successful validation for user {user_id}. Not counting against rate limit.")
        
        # Update rate limit data
        rate_limit_data[user_id] = user_rate_data

        # Add rate limit info to response
        if isinstance(response, tuple) and len(response) >= 2:
            response_json = response[0].json
            if isinstance(response_json, dict):
                response_json['rate_limit'] = {
                    'remaining': RATE_LIMIT_MAX_ATTEMPTS - user_rate_data['attempts'],
                    'reset_time': user_rate_data['reset_time'],
                    'window': RATE_LIMIT_WINDOW
                }
                response = (jsonify(response_json), response[1])
        
        return response
    
    return wrapper

@quicktransfer_bp.route('/api/quicktransfer/contacts', methods=['GET'])
@token_required
def get_trusted_contacts(user_id=None, **kwargs):
    """
    Get user's trusted contacts for quick transfer
    """
    try:
        db = get_db()
        
        # Find user's trusted contacts
        contacts = db.quick_transfer_contacts.find_one({"user_id": user_id})
        
        if contacts:
            # Add can_delete field to each contact based on added_at date
            contacts_list = contacts.get("contacts", [])
            current_time = datetime.utcnow()
            
            # إنشاء قائمة جديدة لجهات الاتصال مع البيانات المحدثة
            updated_contacts = []
            
            for contact in contacts_list:
                # نسخ بيانات جهة الاتصال الأساسية
                contact_details = contact.copy()
                
                # إضافة معلومات من مجموعة users (البابلك أدرس فقط حيث أن البرايفت أدرس موجود بالفعل)
                contact_user = db.users.find_one(
                    {"user_id": contact.get("user_id")},
                    {"public_address": 1, "_id": 0}
                )
                
                if contact_user:
                    contact_details["public_address"] = contact_user.get("public_address")
                
                # إضافة معلومات الأفاتار من مجموعة discord_users
                discord_user = db.discord_users.find_one(
                    {"user_id": contact.get("user_id")},
                    {"avatar": 1, "_id": 0}
                )
                
                if discord_user and discord_user.get("avatar"):
                    avatar_hash = discord_user.get("avatar")
                    contact_details["avatar_hash"] = avatar_hash
                    contact_details["avatar"] = f"https://cdn.discordapp.com/avatars/{contact.get('user_id')}/{avatar_hash}.png?size=128"
                
                added_at = contact.get("added_at")
                if added_at:
                    # تحويل التاريخ إلى كائن datetime
                    if isinstance(added_at, str):
                        added_at = datetime.fromisoformat(added_at.replace('Z', '+00:00'))
                    elif isinstance(added_at, dict) and '$date' in added_at:
                        # تنسيق MongoDB
                        added_at_str = added_at['$date']
                        if isinstance(added_at_str, str):
                            # إذا كان التاريخ بتنسيق نصي
                            added_at = datetime.fromisoformat(added_at_str.replace('Z', '+00:00'))
                        else:
                            # إذا كان التاريخ بتنسيق timestamp (بالمللي ثانية)
                            added_at = datetime.fromtimestamp(added_at_str / 1000)
                    
                    # Debug logging
                    logger.info(f"Contact {contact.get('username')} added_at: {added_at}, current: {current_time}")
                    
                    # حساب عدد الأيام منذ الإضافة
                    days_since_addition = (current_time - added_at).days
                    logger.info(f"Days since addition: {days_since_addition}, threshold: {MIN_DAYS_BEFORE_REMOVAL}")
                    
                    # يمكن الحذف إذا مر 14 يوم أو أكثر منذ الإضافة
                    contact_details["can_delete"] = days_since_addition >= MIN_DAYS_BEFORE_REMOVAL
                    contact_details["days_remaining"] = max(0, MIN_DAYS_BEFORE_REMOVAL - days_since_addition)
                    
                    # إضافة تاريخ الإضافة بتنسيق مقروء
                    contact_details["added_at_formatted"] = added_at.strftime("%Y-%m-%d %H:%M:%S")
                else:
                    # إذا لم يكن هناك تاريخ إضافة، نسمح بالحذف
                    contact_details["can_delete"] = True
                    contact_details["days_remaining"] = 0
                
                updated_contacts.append(contact_details)
            
            return jsonify({
                "success": True,
                "contacts": updated_contacts
            }), 200
        else:
            # Return empty list if no contacts found
            return jsonify({
                "success": True,
                "contacts": []
            }), 200
            
    except Exception as e:
        logger.error(f"Error retrieving trusted contacts: {str(e)}", exc_info=True)
        return jsonify({
            "success": False,
            "error": "Failed to retrieve trusted contacts"
        }), 500

@quicktransfer_bp.route('/api/user/private-address', methods=['GET'])
@token_required
def get_user_private_address(user_id=None, **kwargs):
    """
    Get the current user's private address
    """
    try:
        db = get_db()
        user = db.users.find_one({"user_id": user_id})
        
        if user and "private_address" in user:
            return jsonify({
                "success": True,
                "private_address": user["private_address"]
            }), 200
        else:
            return jsonify({
                "success": False,
                "error": "User private address not found"
            }), 404
    except Exception as e:
        logger.error(f"Error retrieving user private address: {str(e)}")
        return jsonify({
            "success": False,
            "error": "Failed to retrieve user private address"
        }), 500

@quicktransfer_bp.route('/api/user/current', methods=['GET'])
@token_required
def get_current_user_id(user_id=None, **kwargs):
    """
    Get the current user's ID
    """
    try:
        if not user_id:
            return jsonify({
                "success": False,
                "error": "Not authenticated"
            }), 401
            
        return jsonify({
            "success": True,
            "user_id": user_id
        }), 200
    except Exception as e:
        logger.error(f"Error retrieving current user ID: {str(e)}")
        return jsonify({
            "success": False,
            "error": "Failed to retrieve user information"
        }), 500

@quicktransfer_bp.route('/api/quicktransfer/validate-id', methods=['POST'])
@token_required
@rate_limit
def validate_user_id(user_id=None, **kwargs):
    """
    Validate a Discord user ID for quick transfer
    """
    try:
        logger.info(f"Validating user ID for user_id: {user_id}")
        data = request.get_json()
        contact_user_id = data.get('user_id')
        
        if not contact_user_id:
            logger.warning("No user ID provided in request")
            return jsonify({
                "valid": False,
                "message": "User ID is required"
            }), 400
            
        logger.info(f"Validating user ID: {contact_user_id}")
            
        # Check directly in the users collection
        db = get_db()
        contact_user = db.users.find_one({"user_id": contact_user_id})
        
        if not contact_user:
            logger.warning(f"Invalid user ID: {contact_user_id}")
            return jsonify({
                "valid": False,
                "message": "The user ID you entered is invalid or does not exist"
            }), 400
            
        # Don't allow adding yourself
        if contact_user.get('user_id') == user_id:
            logger.warning(f"User tried to add themselves as a contact: {user_id}")
            return jsonify({
                "valid": False,
                "message": "You cannot add your own ID as a trusted contact"
            }), 400
            
        # Check if this contact is already in the user's trusted contacts
        existing_contact = db.quick_transfer_contacts.find_one({
            "user_id": user_id,
            "contacts.user_id": contact_user_id
        })
        
        if existing_contact:
            logger.info(f"Contact already exists for user {user_id}")
            return jsonify({
                "valid": False,
                "message": "This contact is already in your trusted list"
            }), 400
            
        # Check if user has reached the maximum number of trusted contacts
        contacts_doc = db.quick_transfer_contacts.find_one({"user_id": user_id})
        if contacts_doc and len(contacts_doc.get("contacts", [])) >= MAX_TRUSTED_CONTACTS:
            logger.warning(f"User {user_id} has reached maximum contacts limit")
            return jsonify({
                "valid": False,
                "message": f"Maximum number of trusted contacts ({MAX_TRUSTED_CONTACTS}) reached"
            }), 400
            
        # الحصول على معلومات الصورة من مجموعة discord_users مباشرة باستخدام user_id
        discord_user = db.discord_users.find_one({"user_id": contact_user_id})
        
        avatar_url = None
        if discord_user and discord_user.get("avatar"):
            avatar_hash = discord_user.get("avatar")
            avatar_url = f"https://cdn.discordapp.com/avatars/{contact_user_id}/{avatar_hash}.png?size=128"
            logger.info(f"Found Discord avatar for user {contact_user_id}: {avatar_hash}")
            
        # الحصول على البرايفت أدرس والبابلك أدرس من مجموعة users
        private_address = contact_user.get("private_address")
        public_address = contact_user.get("public_address")
            
        # Return user details
        logger.info(f"Valid user ID found for user {user_id}, contact: {contact_user.get('username')}")
        return jsonify({
            "valid": True,
            "username": contact_user.get("username"),
            "user_id": contact_user.get("user_id"),
            "avatar": avatar_url,
            "private_address": private_address,
            "public_address": public_address
        }), 200
            
    except Exception as e:
        logger.error(f"Error validating user ID: {str(e)}")
        return jsonify({
            "valid": False,
            "message": "Failed to validate user ID"
        }), 500

@quicktransfer_bp.route('/api/quicktransfer/contacts', methods=['POST'])
@token_required
def add_trusted_contact(user_id=None, **kwargs):
    """
    Add a trusted contact for quick transfers
    """
    try:
        data = request.get_json()
        contact_user_id = data.get('contact_user_id')  # تغيير من private_address إلى contact_user_id
        wallet_password = data.get('password')
        
        if not contact_user_id:
            return jsonify({
                "success": False,
                "error": "Contact user ID is required"
            }), 400
            
        # التحقق من وجود كلمة المرور
        if not wallet_password:
            return jsonify({
                "success": False,
                "error": "Wallet password is required"
            }), 400
            
        # الآن التحقق من صحة كلمة المرور
        db = get_db()
        user = db.users.find_one({"user_id": user_id})
        if not user or user.get('password') != wallet_password:
            return jsonify({
                "success": False,
                "error": "Invalid wallet password"
            }), 401
            
        # Verify the user ID exists in the system by checking the users collection directly
        contact_user = db.users.find_one({"user_id": contact_user_id})
        
        if not contact_user:
            return jsonify({
                "success": False, 
                "error": "Invalid user ID"
            }), 400
            
        # Don't allow adding yourself as a trusted contact
        if contact_user.get('user_id') == user_id:
            return jsonify({
                "success": False,
                "error": "Cannot add yourself as a trusted contact"
            }), 400
            
        # Check if user has reached the maximum number of trusted contacts
        contacts_doc = db.quick_transfer_contacts.find_one({"user_id": user_id})
        
        # لا نقوم بتخزين الأفاتار، فقط معرف المستخدم واسم المستخدم والعنوان الخاص للتوافق مع مخطط التحقق
        if contacts_doc:
            contacts = contacts_doc.get("contacts", [])
            
            # Check if contact already exists
            for contact in contacts:
                if contact.get("user_id") == contact_user_id:
                    return jsonify({
                        "success": False,
                        "error": "Contact already exists"
                    }), 400
                    
            # Check if max limit reached
            if len(contacts) >= MAX_TRUSTED_CONTACTS:
                return jsonify({
                    "success": False,
                    "error": f"Maximum number of trusted contacts ({MAX_TRUSTED_CONTACTS}) reached"
                }), 400
                
            # الحصول على البرايفت أدرس من جهة الاتصال للتوافق مع مخطط التحقق
            private_address = contact_user.get("private_address", "")
                
            # Add new contact - تخزين معرف المستخدم واسم المستخدم والعنوان الخاص للتوافق مع مخطط التحقق
            new_contact = {
                "id": str(uuid.uuid4()),
                "user_id": contact_user.get("user_id"),
                "username": contact_user.get("username"),
                "private_address": private_address,  # نضيف البرايفت أدرس للتوافق مع مخطط التحقق
                "added_at": datetime.utcnow()
            }
            
            updated_doc = db.quick_transfer_contacts.find_one_and_update(
                {"user_id": user_id},
                {"$push": {"contacts": new_contact}},
                return_document=ReturnDocument.AFTER
            )
            
            # عند إرجاع النتيجة، نقوم بإضافة البيانات الإضافية من مجموعة users و discord_users
            contacts_with_details = []
            for contact in updated_doc.get("contacts", []):
                contact_details = contact.copy()
                
                # إضافة معلومات من مجموعة users
                contact_user_details = db.users.find_one(
                    {"user_id": contact.get("user_id")},
                    {"private_address": 1, "public_address": 1, "_id": 0}
                )
                
                if contact_user_details:
                    contact_details["public_address"] = contact_user_details.get("public_address")
                
                # إضافة معلومات الأفاتار من مجموعة discord_users
                discord_user = db.discord_users.find_one(
                    {"user_id": contact.get("user_id")},
                    {"avatar": 1, "_id": 0}
                )
                
                if discord_user and discord_user.get("avatar"):
                    avatar_hash = discord_user.get("avatar")
                    contact_details["avatar_hash"] = avatar_hash
                    contact_details["avatar"] = f"https://cdn.discordapp.com/avatars/{contact.get('user_id')}/{avatar_hash}.png?size=128"
                
                # حساب الأيام المتبقية للحذف
                added_at = contact.get("added_at")
                if added_at:
                    days_since_addition = (datetime.utcnow() - added_at).days
                    can_delete = days_since_addition >= 14
                    days_remaining = max(0, 14 - days_since_addition)
                    
                    contact_details["can_delete"] = can_delete
                    contact_details["days_remaining"] = days_remaining
                    contact_details["added_at_formatted"] = added_at.strftime("%Y-%m-%d")
                
                contacts_with_details.append(contact_details)
            
            return jsonify({
                "success": True,
                "contact": new_contact,
                "contacts": contacts_with_details
            }), 200
            
        else:
            # First contact for this user
            # الحصول على البرايفت أدرس من جهة الاتصال للتوافق مع مخطط التحقق
            private_address = contact_user.get("private_address", "")
            
            new_contact = {
                "id": str(uuid.uuid4()),
                "user_id": contact_user.get("user_id"),
                "username": contact_user.get("username"),
                "private_address": private_address,  # نضيف البرايفت أدرس للتوافق مع مخطط التحقق
                "added_at": datetime.utcnow()
            }
            
            db.quick_transfer_contacts.insert_one({
                "user_id": user_id,
                "contacts": [new_contact]
            })
            
            # إضافة البيانات الإضافية للاستجابة
            contact_details = new_contact.copy()
            
            # إضافة معلومات من مجموعة users
            contact_user_details = db.users.find_one(
                {"user_id": contact_user.get("user_id")},
                {"private_address": 1, "public_address": 1, "_id": 0}
            )
            
            if contact_user_details:
                contact_details["public_address"] = contact_user_details.get("public_address")
            
            # إضافة معلومات الأفاتار من مجموعة discord_users
            discord_user = db.discord_users.find_one(
                {"user_id": contact_user.get("user_id")},
                {"avatar": 1, "_id": 0}
            )
            
            if discord_user and discord_user.get("avatar"):
                avatar_hash = discord_user.get("avatar")
                contact_details["avatar_hash"] = avatar_hash
                contact_details["avatar"] = f"https://cdn.discordapp.com/avatars/{contact_user.get('user_id')}/{avatar_hash}.png?size=128"
            
            # حساب الأيام المتبقية للحذف
            added_at = new_contact.get("added_at")
            if added_at:
                days_since_addition = (datetime.utcnow() - added_at).days
                can_delete = days_since_addition >= 14
                days_remaining = max(0, 14 - days_since_addition)
                
                contact_details["can_delete"] = can_delete
                contact_details["days_remaining"] = days_remaining
                contact_details["added_at_formatted"] = added_at.strftime("%Y-%m-%d")
            
            return jsonify({
                "success": True,
                "contact": contact_details,
                "contacts": [contact_details]
            }), 201
            
    except Exception as e:
        logger.error(f"Error adding trusted contact: {str(e)}")
        return jsonify({
            "success": False,
            "error": "Failed to add trusted contact"
        }), 500

@quicktransfer_bp.route('/api/quicktransfer/contacts/<contact_id>', methods=['DELETE'])
@token_required
def delete_trusted_contact(contact_id, user_id=None, **kwargs):
    """
    Delete a trusted contact
    """
    try:
        # الحصول على كلمة المرور من معلمات الاستعلام بدلاً من البيانات JSON
        wallet_password = request.args.get('password')
        
        # التحقق من وجود كلمة المرور
        if not wallet_password:
            return jsonify({
                "success": False,
                "error": "Wallet password is required as a query parameter (?password=yourpassword)"
            }), 400
            
        # الآن التحقق من صحة كلمة المرور
        db = get_db()
        user = db.users.find_one({"user_id": user_id})
        if not user or user.get('password') != wallet_password:
            return jsonify({
                "success": False,
                "error": "Invalid wallet password"
            }), 401
        
        # Find the contact in the user's document
        contacts_doc = db.quick_transfer_contacts.find_one({"user_id": user_id})
        
        if not contacts_doc or not contacts_doc.get("contacts"):
            return jsonify({
                "success": False,
                "error": "No trusted contacts found"
            }), 404
            
        # Find the specific contact and check if it can be deleted
        contacts = contacts_doc.get("contacts", [])
        contact_found = False
        can_be_deleted = True
        days_remaining = 0
        
        for contact in contacts:
            if contact.get("id") == contact_id:
                contact_found = True
                
                # Check if the contact can be deleted based on added_at date
                added_at = contact.get("added_at")
                if added_at:
                    # تحويل التاريخ إلى كائن datetime
                    if isinstance(added_at, str):
                        added_at = datetime.fromisoformat(added_at.replace('Z', '+00:00'))
                    elif isinstance(added_at, dict) and '$date' in added_at:
                        # تنسيق MongoDB
                        added_at_str = added_at['$date']
                        if isinstance(added_at_str, str):
                            # إذا كان التاريخ بتنسيق نصي
                            added_at = datetime.fromisoformat(added_at_str.replace('Z', '+00:00'))
                        else:
                            # إذا كان التاريخ بتنسيق timestamp (بالمللي ثانية)
                            added_at = datetime.fromtimestamp(added_at_str / 1000)
                    
                    current_time = datetime.utcnow()
                    days_since_addition = (current_time - added_at).days
                    can_be_deleted = days_since_addition >= MIN_DAYS_BEFORE_REMOVAL
                    days_remaining = max(0, MIN_DAYS_BEFORE_REMOVAL - days_since_addition)
                break
        
        # If contact not found
        if not contact_found:
            return jsonify({
                "success": False,
                "error": "Contact not found"
            }), 404
            
        # Check if the contact can be deleted (based on time restriction)
        if not can_be_deleted:
            return jsonify({
                "success": False,
                "error": f"This contact cannot be deleted yet. Please wait {days_remaining} more days."
            }), 403
            
        # Contact found and can be deleted, proceed with deletion
        result = db.quick_transfer_contacts.update_one(
            {"user_id": user_id},
            {"$pull": {"contacts": {"id": contact_id}}}
        )
        
        if result.modified_count > 0:
            return jsonify({
                "success": True,
                "message": "Contact removed successfully",
                "deleted_id": contact_id
            }), 200
        else:
            return jsonify({
                "success": False,
                "error": "Failed to delete contact"
            }), 500
            
    except Exception as e:
        logger.error(f"Error deleting trusted contact: {str(e)}")
        return jsonify({
            "success": False,
            "error": "Failed to delete trusted contact"
        }), 500

@quicktransfer_bp.route('/api/quicktransfer/transfer', methods=['POST'])
@token_required
def quick_transfer(user_id=None, **kwargs):
    """
    Process a quick transfer to a trusted contact
    """
    try:
        logger.info(f"Processing quick transfer for user_id: {user_id}")
        data = request.get_json()
        contact_id = data.get('contact_id')
        amount = data.get('amount')
        
        if not contact_id or not amount:
            logger.warning(f"Missing required parameters: contact_id={contact_id}, amount={amount}")
            return jsonify({
                "success": False,
                "error": "Contact ID and amount are required"
            }), 400
            
        # Validate amount
        try:
            amount = float(amount)
            if amount <= 0:
                logger.warning(f"Invalid amount: {amount}")
                return jsonify({
                    "success": False,
                    "error": "Amount must be positive"
                }), 400
                
            # Limit to 8 decimal places
            decimal_str = str(amount).split('.')
            if len(decimal_str) > 1 and len(decimal_str[1]) > 8:
                logger.warning(f"Amount has too many decimal places: {amount}")
                return jsonify({
                    "success": False,
                    "error": "Maximum of 8 decimal places allowed"
                }), 400
                
        except ValueError:
            logger.warning(f"Invalid amount format: {amount}")
            return jsonify({
                "success": False,
                "error": "Invalid amount"
            }), 400
            
        db = get_db()
        
        # Find the contact in user's trusted contacts
        logger.info(f"Looking for contact with ID {contact_id} for user {user_id}")
        contacts_doc = db.quick_transfer_contacts.find_one(
            {"user_id": user_id}
        )
        
        if not contacts_doc or not contacts_doc.get("contacts"):
            logger.warning(f"No trusted contacts found for user {user_id}")
            return jsonify({
                "success": False,
                "error": "No trusted contacts found"
            }), 404
            
        # Find the specific contact in the contacts array
        contact = None
        for c in contacts_doc["contacts"]:
            if c["id"] == contact_id:
                contact = c
                break
                
        if not contact:
            logger.warning(f"Contact with ID {contact_id} not found for user {user_id}")
            return jsonify({
                "success": False,
                "error": "Trusted contact not found"
            }), 404
            
        # الحصول على معرف المستخدم من جهة الاتصال
        contact_user_id = contact["user_id"]
        recipient_username = contact["username"]
        
        # Check user balance
        logger.info(f"Checking balance for user {user_id}")
        balance_info = get_user_balance(user_id)
        
        if not balance_info:
            logger.warning(f"Failed to get balance for user {user_id}")
            return jsonify({
                "success": False,
                "error": "Failed to get user balance"
            }), 500
            
        current_balance = float(balance_info)
        
        if current_balance < amount:
            logger.warning(f"Insufficient balance: {current_balance} < {amount}")
            return jsonify({
                "success": False,
                "error": "Insufficient balance"
            }), 400
            
        # Calculate new balance after transfer
        new_balance = current_balance - amount

        # Find sender and recipient details directly
        MONGODB_URI = os.getenv("DATABASE_URL")
        mongo_client = MongoClient(MONGODB_URI)
        mongodb = mongo_client["cryptonel_wallet"]
        users_collection = mongodb["users"]
        user_transactions_collection = mongodb["user_transactions"]
        
        # Find sender details
        sender = users_collection.find_one({"user_id": user_id})
        if not sender:
            logger.error(f"Sender not found: {user_id}")
            return jsonify({
                "success": False,
                "error": "Sender account not found"
            }), 404
            
        # Find recipient details using the user ID
        recipient = users_collection.find_one({"user_id": contact_user_id})
        if not recipient:
            logger.error(f"Recipient not found: {contact_user_id}")
            return jsonify({
                "success": False,
                "error": "Recipient account not found"
            }), 404
        
        # Get recipient ID and private address
        recipient_id = recipient.get("user_id")
        private_address = recipient.get("private_address")
            
        # Generate transaction ID
        tx_id = str(uuid.uuid4())
        
        # Record timestamp for transaction
        now = datetime.now()
        
        # Extract other necessary details
        sender_balance = float(sender.get("balance", "0"))
        recipient_balance = float(recipient.get("balance", "0"))
        sender_public_address = sender.get("public_address", "Unknown")
        recipient_public_address = recipient.get("public_address", "Unknown")
        sender_username = sender.get("username", "Unknown")
        recipient_username = recipient.get("username", "User")
        sender_private_address = sender.get("private_address", "Unknown")
        
        # Use transaction reason
        transfer_reason = f"Quick Transfer to {recipient_username}"
        
        # For simplicity, no fees for quick transfers
        fee = 0
        amount_after_fee = amount
        tax_rate = 0
        tax_enabled = False
        premium_exempt = False
        
        # Calculate new balances
        new_sender_balance = sender_balance - amount
        new_recipient_balance = recipient_balance + amount_after_fee

        # Create sender transaction document
        sender_tx_document = {
            "tx_id": tx_id,
            "type": "sent",
            "amount": f"{amount:.8f}",
            "timestamp": now,
            "fee": f"{fee:.8f}",
            "amount_after_fee": f"{amount:.8f}",  # Same as amount for sender
            "reason": transfer_reason,
            "status": "completed",
            "document_type": "transaction",  # Flag to identify document-based transactions
            
            # Sender complete information
            "user_id": user_id,  # The user this transaction belongs to
            "sender_id": user_id,
            "sender_username": sender_username,
            "sender_public_address": sender_public_address,
            "sender_private_address": sender_private_address,
            "sender_balance_before": f"{sender_balance:.8f}",
            "sender_balance_after": f"{new_sender_balance:.8f}",
            "sender_premium": sender.get("premium", False),
            
            # Recipient complete information
            "recipient_id": recipient_id,
            "recipient_username": recipient_username,
            "recipient_public_address": recipient_public_address,
            "recipient_private_address": private_address,
            "recipient_balance_before": f"{recipient_balance:.8f}",
            "recipient_balance_after": f"{new_recipient_balance:.8f}",
            "recipient_premium": recipient.get("premium", False),
            
            # Counterparty references (for backward compatibility and convenient querying)
            "counterparty_id": recipient_id,
            "counterparty_username": recipient_username,
            "counterparty_address": private_address,
            "counterparty_public_address": recipient_public_address,
            
            # Additional metadata
            "tax_rate": f"{tax_rate:.4f}",
            "tax_enabled": tax_enabled,
            "premium_exempt": premium_exempt,
            "created_at": now,
            "updated_at": now
        }
        
        # Recipient transaction document
        recipient_tx_document = {
            "tx_id": tx_id,
            "type": "received",
            "amount": f"{amount_after_fee:.8f}",
            "timestamp": now,
            "fee": f"{fee:.8f}",
            "amount_after_fee": f"{amount_after_fee:.8f}",  # After fee deduction
            "reason": transfer_reason,
            "status": "completed",
            "document_type": "transaction",  # Flag to identify document-based transactions
            
            # Recipient complete information
            "user_id": recipient_id,  # The user this transaction belongs to
            "recipient_id": recipient_id,
            "recipient_username": recipient_username,
            "recipient_public_address": recipient_public_address,
            "recipient_private_address": private_address,
            "recipient_balance_before": f"{recipient_balance:.8f}",
            "recipient_balance_after": f"{new_recipient_balance:.8f}",
            "recipient_premium": recipient.get("premium", False),
            
            # Sender complete information
            "sender_id": user_id,
            "sender_username": sender_username,
            "sender_public_address": sender_public_address,
            "sender_private_address": sender_private_address,
            "sender_balance_before": f"{sender_balance:.8f}",
            "sender_balance_after": f"{new_sender_balance:.8f}",
            "sender_premium": sender.get("premium", False),
            
            # Counterparty references (for backward compatibility and convenient querying)
            "counterparty_id": user_id,
            "counterparty_username": sender_username,
            "counterparty_address": sender_private_address,
            "counterparty_public_address": sender_public_address,
            
            # Additional metadata
            "tax_rate": f"{tax_rate:.4f}",
            "tax_enabled": tax_enabled,
            "premium_exempt": premium_exempt,
            "created_at": now,
            "updated_at": now
        }
        
        # Attempt to use a MongoDB transaction for atomicity
        try:
            # Start session and transaction
            with mongo_client.start_session() as session:
                with session.start_transaction():
                    # Update sender's balance
                    users_collection.update_one(
                        {"user_id": user_id},
                        {"$set": {"balance": f"{new_sender_balance:.8f}"}},
                        session=session
                    )
                    
                    # Update recipient's balance
                    users_collection.update_one(
                        {"user_id": recipient_id},
                        {"$set": {"balance": f"{new_recipient_balance:.8f}"}},
                        session=session
                    )
                    
                    # Insert the transaction documents
                    user_transactions_collection.insert_one(sender_tx_document, session=session)
                    user_transactions_collection.insert_one(recipient_tx_document, session=session)
                    
                    # No modifications to the old array-based structure
                    
            # Transaction succeeded
            transaction_success = True
            logger.info(f"Transaction completed successfully: {tx_id}")
            
        except Exception as e:
            # Transaction failed, try non-transactional approach
            logger.error(f"Transaction error: {e}")
            
            try:
                # Update sender's balance
                users_collection.update_one(
                    {"user_id": user_id},
                    {"$set": {"balance": f"{new_sender_balance:.8f}"}}
                )
                
                # Update recipient's balance
                users_collection.update_one(
                    {"user_id": recipient_id},
                    {"$set": {"balance": f"{new_recipient_balance:.8f}"}}
                )
                
                # Insert the transaction documents
                user_transactions_collection.insert_one(sender_tx_document)
                user_transactions_collection.insert_one(recipient_tx_document)
                
                # No modifications to the old array-based structure
                
                transaction_success = True
                logger.info(f"Transaction completed successfully (non-transactional): {tx_id}")
            except Exception as fallback_error:
                logger.error(f"Fallback transaction error: {fallback_error}")
                transaction_success = False
        
        if transaction_success:
            # Create transaction data for the response
            transaction_data = {
                "id": tx_id,
                "amount": f"{amount:.8f}",
                "amount_simple": str(int(amount) if amount.is_integer() else amount),
                "timestamp": now.isoformat(),
                "sender": user_id,
                "sender_username": sender_username,
                "sender_public_address": sender_public_address,
                "recipient": recipient_id,
                "recipient_username": recipient_username,
                "recipient_public_address": recipient_public_address,
                "recipient_address": private_address,
                "fee": "0.00000000",
                "amount_after_fee": f"{amount:.8f}"
            }
            
            # إرسال إشعارات البريد الإلكتروني في خلفية العملية
            try:
                # استيراد وظيفة إرسال البريد الإلكتروني
                from backend.cryptonel.email_sender import send_transaction_emails
                import threading
                
                # إرسال الإشعارات في خلفية العملية
                threading.Thread(
                    target=send_transaction_emails,
                    args=(sender, recipient, transaction_data, users_collection),
                    daemon=True
                ).start()
                
                logger.info(f"Email notification thread started for transaction: {tx_id}")
            except Exception as email_error:
                logger.error(f"Error starting email notification thread: {email_error}")
            
            return jsonify({
                "success": True,
                "tx_id": tx_id,
                "transaction": transaction_data,
                "message": f"Successfully transferred {amount} CRN to {recipient_username}",
                "previous_balance": str(current_balance),
                "new_balance": str(new_balance)
            }), 200
        else:
            logger.error("Transaction failed")
            return jsonify({
                "success": False,
                "error": "Transfer failed. Please try again."
            }), 500
            
    except Exception as e:
        logger.error(f"Error processing quick transfer: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({
            "success": False,
            "error": "Failed to process transfer"
        }), 500

def init_routes(app: Flask):
    """
    Register all routes for quick transfer functionality
    """
    app.register_blueprint(quicktransfer_bp)
    return app 