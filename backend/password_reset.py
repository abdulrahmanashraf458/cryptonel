import os
import time
import secrets
import uuid
import re
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, session, redirect, url_for
from pymongo import MongoClient
from dotenv import load_dotenv
from bson.objectid import ObjectId
import logging
import hmac
import json
import random
import jwt
import hashlib
import smtplib
from email.message import EmailMessage

# Import centralized MongoDB connection at the top
from backend.db_connection import (
    client, db, users_collection, rate_limits_collection, 
    blacklist_tokens_collection
)

# Define reset_tokens_collection
reset_tokens_collection = db["password_reset_tokens"]

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Check if required environment variables exist
if not os.getenv("DATABASE_URL"):
    logger.error("Missing DATABASE_URL environment variable")
    raise EnvironmentError("DATABASE_URL environment variable is required")

# Test connection
client.admin.command('ping')
logger.info("Successfully connected to MongoDB")

# Create blueprint
password_reset_bp = Blueprint('password_reset', __name__)

def validate_email(email):
    """Validate email format"""
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(email_pattern, email) is not None

def generate_reset_token():
    """Generate a secure reset token"""
    return secrets.token_urlsafe(64)

def is_reset_token_valid(token):
    """Check if a reset token is valid and not expired"""
    token_data = reset_tokens_collection.find_one({"token": token})
    
    if not token_data:
        return False, None
    
    # Check if token is already used
    if token_data.get("used", False):
        # Token already used - prevent reuse
        return False, None
    
    # Check if token is expired (24 hours)
    if token_data.get("expiry") < datetime.utcnow():
        # Delete expired token
        reset_tokens_collection.delete_one({"token": token})
        return False, None
    
    return True, token_data.get("user_id")

def generate_reset_email(username, reset_url):
    """Generate HTML email for password reset"""
    return f"""
    <html>
        <head>
            <title>Cryptonel Wallet Password Reset</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    margin: 0;
                    padding: 0;
                    background-color: #ffffff;
                }}
                .header {{
                    background-color: #1e2329;
                    padding: 20px;
                    text-align: center;
                    color: #f0b90b;
                    font-size: 24px;
                    font-weight: bold;
                }}
                .content {{
                    padding: 20px;
                }}
                .content h1 {{
                    color: #000000;
                    font-size: 24px;
                }}
                .content p {{
                    color: #000000;
                    font-size: 16px;
                }}
                .content .reset-button {{
                    background-color: #f0b90b;
                    color: #000000;
                    padding: 12px 24px;
                    text-decoration: none;
                    display: inline-block;
                    margin: 20px 0;
                    border-radius: 4px;
                    font-weight: bold;
                }}
                .content .reset-button:hover {{
                    background-color: #e5a800;
                }}
                .footer {{
                    background-color: #f4f4f4;
                    padding: 20px;
                    text-align: center;
                    border-top: 2px solid #e5e5e5;
                }}
                .footer p {{
                    color: #666666;
                    font-size: 12px;
                }}
                .warning {{
                    color: #ff6600;
                    font-size: 14px;
                    margin-top: 30px;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                Cryptonel Wallet
            </div>
            <div class="content">
                <h1>Password Reset Request</h1>
                <p>Hello {username},</p>
                <p>We received a request to reset your password for your Cryptonel Wallet account. To reset your password, please click the button below:</p>
                
                <a href="{reset_url}" class="reset-button">Reset Password</a>
                
                <p>If you did not request a password reset, please ignore this email or contact support if you have concerns about your account security.</p>
                
                <p class="warning">Note: This password reset link will expire in 24 hours.</p>
            </div>
            <div class="footer">
                <p>© {datetime.now().year} Cryptonel. All rights reserved.</p>
                <p>This is an automated message, please do not reply.</p>
            </div>
        </body>
    </html>
    """

@password_reset_bp.route('/api/password/request-reset', methods=['POST'])
def request_reset():
    """
    Handle password reset request
    This endpoint will:
    1. Validate the email
    2. Check if user exists with this email
    3. Check if user has a wallet
    4. Generate a reset token
    5. Send an email with reset link using direct SMTP logic
    """
    try:
        # Get email from request
        data = request.get_json()
        
        if not data or 'email' not in data:
            return jsonify({"error": "Email is required"}), 400
        
        email = data['email'].strip().lower()
        
        # Validate email format
        if not validate_email(email):
            # Return success even if email is invalid for security reasons
            # This prevents user enumeration attacks
            logger.info(f"Invalid email format: {email}")
            return jsonify({
                "success": True,
                "message": "If your email is registered, you will receive password reset instructions."
            }), 200
        
        # التحقق من عدد محاولات إعادة التعيين خلال فترة قصيرة
        # لمنع إساءة استخدام النظام ومنع رسائل البريد المتعددة
        recent_request = reset_tokens_collection.find_one({
            "email": email,
            "created_at": {"$gt": datetime.utcnow() - timedelta(minutes=5)}
        })
        
        if recent_request:
            # احسب الوقت المتبقي قبل السماح بطلب جديد
            time_since_request = datetime.utcnow() - recent_request["created_at"]
            wait_time = timedelta(minutes=5) - time_since_request
            wait_seconds = max(int(wait_time.total_seconds()), 0)
            
            logger.info(f"Rate limiting password reset for {email}. Wait time: {wait_seconds} seconds")
            
            return jsonify({
                "success": True,
                "message": f"A password reset email was recently sent. Please wait {wait_seconds} seconds before requesting another one.",
                "wait_time": wait_seconds
            }), 200
        
        # Find user with this email
        user = users_collection.find_one({"email": email})
        
        if not user:
            # Return success even if user doesn't exist for security reasons
            logger.info(f"Password reset requested for non-existent email: {email}")
            return jsonify({
                "success": True,
                "message": "If your email is registered, you will receive password reset instructions."
            }), 200
        
        # Check if user has a wallet by verifying essential wallet fields
        if not all(key in user for key in ["wallet_id", "public_address", "private_address"]):
            # Return a generic message to prevent user enumeration
            logger.info(f"Password reset requested for user without a complete wallet: {email}")
            return jsonify({
                "success": True,
                "message": "If your email is registered, you will receive password reset instructions."
            }), 200
        
        # Generate reset token
        reset_token = generate_reset_token()
        
        # Calculate expiry time (24 hours from now)
        expiry_time = datetime.utcnow() + timedelta(hours=24)
        
        # Log the email configuration
        logger.info(f"Checking email configuration before sending. SMTP_HOST: {'Set' if os.getenv('SMTP_HOST') else 'Missing'}, SMTP_USER: {'Set' if os.getenv('SMTP_USER') else 'Missing'}, SMTP_PASSWORD: {'Set' if os.getenv('SMTP_PASSWORD') else 'Missing'}")
        
        # Store token in database with user ID and expiry
        reset_tokens_collection.insert_one({
            "user_id": str(user["_id"]),
            "token": reset_token,
            "email": email,
            "created_at": datetime.utcnow(),
            "expiry": expiry_time,
            "used": False,
            "ip_address": request.remote_addr,
            "user_agent": request.headers.get('User-Agent', 'Unknown'),
            "request_details": {
                "host": request.host,
                "platform": request.user_agent.platform if request.user_agent else "Unknown",
                "browser": request.user_agent.browser if request.user_agent else "Unknown",
                "version": request.user_agent.version if request.user_agent else "Unknown"
            }
        })
        
        # Generate reset URL
        reset_url = f"{request.host_url.rstrip('/')}/reset-password?token={reset_token}"
        
        # Log detailed information about the reset request
        logger.info(f"Password reset requested for user: {user.get('username')} (ID: {user['_id']})")
        logger.info(f"Reset token generated: {reset_token[:10]}... (expires: {expiry_time})")
        logger.info(f"Request from IP: {request.remote_addr}, User-Agent: {request.headers.get('User-Agent', 'Unknown')[:50]}...")
        
        # Generate email HTML
        email_html = generate_reset_email(user.get("username", "User"), reset_url)
        
        # --- Direct SMTP Sending Logic ---
        smtp_host = os.getenv("SMTP_HOST")
        smtp_port = int(os.getenv("SMTP_PORT", 587))
        smtp_user = os.getenv("SMTP_USER")
        smtp_password = os.getenv("SMTP_PASSWORD")
        smtp_sender_email = os.getenv("SMTP_SENDER_EMAIL")
        smtp_sender_name = os.getenv("SMTP_SENDER_NAME", "Cryptonel")

        email_sent = False
        try:
            msg = EmailMessage()
            msg["From"] = f"{smtp_sender_name} <{smtp_sender_email}>"
            msg["To"] = email
            msg["Subject"] = "Cryptonel Wallet Password Reset"
            msg.set_content("This is an HTML email. Please use an HTML-compatible client.")
            msg.add_alternative(email_html, subtype='html')

            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_password)
                server.send_message(msg)
            email_sent = True
            logger.info(f"Password reset email sent successfully to {email}")
        except Exception as e:
            logger.error(f"Failed to send password reset email to {email}: {e}")
            email_sent = False
        # --- End of SMTP Logic ---

        if not email_sent:
            return jsonify({
                "error": "Failed to send reset email. Please try again later."
            }), 500
        
        # Return success
        return jsonify({
            "success": True,
            "message": "If your email is registered, you will receive password reset instructions."
        }), 200
        
    except Exception as e:
        logger.error(f"Password reset request error: {str(e)}")
        import traceback
        logger.error(f"Error traceback: {traceback.format_exc()}")
        return jsonify({
            "error": "An unexpected error occurred. Please try again later."
        }), 500

@password_reset_bp.route('/api/password/validate-token', methods=['POST'])
def validate_token():
    """Validate a password reset token"""
    try:
        data = request.get_json()
        
        if not data or 'token' not in data:
            return jsonify({"error": "Token is required"}), 400
        
        token = data['token']
        
        # Check if token is valid and not expired
        is_valid, user_id = is_reset_token_valid(token)
        
        if not is_valid:
            # Check specifically if token was used before
            token_data = reset_tokens_collection.find_one({"token": token})
            
            if token_data and token_data.get("used", False):
                return jsonify({
                    "valid": False,
                    "error": "This reset link has already been used. Please request a new password reset if needed."
                }), 400
            elif token_data and token_data.get("expiry") < datetime.utcnow():
                return jsonify({
                    "valid": False,
                    "error": "This reset link has expired. Please request a new password reset."
                }), 400
            else:
                return jsonify({
                    "valid": False,
                    "error": "Invalid reset token. Please request a new password reset."
                }), 400
        
        return jsonify({
            "valid": True
        }), 200
        
    except Exception as e:
        logger.error(f"Validate token error: {str(e)}")
        return jsonify({
            "error": "An unexpected error occurred. Please try again later."
        }), 500

def is_valid_password(password):
    """
    Check if password meets security requirements:
    - Minimum 8 characters (16+ recommended)
    - Must contain uppercase letters (A-Z)
    - Must contain lowercase letters (a-z)
    - Must contain numbers (0-9)
    - Must contain special characters (!@#$%^&*()_-+=<>?/[]{})
    """
    if not password:
        return False, "Password cannot be empty"
    
    # Check minimum length
    if len(password) < 8:
        return False, "Password must be at least 8 characters (16+ recommended for better security)"
    
    # Check for required character types
    has_uppercase = any(c.isupper() for c in password)
    has_lowercase = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_special = any(c in "!@#$%^&*()_-+=<>?/[]{}" for c in password)
    
    # Create a specific error message based on what's missing
    missing = []
    if not has_uppercase:
        missing.append("uppercase letter")
    if not has_lowercase:
        missing.append("lowercase letter")
    if not has_digit:
        missing.append("number")
    if not has_special:
        missing.append("special character (!@#$%^&*()_-+=<>?/[]{})")
    
    if missing:
        return False, f"Password must include at least one {', one '.join(missing)}"
    
    # If password is valid but shorter than recommended
    if len(password) < 16:
        return True, "Valid password (consider using 16+ characters for even better security)"
    
    return True, "Strong password"

@password_reset_bp.route('/api/password/reset', methods=['POST'])
def reset_password():
    """Reset user password with valid token"""
    try:
        data = request.get_json()
        
        if not data or 'token' not in data or 'new_password' not in data:
            return jsonify({
                "error": "Token and new password are required"
            }), 400
        
        token = data['token']
        new_password = data['new_password']
        
        # Validate password strength
        is_valid, message = is_valid_password(new_password)
        if not is_valid:
            return jsonify({
                "error": message
            }), 400
        
        # Check token first before actually resetting
        token_data = reset_tokens_collection.find_one({"token": token})
        
        # Check if token exists
        if not token_data:
            return jsonify({
                "error": "Invalid reset token. Please request a new password reset."
            }), 400
            
        # Check if token is already used
        if token_data.get("used", False):
            return jsonify({
                "error": "This reset link has already been used. Please request a new password reset if needed."
            }), 400
            
        # Check if token is expired
        if token_data.get("expiry") < datetime.utcnow():
            # Delete expired token
            reset_tokens_collection.delete_one({"token": token})
            return jsonify({
                "error": "This reset link has expired. Please request a new password reset."
            }), 400
        
        # At this point token is valid, get user_id and proceed
        user_id = token_data.get("user_id")
        
        # Find user
        user = users_collection.find_one({"_id": ObjectId(user_id)})
        
        if not user:
            return jsonify({
                "error": "User not found"
            }), 404
        
        # Check if new password is the same as the old one
        if user.get("password") == new_password:
            return jsonify({
                "error": "New password cannot be the same as your current password"
            }), 400
        
        # Update password
        users_collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"password": new_password}}
        )
        
        # Mark token as used IMMEDIATELY to prevent concurrent usage
        reset_tokens_collection.update_one(
            {"token": token},
            {"$set": {"used": True}}
        )
        
        # Send confirmation email
        try:
            confirmation_html = f"""
            <html>
                <head>
                    <title>Password Reset Successful</title>
                    <style>
                        body {{
                            font-family: Arial, sans-serif;
                            margin: 0;
                            padding: 0;
                            background-color: #ffffff;
                        }}
                        .header {{
                            background-color: #1e2329;
                            padding: 20px;
                            text-align: center;
                            color: #f0b90b;
                            font-size: 24px;
                            font-weight: bold;
                        }}
                        .content {{
                            padding: 20px;
                        }}
                        .content h1 {{
                            color: #000000;
                            font-size: 24px;
                        }}
                        .content p {{
                            color: #000000;
                            font-size: 16px;
                        }}
                        .footer {{
                            background-color: #f4f4f4;
                            padding: 20px;
                            text-align: center;
                            border-top: 2px solid #e5e5e5;
                        }}
                        .footer p {{
                            color: #666666;
                            font-size: 12px;
                        }}
                    </style>
                </head>
                <body>
                    <div class="header">
                        Cryptonel Wallet
                    </div>
                    <div class="content">
                        <h1>Password Reset Successful</h1>
                        <p>Hello {user.get('username', 'User')},</p>
                        <p>Your password has been successfully reset. You can now log in with your new password.</p>
                        <p>If you did not request this change, please contact our support team immediately.</p>
                    </div>
                    <div class="footer">
                        <p>© {datetime.now().year} Cryptonel. All rights reserved.</p>
                        <p>This is an automated message, please do not reply.</p>
                    </div>
                </body>
            </html>
            """
            
            # --- Direct SMTP Sending Logic for Confirmation ---
            smtp_host = os.getenv("SMTP_HOST")
            smtp_port = int(os.getenv("SMTP_PORT", 587))
            smtp_user = os.getenv("SMTP_USER")
            smtp_password = os.getenv("SMTP_PASSWORD")
            smtp_sender_email = os.getenv("SMTP_SENDER_EMAIL")
            smtp_sender_name = os.getenv("SMTP_SENDER_NAME", "Cryptonel")

            msg = EmailMessage()
            msg["From"] = f"{smtp_sender_name} <{smtp_sender_email}>"
            msg["To"] = user.get("email")
            msg["Subject"] = "Cryptonel Wallet Password Reset Successful"
            msg.set_content("This is an HTML email.")
            msg.add_alternative(confirmation_html, subtype='html')

            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_password)
                server.send_message(msg)
            # --- End of SMTP Logic ---

        except Exception as e:
            # Log but don't fail if confirmation email fails
            logger.error(f"Failed to send password reset confirmation: {str(e)}")
        
        return jsonify({
            "success": True,
            "message": "Password has been reset successfully"
        }), 200
        
    except Exception as e:
        logger.error(f"Reset password error: {str(e)}")
        return jsonify({
            "error": "An unexpected error occurred. Please try again later."
        }), 500

def init_app(app):
    """Initialize the password reset blueprint with the Flask app"""
    # Register blueprint
    app.register_blueprint(password_reset_bp)
    
    # Create TTL index for expired tokens
    try:
        # Create index on expiry field to automatically remove expired tokens
        reset_tokens_collection.create_index("expiry", expireAfterSeconds=0)
        logger.info("Created TTL index for password reset tokens")
    except Exception as e:
        logger.warning(f"Could not create TTL index for reset tokens: {e}")
    
    # Create index on email and created_at for faster rate limit lookups
    try:
        reset_tokens_collection.create_index([("email", 1), ("created_at", -1)])
        logger.info("Created index for reset token rate limiting")
    except Exception as e:
        logger.warning(f"Could not create rate limit index: {e}")
    
    # Add periodic cleanup function
    cleanup_last_run = [0]  # Use list to store as mutable reference

    @app.before_request
    def cleanup_expired_tokens():
        # Only run occasionally to avoid doing this on every request
        current_time = time.time()
        if current_time - cleanup_last_run[0] > 3600:  # Run once per hour
            try:
                # Delete expired tokens
                result = reset_tokens_collection.delete_many({"expiry": {"$lt": datetime.utcnow()}})
                if result.deleted_count > 0:
                    logger.info(f"Cleaned up {result.deleted_count} expired password reset tokens")
                
                # Update last run time
                cleanup_last_run[0] = current_time
            except Exception as e:
                logger.error(f"Error cleaning up expired tokens: {e}")
                
    # Run cleanup once at startup
    try:
        result = reset_tokens_collection.delete_many({"expiry": {"$lt": datetime.utcnow()}})
        if result.deleted_count > 0:
            logger.info(f"Initial cleanup: removed {result.deleted_count} expired password reset tokens")
    except Exception as e:
        logger.error(f"Error during initial token cleanup: {e}") 