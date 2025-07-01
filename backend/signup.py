import os
import time
import re
import random
import string
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, session
from pymongo import MongoClient
from dotenv import load_dotenv
import logging
import bcrypt
import pyotp
import bip_utils  # Library for mnemonic phrase generation
import smtplib
from email.message import EmailMessage

# Import JWT utilities
from backend.jwt_utils import create_tokens

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# MongoDB connection
try:
    MONGODB_URI = os.getenv("DATABASE_URL")
    client = MongoClient(MONGODB_URI)
    db = client["cryptonel_wallet"]
    users_collection = db["users"]
    discord_users_collection = db["discord_users"]
    rate_limits_collection = db["rate_limits"]  # Add rate limits collection
    
    # Test connection
    client.admin.command('ping')
    logger.info("Successfully connected to MongoDB")
except Exception as e:
    logger.error(f"Failed to connect to MongoDB: {e}")
    raise

# Create blueprint
signup_bp = Blueprint('signup', __name__)

# ----- Helper Functions -----

# Add function to create indexes
def create_indexes():
    """Create necessary indexes for collections"""
    try:
        # Make sure the collection is initialized - Fixed boolean check
        if rate_limits_collection is None:
            logger.warning("Rate limits collection not initialized, skipping index creation")
            return
            
        # Try to create index with a specific name to avoid conflicts
        try:
            rate_limits_collection.create_index(
                [("user_id", 1)], 
                unique=True,
                name="rate_limits_user_id_unique",
                background=True  # Allow creation in the background
            )
            logger.info("Rate limits index created successfully")
        except Exception as idx_error:
            # Check if it's the duplicate index error (code 85 or 86)
            if hasattr(idx_error, 'code') and idx_error.code in (85, 86):
                logger.info("Rate limits index already exists")
            else:
                # Some other index error occurred
                raise idx_error
                
    except Exception as e:
        # Log the error but don't terminate the program
        logger.error(f"Error creating indexes: {e}")
        # Continue execution even if index creation fails

# Add OTP rate limit check function
def check_otp_send_rate_limit(user_id):
    """
    Check if a user has exceeded their rate limit for sending OTPs.
    Rate limit: One OTP per 5 minutes.
    Returns a tuple (is_rate_limited, seconds_remaining)
    """
    current_time = time.time()
    
    # Get user's rate limits record
    user_rate_limits = rate_limits_collection.find_one({"user_id": user_id})
    
    # Initialize if not exists
    if not user_rate_limits:
        user_rate_limits = {
            "user_id": user_id,
            "rate_limits": []
        }
        rate_limits_collection.insert_one(user_rate_limits)
    
    # Find the OTP send limit in the array
    otp_send_limit = None
    if "rate_limits" in user_rate_limits:
        for limit in user_rate_limits["rate_limits"]:
            if limit.get("limit_type") == "otp_send":
                otp_send_limit = limit
                break
    
    # If no OTP send limit exists, user can send OTP
    if not otp_send_limit:
        return False, 0
    
    # Check if user can send OTP (5 minutes cooldown)
    last_attempt = otp_send_limit.get('last_attempt', 0)
    cooldown = 300  # 5 minutes in seconds
    
    # If the cooldown period has passed, user can send OTP
    if current_time - last_attempt > cooldown:
        return False, 0
    
    # User is rate limited, calculate remaining time
    seconds_remaining = int(cooldown - (current_time - last_attempt))
    return True, seconds_remaining

# Update OTP send rate limit tracking
def update_otp_send_rate_limit(user_id):
    """Update rate limit tracking after sending an OTP"""
    current_time = time.time()
    
    # Get user's rate limits record
    user_rate_limits = rate_limits_collection.find_one({"user_id": user_id})
    
    # Initialize if not exists
    if not user_rate_limits:
        user_rate_limits = {
            "user_id": user_id,
            "rate_limits": []
        }
        rate_limits_collection.insert_one(user_rate_limits)
    
    # Find the OTP send limit in the array
    has_limit = False
    if "rate_limits" in user_rate_limits:
        for limit in user_rate_limits["rate_limits"]:
            if limit.get("limit_type") == "otp_send":
                has_limit = True
                break
    
    if has_limit:
        # Update existing limit
        rate_limits_collection.update_one(
            {"user_id": user_id, "rate_limits.limit_type": "otp_send"},
            {"$set": {"rate_limits.$.last_attempt": current_time}}
        )
    else:
        # Add new limit to array
        rate_limits_collection.update_one(
            {"user_id": user_id},
            {"$push": {"rate_limits": {
                "limit_type": "otp_send",
                "last_attempt": current_time
            }}}
        )

# Add OTP verification rate limit check function
def check_otp_verify_rate_limit(user_id):
    """
    Check if a user has exceeded their rate limit for OTP verification attempts.
    After 4 incorrect attempts, block for 15 minutes.
    Returns a tuple (is_rate_limited, attempts_remaining, reset_time)
    """
    current_time = time.time()
    
    # Get user's rate limits record
    user_rate_limits = rate_limits_collection.find_one({"user_id": user_id})
    
    # Initialize if not exists
    if not user_rate_limits:
        return False, 4, 0
    
    # Find the OTP verification limit in the array
    otp_verification = None
    if "rate_limits" in user_rate_limits:
        for limit in user_rate_limits["rate_limits"]:
            if limit.get("limit_type") == "otp_verification":
                otp_verification = limit
                break
    
    # If no OTP verification limit exists
    if not otp_verification:
        return False, 4, 0
    
    # Check if user is currently blocked
    blocked_until = otp_verification.get('blocked_until', 0)
    if blocked_until > current_time:
        # User is rate limited
        seconds_remaining = int(blocked_until - current_time)
        return True, 0, seconds_remaining
    
    # If it's been more than 10 minutes since the last attempt, reset counter
    last_attempt = otp_verification.get('last_attempt', 0)
    if current_time - last_attempt > 600:  # 10 minutes in seconds
        # Reset attempt count in DB
        rate_limits_collection.update_one(
            {"user_id": user_id, "rate_limits.limit_type": "otp_verification"},
            {"$set": {"rate_limits.$.count": 0, "rate_limits.$.last_attempt": current_time}}
        )
        return False, 4, 0
    
    # User is not blocked, return attempts remaining
    count = otp_verification.get('count', 0)
    attempts_remaining = 4 - count
    return False, attempts_remaining, 0

# Update OTP verification rate limit tracking after an attempt
def update_otp_verify_rate_limit(user_id, is_valid):
    """Update rate limit tracking after an OTP verification attempt"""
    current_time = time.time()
    
    # Get user's rate limits record
    user_rate_limits = rate_limits_collection.find_one({"user_id": user_id})
    
    # Initialize if not exists
    if not user_rate_limits:
        user_rate_limits = {
            "user_id": user_id,
            "rate_limits": []
        }
        rate_limits_collection.insert_one(user_rate_limits)
    
    # Find the OTP verification limit in the array
    otp_verification = None
    has_limit = False
    if "rate_limits" in user_rate_limits:
        for i, limit in enumerate(user_rate_limits["rate_limits"]):
            if limit.get("limit_type") == "otp_verification":
                otp_verification = limit
                has_limit = True
                break
    
    # If valid, reset counter
    if is_valid:
        if has_limit:
            # Update existing limit
            rate_limits_collection.update_one(
                {"user_id": user_id, "rate_limits.limit_type": "otp_verification"},
                {"$set": {"rate_limits.$.count": 0, "rate_limits.$.last_attempt": current_time}}
            )
        else:
            # Add new limit to array
            rate_limits_collection.update_one(
                {"user_id": user_id},
                {"$push": {"rate_limits": {
                    "limit_type": "otp_verification",
                    "count": 0,
                    "last_attempt": current_time,
                    "blocked_until": 0
                }}}
            )
        return
    
    # Get current count
    count = 0
    if otp_verification:
        count = otp_verification.get('count', 0)
    
    # Increment attempt counter
    new_count = count + 1
    new_blocked_until = 0
    
    # If max attempts reached, block for 60 seconds
    if new_count >= 4:
        new_blocked_until = current_time + 900  # Block for 15 minutes
        new_count = 0  # Reset counter for next window
    
    if has_limit:
        # Update existing limit
        rate_limits_collection.update_one(
            {"user_id": user_id, "rate_limits.limit_type": "otp_verification"},
            {"$set": {
                "rate_limits.$.count": new_count,
                "rate_limits.$.last_attempt": current_time,
                "rate_limits.$.blocked_until": new_blocked_until
            }}
        )
    else:
        # Add new limit to array
        rate_limits_collection.update_one(
            {"user_id": user_id},
            {"$push": {"rate_limits": {
                "limit_type": "otp_verification",
                "count": new_count,
                "last_attempt": current_time,
                "blocked_until": new_blocked_until
            }}}
        )

def is_valid_username(username):
    """
    Check if username is valid and not taken
    Rules:
    - Must be 3-12 characters
    - Must start with a letter
    - Can only contain letters and numbers
    - Must not be already taken
    """
    # Check length
    if not username:
        return False, "Username cannot be empty"
        
    if len(username) < 3:
        return False, "Username must be at least 3 characters"
        
    if len(username) > 12:
        return False, "Username cannot exceed 12 characters"
    
    # Check if starts with a letter
    if not username[0].isalpha():
        return False, "Username must start with a letter"
    
    # Check format (only letters and numbers)
    if not re.match(r'^[a-zA-Z0-9]+$', username):
        return False, "Username can only contain letters and numbers"
    
    # Check if already exists
    if users_collection.find_one({"username": username}):
        return False, "Username is already taken"
    
    return True, "Valid username"

def is_valid_email(email):
    """
    Check if email is valid and not taken.
    Accepts Gmail, Outlook, and Hotmail addresses.
    Only letters and numbers allowed in the local part (before @).
    No special characters allowed (_, -, ., +, etc.)
    """
    if not email:
        return False, "Email cannot be empty"
        
    email = email.lower()
    
    # Split email into local part and domain
    if '@' not in email:
        return False, "Invalid email format"
        
    local_part = email.split('@')[0]
    domain = email.split('@')[1]
    
    # Check if local part contains only letters and numbers
    if not re.match(r'^[a-zA-Z0-9]+$', local_part):
        return False, "Email username can only contain letters and numbers"
    
    # Check if domain is allowed
    if domain not in ["gmail.com", "outlook.com", "hotmail.com"]:
        return False, "Only Gmail, Outlook, and Hotmail addresses are accepted"
    
    # Check if email is already registered
    if users_collection.find_one({"email": email}):
        return False, "Email is already registered"
    
    return True, "Valid email"

def is_valid_date_of_birth(dob):
    """
    Check if date of birth is valid and user is at least 18 years old
    """
    try:
        # Parse date string
        dob_date = datetime.strptime(dob, "%Y-%m-%d")
        
        # Calculate age
        today = datetime.now()
        age = today.year - dob_date.year - ((today.month, today.day) < (dob_date.month, dob_date.day))
        
        # Check if date is in the future
        if dob_date > today:
            return False, "Date of birth cannot be in the future"
        
        # Check minimum age (18)
        if age < 18:
            return False, "You must be at least 18 years old to register"
        
        # Check maximum reasonable age (120)
        if age > 120:
            return False, "Please enter a valid date of birth"
        
        return True, "Valid date of birth"
    except ValueError:
        return False, "Invalid date format. Please use YYYY-MM-DD"

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

def is_password_match(password, confirm_password):
    """
    Check if password and confirmation match
    """
    return password == confirm_password, "Passwords match" if password == confirm_password else "Passwords do not match"

def is_valid_secret_word(secret_word):
    """
    Check if secret word meets requirements:
    - Must be 6-12 characters long
    - Can only contain letters (a-z, A-Z)
    - No spaces, numbers, or special characters
    """
    if not secret_word:
        return False, "Secret word cannot be empty"
    
    # Check length
    if len(secret_word) < 6:
        return False, "Secret word must be at least 6 characters"
    
    if len(secret_word) > 12:
        return False, "Secret word cannot exceed 12 characters"
    
    # Check for letters only
    if not re.match(r'^[a-zA-Z]+$', secret_word):
        return False, "Secret word can only contain letters (no numbers, spaces, or special characters)"
    
    return True, "Valid secret word"

# ----- Wallet Generation Functions -----

def generate_mnemonic_phrase():
    """
    Generate a unique 12-word mnemonic phrase using BIP-39 standard
    with additional entropy to ensure uniqueness
    """
    # Create new mnemonic phrase with 12 words
    try:
        # Always generate exactly 12 words
        mnemonic = bip_utils.Bip39MnemonicGenerator().FromWordsNumber(bip_utils.Bip39WordsNum.WORDS_NUM_12)
    except Exception as e:
        # Fall back with logging
        logger.error(f"Error generating mnemonic: {e}")
        logger.info("Falling back to alternative mnemonic generation")
        # Ensure we still use 12 words
        mnemonic = bip_utils.Bip39MnemonicGenerator().FromWordsNumber(bip_utils.Bip39WordsNum.WORDS_NUM_12)
    
    # Format with numbers
    words = mnemonic.ToStr().split()
    # Ensure we have exactly 12 words
    words = words[:12]
    formatted_words = [f"{i+1}.{word}" for i, word in enumerate(words)]
    formatted_mnemonic = " ".join(formatted_words)
    
    # Check if the mnemonic already exists with a retry counter for logging
    retry_count = 0
    max_retries = 10
    
    while users_collection.find_one({"mnemonic_phrase": formatted_mnemonic}):
        retry_count += 1
        if retry_count > max_retries:
            logger.warning(f"High number of mnemonic phrase collisions detected ({retry_count})")
        
        # Regenerate with 12 words
        try:
            mnemonic = bip_utils.Bip39MnemonicGenerator().FromWordsNumber(bip_utils.Bip39WordsNum.WORDS_NUM_12)
        except:
            # Alternative fallback
            mnemonic = bip_utils.Bip39MnemonicGenerator().FromWordsNumber(bip_utils.Bip39WordsNum.WORDS_NUM_12)
        
        words = mnemonic.ToStr().split()
        # Ensure we have exactly 12 words
        words = words[:12]
        formatted_words = [f"{i+1}.{word}" for i, word in enumerate(words)]
        formatted_mnemonic = " ".join(formatted_words)
    
    logger.info(f"Generated unique mnemonic phrase after {retry_count} retries")
    return formatted_mnemonic

def generate_backup_code():
    """
    Generate a unique backup code (30 characters, uppercase alphanumeric)
    with additional entropy and verification
    """
    # Add more randomness with timestamp as seed
    random.seed(time.time())
    
    # Use a mix of different character types for better uniqueness
    uppercase = string.ascii_uppercase
    digits = string.digits
    
    # Generate the code with a specific pattern for better entropy
    # 10 uppercase + 10 digits + 10 uppercase for the 30 character code
    part1 = ''.join(random.choices(uppercase, k=10))
    part2 = ''.join(random.choices(digits, k=10))
    part3 = ''.join(random.choices(uppercase, k=10))
    
    code = part1 + part2 + part3
    
    # Check if the code already exists with a retry counter for logging
    retry_count = 0
    max_retries = 5
    
    while users_collection.find_one({"backup_code": code}):
        retry_count += 1
        if retry_count > max_retries:
            logger.warning(f"High number of backup code collisions detected ({retry_count})")
        
        # Reseed random for more entropy on each retry
        random.seed(time.time() + retry_count)
        
        # Regenerate with different character distribution for better uniqueness
        part1 = ''.join(random.choices(uppercase, k=10))
        part2 = ''.join(random.choices(digits, k=10))
        part3 = ''.join(random.choices(uppercase, k=10))
        
        code = part1 + part2 + part3
    
    logger.info(f"Generated unique backup code after {retry_count} retries")
    return code

def generate_wallet_addresses():
    """
    Generate unique public and private addresses with enhanced
    entropy and verification for complete uniqueness
    """
    # Seed the random generator with current timestamp for better randomness
    random.seed(time.time())
    
    # Create varied character sets for better entropy
    uppercase = string.ascii_uppercase
    lowercase = string.ascii_lowercase
    digits = string.digits
    all_chars = uppercase + lowercase + digits
    
    # Generate private address (28-35 characters)
    private_length = random.randint(28, 35)
    
    # Use a pattern for better entropy: start with 'p' + mix of characters
    private_address = 'p' + ''.join(random.choices(all_chars, k=private_length-1))
    
    # Generate public address (64 characters) with a specific pattern
    # Starting with 'CR' prefix for Cryptonel
    public_prefix = 'CR'
    public_main = ''.join(random.choices(all_chars, k=62))
    public_address = public_prefix + public_main
    
    # Check if addresses already exist with a retry counter for logging
    retry_count = 0
    max_retries = 5
    
    while users_collection.find_one({"private_address": private_address}) or users_collection.find_one({"public_address": public_address}):
        retry_count += 1
        if retry_count > max_retries:
            logger.warning(f"High number of wallet address collisions detected ({retry_count})")
        
        # Reseed random for more entropy on each retry
        random.seed(time.time() + retry_count)
        
        # Regenerate with different entropy
        private_length = random.randint(28, 35)
        private_address = 'p' + ''.join(random.choices(all_chars, k=private_length-1))
        
        public_main = ''.join(random.choices(all_chars, k=62))
        public_address = public_prefix + public_main
    
    logger.info(f"Generated unique wallet addresses after {retry_count} retries")
    return private_address, public_address

def generate_wallet_id():
    """
    Generate a unique wallet ID (20 digits) with improved
    randomness and collision detection
    """
    # Seed the random generator with current timestamp
    random.seed(time.time())
    
    # Create a wallet ID with specific format: 
    # Start with current year (4 digits) + 16 random digits
    current_year = datetime.now().year
    year_prefix = str(current_year)
    
    # Generate the random part (16 digits)
    random_part = ''.join(random.choices(string.digits, k=16))
    
    # Combine to form the full wallet ID
    wallet_id = year_prefix + random_part
    
    # Check if the ID already exists with a retry counter for logging
    retry_count = 0
    max_retries = 5
    
    while users_collection.find_one({"wallet_id": wallet_id}):
        retry_count += 1
        if retry_count > max_retries:
            logger.warning(f"High number of wallet ID collisions detected ({retry_count})")
        
        # Reseed random for more entropy on each retry
        random.seed(time.time() + retry_count)
        
        # Regenerate the random part
        random_part = ''.join(random.choices(string.digits, k=16))
        
        # Recombine
        wallet_id = year_prefix + random_part
    
    logger.info(f"Generated unique wallet ID after {retry_count} retries")
    return wallet_id

def generate_otp():
    """
    Generate a 6-digit OTP
    """
    return ''.join(random.choices(string.digits, k=6))

def send_email_verification(email, otp):
    """
    Send email verification OTP using direct SMTP logic and log to otps collection.
    """
    from backend.db_connection import db
    otps_collection = db["otps"]
    status = False

    # SMTP details from the working script
    smtp_server = "mail.clyne.cc"
    smtp_port = 587
    smtp_user = "noreply"
    smtp_password = "iLDh6FCRxPJp4R"
    from_addr = "noreply@clyne.cc"

    # Construct the email
    subject = "Cryptonel Wallet - Email Verification"
    html_body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 5px;">
        <h2 style="color: #7046ff;">Email Verification</h2>
        <p>Thank you for signing up with Cryptonel Wallet. To complete your registration, please use the following verification code:</p>
        <div style="background-color: #f5f5f5; padding: 15px; border-radius: 5px; text-align: center; font-size: 24px; letter-spacing: 5px; font-weight: bold; margin: 20px 0;">
            {otp}
        </div>
        <p>This code will expire in 5 minutes. If you didn't request this verification, please ignore this email.</p>
        <p>Best regards,<br>Cryptonel Wallet Team</p>
    </div>
    """
    
    msg = EmailMessage()
    msg["From"] = f"Cryptonel Wallet <{from_addr}>"
    msg["To"] = email
    msg["Subject"] = subject
    msg.set_content("This is an HTML email. Please use an HTML-compatible client to view it.")
    msg.add_alternative(html_body, subtype='html')

    try:
        # Send the email
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
        
        status = True
        logger.info(f"Verification email sent successfully to {email}")

    except Exception as e:
        logger.error(f"Failed to send verification email: {e}")
        status = False
    
    finally:
        # Log OTP to otps collection regardless of status
        try:
            otps_collection.insert_one({
                "email": email,
                "otp": otp,
                "user_id": session.get("user_id"),
                "timestamp": datetime.now(),
                "status": "sent" if status else "failed"
            })
        except Exception as log_err:
            logger.error(f"Failed to log OTP to otps collection: {log_err}")
    
    return status

def send_wallet_details_email(email, username, mnemonic_phrase, backup_code):
    """
    Send wallet details to user's email using direct SMTP logic.
    """
    # SMTP details
    smtp_server = "mail.clyne.cc"
    smtp_port = 587
    smtp_user = "noreply"
    smtp_password = "iLDh6FCRxPJp4R"
    from_addr = "noreply@clyne.cc"

    # HTML Body
    html_body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 5px;">
        <h2 style="color: #7046ff;">Your Cryptonel Wallet Details</h2>
        <p>Dear {username},</p>
        <p>Thank you for creating your Cryptonel Wallet. Please save the following information securely. <strong>Never share these details with anyone!</strong></p>
        <div style="background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0;">
            <h3 style="color: #7046ff; margin-top: 0;">Recovery Mnemonic Phrase</h3>
            <p style="word-wrap: break-word; font-family: monospace; background: #e0e0e0; padding: 10px; border-radius: 3px;">{mnemonic_phrase}</p>
        </div>
        <div style="background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0;">
            <h3 style="color: #7046ff; margin-top: 0;">Backup Code</h3>
            <p style="word-wrap: break-word; font-family: monospace; background: #e0e0e0; padding: 10px; border-radius: 3px;">{backup_code}</p>
        </div>
        <p><strong>Important:</strong> Store this information in a safe place. It is required to recover your wallet if you lose access.</p>
        <p>Best regards,<br>Cryptonel Wallet Team</p>
    </div>
    """

    # Construct the email
    msg = EmailMessage()
    msg["From"] = f"Cryptonel Wallet <{from_addr}>"
    msg["To"] = email
    msg["Subject"] = "Cryptonel Wallet - Your Wallet Details"
    msg.set_content("This is an HTML email. Please use an HTML-compatible client to view it.")
    msg.add_alternative(html_body, subtype='html')

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
        logger.info(f"Wallet details email sent to {email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send wallet details email: {e}")
        return False

# ----- API Routes -----

@signup_bp.route('/api/signup/check-username', methods=['POST'])
def check_username():
    """
    Check if a username is valid and available
    """
    data = request.get_json()
    username = data.get('username', '').strip()
    
    # Get Discord user ID from session
    discord_user_id = session.get('user_id')
    if not discord_user_id:
        return jsonify({
            "error": "Not authenticated",
            "redirect": "/dashboardselect"
        }), 401
    
    # Check for rate limiting
    is_rate_limited, seconds_remaining, failures_count = check_signup_abuse_rate_limit(discord_user_id)
    if is_rate_limited:
        # Format time remaining
        minutes = seconds_remaining // 60
        seconds = seconds_remaining % 60
        time_format = f"{minutes}m {seconds}s" if minutes > 0 else f"{seconds}s"
        
        return jsonify({
            "error": "Rate limit exceeded",
            "valid": False,
            "message": f"Too many failed attempts. Please wait {time_format} before trying again.",
            "rate_limited": True,
            "seconds_remaining": seconds_remaining
        }), 429
    
    is_valid, message = is_valid_username(username)
    
    # Track errors in rate limit system
    if not is_valid:
        update_signup_abuse_rate_limit(discord_user_id, is_error=True)
    else:
        # Reset error counter on success
        update_signup_abuse_rate_limit(discord_user_id, is_error=False)
    
    return jsonify({
        "valid": is_valid,
        "message": message
    })

@signup_bp.route('/api/signup/check-email', methods=['POST'])
def check_email():
    """
    Check if an email is valid and available
    """
    data = request.get_json()
    email = data.get('email', '').strip().lower()
    
    # Get Discord user ID from session
    discord_user_id = session.get('user_id')
    if not discord_user_id:
        return jsonify({
            "error": "Not authenticated",
            "redirect": "/dashboardselect"
        }), 401
    
    # Check for rate limiting
    is_rate_limited, seconds_remaining, failures_count = check_signup_abuse_rate_limit(discord_user_id)
    if is_rate_limited:
        # Format time remaining
        minutes = seconds_remaining // 60
        seconds = seconds_remaining % 60
        time_format = f"{minutes}m {seconds}s" if minutes > 0 else f"{seconds}s"
        
        return jsonify({
            "error": "Rate limit exceeded",
            "valid": False,
            "message": f"Too many failed attempts. Please wait {time_format} before trying again.",
            "rate_limited": True,
            "seconds_remaining": seconds_remaining
        }), 429
    
    is_valid, message = is_valid_email(email)
    
    # Track errors in rate limit system
    if not is_valid:
        update_signup_abuse_rate_limit(discord_user_id, is_error=True)
    else:
        # Reset error counter on success
        update_signup_abuse_rate_limit(discord_user_id, is_error=False)
    
    return jsonify({
        "valid": is_valid,
        "message": message
    })

@signup_bp.route('/api/signup/check-dob', methods=['POST'])
def check_dob():
    """
    Check if a date of birth is valid
    """
    data = request.get_json()
    dob = data.get('dob', '').strip()
    
    # Get Discord user ID from session
    discord_user_id = session.get('user_id')
    if not discord_user_id:
        return jsonify({
            "error": "Not authenticated",
            "redirect": "/dashboardselect"
        }), 401
    
    # Check for rate limiting
    is_rate_limited, seconds_remaining, failures_count = check_signup_abuse_rate_limit(discord_user_id)
    if is_rate_limited:
        # Format time remaining
        minutes = seconds_remaining // 60
        seconds = seconds_remaining % 60
        time_format = f"{minutes}m {seconds}s" if minutes > 0 else f"{seconds}s"
        
        return jsonify({
            "error": "Rate limit exceeded",
            "valid": False,
            "message": f"Too many failed attempts. Please wait {time_format} before trying again.",
            "rate_limited": True,
            "seconds_remaining": seconds_remaining
        }), 429
    
    is_valid, message = is_valid_date_of_birth(dob)
    
    # Track errors in rate limit system
    if not is_valid:
        update_signup_abuse_rate_limit(discord_user_id, is_error=True)
    else:
        # Reset error counter on success
        update_signup_abuse_rate_limit(discord_user_id, is_error=False)
    
    return jsonify({
        "valid": is_valid,
        "message": message
    })

@signup_bp.route('/api/signup/send-otp', methods=['POST'])
def send_otp():
    """
    Send OTP verification to email
    """
    data = request.get_json()
    email = data.get('email', '').strip().lower()
    discord_user_id = session.get('user_id')
    
    # Add debug information
    logger.info(f"Sending OTP to email: {email}")
    
    if not discord_user_id:
        return jsonify({
            "error": "You must authenticate with Discord first",
            "redirect": "/dashboardselect"
        }), 401
    
    # Check rate limit for sending OTP
    is_rate_limited, seconds_remaining = check_otp_send_rate_limit(discord_user_id)
    if is_rate_limited:
        # Format the time remaining
        minutes = seconds_remaining // 60
        seconds = seconds_remaining % 60
        time_format = f"{minutes}m {seconds}s" if minutes > 0 else f"{seconds}s"
        
        return jsonify({
            "error": "Rate limit exceeded",
            "message": f"Please wait {time_format} before requesting another verification code",
            "seconds_remaining": seconds_remaining
        }), 429
    
    # Generate OTP
    otp = generate_otp()
    
    # Store OTP in user session with expiry time
    session['otp'] = otp
    session['otp_email'] = email
    session['otp_expiry'] = (datetime.now() + timedelta(minutes=5)).timestamp()
    
    # Update rate limit
    update_otp_send_rate_limit(discord_user_id)
    
    # Send OTP to email
    if send_email_verification(email, otp):
        return jsonify({
            "success": True,
            "message": "Verification code sent to your email"
        })
    else:
        return jsonify({
            "error": "Failed to send verification email",
            "message": "Please try again later"
        }), 500

@signup_bp.route('/api/signup/verify-otp', methods=['POST'])
def verify_otp():
    """
    Verify OTP entered by user
    """
    data = request.get_json()
    email = data.get('email', '').strip().lower()
    otp = data.get('otp', '').strip()
    discord_user_id = session.get('user_id')
    
    if not discord_user_id:
        return jsonify({
            "error": "You must authenticate with Discord first",
            "redirect": "/dashboardselect"
        }), 401
    
    # Check rate limit for OTP verification
    is_rate_limited, attempts_remaining, reset_time = check_otp_verify_rate_limit(discord_user_id)
    if is_rate_limited:
        return jsonify({
            "valid": False,
            "message": f"Too many incorrect attempts. You are locked out for {reset_time} seconds (15-minute cooldown).",
            "seconds_remaining": reset_time
        }), 429
    
    # Check if OTP exists in session
    session_otp = session.get('otp')
    session_email = session.get('otp_email')
    expiry_time = session.get('otp_expiry')
    
    if not session_otp or not session_email or not expiry_time:
        update_otp_verify_rate_limit(discord_user_id, False)
        return jsonify({
            "valid": False,
            "message": "Verification failed. Please request a new code.",
            "attempts_remaining": attempts_remaining
        })
    
    # Check if OTP is for the same email
    if session_email != email:
        update_otp_verify_rate_limit(discord_user_id, False)
        return jsonify({
            "valid": False,
            "message": "Email mismatch. Please request a new code.",
            "attempts_remaining": attempts_remaining
        })
    
    # Check if OTP is expired
    now = datetime.now().timestamp()
    if now > expiry_time:
        update_otp_verify_rate_limit(discord_user_id, False)
        return jsonify({
            "valid": False,
            "message": "Verification code has expired. Please request a new code.",
            "attempts_remaining": attempts_remaining
        })
    
    # Check if OTP matches
    if session_otp != otp:
        update_otp_verify_rate_limit(discord_user_id, False)
        return jsonify({
            "valid": False,
            "message": f"Invalid verification code. You have {attempts_remaining} attempts remaining before a 15-minute lockout.",
            "attempts_remaining": attempts_remaining
        })
    
    # OTP is valid - update rate limit as successful validation
    update_otp_verify_rate_limit(discord_user_id, True)
    
    # Clear OTP data from session to prevent reuse
    session.pop('otp', None)
    session.pop('otp_email', None)
    session.pop('otp_expiry', None)
    
    # Mark email as verified in session
    session['email_verified'] = True
    session['verified_email'] = email
    
    return jsonify({
        "valid": True,
        "message": "Email verification successful"
    })

@signup_bp.route('/api/signup', methods=['POST'])
def signup():
    """
    Handle user registration
    """
    data = request.get_json()
    
    # Get Discord user_id from session
    discord_user_id = session.get('user_id')
    discord_authenticated = session.get('discord_authenticated', False)
    
    if not discord_user_id or not discord_authenticated:
        return jsonify({
            "error": "You must authenticate with Discord first",
            "redirect": "/dashboardselect"
        }), 401
    
    # Double-check that user doesn't already have a wallet
    existing_wallet = has_existing_wallet(discord_user_id)
    if existing_wallet:
        return jsonify({
            "error": "Wallet already exists",
            "message": "You already have a Cryptonel wallet. Redirecting to dashboard.",
            "redirect": "/dashboard"
        }), 400
    
    # Check for rate limiting
    is_rate_limited, seconds_remaining, failures_count = check_signup_abuse_rate_limit(discord_user_id)
    if is_rate_limited:
        # Format time remaining
        minutes = seconds_remaining // 60
        seconds = seconds_remaining % 60
        time_format = f"{minutes}m {seconds}s" if minutes > 0 else f"{seconds}s"
        
        return jsonify({
            "error": "Rate limit exceeded",
            "message": f"Too many failed attempts. Please wait {time_format} before trying again.",
            "rate_limited": True,
            "seconds_remaining": seconds_remaining
        }), 429
    
    # Get user info from request
    username = data.get('username', '').strip()
    email = data.get('email', '').strip().lower()
    dob = data.get('dob', '').strip()
    secret_word = data.get('secretWord', '').strip()
    password = data.get('password', '').strip()
    confirm_password = data.get('confirmPassword', '').strip()
    
    # Validate inputs
    validation_errors = {}
    
    # Username validation
    is_valid_user, username_message = is_valid_username(username)
    if not is_valid_user:
        validation_errors["username"] = username_message
    
    # Email validation
    is_valid_mail, email_message = is_valid_email(email)
    if not is_valid_mail:
        validation_errors["email"] = email_message
    
    # Date of birth validation
    is_valid_birth, dob_message = is_valid_date_of_birth(dob)
    if not is_valid_birth:
        validation_errors["dob"] = dob_message
    
    # Secret word validation
    is_valid_secret, secret_message = is_valid_secret_word(secret_word)
    if not is_valid_secret:
        validation_errors["secretWord"] = secret_message
    
    # Password validation
    is_valid_pwd, password_message = is_valid_password(password)
    if not is_valid_pwd:
        validation_errors["password"] = password_message
    
    # Password match validation
    is_match, match_message = is_password_match(password, confirm_password)
    if not is_match:
        validation_errors["confirmPassword"] = match_message
    
    # Return validation errors if any
    if validation_errors:
        # Increment error counter for rate limiting
        update_signup_abuse_rate_limit(discord_user_id, is_error=True)
        
        return jsonify({
            "error": "Validation failed",
            "validation_errors": validation_errors
        }), 400
    
    # Verify OTP - use session data
    email_verified = session.get('email_verified', False)
    if not email_verified:
        # If email_verified flag is not set, the user needs to go through the OTP verification
        # Increment error counter for rate limiting
        update_signup_abuse_rate_limit(discord_user_id, is_error=True)
        
        return jsonify({
            "error": "Email verification required",
            "message": "Please verify your email first"
        }), 400
    
    # Check if email in session matches the submitted email
    verified_email = session.get('verified_email')
    if verified_email != email:
        # If verified email doesn't match the submitted one
        # Increment error counter for rate limiting
        update_signup_abuse_rate_limit(discord_user_id, is_error=True)
        
        return jsonify({
            "error": "Email mismatch",
            "message": "The verified email doesn't match the submitted email"
        }), 400
    
    # Generate wallet details
    mnemonic_phrase = generate_mnemonic_phrase()
    backup_code = generate_backup_code()
    private_address, public_address = generate_wallet_addresses()
    wallet_id = generate_wallet_id()
    
    # Create timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Get Discord user info
    discord_user = discord_users_collection.find_one({"user_id": discord_user_id})
    
    # Store password as plaintext (as requested)
    # Do not hash the password as requested
    
    # Create user document
    user_doc = {
        "user_id": discord_user_id,
        "username": username,
        "password": password,  # Plain text password as requested
        "dob": dob,
        "email": email,
        "avatar": discord_user.get("avatar") if discord_user else None,
        "secret_word": secret_word,
        "balance": "0.0000000000",
        "created_at": timestamp,
        "backup_code": backup_code,
        "private_address": private_address,
        "public_address": public_address,
        "mnemonic_phrase": mnemonic_phrase,
        "wallet_id": wallet_id,
        "2fa_secret": None,  # Changed to None as requested
        "2fa_activated": False,
        "ban": False,
        "verified": False,
        "staff": False,
        "account_type": "Cryptonel Client",
        "membership": "Standard",
        "premium": False,
        "wallet_lock": False,
        "wallet_limit": None,
        "frozen": False,
        "profile_hidden": False,
        "last_login": timestamp
    }
    
    # Insert user into database
    try:
        users_collection.insert_one(user_doc)
        
        # Set session data
        session['wallet_authenticated'] = True
        
        # Create tokens
        tokens = create_tokens(
            user_id=discord_user_id,
            username=username,
            premium=False
        )
        
        # Reset error counter on success
        update_signup_abuse_rate_limit(discord_user_id, is_error=False)
        
        # Send wallet details to email
        if send_wallet_details_email(email, username, mnemonic_phrase, backup_code):
            # Success - wallet details emailed
            return jsonify({
                "success": True,
                "message": "Registration completed successfully. Your wallet details have been sent to your email.",
                "redirect": "/dashboard",
                "tokens": tokens
            })
        else:
            # Email sending failed but account created
            return jsonify({
                "success": True,
                "message": "Registration completed but there was a problem sending your wallet details. Please contact support.",
                "redirect": "/dashboard",
                "tokens": tokens
            })
    except Exception as e:
        # Increment error counter for rate limiting
        update_signup_abuse_rate_limit(discord_user_id, is_error=True)
        
        logger.error(f"Error creating user: {e}")
        return jsonify({
            "error": "Registration failed",
            "message": "There was a problem creating your account. Please try again."
        }), 500

# Add signup abuse rate limit check function
def check_signup_abuse_rate_limit(user_id):
    """
    Check if a user has exceeded their rate limit for failing signup form validation.
    After too many failed validation attempts in a short time, the user will be rate limited.
    Returns a tuple (is_rate_limited, seconds_remaining, failures_count)
    """
    current_time = time.time()
    
    # Get user's rate limits record
    user_rate_limits = rate_limits_collection.find_one({"user_id": user_id})
    
    # Initialize if not exists
    if not user_rate_limits:
        return False, 0, 0
    
    # Find the signup abuse limit in the array
    signup_limit = None
    if "rate_limits" in user_rate_limits:
        for limit in user_rate_limits["rate_limits"]:
            if limit.get("limit_type") == "signup_abuse":
                signup_limit = limit
                break
    
    # If no signup limit exists
    if not signup_limit:
        return False, 0, 0
    
    # Check if user is currently blocked
    blocked_until = signup_limit.get('blocked_until', 0)
    if blocked_until > current_time:
        # User is rate limited
        seconds_remaining = int(blocked_until - current_time)
        failures_count = signup_limit.get('count', 0)
        return True, seconds_remaining, failures_count
    
    # Reset error count after 15 minutes of no errors
    last_failure = signup_limit.get('last_failure', 0)
    if current_time - last_failure > 900:  # 15 minutes in seconds
        # Reset error count in DB
        rate_limits_collection.update_one(
            {"user_id": user_id, "rate_limits.limit_type": "signup_abuse"},
            {"$set": {"rate_limits.$.count": 0, "rate_limits.$.last_failure": current_time}}
        )
        return False, 0, 0
    
    # User is not blocked, return error count
    failures_count = signup_limit.get('count', 0)
    return False, 0, failures_count

# Update signup abuse rate limit tracking
def update_signup_abuse_rate_limit(user_id, is_error=True):
    """
    Update rate limit tracking for signup form validation.
    If a user has too many errors in a short time, they will be temporarily blocked.
    """
    current_time = time.time()
    
    # Get user's rate limits record
    user_rate_limits = rate_limits_collection.find_one({"user_id": user_id})
    
    # Initialize if not exists
    if not user_rate_limits:
        user_rate_limits = {
            "user_id": user_id,
            "rate_limits": []
        }
        rate_limits_collection.insert_one(user_rate_limits)
    
    # Find the signup abuse limit in the array
    signup_limit = None
    has_limit = False
    if "rate_limits" in user_rate_limits:
        for limit in user_rate_limits["rate_limits"]:
            if limit.get("limit_type") == "signup_abuse":
                signup_limit = limit
                has_limit = True
                break
    
    # If this is a successful validation, reset counter
    if not is_error:
        if has_limit:
            # Reset count but keep track of last access
            rate_limits_collection.update_one(
                {"user_id": user_id, "rate_limits.limit_type": "signup_abuse"},
                {"$set": {"rate_limits.$.count": 0, "rate_limits.$.last_failure": current_time}}
            )
        return
    
    # Get current count
    count = 0
    if signup_limit:
        count = signup_limit.get('count', 0)
    
    # Increment error counter
    new_count = count + 1
    new_blocked_until = 0
    
    # Rate limiting tiers:
    # 5 errors: block for 1 minute
    # 10 errors: block for 5 minutes
    # 15+ errors: block for 15 minutes
    if new_count >= 15:
        new_blocked_until = current_time + 900  # 15 minutes
    elif new_count >= 10:
        new_blocked_until = current_time + 300  # 5 minutes
    elif new_count >= 5:
        new_blocked_until = current_time + 60   # 1 minute
    
    if has_limit:
        # Update existing limit
        rate_limits_collection.update_one(
            {"user_id": user_id, "rate_limits.limit_type": "signup_abuse"},
            {"$set": {
                "rate_limits.$.count": new_count,
                "rate_limits.$.last_failure": current_time,
                "rate_limits.$.blocked_until": new_blocked_until
            }}
        )
    else:
        # Add new limit to array
        rate_limits_collection.update_one(
            {"user_id": user_id},
            {"$push": {"rate_limits": {
                "limit_type": "signup_abuse",
                "count": new_count,
                "last_failure": current_time,
                "blocked_until": new_blocked_until
            }}}
        )

# Add function to check if user already has a wallet
def has_existing_wallet(user_id):
    """
    Check if user already has a wallet based on Discord ID
    """
    user = users_collection.find_one({"user_id": user_id})
    return user is not None

@signup_bp.route('/api/signup/check-existing-wallet', methods=['GET'])
def check_existing_wallet():
    """
    Check if the authenticated user already has a wallet
    """
    # Get Discord user_id from session
    discord_user_id = session.get('user_id')
    
    if not discord_user_id:
        return jsonify({
            "error": "Not authenticated",
            "authenticated": False,
            "redirect": "/dashboardselect"
        }), 401
    
    # Check if user already has a wallet
    existing_wallet = has_existing_wallet(discord_user_id)
    
    if existing_wallet:
        return jsonify({
            "has_wallet": True,
            "message": "You already have a wallet. Redirecting to dashboard.",
            "redirect": "/dashboard"
        })
    
    return jsonify({
        "has_wallet": False
    })

def init_app(app):
    """
    Initialize signup Blueprint in the Flask app
    """
    app.register_blueprint(signup_bp)
    
    # Create indexes
    create_indexes()
    
    logger.info("Signup module initialized") 