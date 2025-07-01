import os
import json
import csv
import io
import time
import functools
import random
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request, session, send_file, make_response, current_app
from pymongo import MongoClient, ASCENDING, DESCENDING
from dotenv import load_dotenv
from bson import ObjectId, json_util
import pytz

# Load environment variables
load_dotenv()

# Create Blueprint for Backup endpoints
backup_bp = Blueprint('backup', __name__)

# MongoDB connection
MONGODB_URI = os.getenv("DATABASE_URL")
client = MongoClient(MONGODB_URI)
db = client["cryptonel_wallet"]
users_collection = db["users"]
rate_limits_collection = db["rate_limits"]  # Separate collection for rate limits

# Rate limit constants
MAX_BACKUP_CODE_ATTEMPTS = 5  # Maximum number of failed attempts
BACKUP_CODE_BLOCK_DURATION = 60  # Block duration in seconds (1 minute)
BACKUP_COOLDOWN_HOURS = 336  # Hours between allowed backups (14 days)

# Limit types
BACKUP_CODE_LIMIT_TYPE = "backup_code_verification"
BACKUP_COOLDOWN_LIMIT_TYPE = "backup_cooldown"

# Field name mapping - Convert DB field names to more formal/readable names
FIELD_NAME_MAPPING = {
    "user_id": "User ID",
    "username": "Username",
    "dob": "Date of Birth",
    "email": "Email Address",
    "balance": "Wallet Balance",
    "created_at": "Account Created Date",
    "last_login": "Last Login Date",
    "backup_code": "Backup Recovery Code",
    "private_address": "Private Wallet Address",
    "public_address": "Public Wallet Address",
    "wallet_id": "Wallet ID",
    "password": "Account Password",
    "secret_word": "Secret Recovery Word",
    "mnemonic_phrase": "Mnemonic Recovery Phrase",
    "account_type": "Account Type",
    "membership": "Membership Status",
    "premium": "Premium Status",
    "wallet_limit": "Wallet Transfer Limit",
    "transfer_password": "Transfer Password",
    "2fa_secret": "2FA Secret Key"
}

# Cache for user data (simple in-memory cache with TTL 60 seconds)
user_data_cache = {}
USER_CACHE_TTL = 60  # seconds

# Create MongoDB indexes on startup
def create_indexes():
    """Create indexes for frequently queried fields if they don't exist"""
    try:
        # Check existing indexes first
        existing_indexes = list(users_collection.list_indexes())
        existing_index_names = [idx.get('name') for idx in existing_indexes]
        
        # Check if ANY user_id index exists before creating one
        has_user_id_index = any('user_id' in idx_name for idx_name in existing_index_names)
        
        # Create user_id index only if NO user_id index exists at all
        if not has_user_id_index:
            users_collection.create_index([("user_id", ASCENDING)], name="backup_user_id_index", background=True)
            print("Created user_id index for backup module")
        else:
            print("User ID index already exists, skipping creation")
        
        # Check rate_limits collection indexes
        existing_rate_indexes = list(rate_limits_collection.list_indexes())
        existing_rate_index_names = [idx.get('name') for idx in existing_rate_indexes]
        
        # Check if ANY user_id index exists in rate_limits collection
        has_rate_user_id_index = any('user_id' in idx_name for idx_name in existing_rate_index_names)
        
        # Create indexes only if they don't exist
        if not has_rate_user_id_index:
            rate_limits_collection.create_index([("user_id", ASCENDING)], name="backup_rate_user_id_index", background=True)
            print("Created user_id index for rate_limits collection")
        else:
            print("Rate limits user_id index already exists, skipping creation")
        
        # Check for compound index with more specific name matching
        has_compound_index = any('user_id' in idx_name and 'rate_limits.limit_type' in idx_name for idx_name in existing_rate_index_names)
        
        if not has_compound_index:
            rate_limits_collection.create_index(
                [("user_id", ASCENDING), ("rate_limits.limit_type", ASCENDING)], 
                name="backup_rate_limits_compound_index",
                background=True
            )
            print("Created compound index for rate_limits collection")
        else:
            print("Rate limits compound index already exists, skipping creation")
        
        print("MongoDB indexes checked for backup module")
    except Exception as e:
        print(f"Warning: Error checking/creating MongoDB indexes: {e}")
        # Continue even if index creation fails - they might already exist

# Helper functions
def get_user_data(user_id, fields=None):
    """
    Fetch user data from MongoDB by user_id with optional field projection
    Uses caching to reduce database load
    """
    # Check cache first
    cache_key = f"user_{user_id}"
    current_time = time.time()
    
    if cache_key in user_data_cache:
        cached_data, cache_time = user_data_cache[cache_key]
        # If cache is still valid
        if current_time - cache_time < USER_CACHE_TTL:
            # If no specific fields requested or if we have all fields cached
            if not fields or all(field in cached_data for field in fields):
                return cached_data
    
    # Prepare projection if needed
    projection = None
    if fields:
        projection = {field: 1 for field in fields}
        # Always include _id
        projection["_id"] = 1
    
    # Query database with optional projection
    user = users_collection.find_one({"user_id": user_id}, projection)
    if not user:
        return None
    
    # Convert ObjectId to string
    if '_id' in user:
        user['_id'] = str(user['_id'])
    
    # Update cache (store complete user object)
    user_data_cache[cache_key] = (user, current_time)
    
    return user

def validate_backup_code(user_id, backup_code):
    """
    Centralized function to validate backup code
    Returns tuple (is_valid, user_data, error_message, remaining_attempts)
    """
    if not backup_code:
        return (False, None, "Backup code is required", None)
    
    # Check if user is rate limited for backup code attempts
    code_limit = check_rate_limit(user_id, BACKUP_CODE_LIMIT_TYPE)
    if code_limit["limited"]:
        return (False, None, code_limit["message"], 0)
    
    # Get user data with all fields - don't optimize here
    user_data = get_user_data(user_id)
    if not user_data:
        return (False, None, "User not found", None)
    
    # Verify backup code using constant-time comparison to prevent timing attacks
    if not constant_time_compare(user_data.get('backup_code', ''), backup_code):
        # Update rate limit for failed attempt
        update_rate_limit_info(user_id, BACKUP_CODE_LIMIT_TYPE, failed=True)
        limit_info = get_rate_limit_info(user_id, BACKUP_CODE_LIMIT_TYPE)
        remaining_attempts = MAX_BACKUP_CODE_ATTEMPTS - (limit_info.get("count", 0) if limit_info else 0)
        
        return (False, None, f"Invalid backup code. {remaining_attempts} attempts remaining before timeout.", remaining_attempts)
    
    # Reset the backup code rate limit counter on success
    update_rate_limit_info(user_id, BACKUP_CODE_LIMIT_TYPE, reset=True)
    
    # We already have complete user data, no need to fetch again
    return (True, user_data, None, None)

def constant_time_compare(val1, val2):
    """
    Performs constant-time comparison to prevent timing attacks
    """
    if val1 is None or val2 is None:
        return False
    
    return len(val1) == len(val2) and all(a == b for a, b in zip(val1, val2))

# Memoize function for rate limit checks with short TTL (1 second)
@functools.lru_cache(maxsize=128, typed=False)
def get_rate_limit_info_cached(user_id, limit_type, timestamp):
    """Cached version of get_rate_limit_info with timestamp to control TTL"""
    return get_rate_limit_info(user_id, limit_type)

def get_rate_limit_info(user_id, limit_type):
    """Get rate limit information for a user"""
    # Get user's rate limits record with projection to only get necessary fields
    user_rate_limits = rate_limits_collection.find_one(
        {"user_id": user_id},
        {"rate_limits": 1}
    )
    
    # Initialize if not exists
    if not user_rate_limits:
        current_time = time.time()
        user_rate_limits = {
            "user_id": user_id,
            "rate_limits": []
        }
        rate_limits_collection.insert_one(user_rate_limits)
        return None
    
    # Find the limit in the array
    limit_info = None
    if "rate_limits" in user_rate_limits:
        for limit in user_rate_limits["rate_limits"]:
            if limit.get("limit_type") == limit_type:
                limit_info = limit
                break
    
    return limit_info

def update_rate_limit_info(user_id, limit_type, failed=False, reset=False):
    """Update rate limit information for a user"""
    current_time = time.time()
    
    # Check if the rate limit already exists to optimize update
    limit_info = get_rate_limit_info(user_id, limit_type)
    has_limit = limit_info is not None
    
    # Determine the update operation based on the scenario
    if limit_type == BACKUP_COOLDOWN_LIMIT_TYPE:
        # Special handling for backup cooldown
        if has_limit:
            if reset:
                # Reset the cooldown with a single atomic update
                rate_limits_collection.update_one(
                    {"user_id": user_id, "rate_limits.limit_type": limit_type},
                    {"$set": {"rate_limits.$.last_transfer": 0}}
                )
            else:
                # Set cooldown with a single atomic update
                rate_limits_collection.update_one(
                    {"user_id": user_id, "rate_limits.limit_type": limit_type},
                    {"$set": {"rate_limits.$.last_transfer": current_time}}
                )
        else:
            # Add new limit in a single operation
            rate_limits_collection.update_one(
                {"user_id": user_id},
                {"$push": {"rate_limits": {
                    "limit_type": limit_type,
                    "last_transfer": current_time
                }}},
                upsert=True  # Create if not exists
            )
    else:
        # Standard handling for code verification limits
        if has_limit:
            if reset:
                # Reset counter in a single atomic update
                rate_limits_collection.update_one(
                    {"user_id": user_id, "rate_limits.limit_type": limit_type},
                    {"$set": {
                        "rate_limits.$.count": 0,
                        "rate_limits.$.blocked_until": 0,
                        "rate_limits.$.last_attempt": current_time
                    }}
                )
            elif failed:
                # Get current count from the limit_info we already have
                current_count = limit_info.get("count", 0)
                
                # Increment counter
                new_count = current_count + 1
                new_blocked_until = 0
                
                # If max attempts reached, block for specified duration
                if new_count >= MAX_BACKUP_CODE_ATTEMPTS:
                    new_blocked_until = current_time + BACKUP_CODE_BLOCK_DURATION
                
                # Update in a single atomic operation
                rate_limits_collection.update_one(
                    {"user_id": user_id, "rate_limits.limit_type": limit_type},
                    {"$set": {
                        "rate_limits.$.count": new_count,
                        "rate_limits.$.last_attempt": current_time,
                        "rate_limits.$.blocked_until": new_blocked_until
                    }}
                )
            else:
                # Update timestamp only
                rate_limits_collection.update_one(
                    {"user_id": user_id, "rate_limits.limit_type": limit_type},
                    {"$set": {"rate_limits.$.last_attempt": current_time}}
                )
        else:
            # Add new limit in a single operation
            rate_limits_collection.update_one(
                {"user_id": user_id},
                {"$push": {"rate_limits": {
                    "limit_type": limit_type,
                    "count": 1 if failed else 0,
                    "last_attempt": current_time,
                    "blocked_until": 0
                }}},
                upsert=True  # Create if not exists
            )
            
    # Clear the cached value after updating
    cache_key = f"ratelimit_info_{user_id}_{limit_type}"
    if cache_key in user_data_cache:
        del user_data_cache[cache_key]

def check_rate_limit(user_id, limit_type):
    """Check if a user is rate limited with caching for performance"""
    # Use cached version with current timestamp rounded to seconds
    # This limits cache invalidation to once per second max
    timestamp = int(time.time())
    limit_info = get_rate_limit_info_cached(user_id, limit_type, timestamp)
    
    if not limit_info:
        return {"limited": False}
    
    current_time = time.time()
    
    if limit_type == BACKUP_COOLDOWN_LIMIT_TYPE:
        # Check user's actual last backup timestamp from users collection first
        user_data = get_user_data(user_id, fields=["last_backup"])
        
        # If there's a last_backup timestamp in user data, use that for validation
        if user_data and user_data.get("last_backup"):
            try:
                # Parse the last backup timestamp
                last_backup_date = datetime.strptime(user_data["last_backup"], "%Y-%m-%d %H:%M:%S")
                
                # Convert to UTC timestamp for comparison
                last_backup_timestamp = datetime.timestamp(last_backup_date)
                current_timestamp = datetime.timestamp(datetime.now())
                
                # Check if the cooldown period has already passed
                seconds_since_backup = current_timestamp - last_backup_timestamp
                cooldown_seconds = BACKUP_COOLDOWN_HOURS * 3600  # Convert hours to seconds
                
                # Print debug information
                print(f"DEBUG: Last backup: {user_data['last_backup']}")
                print(f"DEBUG: Seconds since backup: {seconds_since_backup}")
                print(f"DEBUG: Cooldown seconds: {cooldown_seconds}")
                print(f"DEBUG: Passed cooldown: {seconds_since_backup >= cooldown_seconds}")
                
                # If the backup is older than the cooldown period, allow creating a new one
                if seconds_since_backup >= cooldown_seconds:
                    # Reset the cooldown in rate_limits to fix inconsistency
                    update_rate_limit_info(user_id, BACKUP_COOLDOWN_LIMIT_TYPE, reset=True)
                    return {"limited": False}
            except Exception as e:
                print(f"Error parsing last_backup date: {e}")
                # Continue to check rate_limits as fallback
        
        # Special case for backup cooldown with different structure
        last_transfer = limit_info.get("last_transfer", 0)
        cooldown_end = last_transfer + (BACKUP_COOLDOWN_HOURS * 3600)
        
        if cooldown_end > current_time and last_transfer > 0:
            time_remaining = int(cooldown_end - current_time)
            
            # Format time as days, hours, minutes, seconds
            days = time_remaining // 86400
            hours = (time_remaining % 86400) // 3600
            minutes = (time_remaining % 3600) // 60
            seconds = time_remaining % 60
            
            formatted_time = f"{days}d {hours:02d}h {minutes:02d}m {seconds:02d}s"
            
            return {
                "limited": True,
                "reason": "backup_cooldown",
                "message": f"You can only create one backup every {BACKUP_COOLDOWN_HOURS // 24} days",
                "time_remaining": time_remaining,
                "formatted_time": formatted_time
            }
    else:
        # Standard structure for verification attempts
        blocked_until = limit_info.get("blocked_until", 0)
        if blocked_until > current_time:
            time_remaining = int(blocked_until - current_time)
            
            # Format time as minutes and seconds
            minutes = time_remaining // 60
            seconds = time_remaining % 60
            formatted_time = f"{minutes}m {seconds}s"
            
            return {
                "limited": True,
                "reason": "too_many_attempts",
                "message": f"Too many failed attempts. Please try again in {formatted_time}.",
                "time_remaining": time_remaining,
                "formatted_time": formatted_time
            }
    
    return {"limited": False}

def update_last_backup_timestamp(user_id):
    """Update the last_backup timestamp in the user's data and set cooldown"""
    now = datetime.now(pytz.UTC)
    formatted_time = now.strftime("%Y-%m-%d %H:%M:%S")
    current_time = time.time()
    
    # Update the last_backup field in users collection
    users_collection.update_one(
        {"user_id": user_id},
        {"$set": {"last_backup": formatted_time}}
    )
    
    # Update the rate limit for backup cooldown in a single operation
    # First check if it exists to choose the right operation
    has_limit = get_rate_limit_info(user_id, BACKUP_COOLDOWN_LIMIT_TYPE) is not None
    
    if has_limit:
        # Update existing cooldown
        rate_limits_collection.update_one(
            {"user_id": user_id, "rate_limits.limit_type": BACKUP_COOLDOWN_LIMIT_TYPE},
            {"$set": {"rate_limits.$.last_transfer": current_time}}
        )
    else:
        # Add new cooldown with upsert
        rate_limits_collection.update_one(
            {"user_id": user_id},
            {"$push": {"rate_limits": {
                "limit_type": BACKUP_COOLDOWN_LIMIT_TYPE,
                "last_transfer": current_time
            }}},
            upsert=True
        )
    
    # Clear user from cache to ensure fresh data
    cache_key = f"user_{user_id}"
    if cache_key in user_data_cache:
        del user_data_cache[cache_key]
    
    return formatted_time

def generate_backup_data(user_data, backup_code, include_wallet=True):
    """Generate backup data with no encryption and only specific fields"""
    try:
        if not user_data:
            print("Error: user_data is None in generate_backup_data")
            return None
            
        backup_data = {}
        
        # Always add some default values for critical fields
        default_values = {
            "user_id": user_data.get("user_id", "Unknown"),
            "username": user_data.get("username", "Unknown User"),
            "email": user_data.get("email", "No Email Provided"),
            "balance": user_data.get("balance", "0.00"),
            "created_at": user_data.get("created_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            "wallet_id": user_data.get("wallet_id", "Not Available"),
        }
        
        # Include only these specific fields, no encryption
        specific_fields = [
            "user_id", "username", "dob", "email", 
            "balance", "created_at", "private_address", 
            "public_address", "mnemonic_phrase", "wallet_id",
            "secret_word"
        ]
        
        # Add only the specified fields without encryption
        for field in specific_fields:
            if field in user_data:
                formal_name = FIELD_NAME_MAPPING.get(field, field)
                backup_data[formal_name] = user_data[field]
            elif field in default_values:
                # Use default values for missing critical fields
                formal_name = FIELD_NAME_MAPPING.get(field, field)
                backup_data[formal_name] = default_values[field]
        
        if not backup_data:
            print(f"Warning: No backup data was generated for user. User data keys: {list(user_data.keys())}")
            # If we still have no data, use all the defaults as a last resort
            for field, value in default_values.items():
                formal_name = FIELD_NAME_MAPPING.get(field, field)
                backup_data[formal_name] = value
        
        print(f"Backup data generated successfully with {len(backup_data)} fields")
        return backup_data
    except Exception as e:
        print(f"Error in generate_backup_data: {e}")
        import traceback
        traceback.print_exc()
        
        # As a fallback, provide some generic data rather than failing entirely
        backup_data = {
            "User ID": "Unknown",
            "Username": "Unknown User",
            "Date of Birth": "Not Available",
            "Email Address": "Not Available",
            "Wallet Balance": "0.00",
            "Account Created Date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Note": "Error occurred during backup. This is a fallback backup with placeholder data."
        }
        return backup_data

def generate_csv_backup(user_data, backup_code, include_wallet=True):
    """Generate a CSV backup file"""
    backup_data = generate_backup_data(user_data, backup_code, include_wallet)
    if not backup_data:
        return None
    
    # Create in-memory CSV file - use BytesIO instead of StringIO to fix the error
    csv_buffer = io.BytesIO()
    
    # Create a string buffer for writing
    string_buffer = io.StringIO()
    writer = csv.writer(string_buffer)
    
    # Write header row
    writer.writerow(["Field", "Value"])
    
    # Write data rows
    for field, value in backup_data.items():
        writer.writerow([field, value])
    
    # Get the data as a string
    csv_string = string_buffer.getvalue()
    
    # Write to the binary buffer for sending
    csv_buffer.write(csv_string.encode('utf-8'))
    
    # Reset file pointer to beginning
    csv_buffer.seek(0)
    return csv_buffer

def generate_pdf_backup(user_data, backup_code, include_wallet=True):
    """Generate a PDF backup file without encryption"""
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors
        from io import BytesIO
        
        backup_data = generate_backup_data(user_data, backup_code, include_wallet)
        if not backup_data:
            return None
        
        # Create in-memory PDF file
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        
        # Create document elements
        elements = []
        
        # Add title
        title_style = styles["Heading1"]
        title = Paragraph(f"Cryptonel Wallet Backup - {backup_data.get('Username', 'User')}", title_style)
        elements.append(title)
        elements.append(Spacer(1, 12))
        
        # Add timestamp
        date_style = styles["Normal"]
        date_style.alignment = 1  # Center alignment
        date_text = Paragraph(f"Backup created on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", date_style)
        elements.append(date_text)
        elements.append(Spacer(1, 20))
        
        # Create data table
        data = [["Field", "Value"]]
        for field, value in backup_data.items():
            data.append([field, str(value)])
        
        # Create table and style
        table = Table(data, colWidths=[150, 350])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (1, 0), colors.blue),
            ('TEXTCOLOR', (0, 0), (1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (1, 0), 12),
            ('BACKGROUND', (0, 1), (1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        
        elements.append(table)
        
        # Add security note
        elements.append(Spacer(1, 20))
        note_style = ParagraphStyle('Note', parent=styles['Normal'], textColor=colors.red)
        note = Paragraph("Note: This backup contains sensitive wallet information. Store it securely.", note_style)
        elements.append(note)
        
        # Build PDF
        doc.build(elements)
        buffer.seek(0)
        return buffer
        
    except ImportError:
        # If ReportLab is not available, return None
        print("ReportLab library not installed. PDF generation not available.")
        return None

def generate_txt_backup(user_data, backup_code, include_wallet=True):
    """Generate a TXT backup file with only the specified fields"""
    try:
        backup_data = generate_backup_data(user_data, backup_code, include_wallet)
        if not backup_data:
            print(f"Error: generate_backup_data returned None for user_id: {user_data.get('user_id')}")
            return None
        
        # Create in-memory text file
        txt_buffer = io.BytesIO()
        
        # Create decorative header
        header = "╔══════════════════════════════════════════════════════════╗\n"
        header += "║              CRYPTONEL WALLET BACKUP                    ║\n"
        header += f"║              {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}                   ║\n"
        header += "╚══════════════════════════════════════════════════════════╝\n\n"
        
        # Write header
        txt_buffer.write(header.encode('utf-8'))
        
        # Calculate max field width for nice alignment - add extra safety check
        if not backup_data or len(backup_data.keys()) == 0:
            print("Error: No backup data keys available")
            # Use a default width if no keys available
            max_field_width = 30
        else:
            max_field_width = max(len(field) for field in backup_data.keys()) + 2
        
        # Write data fields directly - no sections, no sensitive data encryption
        for field, value in backup_data.items():
            # Format each line with field name aligned and value
            line = f"{field:<{max_field_width}}: {value}\n"
            txt_buffer.write(line.encode('utf-8'))
            
            # Add separator for better readability
            separator = "─" * 64 + "\n"
            txt_buffer.write(separator.encode('utf-8'))
        
        # Add a footer
        footer = "\n╔══════════════════════════════════════════════════════════╗\n"
        footer += "║            STORE THIS FILE SECURELY                     ║\n"
        footer += "║            END OF BACKUP DOCUMENT                       ║\n"
        footer += "╚══════════════════════════════════════════════════════════╝\n"
        txt_buffer.write(footer.encode('utf-8'))
        
        # Reset file pointer to beginning
        txt_buffer.seek(0)
        return txt_buffer
    except Exception as e:
        print(f"Error generating TXT backup: {e}")
        import traceback
        traceback.print_exc()
        return None

# Routes with secure rate limiting and centralized validation
@backup_bp.route('/api/backup/create', methods=['POST'])
def create_backup():
    """Generate and download a backup file"""
    try:
        # Check if user is authenticated
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({"error": "Not authenticated"}), 401
        
        print(f"Processing backup request for user ID: {user_id}")
        
        # Get post data
        data = request.json
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        backup_code = data.get('backupCode')
        
        # VALIDATE BACKUP CODE - This was missing
        is_valid, user_data, error_message, remaining_attempts = validate_backup_code(user_id, backup_code)
        
        if not is_valid:
            # If it's a rate limit, return 429
            if not remaining_attempts:
                code_limit = check_rate_limit(user_id, BACKUP_CODE_LIMIT_TYPE)
                return jsonify({
                    "error": error_message,
                    "time_remaining": code_limit.get("time_remaining", 60)
                }), 429
            else:
                return jsonify({
                    "error": error_message,
                    "remaining_attempts": remaining_attempts
                }), 400
        
        # Security check passed, now we can continue with user data we got from validation
        print(f"User data retrieved with fields: {list(user_data.keys())}")
        
        # Check if the user is premium - cast to boolean to ensure consistent behavior
        is_premium = bool(user_data.get('premium', False))
        print(f"User {user_id} premium status: {is_premium}, raw value: {user_data.get('premium')}")
        
        # For non-premium users, enforce the 14-day cooldown
        if not is_premium:
            last_backup = user_data.get('last_backup')
            if last_backup:
                try:
                    last_backup_date = datetime.strptime(last_backup, "%Y-%m-%d %H:%M:%S")
                    now = datetime.now()
                    
                    # Calculate time difference
                    delta = now - last_backup_date
                    total_seconds = delta.total_seconds()
                    cooldown_seconds = 14 * 86400  # 14 days in seconds
                    seconds_remaining = cooldown_seconds - total_seconds
                    
                    if seconds_remaining > 0:
                        days_remaining = int(seconds_remaining // 86400)
                        hours = int((seconds_remaining % 86400) // 3600)
                        minutes = int((seconds_remaining % 3600) // 60)
                        seconds = int(seconds_remaining % 60)
                        formatted_time = f"{days_remaining}d {hours:02d}h {minutes:02d}m {seconds:02d}s"
                        
                        # Add no-cache headers to the error response
                        response = jsonify({
                            "error": f"Regular users can only create backups every 14 days. Time remaining: {formatted_time}",
                            "days_remaining": days_remaining,
                            "formatted_time_remaining": formatted_time
                        })
                        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
                        response.headers['Pragma'] = 'no-cache'
                        response.headers['Expires'] = '0'
                        return response, 429
                except Exception as e:
                    print(f"Error checking backup date: {e}")
                    # Continue anyway if there's an error parsing the date
        
        # Create simple backup with only the required fields
        backup_data = {}
        specific_fields = [
            "user_id", "username", "dob", "email", 
            "balance", "created_at", "private_address", 
            "public_address", "mnemonic_phrase", "wallet_id",
            "secret_word"
        ]
        
        # Extract the specified fields
        for field in specific_fields:
            if field in user_data:
                formal_name = FIELD_NAME_MAPPING.get(field, field)
                backup_data[formal_name] = user_data[field]
        
        # Add premium status to backup data
        if is_premium:
            backup_data["Premium Status"] = "PREMIUM USER"
        
        # Create in-memory text file
        txt_buffer = io.BytesIO()
        
        # Create decorative header - different for premium users
        if is_premium:
            header = "╔══════════════════════════════════════════════════════════╗\n"
            header += "║            CRYPTONEL WALLET PREMIUM BACKUP              ║\n"
            header += f"║              {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}                   ║\n"
            header += "╚══════════════════════════════════════════════════════════╝\n\n"
        else:
            header = "╔══════════════════════════════════════════════════════════╗\n"
            header += "║              CRYPTONEL WALLET BACKUP                    ║\n"
            header += f"║              {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}                   ║\n"
            header += "╚══════════════════════════════════════════════════════════╝\n\n"
        
        # Write header
        txt_buffer.write(header.encode('utf-8'))
        
        # Calculate max field width
        max_field_width = max([len(field) for field in backup_data.keys()] or [20]) + 2
        
        # Write data fields
        for field, value in backup_data.items():
            line = f"{field:<{max_field_width}}: {value}\n"
            txt_buffer.write(line.encode('utf-8'))
            separator = "─" * 64 + "\n"
            txt_buffer.write(separator.encode('utf-8'))
        
        # Add a footer - different for premium users
        if is_premium:
            footer = "\n╔══════════════════════════════════════════════════════════╗\n"
            footer += "║            PREMIUM USER BACKUP                          ║\n"
            footer += "║            STORE THIS FILE SECURELY                     ║\n"
            footer += "╚══════════════════════════════════════════════════════════╝\n"
        else:
            footer = "\n╔══════════════════════════════════════════════════════════╗\n"
            footer += "║            STORE THIS FILE SECURELY                     ║\n"
            footer += "║            END OF BACKUP DOCUMENT                       ║\n"
            footer += "╚══════════════════════════════════════════════════════════╝\n"
        
        txt_buffer.write(footer.encode('utf-8'))
        
        # Reset file pointer to beginning
        txt_buffer.seek(0)
        
        # Update last backup timestamp
        now = datetime.now(pytz.UTC)
        formatted_time = now.strftime("%Y-%m-%d %H:%M:%S")
        users_collection.update_one(
            {"user_id": user_id},
            {"$set": {"last_backup": formatted_time}}
        )
        
        # Update rate limit cooldown
        update_rate_limit_info(user_id, BACKUP_COOLDOWN_LIMIT_TYPE)
        
        # Prepare response
        if is_premium:
            filename = f"cryptonel_premium_backup_{datetime.now().strftime('%Y%m%d%H%M%S')}.txt"
        else:
            filename = f"cryptonel_wallet_backup_{datetime.now().strftime('%Y%m%d%H%M%S')}.txt"
        
        # Return the file for download
        backup_file_content = txt_buffer.getvalue()
        response = make_response(backup_file_content)
        response.headers['Content-Type'] = 'text/plain'
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        response.headers['Content-Length'] = str(len(backup_file_content))
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        
        print(f"Backup file prepared successfully for user {user_id} - Premium: {is_premium}")
        return response

    except Exception as e:
        print(f"Error in create_backup: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": "Server error creating backup"}), 500

@backup_bp.route('/api/backup/view', methods=['POST'])
def view_backup():
    """Generate and return backup data for direct display in the UI"""
    # Check if user is authenticated
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Not authenticated"}), 401
    
    # Get post data
    data = request.json
    include_wallet = data.get('includeWallet', True)
    backup_code = data.get('backupCode')
    
    # Use centralized validation function
    is_valid, user_data, error_message, remaining_attempts = validate_backup_code(user_id, backup_code)
    
    if not is_valid:
        # If it's a rate limit, return 429
        if not remaining_attempts:
            code_limit = check_rate_limit(user_id, BACKUP_CODE_LIMIT_TYPE)
            return jsonify({
                "error": error_message,
                "time_remaining": code_limit["time_remaining"]
            }), 429
        else:
            return jsonify({
                "error": error_message,
                "remaining_attempts": remaining_attempts
            }), 400
    
    # Generate backup data
    backup_data = generate_backup_data(user_data, backup_code, include_wallet)
    if not backup_data:
        return jsonify({"error": "Failed to generate backup data"}), 500
    
    # Update last backup timestamp and cooldown
    last_backup = update_last_backup_timestamp(user_id)
    
    # Format the data for display
    formatted_data = []
    for field, value in backup_data.items():
        formatted_data.append({
            "field": field,
            "value": value,
            "isEncrypted": False  # No fields are encrypted
        })
    
    # Return the formatted data
    response_data = {
        "backupData": formatted_data,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "lastBackup": last_backup
    }
    
    # Log the backup view activity
    print(f"Backup created for user {user_id} at {last_backup}")
    
    return jsonify(response_data)

@backup_bp.route('/api/backup/status', methods=['GET'])
def get_backup_status():
    """Get the backup status for the authenticated user"""
    # Check if user is authenticated
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Not authenticated"}), 401
    
    # Force fetch fresh user data from MongoDB (skip cache)
    user_data = users_collection.find_one({"user_id": user_id})
    if not user_data:
        return jsonify({"error": "User not found"}), 404
    
    # Convert ObjectId to string
    if '_id' in user_data:
        user_data['_id'] = str(user_data['_id'])
    
    # Check if the user is premium - explicit cast to boolean to avoid any issues
    is_premium = bool(user_data.get('premium', False))
    
    # Log premium status check for debugging
    print(f"User {user_id} premium status: {is_premium}, raw value: {user_data.get('premium')}")
    
    # Get last backup timestamp
    last_backup = user_data.get('last_backup')
    
    # For premium users, always allow backup creation
    if is_premium:
        backup_status = {
            "status": "premium",
            "lastBackup": last_backup,
            "daysAgo": None,
            "message": "As a premium user, you can create backups anytime",
            "canCreateBackup": True,
            "isPremium": True
        }
        
        # Calculate days ago for information only
        if last_backup:
            try:
                last_backup_date = datetime.strptime(last_backup, "%Y-%m-%d %H:%M:%S")
                now = datetime.now()
                delta = now - last_backup_date
                days_ago = delta.days
                backup_status["daysAgo"] = days_ago
            except Exception as e:
                print(f"Error parsing backup date for premium user: {e}")
        
        # Add cache control headers in the response
        response = jsonify(backup_status)
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        return response
    
    # Non-premium users are subject to the cooldown
    # If no backup has been made, set status to 'never'
    if not last_backup:
        backup_status = {
            "status": "never",
            "lastBackup": None,
            "daysAgo": None,
            "message": "No backup has been created yet",
            "canCreateBackup": True,
            "isPremium": False
        }
    else:
        # Parse the last backup timestamp
        try:
            last_backup_date = datetime.strptime(last_backup, "%Y-%m-%d %H:%M:%S")
            now = datetime.now()
            
            # Calculate time difference
            delta = now - last_backup_date
            total_seconds = delta.total_seconds()
            days_ago = int(total_seconds // 86400)  # Convert to days
            
            # Calculate remaining time until next backup
            cooldown_seconds = 14 * 86400  # 14 days in seconds
            seconds_remaining = cooldown_seconds - total_seconds
            
            # For non-premium users, check if cooldown period has passed
            can_create_backup = seconds_remaining <= 0
            
            if can_create_backup:
                days_remaining = 0
                formatted_time_remaining = None
            else:
                days_remaining = int(seconds_remaining // 86400)
                hours = int((seconds_remaining % 86400) // 3600)
                minutes = int((seconds_remaining % 3600) // 60)
                seconds = int(seconds_remaining % 60)
                formatted_time_remaining = f"{hours:02d}h {minutes:02d}m {seconds:02d}s"
            
            # Determine status based on days ago
            if days_ago < 7:
                status = "up to date"
                message = "Your backup is up to date"
            elif days_ago < 30:
                status = "outdated"
                message = "Your backup is outdated, consider creating a new one"
            else:
                status = "critical"
                message = "Your backup is critically outdated, please create a new one immediately"
            
            backup_status = {
                "status": status,
                "lastBackup": last_backup,
                "daysAgo": days_ago,
                "message": message,
                "canCreateBackup": can_create_backup,
                "isPremium": False
            }
            
            # If on cooldown, add the time remaining
            if not can_create_backup:
                backup_status["daysRemaining"] = days_remaining
                backup_status["formattedTimeRemaining"] = formatted_time_remaining
                backup_status["message"] = f"You can create a new backup in {days_remaining} days. Upgrade to premium for unlimited backups."
                
        except Exception as e:
            print(f"Error calculating backup status: {e}")
            backup_status = {
                "status": "unknown",
                "lastBackup": last_backup,
                "daysAgo": None,
                "message": f"Error parsing backup date: {str(e)}",
                "canCreateBackup": False,
                "isPremium": False
            }
    
    # Add cache control headers in the response
    response = jsonify(backup_status)
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

# For development/testing only - should be removed in production
@backup_bp.route('/api/backup/test/<user_id>', methods=['GET'])
def test_backup_status(user_id):
    """Test endpoint to get backup status for a specific user"""
    # This endpoint should be disabled in production
    if not current_app.debug:
        return jsonify({"error": "Endpoint not available in production"}), 403
        
    user_data = get_user_data(user_id, fields=["last_backup"])
    if not user_data:
        return jsonify({"error": "User not found"}), 404
    
    # Get last backup timestamp
    last_backup = user_data.get('last_backup')
    
    # If no backup has been made, set status to 'never'
    if not last_backup:
        backup_status = {
            "status": "never",
            "lastBackup": None,
            "daysAgo": None,
            "message": "No backup has been created yet"
        }
    else:
        backup_status = {
            "status": "up to date",
            "lastBackup": last_backup,
            "daysAgo": 3,  # Hardcoded for test
            "message": "Your backup is up to date"
        }
    
    return jsonify(backup_status)

# Clear expired cache entries periodically
def clear_expired_cache():
    """Clear expired cache entries to prevent memory leaks"""
    current_time = time.time()
    expired_keys = []
    
    for key, (data, timestamp) in user_data_cache.items():
        if current_time - timestamp > USER_CACHE_TTL:
            expired_keys.append(key)
    
    for key in expired_keys:
        del user_data_cache[key]

# Initialize Blueprint
def init_app(app):
    app.register_blueprint(backup_bp)
    
    # Create indexes on startup
    create_indexes()
    
    # Schedule cache cleanup
    @app.before_request
    def cleanup_cache():
        if random.random() < 0.05:  # 5% chance to run on each request
            clear_expired_cache()
            
    return app 