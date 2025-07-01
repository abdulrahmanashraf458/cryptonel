"""
Fingerprint storage module for advanced fingerprinting system

Handles the secure storage and retrieval of device fingerprints
"""

import logging
import time
import json
import hashlib
from datetime import datetime
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import DuplicateKeyError
import os
from dotenv import load_dotenv

# Setup logging
logger = logging.getLogger("advanced_fingerprinting.storage")

# Load environment variables
load_dotenv()

# MongoDB connection
DATABASE_URL = os.getenv("DATABASE_URL")
client = MongoClient(DATABASE_URL)

class FingerprintStorage:
    def __init__(self):
        # Database references - using the mining database
        self.client = MongoClient(DATABASE_URL)
        self.mining_db = self.client["cryptonel_mining"]
        
        # Collections
        self.fingerprints = self.mining_db["advanced_fingerprints"]
        self.fingerprint_history = self.mining_db["fingerprint_history"]
        self.user_devices = self.mining_db["user_devices"]  # Now: one document per device (no array)
        self.user_networks = self.mining_db["user_networks"]  # Now: one document per network (no array)
        
        # Maximum allowed devices per user
        self.MAX_DEVICES_PER_USER = 3
        
        # Create indexes on initialization
        self.create_indexes()

    def _generate_device_id(self, fingerprint_data):
        """
        Generate a unique device ID based on multiple hardware and software characteristics
        """
        # Collect various device identifiers
        hardware_info = fingerprint_data.get("hardware_info", {})
        screen_info = fingerprint_data.get("screen_info", {})
        
        # Create a unique string based on device characteristics
        device_string = (
            f"{hardware_info.get('cpu_cores', '')}:"
            f"{hardware_info.get('memory', '')}:"
            f"{screen_info.get('resolution', '')}:"
            f"{fingerprint_data.get('user_agent', '')}:"
            f"{fingerprint_data.get('browser_language', '')}:"
            f"{fingerprint_data.get('timezone', '')}"
        )
        
        # Generate a hash of the device string
        return hashlib.sha256(device_string.encode('utf-8')).hexdigest()

    def _find_similar_device(self, fingerprint_data, current_user_id):
        """
        Find devices with similar characteristics to detect potential multi-account abuse
        """
        hardware_info = fingerprint_data.get("hardware_info", {})
        screen_info = fingerprint_data.get("screen_info", {})
        
        # Build query for similar devices
        query = {
            "user_id": {"$ne": current_user_id},  # Exclude current user
            "$or": [
                # Check for same hardware characteristics
                {"hardware_info.cpu_cores": hardware_info.get("cpu_cores")},
                {"hardware_info.memory": hardware_info.get("memory")},
                
                # Check for same screen resolution
                {"screen_info.resolution": screen_info.get("resolution")},
                
                # Check for same WebGL vendor/renderer
                {"webgl_info.vendor": fingerprint_data.get("webgl_info", {}).get("vendor")},
                {"webgl_info.renderer": fingerprint_data.get("webgl_info", {}).get("renderer")},
                
                # Check for same audio context fingerprint
                {"audio_fingerprint": fingerprint_data.get("audio_fingerprint")},
                
                # Check for same canvas fingerprint
                {"canvas_fingerprint": fingerprint_data.get("canvas_fingerprint")}
            ]
        }
        
        # Execute query and return first match
        return self.fingerprints.find_one(query)

    def _ensure_real_ip(self, fingerprint_data):
        """
        Ensure the IP address is the real external IP, not localhost
        """
        ip_address = fingerprint_data.get("ip_address")
        
        # If IP is localhost or private, try to get real IP from headers
        if not ip_address or ip_address in ["127.0.0.1", "::1"] or ip_address.startswith(("192.168.", "10.", "172.16.")):
            headers = fingerprint_data.get("headers", {})
            
            # Check common proxy headers for real IP
            for header in ["X-Real-IP", "X-Forwarded-For", "CF-Connecting-IP", "True-Client-IP"]:
                if header in headers:
                    # Handle X-Forwarded-For which can contain multiple IPs
                    if header == "X-Forwarded-For":
                        ips = [ip.strip() for ip in headers[header].split(",")]
                        # Get the first non-internal IP
                        for ip in ips:
                            if not (ip.startswith(("192.168.", "10.", "172.16.")) or ip in ["127.0.0.1", "::1"]):
                                fingerprint_data["ip_address"] = ip
                                fingerprint_data["ip_detection_source"] = header
                                return fingerprint_data
                    else:
                        ip = headers[header].split(",")[0].strip()
                        if not (ip.startswith(("192.168.", "10.", "172.16.")) or ip in ["127.0.0.1", "::1"]):
                            fingerprint_data["ip_address"] = ip
                            fingerprint_data["ip_detection_source"] = header
                            return fingerprint_data
        
        return fingerprint_data

    def _generate_fallback_hash(self, fingerprint_data):
        """
        Generate a fallback hash when no fingerprint hash is provided
        """
        # Create a string representation of relevant data
        data_str = json.dumps({
            'user_agent': fingerprint_data.get('user_agent', ''),
            'language': fingerprint_data.get('browser_language', ''),
            'platform': fingerprint_data.get('platform', ''),
            'hardware_concurrency': fingerprint_data.get('hardware_concurrency', ''),
            'device_memory': fingerprint_data.get('device_memory', ''),
            'timezone': fingerprint_data.get('timezone', ''),
            'screen_resolution': fingerprint_data.get('screen', {}).get('resolution', ''),
            'available_screen_resolution': fingerprint_data.get('screen', {}).get('available_resolution', '')
        }, sort_keys=True)
        
        # Generate SHA-256 hash
        return hashlib.sha256(data_str.encode('utf-8')).hexdigest()

    def store_fingerprint(self, user_id, fingerprint_data):
        """
        Store a device fingerprint for a user
        
        Args:
            user_id: User ID
            fingerprint_data: Device fingerprint data
            
        Returns:
            tuple: (success, message)
        """
        try:
            # Get device identifier from multiple sources
            device_id = fingerprint_data.get("device_id") or \
                      fingerprint_data.get("device_fingerprint") or \
                      fingerprint_data.get("fingerprint_hash") or \
                      self._generate_device_id(fingerprint_data)
            
            # Store the device ID in fingerprint data
            fingerprint_data["device_id"] = device_id
            
            # Check if this device is already registered to any user
            existing_device = self.fingerprints.find_one({
                "device_id": device_id,
                "user_id": {"$ne": user_id}  # Exclude current user
            })
            
            if existing_device:
                logger.warning(f"Device {device_id} already registered to user {existing_device['user_id']}")
                return False, "This device is already registered to another account. Each device can only be used with one account."
                
            # Additional check for similar hardware/network characteristics
            similar_device = self._find_similar_device(fingerprint_data, user_id)
            if similar_device:
                logger.warning(f"Similar device found for user {user_id}: {similar_device}")
                return False, "This device appears to be already in use with another account."
            
            # Ensure we have a real IP address
            fingerprint_data = self._ensure_real_ip(fingerprint_data)
            
            # Get or generate fingerprint hash
            fingerprint_hash = fingerprint_data.get("fingerprint_hash") or self._generate_fallback_hash(fingerprint_data)
            fingerprint_data["fingerprint_hash"] = fingerprint_hash
            
            # Ensure IP address exists
            ip_address = fingerprint_data.get("ip_address", "0.0.0.0")
            fingerprint_data["ip_address"] = ip_address
            
            # Get current timestamp
            timestamp = datetime.utcnow()
            
            # Create fingerprint document
            fingerprint_doc = {
                "user_id": user_id,
                "device_id": device_id,
                "fingerprint_hash": fingerprint_hash,
                "ip_address": ip_address,
                "user_agent": fingerprint_data.get("user_agent", ""),
                "device_type": fingerprint_data.get("device_type", "unknown"),
                "browser_language": fingerprint_data.get("browser_language", ""),
                "hardware_info": fingerprint_data.get("hardware_info", {}),
                "screen_info": fingerprint_data.get("screen_info", {}),
                "webgl_info": fingerprint_data.get("webgl_info", {}),
                "canvas_fingerprint": fingerprint_data.get("canvas_fingerprint", ""),
                "audio_fingerprint": fingerprint_data.get("audio_fingerprint", ""),
                "first_seen": timestamp,
                "last_seen": timestamp,
                "usage_count": 1,
                "is_trusted": False,
                "security_flags": {
                    "vpn_detected": False,
                    "proxy_detected": False,
                    "tor_detected": False,
                    "automation_detected": False,
                    "spoofing_suspected": False
                },
                "created_at": timestamp,
                "updated_at": timestamp
            }
            
            # Store the fingerprint
            self.fingerprints.insert_one(fingerprint_doc)
            
            # Update fingerprint history
            self.update_fingerprint_history(user_id, fingerprint_hash, 
                                         fingerprint_data.get("device_type", "unknown"),
                                         ip_address, timestamp)
            
            # Update user devices
            self.update_user_devices(user_id, fingerprint_hash)
            
            # Update user networks
            self.update_user_networks(user_id, ip_address)
            
            logger.info(f"New fingerprint registered for user {user_id}")
            return True, "Fingerprint stored successfully"
            
        except Exception as e:
            logger.error(f"Error storing fingerprint: {e}")
            return False, f"Error storing fingerprint: {str(e)}"
    
    def update_fingerprint_history(self, user_id, fingerprint_hash, device_type, ip_address, timestamp):
        """Update fingerprint history"""
        try:
            history_entry = {
                "user_id": user_id,
                "fingerprint_hash": fingerprint_hash,
                "device_type": device_type,
                "ip_address": ip_address,
                "timestamp": timestamp
            }
            
            self.fingerprint_history.insert_one(history_entry)
            logger.debug(f"Updated fingerprint history for user {user_id}")
        except Exception as e:
            logger.error(f"Error updating fingerprint history: {e}")
    
    def update_user_devices(self, user_id, fingerprint_hash):
        """Update user's device list (v2 schema)"""
        # First, ensure an individual document exists
        try:
            self.user_devices.update_one(
                {"user_id": user_id, "device_hash": fingerprint_hash},
                {"$setOnInsert": {
                    "user_id": user_id,
                    "device_hash": fingerprint_hash,
                    "first_seen": datetime.utcnow(),
                    "last_seen": datetime.utcnow()
                }, "$set": {"last_seen": datetime.utcnow()}},
                upsert=True
            )
        except Exception as e:
            logger.error(f"Error updating individual user_devices for user {user_id}: {e}")

        # Legacy document is left untouched for backward compatibility – do not push new device to array

    def update_user_networks(self, user_id, ip_address):
        """Update user's network list (v2 schema)"""
        try:
            self.user_networks.update_one(
                {"user_id": user_id, "ip_address": ip_address},
                {"$setOnInsert": {
                    "user_id": user_id,
                    "ip_address": ip_address,
                    "first_seen": datetime.utcnow(),
                    "last_seen": datetime.utcnow()
                }, "$set": {"last_seen": datetime.utcnow()}},
                upsert=True
            )
        except Exception as e:
            logger.error(f"Error updating individual user_networks for user {user_id}: {e}")

        # Legacy document is left untouched

    def check_device_limit(self, user_id, new_fingerprint_hash=None):
        """Check if user has reached device limit (compatible with v2 and legacy)"""
        # Count in v2 collection
        try:
            individual_count = self.user_devices.count_documents({"user_id": user_id})
        except Exception:
            individual_count = 0

        # Legacy count
        legacy_doc = self.user_devices.find_one({"user_id": user_id})
        legacy_count = len(legacy_doc.get("devices", [])) if legacy_doc else 0

        device_count = individual_count + legacy_count

        # If this is a new device, check if adding it would exceed the limit
        if new_fingerprint_hash:
            exists_individual = self.user_devices.find_one({"user_id": user_id, "device_hash": new_fingerprint_hash}) is not None
            exists_legacy = legacy_doc and new_fingerprint_hash in legacy_doc.get("devices", [])
            if not (exists_individual or exists_legacy):
                device_count += 1

        return device_count > self.MAX_DEVICES_PER_USER, device_count
    
    def create_indexes(self):
        """Create necessary database indexes"""
        try:
            # Fingerprints collection indexes
            self.fingerprints.create_index([("user_id", 1)])
            self.fingerprints.create_index([("device_id", 1)], unique=True)
            self.fingerprints.create_index([("fingerprint_hash", 1)])
            
            # Fingerprint history indexes
            self.fingerprint_history.create_index([("user_id", 1)])
            self.fingerprint_history.create_index([("fingerprint_hash", 1)])
            self.fingerprint_history.create_index([("timestamp", -1)])
            
            # User devices indexes (compound)
            self.user_devices.create_index([("user_id", 1), ("device_hash", 1)], unique=True)
            self.user_devices.create_index([("user_id", 1)])  # non-unique for filtering
            
            # User networks indexes
            self.user_networks.create_index([("user_id", 1), ("ip_address", 1)], unique=True)
            self.user_networks.create_index([("user_id", 1)])
            
            # Add compound indexes for per-document structure
            self.user_devices.create_index([("user_id", 1), ("device_hash", 1)], unique=True)
            self.user_networks.create_index([("user_id", 1), ("ip_address", 1)], unique=True)
            
            logger.info("Created database indexes")
        except Exception as e:
            logger.error(f"Error creating indexes: {e}")

# Create a singleton instance
fingerprint_storage = FingerprintStorage()