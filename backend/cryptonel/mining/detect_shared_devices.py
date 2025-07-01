#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Shared Device Detection Tool
----------------------------
This tool detects when multiple user accounts are using the same device fingerprint,
which may indicate account sharing or other security violations.
"""

import logging
import os
import json
import argparse
from datetime import datetime
from pymongo import MongoClient

# Setup logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("shared_device_detector")

def get_db_connection():
    """
    Get database connection
    
    Returns:
        tuple: (client, mining_db) or (None, None) on failure
    """
    try:
        # Use environment variable for database URL
        mongodb_uri = os.environ.get('DATABASE_URL')
        if not mongodb_uri:
            logger.error("Database URL not available")
            return None, None
            
        # Create connection and return client and database
        client = MongoClient(mongodb_uri)
        mining_db = client["cryptonel_mining"]
        return client, mining_db
    except Exception as e:
        logger.error(f"Error connecting to database: {str(e)}")
        return None, None

def find_shared_devices(mining_db, min_users=2, detailed=False):
    """
    Find devices shared between multiple users
    
    Args:
        mining_db: MongoDB database connection
        min_users: Minimum number of users sharing a device to report
        detailed: Whether to include detailed user information
        
    Returns:
        list: Shared devices information
    """
    try:
        # Aggregate to find device fingerprints used by multiple users
        pipeline = [
            # Group by device fingerprint and collect unique user IDs
            {"$unwind": "$activities"},
            {"$group": {
                "_id": "$activities.device_fingerprint",
                "users": {"$addToSet": "$user_id"},
                "device_fingerprint": {"$first": "$activities.device_fingerprint"},
                "last_timestamp": {"$max": "$activities.timestamp"},
                "user_count": {"$sum": 1},
                "all_activities": {"$push": {
                    "user_id": "$user_id",
                    "timestamp": "$activities.timestamp",
                    "ip_address": "$activities.ip_address",
                    "browser_fingerprint": "$activities.browser_fingerprint",
                    "device_type": "$activities.device_type",
                    "user_agent": "$activities.user_agent"
                }}
            }},
            # Filter only devices used by multiple users
            {"$match": {"users": {"$size": {"$gte": min_users}}}},
            # Sort by number of users (descending)
            {"$sort": {"users": -1}}
        ]
        
        shared_devices = list(mining_db.mining_activities.aggregate(pipeline))
        
        # Format results
        results = []
        for device in shared_devices:
            # Skip if device fingerprint is empty or None
            if not device.get("device_fingerprint"):
                continue
                
            # Format device data
            device_data = {
                "device_fingerprint": device.get("device_fingerprint"),
                "user_count": len(device.get("users", [])),
                "users": device.get("users", []),
                "last_activity": device.get("last_timestamp")
            }
            
            # Add detailed information if requested
            if detailed:
                # Sort activities by timestamp
                sorted_activities = sorted(
                    device.get("all_activities", []),
                    key=lambda x: x.get("timestamp", datetime.min),
                    reverse=True
                )
                
                # Get unique activities (one per user)
                unique_user_activities = {}
                for activity in sorted_activities:
                    user_id = activity.get("user_id")
                    if user_id and user_id not in unique_user_activities:
                        unique_user_activities[user_id] = activity
                
                # Format user details
                user_details = []
                for user_id, activity in unique_user_activities.items():
                    user_details.append({
                        "user_id": user_id,
                        "last_activity": activity.get("timestamp"),
                        "ip_address": activity.get("ip_address"),
                        "browser_fingerprint": activity.get("browser_fingerprint"),
                        "device_type": activity.get("device_type"),
                        "user_agent": activity.get("user_agent")
                    })
                
                device_data["user_details"] = user_details
            
            results.append(device_data)
        
        return results
    except Exception as e:
        logger.error(f"Error finding shared devices: {str(e)}")
        return []

def find_multiple_device_users(mining_db, min_devices=5):
    """
    Find users with an unusually high number of devices
    
    Args:
        mining_db: MongoDB database connection
        min_devices: Minimum number of devices to report
        
    Returns:
        list: Users with many devices
    """
    try:
        # Aggregate to find users with many devices
        pipeline = [
            # Group by user and collect unique device fingerprints
            {"$unwind": "$activities"},
            {"$group": {
                "_id": "$user_id",
                "user_id": {"$first": "$user_id"},
                "devices": {"$addToSet": "$activities.device_fingerprint"},
                "device_count": {"$sum": 1},
                "last_activity": {"$max": "$activities.timestamp"}
            }},
            # Filter only users with many devices
            {"$match": {"devices": {"$size": {"$gte": min_devices}}}},
            # Sort by device count (descending)
            {"$sort": {"device_count": -1}}
        ]
        
        high_device_users = list(mining_db.mining_activities.aggregate(pipeline))
        
        # Format results
        results = []
        for user in high_device_users:
            # Skip if user ID is empty or None
            if not user.get("user_id"):
                continue
                
            # Format user data
            user_data = {
                "user_id": user.get("user_id"),
                "device_count": len(user.get("devices", [])),
                "devices": user.get("devices", []),
                "last_activity": user.get("last_activity")
            }
            
            results.append(user_data)
        
        return results
    except Exception as e:
        logger.error(f"Error finding users with many devices: {str(e)}")
        return []

def format_timestamp(timestamp):
    """Format timestamp for display"""
    if not timestamp:
        return "Unknown"
    
    try:
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        
        return timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")
    except Exception:
        return str(timestamp)

def generate_report(shared_devices, high_device_users, detailed=False):
    """
    Generate a formatted report of shared devices and high device users
    
    Args:
        shared_devices: List of shared devices
        high_device_users: List of users with many devices
        detailed: Whether to include detailed information
        
    Returns:
        str: Formatted report
    """
    report = []
    
    # Report header
    report.append("=" * 80)
    report.append("CRYPTONEL SECURITY REPORT - SHARED DEVICE DETECTION")
    report.append("=" * 80)
    report.append(f"Report generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"Found {len(shared_devices)} devices shared across multiple users")
    report.append(f"Found {len(high_device_users)} users with unusually high device counts")
    report.append("=" * 80)
    
    # Shared devices section
    report.append("\nDEVICES SHARED ACROSS MULTIPLE ACCOUNTS")
    report.append("-" * 80)
    
    for i, device in enumerate(shared_devices, 1):
        report.append(f"\n{i}. Device Fingerprint: {device.get('device_fingerprint')}")
        report.append(f"   User Count: {device.get('user_count')}")
        report.append(f"   Last Activity: {format_timestamp(device.get('last_activity'))}")
        report.append(f"   Users: {', '.join(device.get('users', []))}")
        
        if detailed and "user_details" in device:
            report.append("\n   User Details:")
            for user in device.get("user_details", []):
                report.append(f"   - User ID: {user.get('user_id')}")
                report.append(f"     Last Activity: {format_timestamp(user.get('last_activity'))}")
                report.append(f"     IP Address: {user.get('ip_address')}")
                report.append(f"     Device Type: {user.get('device_type')}")
                report.append(f"     User Agent: {user.get('user_agent')}")
                report.append("")
    
    # High device users section
    report.append("\nUSERS WITH UNUSUALLY HIGH DEVICE COUNTS")
    report.append("-" * 80)
    
    for i, user in enumerate(high_device_users, 1):
        report.append(f"\n{i}. User ID: {user.get('user_id')}")
        report.append(f"   Device Count: {user.get('device_count')}")
        report.append(f"   Last Activity: {format_timestamp(user.get('last_activity'))}")
        
        if detailed:
            report.append(f"   Devices: {', '.join(user.get('devices', []))}")
    
    # Final section with recommendations
    report.append("\n" + "=" * 80)
    report.append("RECOMMENDATIONS")
    report.append("-" * 80)
    report.append("1. Review shared devices and consider if they represent legitimate use cases")
    report.append("2. For suspicious cases, investigate the user accounts for policy violations")
    report.append("3. Consider implementing a policy to limit device sharing across accounts")
    report.append("4. For recurring violations, implement automated alerts or account restrictions")
    report.append("=" * 80)
    
    return "\n".join(report)

def main():
    """Main function to run the shared device detection"""
    parser = argparse.ArgumentParser(description="Detect shared devices across multiple user accounts")
    parser.add_argument("--min-users", type=int, default=2, help="Minimum users sharing a device to report")
    parser.add_argument("--min-devices", type=int, default=5, help="Minimum devices per user to report")
    parser.add_argument("--detailed", action="store_true", help="Include detailed information in report")
    parser.add_argument("--output", type=str, help="Output file for report (default: stdout)")
    parser.add_argument("--json", action="store_true", help="Output in JSON format")
    
    args = parser.parse_args()
    
    # Connect to database
    client, mining_db = get_db_connection()
    if not client or not mining_db:
        logger.error("Failed to connect to database")
        return 1
    
    try:
        # Find shared devices and high device users
        shared_devices = find_shared_devices(mining_db, args.min_users, args.detailed)
        high_device_users = find_multiple_device_users(mining_db, args.min_devices)
        
        # Generate output
        if args.json:
            output = json.dumps({
                "shared_devices": shared_devices,
                "high_device_users": high_device_users,
                "generated_at": datetime.now().isoformat(),
                "settings": {
                    "min_users": args.min_users,
                    "min_devices": args.min_devices,
                    "detailed": args.detailed
                }
            }, default=str, indent=2)
        else:
            output = generate_report(shared_devices, high_device_users, args.detailed)
        
        # Write output
        if args.output:
            with open(args.output, "w") as f:
                f.write(output)
            logger.info(f"Report written to {args.output}")
        else:
            print(output)
        
        # Log summary
        logger.info(f"Found {len(shared_devices)} devices shared across multiple users")
        logger.info(f"Found {len(high_device_users)} users with unusually high device counts")
        
        return 0
    except Exception as e:
        logger.error(f"Error running shared device detection: {str(e)}")
        return 1
    finally:
        client.close()

def block_shared_devices(mining_db, device_fingerprints=None, min_users=2, dry_run=True):
    """
    Block devices that are shared across multiple accounts
    
    Args:
        mining_db: MongoDB database connection
        device_fingerprints: List of specific device fingerprints to block
                            If None, will find and block all devices shared by min_users
        min_users: Minimum number of users sharing a device to block
        dry_run: If True, only report what would be blocked without making changes
        
    Returns:
        dict: Results of the operation
    """
    try:
        devices_to_block = []
        
        # If specific fingerprints provided, use those
        if device_fingerprints:
            devices_to_block = device_fingerprints
        else:
            # Find devices shared by multiple users
            shared_devices = find_shared_devices(mining_db, min_users, detailed=False)
            devices_to_block = [device.get('device_fingerprint') for device in shared_devices]
        
        if not devices_to_block:
            return {"status": "no_devices", "message": "No devices found to block"}
        
        # Log devices to block
        logger.info(f"Found {len(devices_to_block)} devices to block")
        
        # If dry run, just return the list
        if dry_run:
            return {
                "status": "dry_run",
                "message": f"Would block {len(devices_to_block)} devices",
                "devices": devices_to_block
            }
        
        # Add devices to blocked_devices collection
        for fingerprint in devices_to_block:
            mining_db.blocked_devices.update_one(
                {"device_fingerprint": fingerprint},
                {"$set": {
                    "device_fingerprint": fingerprint,
                    "reason": "shared_across_multiple_accounts",
                    "blocked_at": datetime.now(),
                    "status": "blocked"
                }},
                upsert=True
            )
        
        return {
            "status": "success",
            "message": f"Blocked {len(devices_to_block)} devices",
            "devices": devices_to_block
        }
    except Exception as e:
        logger.error(f"Error blocking shared devices: {str(e)}")
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    exit(main()) 