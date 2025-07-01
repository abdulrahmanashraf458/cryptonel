import json
from datetime import datetime
from flask import request
from .utils import get_db_connection, get_real_ip, get_user_id
import re

def check_security_violation(device_fingerprint, user_id):
    """
    Check for security violations based on device fingerprint and IP address
    Enhanced to detect multiple accounts from the same device even with different IPs
    """
    db = get_db_connection()
    current_ip = get_real_ip()
    
    # First, check if this device fingerprint is already associated with another user
    other_users_same_device = db.mining_activities.find({
        "activities.device_fingerprint": device_fingerprint,
        "user_id": {"$ne": user_id}
    })
    
    # Check for similar devices using partial fingerprint matching
    if len(device_fingerprint) > 8:  # Only check if fingerprint is long enough
        fingerprint_prefix = device_fingerprint[:8]  # First 8 chars for partial match
        similar_devices = db.mining_activities.find({
            "activities.device_fingerprint": {"$regex": f"^{re.escape(fingerprint_prefix)}"},
            "user_id": {"$ne": user_id}
        })
    else:
        similar_devices = []
    
    # Get all unique user IDs with the same or similar device
    other_user_list = set()
    
    # Add users with same device fingerprint
    for user in other_users_same_device:
        other_user_list.add(user.get("user_id"))
    
    # Add users with similar device fingerprints
    for user in similar_devices:
        other_user_list.add(user.get("user_id"))
    
    # Remove None values and convert to list
    other_user_list = [uid for uid in other_user_list if uid is not None]
    
    # Return violation if we found any matching users
    if other_user_list:
        return {
            "violation": True,
            "type": "device_violation",
            "users": other_user_list,
            "message": "This device is already associated with another account"
        }
    
    # Also check if the current IP has been used by too many accounts recently
    recent_activities = db.mining_activities.aggregate([
        {"$match": {"activities.ip_address": current_ip}},
        {"$group": {"_id": "$user_id"}},
        {"$count": "unique_users"}
    ])
    
    unique_users = next(recent_activities, {}).get("unique_users", 0)
    
    # If more than 2 unique users from same IP, it's suspicious
    if unique_users >= 2:
        return {
            "violation": True,
            "type": "ip_abuse",
            "message": f"This IP address has been used by {unique_users} different accounts"
        }
    
    # No violation found
    return {
        "violation": False
    }

def process_security_check(fingerprint_data):
    """
    Process full security check including device fingerprint and IP analysis
    """
    user_id = get_user_id()
    device_fingerprint = fingerprint_data.get("device_fingerprint")
    
    if not user_id or not device_fingerprint:
        return {
            "status": "error", 
            "message": "Missing user ID or device fingerprint",
            "risk_score": 100
        }
    
    # Check for device violations (even with different IPs)
    device_check = check_security_violation(device_fingerprint, user_id)
    
    if device_check.get("violation"):
        violation_type = device_check.get("type", "device_violation")
        
        # Different responses based on violation type
        if violation_type == "device_violation":
            return {
                "status": "security_violation",
                "message": "This device is already associated with another account",
                "penalty_type": "permanent_ban",
                "risk_score": 95,
                "details": {
                    "violations": ["device_reuse_across_accounts"],
                    "existing_users": device_check.get("users", []),
                    "action": "Account termination may be required"
                }
            }
        elif violation_type == "ip_abuse":
            return {
                "status": "security_violation",
                "message": device_check.get("message", "Suspicious activity detected from this IP"),
                "penalty_type": "temporary_block",
                "risk_score": 85,
                "details": {
                    "violations": ["ip_abuse"],
                    "action": "Temporary block for 24 hours"
                }
            }
    
    # Check for other security measures (VPN, proxy, etc.)
    security_checks = []
    
    # Add more security checks here as needed
    
    # If all checks passed
    if not security_checks:
        return {
            "status": "ok",
            "risk_score": 0,
            "details": {
                "message": "Security check passed",
                "checks_passed": ["device_verification", "ip_verification"]
            }
        }
    
    # If we have security checks that failed
    return {
        "status": "security_warning",
        "message": "Potential security issues detected",
        "risk_score": 50,
        "details": {
            "warnings": security_checks,
            "action": "Additional verification may be required"
        }
    }